// components/ShareModal.tsx
// PRD § 4.5 PHASE B Step 5 — last-chance review + consent + create flow,
// followed by a copy/social share surface on success.
//
// PRD § 4.5 UX polish 2/3 — QR code section removed (qrcode.react dep
// dropped); copied toast restyled from green to brand-aligned surface.

import { useEffect, useMemo, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { track } from '../utils/analytics';
import { useLang } from '../utils/LangContext';
import { getShare } from '../utils/i18n-share';
import type { ShareFeature, ShareSource } from './ShareButton';

type ModalState =
    | { kind: 'idle' }
    | { kind: 'submitting' }
    | { kind: 'done'; shareId: string; url: string }
    | { kind: 'error_sensitive'; reasons: string[]; unknownLocaleFallback: boolean }
    | { kind: 'error_quota' }
    | { kind: 'error_other'; message?: string };

interface Citation {
    title?: string | null;
    url?: string | null;
    text?: string | null;
}

interface Props {
    feature: ShareFeature;
    queryId: string;
    queryText: string;
    answerText: string;
    citations: Citation[];
    source: ShareSource;
    onClose: () => void;
}

// Locale-aware social platform ordering. zh-TW gets LINE first; everyone
// else falls back to LinkedIn / X first. The five platforms are fixed.
const SOCIAL_ORDER_BY_LANG: Record<string, ReadonlyArray<SocialKey>> = {
    'zh-TW': ['line', 'whatsapp', 'x', 'linkedin', 'facebook'],
    en: ['linkedin', 'x', 'facebook', 'whatsapp', 'line'],
};

type SocialKey = 'linkedin' | 'x' | 'facebook' | 'whatsapp' | 'line';

const SOCIAL_LABELS: Record<SocialKey, string> = {
    linkedin: 'LinkedIn',
    x: 'X',
    facebook: 'Facebook',
    whatsapp: 'WhatsApp',
    line: 'LINE',
};

function buildSocialUrl(key: SocialKey, shareUrl: string, queryText: string): string {
    const u = encodeURIComponent(shareUrl);
    const text = encodeURIComponent(queryText.slice(0, 200));
    switch (key) {
        case 'linkedin':
            return `https://www.linkedin.com/sharing/share-offsite/?url=${u}`;
        case 'x':
            return `https://twitter.com/intent/tweet?url=${u}&text=${text}`;
        case 'facebook':
            return `https://www.facebook.com/sharer/sharer.php?u=${u}`;
        case 'whatsapp':
            return `https://wa.me/?text=${text}%20${u}`;
        case 'line':
            return `https://social-plugins.line.me/lineit/share?url=${u}`;
    }
}

export default function ShareModal({
    feature,
    queryId,
    queryText,
    answerText,
    citations,
    source,
    onClose,
}: Props) {
    const { getToken } = useAuth();
    const { lang } = useLang();
    const t = getShare(lang);

    const [state, setState] = useState<ModalState>({ kind: 'idle' });
    const [consent, setConsent] = useState(false);
    const [showCopiedToast, setShowCopiedToast] = useState(false);

    const socialOrder = useMemo<ReadonlyArray<SocialKey>>(
        () => SOCIAL_ORDER_BY_LANG[lang] ?? SOCIAL_ORDER_BY_LANG.en,
        [lang]
    );

    useEffect(() => {
        function onKey(e: KeyboardEvent) {
            if (e.key === 'Escape' && state.kind !== 'submitting') onClose();
        }
        document.addEventListener('keydown', onKey);
        return () => document.removeEventListener('keydown', onKey);
    }, [state.kind, onClose]);

    async function handleConfirm() {
        setState({ kind: 'submitting' });
        try {
            const token = await getToken();
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/share/create`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({
                    query_id: queryId,
                    query_text: queryText,
                    answer_text: answerText,
                    citations,
                    locale: lang,
                }),
            });

            if (res.status === 201 || res.status === 200) {
                const data = await res.json();
                setState({ kind: 'done', shareId: data.share_id, url: data.url });
                track('share_link_generated', {
                    feature,
                    source,
                    query_id: queryId,
                    share_id: data.share_id,
                    locale: lang,
                    created: data.created !== false,
                });
                return;
            }

            if (res.status === 422) {
                const data = await res.json().catch(() => ({}));
                // 422 now has TWO senders. The PHI/sensitive-content block sends
                // `type: 'share_sensitive_blocked'`; FastAPI's request-validation
                // 422 (added 2026-08-10 when ShareCreateRequest.citations became a
                // typed, bounded list) sends `detail` and no `type`. Without this
                // discriminator a malformed payload would render the "sensitive
                // content" copy, telling the user something false about their data.
                if (data?.type === 'share_sensitive_blocked') {
                    setState({
                        kind: 'error_sensitive',
                        reasons: Array.isArray(data.reasons) ? data.reasons : [],
                        unknownLocaleFallback: Boolean(data.unknown_locale_fallback),
                    });
                } else {
                    setState({ kind: 'error_other', message: t.modalGenericError });
                }
                return;
            }
            if (res.status === 429) {
                setState({ kind: 'error_quota' });
                return;
            }
            if (res.status === 403) {
                // Anonymous block — should be unreachable because ShareButton gates this.
                setState({ kind: 'error_other', message: t.modalGenericError });
                return;
            }
            setState({ kind: 'error_other' });
        } catch (err) {
            setState({ kind: 'error_other' });
        }
    }

    async function handleCopy(url: string) {
        try {
            await navigator.clipboard.writeText(url);
            setShowCopiedToast(true);
            setTimeout(() => setShowCopiedToast(false), 1800);
            track('share_link_copied', {
                feature,
                source,
                query_id: queryId,
                method: 'copy_button',
            });
        } catch {
            // Some browsers reject clipboard outside user gesture or insecure context.
        }
    }

    function handleSocialClick(key: SocialKey, url: string) {
        const target = buildSocialUrl(key, url, queryText);
        track('share_link_copied', {
            feature,
            source,
            query_id: queryId,
            method: `social_${key}`,
        });
        window.open(target, '_blank', 'noopener,noreferrer');
    }

    const dismissable = state.kind !== 'submitting';

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            style={{ background: 'rgba(0,0,0,0.7)' }}
            onClick={() => { if (dismissable) onClose(); }}
        >
            <div
                role="dialog"
                aria-modal="true"
                className="relative w-full max-w-lg rounded-2xl p-6 bg-bg-2 border border-text/12"
                onClick={e => e.stopPropagation()}
            >
                {state.kind !== 'done' ? (
                    <PreShareView
                        t={t}
                        state={state}
                        consent={consent}
                        onConsentChange={setConsent}
                        queryText={queryText}
                        onConfirm={handleConfirm}
                        onClose={onClose}
                    />
                ) : (
                    <PostShareView
                        t={t}
                        url={state.url}
                        queryText={queryText}
                        socialOrder={socialOrder}
                        onCopy={handleCopy}
                        onSocialClick={handleSocialClick}
                        onClose={onClose}
                        showCopiedToast={showCopiedToast}
                    />
                )}
            </div>
        </div>
    );
}

interface PreShareViewProps {
    t: ReturnType<typeof getShare>;
    state: ModalState;
    consent: boolean;
    onConsentChange: (v: boolean) => void;
    queryText: string;
    onConfirm: () => void;
    onClose: () => void;
}

function PreShareView({ t, state, consent, onConsentChange, queryText, onConfirm, onClose }: PreShareViewProps) {
    const submitting = state.kind === 'submitting';

    return (
        <>
            <h2 className="text-lg font-semibold text-text">{t.modalTitle}</h2>
            <p className="mt-3 text-sm text-text/70">{t.modalWarning}</p>

            <div className="mt-4 rounded-lg p-3 max-h-32 overflow-auto text-sm whitespace-pre-wrap bg-text/6 text-text/85">
                {queryText}
            </div>

            {state.kind === 'error_sensitive' && (
                <div
                    className="mt-3 rounded-lg p-3 text-sm"
                    style={{ background: 'rgb(var(--color-danger) / 0.10)', border: '1px solid rgb(var(--color-danger) / 0.4)', color: 'rgb(var(--color-danger-soft))' }}
                >
                    <p className="font-medium">{t.modalSensitiveBlocked}</p>
                    {state.reasons.length > 0 && (
                        <ul className="mt-2 list-disc list-inside text-xs opacity-90">
                            {state.reasons.map((r, i) => <li key={i}>{r}</li>)}
                        </ul>
                    )}
                    {state.unknownLocaleFallback && (
                        <p className="mt-2 text-xs opacity-90">{t.modalGenericWarning}</p>
                    )}
                </div>
            )}
            {state.kind === 'error_quota' && (
                <div
                    className="mt-3 rounded-lg p-3 text-sm"
                    style={{ background: 'rgb(var(--color-warning) / 0.10)', border: '1px solid rgb(var(--color-warning) / 0.4)', color: 'rgb(var(--color-warning))' }}
                >
                    {t.modalQuotaBlocked}
                </div>
            )}
            {state.kind === 'error_other' && (
                <div
                    className="mt-3 rounded-lg p-3 text-sm"
                    style={{ background: 'rgb(var(--color-danger) / 0.10)', border: '1px solid rgb(var(--color-danger) / 0.4)', color: 'rgb(var(--color-danger-soft))' }}
                >
                    {state.message || t.modalGenericError}
                </div>
            )}

            <label className="mt-4 flex items-start gap-2 text-xs cursor-pointer text-text/75">
                <input
                    type="checkbox"
                    checked={consent}
                    onChange={e => onConsentChange(e.target.checked)}
                    className="mt-0.5"
                    disabled={submitting}
                />
                <span>{t.modalConsentCheckbox}</span>
            </label>

            <div className="mt-5 flex justify-end gap-2">
                <button
                    type="button"
                    onClick={onClose}
                    disabled={submitting}
                    className="px-4 py-2 text-sm font-medium rounded-lg transition-colors disabled:opacity-50 border border-text/20 text-text/85"
                >
                    {t.modalCancel}
                </button>
                <button
                    type="button"
                    onClick={onConfirm}
                    disabled={!consent || submitting}
                    className="px-4 py-2 text-sm font-medium rounded-lg transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{ background: 'rgb(var(--color-brand))', color: 'white' }}
                >
                    {submitting ? '…' : t.modalConfirm}
                </button>
            </div>
        </>
    );
}

interface PostShareViewProps {
    t: ReturnType<typeof getShare>;
    url: string;
    queryText: string;
    socialOrder: ReadonlyArray<SocialKey>;
    onCopy: (url: string) => void;
    onSocialClick: (key: SocialKey, url: string) => void;
    onClose: () => void;
    showCopiedToast: boolean;
}

function PostShareView({ t, url, socialOrder, onCopy, onSocialClick, onClose, showCopiedToast }: PostShareViewProps) {
    return (
        <>
            <h2 className="text-lg font-semibold text-text">{t.modalTitle}</h2>

            <div className="mt-4 flex items-center gap-2">
                <input
                    type="text"
                    readOnly
                    value={url}
                    onFocus={e => e.currentTarget.select()}
                    className="flex-1 px-3 py-2 text-xs rounded-lg bg-text/6 border border-text/15 text-text/90"
                />
                <button
                    type="button"
                    onClick={() => onCopy(url)}
                    className="px-3 py-2 text-xs font-medium rounded-lg transition-colors cursor-pointer"
                    style={{ background: 'rgb(var(--color-brand))', color: 'white' }}
                >
                    {t.modalCopyLink}
                </button>
            </div>

            <div className="mt-5">
                <p className="text-xs mb-2 text-text/55">{t.modalShareOn}</p>
                <div className="flex flex-wrap gap-2">
                    {socialOrder.map(key => (
                        <button
                            key={key}
                            type="button"
                            onClick={() => onSocialClick(key, url)}
                            className="px-3 py-1.5 text-xs font-medium rounded-lg transition-colors cursor-pointer bg-text/6 border border-text/15 text-text/85"
                        >
                            {SOCIAL_LABELS[key]}
                        </button>
                    ))}
                </div>
            </div>

            <div className="mt-5 flex justify-end">
                <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2 text-sm font-medium rounded-lg transition-colors border border-text/20 text-text/85"
                >
                    {t.modalCancel}
                </button>
            </div>

            {showCopiedToast && (
                <div className="absolute top-4 right-4 px-3 py-1.5 text-xs rounded-lg bg-text/8 border border-text/15 text-text">
                    {t.modalLinkCopied}
                </div>
            )}
        </>
    );
}
