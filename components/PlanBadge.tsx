// components/PlanBadge.tsx
"use client"

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useAuth, useUser } from '@clerk/nextjs';
import { useLang } from '../utils/LangContext';
import { landingContent } from '../utils/i18n';
import { ARCHIVE_MODE } from '../utils/archiveMode';

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

const ctaStyle = {
    background: 'rgba(255,107,74,0.15)',
    border: '1px solid rgba(255,107,74,0.4)',
    color: 'rgb(var(--color-brand))',
} as const;

// 2026-08-28 redesign ruling B1: the landing nav CTA is "Try Vela" -> /research
// for BOTH signed-out and signed-in-free (was a hardcoded-EN "Upgrade" opening
// the Clerk modal / UpgradeModal - the /?upgrade=true funnel still exists for
// the signed-in Dashboard, which owns its own Upgrade entry points). The PRO
// badge branch is unchanged. Label is i18n (landingContent.tryVela, 16 locales)
// - this component renders only in the landing nav (pages/index.tsx).
export default function PlanBadge() {
    const { getToken } = useAuth();
    const { isSignedIn, isLoaded } = useUser();
    const { lang } = useLang();
    const lc = landingContent[lang];
    // Synchronously read cache to avoid flash on navigation
    const [plan, setPlan] = useState<'free' | 'pro' | null>(() => {
        if (typeof window === 'undefined') return null;
        return readCache();
    });

    useEffect(() => {
        if (!isLoaded || !isSignedIn || ARCHIVE_MODE) return;  // archive UI car: no plan to read

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

    const tryVelaCta = (
        <Link href="/research">
            <button className="text-base font-semibold px-3 py-1 rounded-lg transition-all mr-2" style={ctaStyle}>
                {lc.tryVela}
            </button>
        </Link>
    );

    if (!isLoaded) return null;

    // Archive UI car U1 (2026-10-05): no plans — everyone gets "Try Vela" → /research, never a PRO badge.
    if (ARCHIVE_MODE || !isSignedIn) return tryVelaCta;

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

    return tryVelaCta;
}
