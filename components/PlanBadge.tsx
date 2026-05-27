// components/PlanBadge.tsx
"use client"

import { useEffect, useState } from 'react';
import { useAuth, useUser, SignInButton } from '@clerk/nextjs';

interface PlanBadgeProps {
    onUpgrade?: () => void;
}

const CACHE_KEY = 'vela_plan_cache';
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes

function readCache(): 'free' | 'pro' | null {
    try {
        const raw = localStorage.getItem(CACHE_KEY);
        if (!raw) return null;
        const { plan, ts } = JSON.parse(raw);
        if (Date.now() - ts > CACHE_TTL_MS) { localStorage.removeItem(CACHE_KEY); return null; }
        return plan;
    } catch { return null; }
}

function writeCache(plan: 'free' | 'pro') {
    try { localStorage.setItem(CACHE_KEY, JSON.stringify({ plan, ts: Date.now() })); } catch {}
}

export function clearPlanCache() {
    try { localStorage.removeItem(CACHE_KEY); } catch {}
    try { localStorage.removeItem('vela_status_cache'); } catch {}
}

const upgradeStyle = {
    background: 'rgba(255,107,74,0.15)',
    border: '1px solid rgba(255,107,74,0.4)',
    color: 'rgb(var(--color-brand))',
} as const;

export default function PlanBadge({ onUpgrade }: PlanBadgeProps) {
    const { getToken } = useAuth();
    const { isSignedIn, isLoaded } = useUser();
    // Synchronously read cache to avoid flash on navigation
    const [plan, setPlan] = useState<'free' | 'pro' | null>(() => {
        if (typeof window === 'undefined') return null;
        return readCache();
    });

    useEffect(() => {
        if (!isLoaded || !isSignedIn) return;

        // If cache already provided a value, only background-refresh
        const cached = readCache();
        if (cached && !plan) setPlan(cached);

        // Always fetch from API to keep cache fresh
        (async () => {
            try {
                const token = await getToken({ skipCache: true });
                if (!token) return;
                const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/user/status`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                const data = await res.json();
                const fetched: 'free' | 'pro' = data.plan_type === 'pro' ? 'pro' : 'free';
                setPlan(fetched);
                writeCache(fetched);
            } catch {}
        })();
    }, [getToken, isLoaded, isSignedIn]);

    if (!isLoaded) return null;

    // Not signed in → Upgrade button opens sign-in flow, then redirects with ?upgrade=true
    if (!isSignedIn) {
        return (
            // Intentional: Upgrade CTA uses modal + forceRedirectUrl for conversion funnel UX
            // (modal-then-auto-open-UpgradeModal). Plain /sign-in link would drop the
            // ?upgrade=true redirect chain and require a second click post-signin.
            <SignInButton mode="modal" forceRedirectUrl="/?upgrade=true">
                <button className="text-base font-semibold px-3 py-1 rounded-lg transition-all mr-2" style={upgradeStyle}>
                    Upgrade
                </button>
            </SignInButton>
        );
    }

    // Still loading plan (no cache) — hide to prevent flash
    if (plan === null) return null;

    if (plan === 'pro') {
        return (
            <span
                className="text-base font-bold px-2 py-0.5 rounded mr-2 bg-gradient-to-r from-brand to-[#fbbf24] bg-clip-text text-transparent"
                style={{ letterSpacing: '0.12em' }}
            >
                PRO
            </span>
        );
    }

    return (
        <button
            onClick={onUpgrade}
            className="text-base font-semibold px-3 py-1 rounded-lg transition-all mr-2"
            style={upgradeStyle}
        >
            Upgrade
        </button>
    );
}
