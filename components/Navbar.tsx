"use client"

import { useState, useEffect, useRef } from 'react';
import { SignedIn, SignedOut, UserButton, useAuth, useUser } from '@clerk/nextjs';
import Link from 'next/link';
import Image from 'next/image';
import { Settings } from 'lucide-react';
import UpgradeModal from './UpgradeModal';
import SettingsControls from './SettingsControls';
import ShareButton from './ShareButton';
import { useShareContext } from '../contexts/ShareContext';
import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';
import { getExtra } from '../utils/i18n-extra';
import { getShare } from '../utils/i18n-share';
import { ARCHIVE_MODE } from '../utils/archiveMode';

type ActivePage = 'research' | 'verify' | 'explain' | 'history' | 'settings';
type NavLinkPage = 'research' | 'verify' | 'explain' | 'history';
// Archive car (2026-10-05): an archive-mode build links only the live surface.
const NAV_LINK_PAGES: readonly NavLinkPage[] = ARCHIVE_MODE
    ? ['research', 'history']
    : ['research', 'verify', 'explain', 'history'];

interface NavbarProps {
    activePage?: ActivePage;
}

const STATUS_CACHE_KEY = 'vela_status_cache';
const CACHE_TTL_MS = 5 * 60 * 1000;

interface StatusCache {
    plan: 'free' | 'pro';
    credits_used_today: number;
    daily_limit: number;
    ts: number;
}

function readStatusCache(): StatusCache | null {
    try {
        const raw = localStorage.getItem(STATUS_CACHE_KEY);
        if (!raw) return null;
        const data = JSON.parse(raw);
        if (Date.now() - data.ts > CACHE_TTL_MS) { localStorage.removeItem(STATUS_CACHE_KEY); return null; }
        return data;
    } catch { return null; }
}

function writeStatusCache(plan: 'free' | 'pro', credits_used_today: number, daily_limit: number) {
    try {
        localStorage.setItem(STATUS_CACHE_KEY, JSON.stringify({ plan, credits_used_today, daily_limit, ts: Date.now() }));
    } catch {}
}

export default function Navbar({ activePage }: NavbarProps) {
    const { lang } = useLang();
    const ui = getUI(lang);
    const extra = getExtra(lang);
    const share = getShare(lang);
    const navLabels: Record<NavLinkPage, string> = {
        research: extra.navResearch,
        verify: extra.navVerify,
        explain: extra.navExplain,
        history: extra.navHistory,
    };
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);
    const [settingsOpen, setSettingsOpen] = useState(false);
    const settingsRef = useRef<HTMLDivElement>(null);
    const { getToken } = useAuth();
    const { isSignedIn, isLoaded } = useUser();
    const { shareData } = useShareContext();

    const [plan, setPlan] = useState<'free' | 'pro' | null>(() => {
        if (typeof window === 'undefined') return null;
        return readStatusCache()?.plan ?? null;
    });
    const [creditsUsed, setCreditsUsed] = useState<number>(() => {
        if (typeof window === 'undefined') return 0;
        return readStatusCache()?.credits_used_today ?? 0;
    });
    const [dailyLimit, setDailyLimit] = useState<number>(() => {
        if (typeof window === 'undefined') return 10;
        return readStatusCache()?.daily_limit ?? 10;
    });

    const fetchStatus = async () => {
        try {
            const token = await getToken({ skipCache: true });
            if (!token) return;
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/user/status`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            const data = await res.json();
            const fetched: 'free' | 'pro' = data.plan_type === 'pro' ? 'pro' : 'free';
            setPlan(fetched);
            setCreditsUsed(data.credits_used_today ?? 0);
            setDailyLimit(data.daily_limit ?? (fetched === 'pro' ? 100 : 10));
            writeStatusCache(fetched, data.credits_used_today ?? 0, data.daily_limit ?? (fetched === 'pro' ? 100 : 10));
        } catch {}
    };

    useEffect(() => {
        if (!isLoaded || !isSignedIn) return;
        fetchStatus();
        const interval = setInterval(fetchStatus, 30_000);
        return () => clearInterval(interval);
    }, [getToken, isLoaded, isSignedIn]);

    // Close settings dropdown on outside click
    useEffect(() => {
        function handleClick(e: MouseEvent) {
            if (settingsRef.current && !settingsRef.current.contains(e.target as Node)) {
                setSettingsOpen(false);
            }
        }
        if (settingsOpen) document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, [settingsOpen]);

    const [showCancelConfirm, setShowCancelConfirm] = useState(false);
    const [cancelling, setCancelling] = useState(false);
    const [cancelMessage, setCancelMessage] = useState('');

    const handleManageSubscription = async () => {
        setSettingsOpen(false);
        try {
            const token = await getToken({ skipCache: true });
            if (!token) return;
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/user/portal`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            const data = await res.json();
            if (data.url) window.open(data.url, '_blank');
        } catch {}
    };

    const handleCancelSubscription = async () => {
        setCancelling(true);
        setCancelMessage('');
        try {
            const token = await getToken({ skipCache: true });
            if (!token) return;
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/subscription/cancel`, {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.ok) {
                setCancelMessage('success');
                setTimeout(() => window.location.reload(), 2000);
            } else {
                setCancelMessage('error');
            }
        } catch {
            setCancelMessage('error');
        } finally {
            setCancelling(false);
        }
    };

    return (
        <>
            <nav className="border-b bg-app-bg border-text/7">
                <div className="container mx-auto px-4 py-3">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-8">
                            <Link href="/" className="group relative flex items-center" title="Homepage">
                                <Image src="/coral_logo.png" alt="Vela" width={60} height={60} style={{ objectFit: 'contain' }} />
                                <span className="absolute -bottom-7 left-1/2 -translate-x-1/2 text-xs bg-gray-800 text-white px-2 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
                                    Homepage
                                </span>
                            </Link>
                            <div className="hidden md:flex items-center gap-6 text-sm">
                                {NAV_LINK_PAGES.map(page => (
                                    <Link
                                        key={page}
                                        href={`/${page}`}
                                        className={activePage === page ? 'font-medium transition-colors' : 'text-text/50 hover:text-text transition-colors'}
                                        style={activePage === page ? { color: 'rgb(var(--color-brand))' } : {}}
                                    >
                                        {navLabels[page]}
                                    </Link>
                                ))}
                                {/* PRO badge — shown next to nav links for Pro users (display only) */}
                                <SignedIn>
                                    {plan === 'pro' && (
                                        <span
                                            className="text-base font-bold px-2.5 py-1"
                                            style={{ letterSpacing: '0.12em' }}
                                        >
                                            <span className="bg-gradient-to-r from-brand to-[#fbbf24] bg-clip-text text-transparent">PRO</span>
                                        </span>
                                    )}
                                </SignedIn>
                            </div>
                        </div>

                        {/* Right side: [Share (when shareData present)] [Upgrade (free only)] [⚙️] [👤] */}
                        <div className="flex items-center gap-2">
                            {/* PRD § 4.5 UX polish 2/3 — Share button moved here from
                                FeedbackBar adjacency. Visible only on md+ (matches nav
                                links) and only when the active answer page has populated
                                shareData via ShareContext. Anonymous users still see the
                                disabled-style pill (sign-up redirect on click). */}
                            {shareData && (
                                <div className="hidden md:flex">
                                    <ShareButton
                                        feature={shareData.feature}
                                        queryId={shareData.queryId}
                                        queryText={shareData.queryText}
                                        answerText={shareData.answerText}
                                        citations={shareData.citations as never}
                                        source="answer_block"
                                        variant="navbar"
                                    />
                                </div>
                            )}
                            <SignedIn>
                                {/* 1. Upgrade button — free users only (Pro badge moved to left); none in an archive build */}
                                {plan !== 'pro' && !ARCHIVE_MODE && (
                                    <button
                                        onClick={() => setShowUpgradeModal(true)}
                                        className="text-sm font-semibold px-3 py-1 rounded-lg cursor-pointer transition-all"
                                        style={{
                                            background: 'rgba(255,107,74,0.15)',
                                            border: '1px solid rgba(255,107,74,0.4)',
                                            color: 'rgb(var(--color-brand))',
                                        }}
                                        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,107,74,0.25)'; }}
                                        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,107,74,0.15)'; }}
                                    >
                                        {ui.upgrade}
                                    </button>
                                )}
                            </SignedIn>

                            {/* Settings gear — rendered for EVERYONE. Anon sees theme + language
                                (+ a Sign In row); the account rows in the dropdown are <SignedIn>-gated.
                                Unifies the gear so anon gets the same theme/language access here as
                                on the landing. */}
                                <div className="relative" ref={settingsRef}>
                                    <button
                                        onClick={() => setSettingsOpen(prev => !prev)}
                                        className="p-1.5 rounded-lg transition-all"
                                        style={{ color: settingsOpen ? 'rgb(var(--color-text))' : 'rgb(var(--color-text) / 0.45)', background: settingsOpen ? 'rgb(var(--color-text) / 0.1)' : 'transparent' }}
                                        onMouseEnter={e => { if (!settingsOpen) (e.currentTarget as HTMLElement).style.color = 'rgb(var(--color-text) / 0.8)'; }}
                                        onMouseLeave={e => { if (!settingsOpen) (e.currentTarget as HTMLElement).style.color = 'rgb(var(--color-text) / 0.45)'; }}
                                    >
                                        <Settings size={18} strokeWidth={1.8} />
                                    </button>

                                    {settingsOpen && (
                                        <div
                                            className="absolute right-0 top-full mt-2 rounded-xl shadow-2xl border border-text/10 py-2 z-50 max-h-[calc(100vh-5rem)] overflow-y-auto"
                                            style={{
                                                width: '300px',
                                                background: 'rgb(var(--color-bg-1) / 0.98)',
                                                backdropFilter: 'blur(20px)',
                                            }}
                                        >
                                            <SettingsControls />

                                            {/* Anon entry point — mirrors LandingSettingsDropdown; none in an archive build */}
                                            {!ARCHIVE_MODE && <SignedOut>
                                                <Link
                                                    href="/sign-in"
                                                    onClick={() => setSettingsOpen(false)}
                                                    className="block w-full text-left px-4 py-2.5 text-sm font-medium transition-colors hover:bg-text/5"
                                                    style={{ color: 'rgb(var(--color-brand))' }}
                                                >
                                                    {ui.signIn}
                                                </Link>
                                            </SignedOut>}

                                            {/* Account-specific rows — signed-in only (anon never sees plan/credits/shares/subscription) */}
                                            <SignedIn>
                                            {/* Plan label */}
                                            <div className="px-4 py-2 border-b border-text/7">
                                                <p className="text-xs font-semibold" style={{ color: plan === 'pro' ? '#fbbf24' : 'rgb(var(--color-text) / 0.5)' }}>
                                                    {plan === 'pro' ? ui.proPlan : ui.freePlan}
                                                </p>
                                            </div>

                                            {/* Usage today */}
                                            <div className="px-4 py-3 border-b border-text/7">
                                                <p className="text-xs mb-1 text-text/70">
                                                    {ui.todayCredits} <span className="font-medium text-text">{creditsUsed}</span> / {dailyLimit} {ui.creditsUsed}
                                                </p>
                                                <p className="text-xs mb-2 text-text/40">
                                                    Research: 3 · Verify: 1 · Explain: 2
                                                </p>
                                                <div className="w-full h-1.5 rounded-full overflow-hidden bg-text/10">
                                                    <div
                                                        className="h-full rounded-full transition-all duration-300"
                                                        style={{
                                                            width: `${Math.min((creditsUsed / dailyLimit) * 100, 100)}%`,
                                                            background: (() => {
                                                                const pct = dailyLimit > 0 ? (creditsUsed / dailyLimit) * 100 : 0;
                                                                if (pct >= 80) return 'rgb(var(--color-danger))';
                                                                if (pct >= 60) return 'rgb(var(--color-warning))';
                                                                return 'rgb(var(--color-success))';
                                                            })(),
                                                        }}
                                                    />
                                                </div>
                                            </div>

                                            {/* Settings link — opens /settings (PRD §4.5 PHASE C) */}
                                            <Link
                                                href="/settings"
                                                onClick={() => setSettingsOpen(false)}
                                                className="block w-full text-left px-4 py-2 text-sm transition-colors hover:bg-text/5 text-text/70"
                                            >
                                                {share.navbarManageSharesMenuItem}
                                            </Link>
                                            <div className="border-b border-text/7" />

                                            {/* Actions */}
                                            {plan === 'pro' ? (
                                                <>
                                                    <button
                                                        onClick={handleManageSubscription}
                                                        className="w-full text-left px-4 py-2 text-sm transition-colors hover:bg-text/5 text-text/70"
                                                    >
                                                        {ui.manageSubscription}
                                                    </button>
                                                    {!ARCHIVE_MODE && <button
                                                        onClick={() => { setSettingsOpen(false); setShowCancelConfirm(true); }}
                                                        className="w-full text-left px-4 py-2 text-sm transition-colors hover:bg-text/5"
                                                        style={{ color: 'rgb(var(--color-danger))' }}
                                                    >
                                                        {ui.cancelSubscription}
                                                    </button>}
                                                </>
                                            ) : !ARCHIVE_MODE && (
                                                <button
                                                    onClick={() => { setSettingsOpen(false); setShowUpgradeModal(true); }}
                                                    className="w-full text-left px-4 py-2 text-sm font-medium transition-colors hover:bg-text/5"
                                                    style={{ color: 'rgb(var(--color-brand))' }}
                                                >
                                                    {ui.upgradeToPro}
                                                </button>
                                            )}
                                            </SignedIn>
                                        </div>
                                    )}
                                </div>

                                {/* Clerk UserButton (avatar) — signed-in only */}
                                <SignedIn>
                                    <UserButton />
                                </SignedIn>
                            {!ARCHIVE_MODE && <SignedOut>
                                <Link href="/sign-in">
                                    <button
                                        className="px-4 py-1.5 text-sm font-medium text-text rounded-lg transition-all duration-200 border border-text/20"
                                        onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.1)')}
                                        onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'transparent')}
                                    >
                                        {ui.signIn}
                                    </button>
                                </Link>
                            </SignedOut>}
                        </div>
                    </div>
                </div>
            </nav>
            <UpgradeModal isOpen={showUpgradeModal} onClose={() => setShowUpgradeModal(false)} />

            {/* Cancel Subscription Confirmation Dialog — none in an archive build (cancel API answers 410) */}
            {showCancelConfirm && !ARCHIVE_MODE && (
                <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}>
                    <div className="w-full max-w-md mx-4 rounded-xl p-6 border border-text/10" style={{ background: 'rgb(var(--color-bg-1) / 0.98)' }}>
                        {cancelMessage === 'success' ? (
                            <div className="text-center py-4">
                                <p className="text-sm text-text/80">
                                    {ui.cancelledMsg}
                                </p>
                            </div>
                        ) : cancelMessage === 'error' ? (
                            <div className="text-center py-4 space-y-4">
                                <p className="text-sm" style={{ color: 'rgb(var(--color-danger))' }}>
                                    {ui.cancelError}
                                </p>
                                <button
                                    onClick={() => { setShowCancelConfirm(false); setCancelMessage(''); }}
                                    className="px-4 py-2 text-sm rounded-lg bg-text/10 text-text/70"
                                >
                                    {ui.closeBtn}
                                </button>
                            </div>
                        ) : (
                            <>
                                <h3 className="text-lg font-semibold text-text mb-3">{ui.cancelTitle}</h3>
                                <p className="text-sm mb-6 text-text/60">
                                    {ui.cancelConfirmMsg}
                                </p>
                                <div className="flex gap-3 justify-end">
                                    <button
                                        onClick={() => { setShowCancelConfirm(false); setCancelMessage(''); }}
                                        className="px-4 py-2 text-sm font-medium rounded-lg transition-colors bg-text/10 text-text/80"
                                    >
                                        {ui.keepPro}
                                    </button>
                                    <button
                                        onClick={handleCancelSubscription}
                                        disabled={cancelling}
                                        className="px-4 py-2 text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
                                        style={{ background: 'rgb(var(--color-danger) / 0.15)', border: '1px solid rgb(var(--color-danger) / 0.3)', color: 'rgb(var(--color-danger))' }}
                                    >
                                        {cancelling ? ui.cancellingBtn : ui.cancelSubscription}
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            )}
        </>
    );
}
