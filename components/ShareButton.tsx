// components/ShareButton.tsx
// PRD § 4.5 PHASE B Step 4 — entry point for the public Share Answer flow.
// Anonymous users see a disabled button; clicking it surfaces the same
// AnonymousUpgradeCTA quota_hit modal pattern used elsewhere in the app
// (the CTA's signup path is the conversion goal).

import { useState } from 'react';
import { useUser } from '@clerk/nextjs';
import { useRouter } from 'next/router';
import { track } from '../utils/analytics';
import { useLang } from '../utils/LangContext';
import { getShare } from '../utils/i18n-share';
import ShareModal from './ShareModal';

export type ShareSource = 'answer_block' | 'history';
export type ShareFeature = 'research' | 'verify' | 'explain';

interface Citation {
    title?: string | null;
    url?: string | null;
    text?: string | null;
}

interface Props {
    feature: ShareFeature;
    queryId: string | null | undefined;
    queryText: string;
    answerText: string;
    citations?: Citation[];
    source: ShareSource;
}

export default function ShareButton({
    feature,
    queryId,
    queryText,
    answerText,
    citations,
    source,
}: Props) {
    const { isSignedIn } = useUser();
    const router = useRouter();
    const { lang } = useLang();
    const t = getShare(lang);
    const [open, setOpen] = useState(false);

    const disabled = !queryId || !queryText || !answerText;

    if (!isSignedIn) {
        // Disabled-style button. On click, route to /sign-up — matches the
        // primary conversion path of AnonymousUpgradeCTA without needing
        // to render a full modal in-place (we don't have a 'share_locked'
        // CTA trigger in i18n-anonymous.ts, so the simplest correct
        // behavior is to send the user straight to sign-up).
        return (
            <button
                type="button"
                title={t.buttonTooltipAnon}
                onClick={() => {
                    track('share_modal_opened', {
                        feature,
                        source,
                        gated: true,
                        gate_reason: 'anonymous',
                    });
                    router.push('/sign-up');
                }}
                className="inline-flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors cursor-pointer"
                style={{
                    background: 'rgba(255,255,255,0.06)',
                    border: '1px solid rgba(255,255,255,0.15)',
                    color: 'rgba(255,255,255,0.45)',
                }}
            >
                <ShareIcon />
                {t.buttonDisabledAnon}
            </button>
        );
    }

    return (
        <>
            <button
                type="button"
                disabled={disabled}
                onClick={() => {
                    track('share_modal_opened', {
                        feature,
                        source,
                        query_id: queryId,
                    });
                    setOpen(true);
                }}
                className="inline-flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-lg transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                style={{
                    background: 'rgba(255,255,255,0.06)',
                    border: '1px solid rgba(255,255,255,0.15)',
                    color: 'rgba(255,255,255,0.55)',
                }}
                onMouseEnter={e => {
                    if (disabled) return;
                    (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.12)';
                    (e.currentTarget as HTMLElement).style.color = 'white';
                }}
                onMouseLeave={e => {
                    (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.06)';
                    (e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,0.55)';
                }}
            >
                <ShareIcon />
                {t.buttonLabel}
            </button>

            {open && (
                <ShareModal
                    feature={feature}
                    queryId={queryId as string}
                    queryText={queryText}
                    answerText={answerText}
                    citations={citations ?? []}
                    source={source}
                    onClose={() => setOpen(false)}
                />
            )}
        </>
    );
}

function ShareIcon() {
    return (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="18" cy="5" r="3" />
            <circle cx="6" cy="12" r="3" />
            <circle cx="18" cy="19" r="3" />
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
        </svg>
    );
}
