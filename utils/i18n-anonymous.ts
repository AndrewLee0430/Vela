// utils/i18n-anonymous.ts — Round 3 Anonymous upgrade CTA strings.
// Self-contained per PRD 2.8 Round 3: avoids polluting utils/i18n-ui.ts
// with 11 keys × 16 languages. Phase 1A mop-up replaces the EN reference
// per language with a concrete translation block.

import type { LangCode } from './i18n';

export interface AnonymousCtaStrings {
    thirdQueryTitle: string;
    thirdQueryBody: string;
    thirdQueryDismiss: string;

    quotaHitTitle: string;
    quotaHitBody: string;
    quotaHitSignup: string;
    quotaHitTomorrow: string;
    quotaHitPro: string;

    explainLockedTitle: string;
    explainLockedBody: string;
    explainLockedSignup: string;
}

const EN: AnonymousCtaStrings = {
    thirdQueryTitle: 'Enjoying Vela?',
    thirdQueryBody: 'Create a free account to save your history, increase your daily limit, and unlock Explain.',
    thirdQueryDismiss: 'Maybe later',

    quotaHitTitle: 'You\u2019ve reached today\u2019s free limit',
    quotaHitBody: 'You\u2019ve used {used} of {limit} free queries today. Sign up to keep going, come back tomorrow, or upgrade to Pro for up to 100 per day.',
    quotaHitSignup: 'Sign up free',
    quotaHitTomorrow: 'Continue tomorrow',
    quotaHitPro: 'Go Pro \u2014 $9.99 / mo',

    explainLockedTitle: 'Explain is free \u2014 just sign up',
    explainLockedBody: 'Understanding your lab results and medical reports requires a free Vela account. No identity check, no real name required.',
    explainLockedSignup: 'Sign up free',
};

// All non-EN languages currently fall back to EN. Phase 1A mop-up replaces
// each entry with a translated AnonymousCtaStrings block.
const translations: Record<LangCode, AnonymousCtaStrings> = {
    en: EN,
    'zh-TW': EN,
    'zh-CN': EN,
    ja: EN,
    ko: EN,
    es: EN,
    fr: EN,
    de: EN,
    it: EN,
    pt: EN,
    th: EN,
    ar: EN,
    hi: EN,
    bn: EN,
    he: EN,
    vi: EN,
};

export function getAnonymousCta(lang: LangCode): AnonymousCtaStrings {
    return translations[lang] ?? EN;
}
