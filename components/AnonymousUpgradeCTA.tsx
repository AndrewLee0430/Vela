// components/AnonymousUpgradeCTA.tsx
// Round 3 — Decision 001 v0.4 § 3.2 / § 2 acceptance #5.
// Three render modes driven by `trigger`:
//   - third_query   → dismissible inline banner below the answer
//   - explain_locked → full-area card replacing the form
//   - quota_hit     → modal with THREE equal-weight buttons (signup / tomorrow / pro).
// The "Continue tomorrow" button MUST be visually equal to the other two per
// privacy-first narrative requirement (not a text link, not a footer).

import { useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import { track } from '../utils/analytics';
import { useLang } from '../utils/LangContext';
import { getAnonymousCta } from '../utils/i18n-anonymous';

export type AnonymousCtaTrigger = 'third_query' | 'quota_hit' | 'explain_locked';

interface QuotaDetails {
    feature: 'research' | 'verify';
    used: number;
    limit: number;
}

interface Props {
    trigger: AnonymousCtaTrigger;
    onDismiss?: () => void;          // third_query + quota_hit ("Continue tomorrow")
    quotaDetails?: QuotaDetails;     // quota_hit only
}

export default function AnonymousUpgradeCTA({ trigger, onDismiss, quotaDetails }: Props) {
    const router = useRouter();
    const { lang } = useLang();
    const cta = getAnonymousCta(lang);
    const firedRef = useRef(false);

    useEffect(() => {
        if (firedRef.current) return;
        firedRef.current = true;
        const payload: Record<string, unknown> = { trigger };
        if (trigger === 'quota_hit' && quotaDetails) {
            payload.feature = quotaDetails.feature;
            payload.used = quotaDetails.used;
            payload.limit = quotaDetails.limit;
        }
        track('anonymous_cta_shown', payload);
    }, [trigger, quotaDetails]);

    const handleSignup = () => {
        track('anonymous_cta_clicked', { trigger, action: 'signup' });
        router.push('/sign-up');
    };

    const handleTomorrow = () => {
        track('anonymous_cta_clicked', { trigger, action: 'dismiss_tomorrow' });
        onDismiss?.();
    };

    const handlePro = () => {
        track('anonymous_cta_clicked', { trigger, action: 'upgrade_pro' });
        router.push('/pricing');
    };

    const handleDismiss = () => {
        track('anonymous_cta_clicked', { trigger, action: 'dismiss' });
        onDismiss?.();
    };

    // ── third_query: dismissible inline banner ──
    if (trigger === 'third_query') {
        return (
            <div
                className="mt-4 flex items-start gap-3 p-4 rounded-xl"
                style={{ background: 'rgba(255,142,110,0.08)', border: '1px solid rgba(255,142,110,0.3)' }}
            >
                <div className="flex-1">
                    <p className="text-sm font-semibold" style={{ color: '#ff8e6e' }}>
                        {cta.thirdQueryTitle}
                    </p>
                    <p className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.7)' }}>
                        {cta.thirdQueryBody}
                    </p>
                    <div className="mt-3 flex gap-2">
                        <button
                            onClick={handleSignup}
                            className="px-4 py-1.5 text-xs font-medium rounded-lg transition-opacity"
                            style={{ background: '#ff8e6e', color: 'white' }}
                        >
                            {cta.quotaHitSignup}
                        </button>
                        <button
                            onClick={handleDismiss}
                            className="px-4 py-1.5 text-xs font-medium rounded-lg transition-colors"
                            style={{ background: 'transparent', border: '1px solid rgba(255,255,255,0.2)', color: 'rgba(255,255,255,0.65)' }}
                        >
                            {cta.thirdQueryDismiss}
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // ── explain_locked: full-area card ──
    if (trigger === 'explain_locked') {
        return (
            <div
                className="max-w-xl mx-auto my-16 rounded-2xl p-10 text-center"
                style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.12)' }}
            >
                <h2 className="text-xl font-semibold" style={{ color: '#ffffff' }}>
                    {cta.explainLockedTitle}
                </h2>
                <p className="mt-3 text-sm" style={{ color: 'rgba(255,255,255,0.65)' }}>
                    {cta.explainLockedBody}
                </p>
                <button
                    onClick={handleSignup}
                    className="mt-6 px-6 py-2.5 text-sm font-medium rounded-lg transition-opacity"
                    style={{ background: '#ff8e6e', color: 'white' }}
                >
                    {cta.explainLockedSignup}
                </button>
            </div>
        );
    }

    // ── quota_hit: modal with three equal-weight buttons ──
    const used = quotaDetails?.used ?? 0;
    const limit = quotaDetails?.limit ?? 0;
    const body = cta.quotaHitBody.replace('{used}', String(used)).replace('{limit}', String(limit));

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
            style={{ background: 'rgba(0,0,0,0.7)' }}
        >
            <div
                className="relative w-full max-w-lg rounded-2xl p-8"
                style={{ background: '#0f2040', border: '1px solid rgba(255,255,255,0.12)' }}
            >
                <h2 className="text-lg font-semibold" style={{ color: '#ffffff' }}>
                    {cta.quotaHitTitle}
                </h2>
                <p className="mt-3 text-sm" style={{ color: 'rgba(255,255,255,0.7)' }}>
                    {body}
                </p>
                <div className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <button
                        onClick={handleSignup}
                        className="px-4 py-2.5 text-sm font-medium rounded-lg transition-opacity"
                        style={{ background: '#ff8e6e', color: 'white' }}
                    >
                        {cta.quotaHitSignup}
                    </button>
                    <button
                        onClick={handleTomorrow}
                        className="px-4 py-2.5 text-sm font-medium rounded-lg transition-colors"
                        style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.2)', color: 'rgba(255,255,255,0.9)' }}
                    >
                        {cta.quotaHitTomorrow}
                    </button>
                    <button
                        onClick={handlePro}
                        className="px-4 py-2.5 text-sm font-medium rounded-lg transition-colors"
                        style={{ background: '#2563eb', color: 'white' }}
                    >
                        {cta.quotaHitPro}
                    </button>
                </div>
            </div>
        </div>
    );
}
