"use client"

import { useState, useEffect, useRef } from 'react';
import { SignedIn, SignedOut, SignInButton, UserButton, useAuth, useUser } from '@clerk/nextjs';
import Link from 'next/link';
import Image from 'next/image';
import UpgradeModal from './UpgradeModal';

const BG = 'linear-gradient(135deg, #0a1628 0%, #0f2040 45%, #1a1035 75%, #0d1a2e 100%)';

const LINK_COLORS: Record<string, string> = {
    research: '#ff8e6e',
    verify:   '#63b3ed',
    explain:  '#68d391',
    history:  '#ffffff',
};

type ActivePage = 'research' | 'verify' | 'explain' | 'history';

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
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);
    const [menuOpen, setMenuOpen] = useState(false);
    const menuRef = useRef<HTMLDivElement>(null);
    const { getToken } = useAuth();
    const { isSignedIn, isLoaded } = useUser();

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

    // Close menu on outside click
    useEffect(() => {
        function handleClick(e: MouseEvent) {
            if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
                setMenuOpen(false);
            }
        }
        if (menuOpen) document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, [menuOpen]);

    const [showCancelConfirm, setShowCancelConfirm] = useState(false);
    const [cancelling, setCancelling] = useState(false);
    const [cancelMessage, setCancelMessage] = useState('');

    const handleManageSubscription = async () => {
        setMenuOpen(false);
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
            <nav className="border-b" style={{ background: BG, borderColor: 'rgba(255,255,255,0.07)' }}>
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
                                {(['research', 'verify', 'explain', 'history'] as const).map(page => (
                                    <Link
                                        key={page}
                                        href={`/${page}`}
                                        className={activePage === page ? 'font-medium transition-colors' : 'text-gray-400 hover:text-white transition-colors'}
                                        style={activePage === page ? { color: LINK_COLORS[page] } : {}}
                                    >
                                        {page.charAt(0).toUpperCase() + page.slice(1)}
                                    </Link>
                                ))}
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <SignedIn>
                                {/* Plan badge + menu dropdown */}
                                <div className="relative" ref={menuRef}>
                                    {plan === 'pro' ? (
                                        <button
                                            onClick={() => setMenuOpen(prev => !prev)}
                                            className="text-base font-bold px-2.5 py-1 rounded-lg cursor-pointer transition-all"
                                            style={{ letterSpacing: '0.12em', background: 'transparent' }}
                                            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.1)'; }}
                                            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                                        >
                                            <span className="bg-gradient-to-r from-[#ff8e6e] to-[#fbbf24] bg-clip-text text-transparent">PRO</span>
                                        </button>
                                    ) : plan === 'free' ? (
                                        <button
                                            onClick={() => setShowUpgradeModal(true)}
                                            className="text-sm font-semibold px-3 py-1 rounded-lg transition-all"
                                            style={{
                                                background: 'rgba(255,107,74,0.15)',
                                                border: '1px solid rgba(255,107,74,0.4)',
                                                color: '#ff8e6e',
                                            }}
                                        >
                                            Upgrade
                                        </button>
                                    ) : null}

                                    {menuOpen && (
                                        <div
                                            className="absolute right-0 top-full mt-2 w-56 rounded-xl shadow-2xl border py-2 z-50"
                                            style={{
                                                background: 'rgba(15, 23, 42, 0.98)',
                                                borderColor: 'rgba(255,255,255,0.1)',
                                                backdropFilter: 'blur(20px)',
                                            }}
                                        >
                                            {/* Usage today */}
                                            <div className="px-4 py-3 border-b" style={{ borderColor: 'rgba(255,255,255,0.07)' }}>
                                                <p className="text-xs mb-2" style={{ color: 'rgba(255,255,255,0.7)' }}>
                                                    Today: <span className="font-medium text-white">{creditsUsed}</span> / {dailyLimit} credits used
                                                </p>
                                                <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.1)' }}>
                                                    <div
                                                        className="h-full rounded-full transition-all duration-300"
                                                        style={{
                                                            width: `${Math.min((creditsUsed / dailyLimit) * 100, 100)}%`,
                                                            background: (() => {
                                                                const pct = dailyLimit > 0 ? (creditsUsed / dailyLimit) * 100 : 0;
                                                                if (pct >= 80) return '#ef4444';
                                                                if (pct >= 60) return '#f59e0b';
                                                                return '#22c55e';
                                                            })(),
                                                        }}
                                                    />
                                                </div>
                                            </div>

                                            {/* Actions */}
                                            {plan === 'pro' ? (
                                                <>
                                                    <button
                                                        onClick={handleManageSubscription}
                                                        className="w-full text-left px-4 py-2 text-sm transition-colors hover:bg-white/5"
                                                        style={{ color: 'rgba(255,255,255,0.7)' }}
                                                    >
                                                        Manage Subscription
                                                    </button>
                                                    <button
                                                        onClick={() => { setMenuOpen(false); setShowCancelConfirm(true); }}
                                                        className="w-full text-left px-4 py-2 text-sm transition-colors hover:bg-white/5"
                                                        style={{ color: '#ef4444' }}
                                                    >
                                                        Cancel Subscription
                                                    </button>
                                                </>
                                            ) : (
                                                <button
                                                    onClick={() => { setMenuOpen(false); setShowUpgradeModal(true); }}
                                                    className="w-full text-left px-4 py-2 text-sm font-medium transition-colors hover:bg-white/5"
                                                    style={{ color: '#ff8e6e' }}
                                                >
                                                    Upgrade to Pro
                                                </button>
                                            )}
                                        </div>
                                    )}
                                </div>

                                {/* Clerk UserButton */}
                                <UserButton />
                            </SignedIn>
                            <SignedOut>
                                <SignInButton mode="modal">
                                    <button
                                        className="px-4 py-1.5 text-sm font-medium text-white rounded-lg transition-all duration-200"
                                        style={{ border: '1px solid rgba(255,255,255,0.2)' }}
                                        onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.1)')}
                                        onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'transparent')}
                                    >
                                        Sign In
                                    </button>
                                </SignInButton>
                            </SignedOut>
                        </div>
                    </div>
                </div>
            </nav>
            <UpgradeModal isOpen={showUpgradeModal} onClose={() => setShowUpgradeModal(false)} />

            {/* Cancel Subscription Confirmation Dialog */}
            {showCancelConfirm && (
                <div className="fixed inset-0 z-50 flex items-center justify-center" style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}>
                    <div className="w-full max-w-md mx-4 rounded-xl p-6 border" style={{ background: 'rgba(15, 23, 42, 0.98)', borderColor: 'rgba(255,255,255,0.1)' }}>
                        {cancelMessage === 'success' ? (
                            <div className="text-center py-4">
                                <p className="text-sm" style={{ color: 'rgba(255,255,255,0.8)' }}>
                                    Subscription cancelled. You'll retain access until your billing period ends.
                                </p>
                            </div>
                        ) : cancelMessage === 'error' ? (
                            <div className="text-center py-4 space-y-4">
                                <p className="text-sm" style={{ color: '#ef4444' }}>
                                    Unable to cancel. Please contact <a href="mailto:support@an-tho.com" className="underline">support@an-tho.com</a>
                                </p>
                                <button
                                    onClick={() => { setShowCancelConfirm(false); setCancelMessage(''); }}
                                    className="px-4 py-2 text-sm rounded-lg"
                                    style={{ background: 'rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.7)' }}
                                >
                                    Close
                                </button>
                            </div>
                        ) : (
                            <>
                                <h3 className="text-lg font-semibold text-white mb-3">Cancel Subscription</h3>
                                <p className="text-sm mb-6" style={{ color: 'rgba(255,255,255,0.6)' }}>
                                    Are you sure you want to cancel your subscription? You will retain Pro access until the end of your current billing period.
                                </p>
                                <div className="flex gap-3 justify-end">
                                    <button
                                        onClick={() => { setShowCancelConfirm(false); setCancelMessage(''); }}
                                        className="px-4 py-2 text-sm font-medium rounded-lg transition-colors"
                                        style={{ background: 'rgba(255,255,255,0.1)', color: 'rgba(255,255,255,0.8)' }}
                                    >
                                        Keep Pro
                                    </button>
                                    <button
                                        onClick={handleCancelSubscription}
                                        disabled={cancelling}
                                        className="px-4 py-2 text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
                                        style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)', color: '#ef4444' }}
                                    >
                                        {cancelling ? 'Cancelling...' : 'Cancel Subscription'}
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
