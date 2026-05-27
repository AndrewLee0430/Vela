// components/MySharesTab.tsx
// PRD § 4.5 PHASE C — list / copy link / revoke flow for /settings page.
// Pure frontend; consumes existing PHASE B endpoints
// (GET /api/share/list, POST /api/share/{share_id}/revoke).
//
// Visibility decisions:
//   - view_count column intentionally NOT shown (PRD §4.5 需求 5
//     explicit deferral — analytics columns post-Phase 0).
//   - Revoked rows stay in the list (visually distinct) so the user
//     remembers what was previously shared, instead of disappearing
//     from history.
//
// Time formatting: Intl.RelativeTimeFormat keyed off current locale —
// no custom i18n strings, browser handles 16+ languages natively.

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { track } from '../utils/analytics';
import { useLang } from '../utils/LangContext';
import { getShare } from '../utils/i18n-share';

interface ShareRow {
    share_id: string;
    query_preview: string;
    created_at: string | null;
    is_public: boolean;
    view_count: number;
}

type LoadState =
    | { kind: 'idle' }
    | { kind: 'loading' }
    | { kind: 'loaded'; shares: ShareRow[] }
    | { kind: 'error' };

const ACCENT = '#ff8e6e';
const PUBLIC_BASE = process.env.NEXT_PUBLIC_PUBLIC_BASE_URL || (typeof window !== 'undefined' ? window.location.origin : '');

function shareUrlFor(shareId: string): string {
    return `${PUBLIC_BASE.replace(/\/$/, '')}/q/${shareId}`;
}

function relativeTime(iso: string | null, lang: string): string {
    if (!iso) return '';
    const t = Date.parse(iso);
    if (!Number.isFinite(t)) return '';
    const diffSec = Math.round((t - Date.now()) / 1000);
    const abs = Math.abs(diffSec);
    let value: number;
    let unit: Intl.RelativeTimeFormatUnit;
    if (abs < 60) { value = diffSec; unit = 'second'; }
    else if (abs < 3600) { value = Math.round(diffSec / 60); unit = 'minute'; }
    else if (abs < 86400) { value = Math.round(diffSec / 3600); unit = 'hour'; }
    else if (abs < 604800) { value = Math.round(diffSec / 86400); unit = 'day'; }
    else if (abs < 2592000) { value = Math.round(diffSec / 604800); unit = 'week'; }
    else if (abs < 31536000) { value = Math.round(diffSec / 2592000); unit = 'month'; }
    else { value = Math.round(diffSec / 31536000); unit = 'year'; }
    try {
        return new Intl.RelativeTimeFormat(lang, { numeric: 'auto' }).format(value, unit);
    } catch {
        return new Intl.RelativeTimeFormat('en', { numeric: 'auto' }).format(value, unit);
    }
}

function daysSince(iso: string | null): number | null {
    if (!iso) return null;
    const t = Date.parse(iso);
    if (!Number.isFinite(t)) return null;
    return Math.max(0, Math.round((Date.now() - t) / 86400000));
}

export default function MySharesTab() {
    const { getToken } = useAuth();
    const { lang } = useLang();
    const t = getShare(lang);

    const [state, setState] = useState<LoadState>({ kind: 'idle' });
    const [revokeTarget, setRevokeTarget] = useState<ShareRow | null>(null);
    const [revokingId, setRevokingId] = useState<string | null>(null);
    const [toast, setToast] = useState<string | null>(null);

    const fetchShares = useCallback(async () => {
        setState({ kind: 'loading' });
        try {
            const token = await getToken();
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/share/list`, {
                headers: token ? { Authorization: `Bearer ${token}` } : undefined,
            });
            if (!res.ok) {
                setState({ kind: 'error' });
                return;
            }
            const data = await res.json();
            const shares: ShareRow[] = Array.isArray(data?.shares) ? data.shares : [];
            setState({ kind: 'loaded', shares });
        } catch {
            setState({ kind: 'error' });
        }
    }, [getToken]);

    useEffect(() => {
        fetchShares();
    }, [fetchShares]);

    const showToast = useCallback((msg: string) => {
        setToast(msg);
        const id = window.setTimeout(() => setToast(null), 2000);
        return () => window.clearTimeout(id);
    }, []);

    async function handleCopy(row: ShareRow) {
        const url = shareUrlFor(row.share_id);
        try {
            await navigator.clipboard.writeText(url);
            showToast(t.modalLinkCopied);
            track('share_link_copied', {
                share_id: row.share_id,
                source: 'history',
                method: 'copy_button',
            });
        } catch {
            // clipboard unavailable (insecure context / browser block) — silent
        }
    }

    function handleAskRevoke(row: ShareRow) {
        setRevokeTarget(row);
    }

    async function handleConfirmRevoke() {
        if (!revokeTarget) return;
        const target = revokeTarget;
        setRevokeTarget(null);
        setRevokingId(target.share_id);

        // Optimistic update — flip is_public locally before the server confirms.
        setState(prev => prev.kind === 'loaded'
            ? { kind: 'loaded', shares: prev.shares.map(s => s.share_id === target.share_id ? { ...s, is_public: false } : s) }
            : prev
        );

        try {
            const token = await getToken();
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/share/${target.share_id}/revoke`, {
                method: 'POST',
                headers: token ? { Authorization: `Bearer ${token}` } : undefined,
            });
            if (!res.ok) {
                // Revert optimistic update on failure
                setState(prev => prev.kind === 'loaded'
                    ? { kind: 'loaded', shares: prev.shares.map(s => s.share_id === target.share_id ? { ...s, is_public: true } : s) }
                    : prev
                );
                showToast(t.mySharesError);
                return;
            }
            track('share_revoked', {
                share_id: target.share_id,
                days_since_created: daysSince(target.created_at),
            });
        } catch {
            setState(prev => prev.kind === 'loaded'
                ? { kind: 'loaded', shares: prev.shares.map(s => s.share_id === target.share_id ? { ...s, is_public: true } : s) }
                : prev
            );
            showToast(t.mySharesError);
        } finally {
            setRevokingId(null);
        }
    }

    const content = useMemo(() => {
        if (state.kind === 'idle' || state.kind === 'loading') {
            return (
                <p className="text-sm" style={{ color: 'rgba(255,255,255,0.55)' }}>
                    {t.mySharesLoading}
                </p>
            );
        }
        if (state.kind === 'error') {
            return (
                <div className="rounded-lg p-4" style={{ background: 'rgba(248,113,113,0.10)', border: '1px solid rgba(248,113,113,0.4)', color: '#fca5a5' }}>
                    <p className="text-sm">{t.mySharesError}</p>
                    <button
                        type="button"
                        onClick={fetchShares}
                        className="mt-3 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors cursor-pointer"
                        style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.2)', color: 'rgba(255,255,255,0.85)' }}
                    >
                        {t.mySharesRetry}
                    </button>
                </div>
            );
        }
        if (state.shares.length === 0) {
            return (
                <p className="text-sm" style={{ color: 'rgba(255,255,255,0.55)' }}>
                    {t.settingsEmpty}
                </p>
            );
        }
        return (
            <div className="flex flex-col gap-3">
                {state.shares.map(row => {
                    const isRevoked = !row.is_public;
                    const url = shareUrlFor(row.share_id);
                    return (
                        <div
                            key={row.share_id}
                            className="rounded-lg p-4"
                            style={{
                                background: 'rgba(255,255,255,0.06)',
                                border: '1px solid rgba(255,255,255,0.12)',
                                opacity: isRevoked ? 0.55 : 1,
                            }}
                        >
                            <div className="flex flex-wrap items-start justify-between gap-3">
                                <div className="min-w-0 flex-1">
                                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                                        {isRevoked && (
                                            <span
                                                className="text-xs px-2 py-0.5 rounded-full font-medium"
                                                style={{ background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.6)' }}
                                            >
                                                {t.mySharesRevokedBadge}
                                            </span>
                                        )}
                                        <span className="text-xs" style={{ color: 'rgba(255,255,255,0.5)' }}>
                                            {relativeTime(row.created_at, lang)}
                                        </span>
                                    </div>
                                    <p
                                        className="text-sm leading-snug truncate"
                                        style={{ color: 'rgba(255,255,255,0.85)' }}
                                        title={row.query_preview}
                                    >
                                        {row.query_preview}
                                    </p>
                                    <a
                                        href={url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="text-xs mt-1 inline-block hover:underline"
                                        style={{ color: 'rgba(255,255,255,0.4)' }}
                                    >
                                        {url}
                                    </a>
                                </div>
                                <div className="flex flex-shrink-0 items-center gap-2">
                                    <button
                                        type="button"
                                        onClick={() => handleCopy(row)}
                                        disabled={isRevoked}
                                        className="px-3 py-1.5 text-xs font-medium rounded-lg transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                                        style={{
                                            background: 'rgba(255,255,255,0.06)',
                                            border: '1px solid rgba(255,255,255,0.15)',
                                            color: 'rgba(255,255,255,0.85)',
                                        }}
                                    >
                                        {t.modalCopyLink}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => handleAskRevoke(row)}
                                        disabled={isRevoked || revokingId === row.share_id}
                                        className="px-3 py-1.5 text-xs font-medium rounded-lg transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                                        style={{
                                            background: 'transparent',
                                            border: '1px solid rgba(239,68,68,0.4)',
                                            color: '#f87171',
                                        }}
                                    >
                                        {revokingId === row.share_id ? t.mySharesRevoking : t.settingsRevokeButton}
                                    </button>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        );
    }, [state, lang, t, revokingId, fetchShares]);

    return (
        <>
            {content}

            {revokeTarget && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center p-4"
                    style={{ background: 'rgba(0,0,0,0.7)' }}
                    onClick={() => setRevokeTarget(null)}
                >
                    <div
                        role="dialog"
                        aria-modal="true"
                        className="w-full max-w-md rounded-2xl p-6 bg-bg-2"
                        style={{ border: '1px solid rgba(255,255,255,0.12)' }}
                        onClick={e => e.stopPropagation()}
                    >
                        <h2 className="text-base font-semibold mb-3" style={{ color: '#ffffff' }}>
                            {t.settingsRevokeButton}
                        </h2>
                        <p className="text-sm mb-5" style={{ color: 'rgba(255,255,255,0.7)' }}>
                            {t.settingsRevokeConfirm}
                        </p>
                        <div className="flex justify-end gap-2">
                            <button
                                type="button"
                                onClick={() => setRevokeTarget(null)}
                                className="px-4 py-2 text-sm font-medium rounded-lg transition-colors cursor-pointer"
                                style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: 'rgba(255,255,255,0.85)' }}
                            >
                                {t.modalCancel}
                            </button>
                            <button
                                type="button"
                                onClick={handleConfirmRevoke}
                                className="px-4 py-2 text-sm font-medium rounded-lg transition-colors cursor-pointer"
                                style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.4)', color: '#f87171' }}
                            >
                                {t.settingsRevokeButton}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {toast && (
                <div
                    className="fixed top-6 right-6 px-4 py-2 text-sm rounded-lg z-50"
                    style={{
                        background: 'rgba(255,255,255,0.08)',
                        border: '1px solid rgba(255,255,255,0.15)',
                        color: '#ffffff',
                    }}
                >
                    {toast}
                </div>
            )}
        </>
    );
}

// Suppress "ACCENT unused" warning when nothing in this file references it
// directly. Kept exported as a hint for sibling settings tabs that may
// share the brand accent.
export const _MY_SHARES_ACCENT = ACCENT;
