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
}

const upgradeStyle = {
    background: 'rgba(255,107,74,0.15)',
    border: '1px solid rgba(255,107,74,0.4)',
    color: '#ff8e6e',
} as const;

export default function PlanBadge({ onUpgrade }: PlanBadgeProps) {
    const { getToken } = useAuth();
    const { isSignedIn, isLoaded } = useUser();
    // Start optimistic: assume free so button renders immediately
    const [plan, setPlan] = useState<'free' | 'pro'>('free');

    useEffect(() => {
        if (!isLoaded || !isSignedIn) return;

        // Try cache first
        const cached = readCache();
        if (cached) { setPlan(cached); return; }

        // Fetch from API
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

    // Not signed in → Upgrade button opens sign-in flow
    if (!isSignedIn) {
        return (
            <SignInButton mode="modal">
                <button className="text-base font-semibold px-3 py-1 rounded-lg transition-all mr-2" style={upgradeStyle}>
                    Upgrade
                </button>
            </SignInButton>
        );
    }

    if (plan === 'pro') {
        return (
            <span
                className="text-base font-bold px-2 py-0.5 rounded mr-2"
                style={{ color: '#ffb347', letterSpacing: '0.12em' }}
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
