"use client"

import Head from 'next/head';
import { useUser, UserButton } from '@clerk/nextjs';
import { SignedIn, SignedOut } from '@clerk/nextjs';
import Link from 'next/link';
import Image from 'next/image';
import { ArrowUp } from 'lucide-react';
import { useRouter } from 'next/router';
import { useState, useEffect, useRef, FormEvent } from 'react';
import MobileNav from '../components/MobileNav';
import PlanBadge from '../components/PlanBadge';
import UpgradeModal from '../components/UpgradeModal';
import Navbar from '../components/Navbar';
import LandingSettingsDropdown from '../components/LandingSettingsDropdown';
import HeroComposerModeSelector, { type ComposerMode } from '../components/HeroComposerModeSelector';
import OnboardingOverlay from '../components/OnboardingOverlay';
import OnboardingWizard from '../components/OnboardingWizard';
import { readRaw } from '../utils/userContext';
import { translations, RTL_LANGS, landingContent } from '../utils/i18n';
import { useLang } from '../utils/LangContext';
import { getExtra } from '../utils/i18n-extra';
import { track } from '../utils/analytics';

// ─── Design tokens ────────────────────────────────────────────────────────────

// Multilingual Research prompts for the hero typewriter — the language mix IS the
// "ask in any language" showcase, so intentionally NOT i18n-translated (copied
// verbatim from research.tsx defaultSuggestions). Rotates regardless of UI locale.
const TYPEWRITER_PROMPTS = [
  'What are the common side effects of Metformin?',
  '小孩發燒幾度需要看醫生？',
  'ワルファリンの副作用は何ですか？',
  '심부전에서 베타차단제는 언제 사용하나요?',
  'DOACs vs Warfarin — key differences?',
];

function TypewriterPrompt() {
  const prompts = TYPEWRITER_PROMPTS;
  const [index, setIndex] = useState(0);
  const [text, setText] = useState('');
  const [deleting, setDeleting] = useState(false);
  const currentText = prompts[index];

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (!deleting && text.length < currentText.length) {
      timer = setTimeout(() => setText(currentText.slice(0, text.length + 1)), 50);
    } else if (!deleting && text.length === currentText.length) {
      timer = setTimeout(() => setDeleting(true), 2200);
    } else if (deleting && text.length > 0) {
      timer = setTimeout(() => setText(text.slice(0, -1)), 25);
    } else {
      setDeleting(false);
      setIndex((prev) => (prev + 1) % prompts.length);
    }
    return () => clearTimeout(timer);
  }, [text, deleting, index, currentText, prompts.length]);

  return (
    <span
      aria-hidden="true"
      className="pointer-events-none"
      style={{ color: 'rgb(var(--color-text) / 0.5)' }}
    >
      {text}
      <span
        style={{ background: 'rgb(var(--color-text) / 0.5)' }}
        className="inline-block w-0.5 h-5 ml-0.5 align-middle animate-pulse"
      />
    </span>
  );
}

// ─── Landing Page (unauthenticated) ──────────────────────────────────────────
function LandingPage() {
  const router = useRouter();
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [query, setQuery] = useState<string>('');
  const [isFocused, setIsFocused] = useState<boolean>(false);
  const [mode, setMode] = useState<ComposerMode>('research');
  // §3.2 onboarding wizard — show once for users who haven't completed it. Gate
  // read post-mount (SSR-safe; readRaw guards isBrowser) so SSG output is stable.
  const [showWizard, setShowWizard] = useState(false);
  useEffect(() => {
    if (!readRaw().onboarding_completed) setShowWizard(true);
  }, []);
  const inputRef = useRef<HTMLInputElement>(null);
  const { lang } = useLang();
  const t = translations[lang];
  const lc = landingContent[lang];
  const extra = getExtra(lang);
  const isRtl = RTL_LANGS.includes(lang);

  // T3: the inline composer is Research-only. Picking Verify/Explain navigates to
  // their dedicated pages on SELECT (see handleModeChange) — their input shapes
  // (drug list / lab paste) don't fit the landing's single-line box — so `mode`
  // is always 'research' here. The non-research no-op guard is defensive.
  const handleHeroSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (mode !== 'research') return;
    const trimmed = query.trim();
    if (!trimmed) return;
    router.push(`/research?q=${encodeURIComponent(trimmed)}`); // Research auto-run (Step 3)
    setQuery('');
  };

  // T3: Research stays inline; Verify/Explain jump to their dedicated pages
  // (clean navigate — no ?prefill=, since the single-line input can't represent
  // a drug list / lab report). Landing-only — this selector isn't used in-app.
  const handleModeChange = (m: ComposerMode) => {
    if (m === 'verify')  { router.push('/verify');  return; }
    if (m === 'explain') { router.push('/explain'); return; }
    setMode(m); // research
  };

  const handleChipClick = (text: string) => {
    setQuery(text);
    requestAnimationFrame(() => {
      const el = inputRef.current;
      if (!el) return;
      el.focus();
      el.setSelectionRange(text.length, text.length);
    });
  };

  return (
    <>
      <Head>
        {/* Basics */}
        <title>Vela — Privacy-first AI medical search for healthcare professionals</title>
        <meta
          key="description"
          name="description"
          content="AI medical search for healthcare professionals who work beyond English. Ask in your language, verified by PubMed, FDA, and local authorities, answered in yours. 16 languages, no identity verification required."
        />
        <meta name="robots" content="index, follow" />
        <link key="canonical" rel="canonical" href="https://vela.an-tho.com/" />

        {/* Open Graph (LinkedIn, Facebook) */}
        <meta key="og:type" property="og:type" content="website" />
        <meta key="og:site_name" property="og:site_name" content="Vela" />
        <meta key="og:url" property="og:url" content="https://vela.an-tho.com/" />
        <meta
          key="og:title"
          property="og:title"
          content="Vela — Privacy-first AI medical search"
        />
        <meta
          key="og:description"
          property="og:description"
          content="Ask in your language. Verified by official sources. Answered in yours. For healthcare professionals who work beyond English."
        />
        <meta key="og:image" property="og:image" content="https://vela.an-tho.com/og-image.png" />
        <meta key="og:image:width" property="og:image:width" content="1200" />
        <meta key="og:image:height" property="og:image:height" content="630" />

        {/* Twitter / X */}
        <meta key="twitter:card" name="twitter:card" content="summary_large_image" />
        <meta
          key="twitter:title"
          name="twitter:title"
          content="Vela — Privacy-first AI medical search"
        />
        <meta
          key="twitter:description"
          name="twitter:description"
          content="Ask in your language. Verified by official sources. Answered in yours."
        />
        <meta key="twitter:image" name="twitter:image" content="https://vela.an-tho.com/og-image.png" />

        {/* JSON-LD: SoftwareApplication */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'SoftwareApplication',
              name: 'Vela',
              applicationCategory: 'HealthApplication',
              applicationSubCategory: 'Medical Search',
              operatingSystem: 'Web',
              url: 'https://vela.an-tho.com/',
              description:
                'AI medical search for healthcare professionals who work beyond English. Privacy-first, no identity verification required.',
              offers: [
                {
                  '@type': 'Offer',
                  name: 'Free',
                  price: '0',
                  priceCurrency: 'USD',
                  description: '10 credits per day',
                },
                {
                  '@type': 'Offer',
                  name: 'Pro',
                  price: '9',
                  priceCurrency: 'USD',
                  description: 'Unlimited queries, monthly subscription',
                },
              ],
              featureList: [
                'Multi-language support (16 languages)',
                'PubMed citation verification',
                'FDA reference integration',
                'Anonymous usage without sign-up',
                'Prescription analysis for pharmacists',
              ],
            }),
          }}
        />

        {/* JSON-LD: Organization */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'Organization',
              name: 'Vela',
              url: 'https://vela.an-tho.com/',
              logo: 'https://vela.an-tho.com/coral_logo.png',
              description:
                'Privacy-first AI medical search for healthcare professionals who work beyond English.',
              contactPoint: {
                '@type': 'ContactPoint',
                email: 'support@an-tho.com',
                contactType: 'customer support',
              },
            }),
          }}
        />
      </Head>
      <div
        className="min-h-screen flex flex-col"
        dir={isRtl ? 'rtl' : undefined}
      >
        <UpgradeModal isOpen={showUpgradeModal} onClose={() => setShowUpgradeModal(false)} />

        {/* Landing hero zone — single-fold hero (nav + input + mode selector + chips
            + privacy) + footer. RESPECTS THE THEME (Stage 3.8): the `.landing-bg`
            class (styles/globals.css) renders the warm-orange radial gradient in
            light (the Stage-4 brand first-impression, default theme) and the
            standard `bg-app-bg` token gradient in dark — class-driven off the root
            <html> theme class (set by the FOUC head script in _document.tsx) so it's
            flicker-free with NO useTheme/mounted logic here. Reversed the 3.3
            forced-`.light` wrapper now that all hero elements are token-based and the
            two landing dropdowns (mode selector + settings) were tokenized to flip.
            Dual-`/`: the signed-in Dashboard is a SEPARATE component (its own
            `bg-app-bg`) and likewise respects the theme. */}
        <div className="landing-bg flex flex-col">
          {/* First viewport: nav + hero */}
          <div className="min-h-screen flex flex-col">
          {/* Top bar */}
          <nav className="flex-shrink-0 flex justify-between items-center gap-2 px-4 md:px-10 py-4">
            <Link href="/" className="flex items-center gap-2">
              <Image src="/coral_logo.png" alt="Vela" width={28} height={28} style={{ objectFit: 'contain' }} priority />
              <span className="font-semibold text-text text-lg tracking-tight">Vela</span>
            </Link>
            <div className="flex items-center gap-2">
              <LandingSettingsDropdown />
              <PlanBadge onUpgrade={() => setShowUpgradeModal(true)} />
              <SignedIn><UserButton /></SignedIn>
              <SignedOut>
                <Link href="/sign-in">
                  <button
                    className="px-5 py-2 text-sm font-medium text-text rounded-lg transition-all duration-200"
                    style={{ border: '1px solid rgb(var(--color-text) / 0.2)' }}
                    onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = 'rgb(var(--color-text) / 0.1)')}
                    onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'transparent')}
                  >
                    {t.signIn}
                  </button>
                </Link>
              </SignedOut>
            </div>
          </nav>

          {/* Hero center — lovable.dev-style minimal */}
          <div className="flex-1 flex flex-col items-center justify-center px-4 text-center pb-8">
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-semibold tracking-tight text-text mb-3 max-w-2xl">
              {lc.tagline}
            </h1>
            <p className="text-base sm:text-lg max-w-xl mb-8" style={{ color: 'rgb(var(--color-text) / 0.6)' }}>
              {lc.subtitle}
            </p>

            <form onSubmit={handleHeroSubmit} className="w-full max-w-2xl" dir="ltr">
              <div className="bg-bg-1 rounded-2xl border border-text/15 shadow-sm transition-shadow focus-within:ring-2 focus-within:ring-brand/30">
                {/* Input row — typewriter overlay scoped to THIS row only (not the control row) */}
                <div className="relative">
                  <input
                    ref={inputRef}
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onFocus={() => setIsFocused(true)}
                    onBlur={() => setIsFocused(false)}
                    className="w-full bg-transparent text-text px-5 pt-4 pb-2 text-base focus:outline-none"
                  />
                  {query === '' && !isFocused && (
                    <div
                      aria-hidden="true"
                      className="pointer-events-none absolute inset-0 px-5 pt-4 pb-2 flex items-center text-base"
                    >
                      <TypewriterPrompt />
                    </div>
                  )}
                </div>
                {/* Control row — mode selector (bottom-left) + submit (bottom-right) */}
                <div className="flex items-center justify-end gap-2 px-3 pb-3 pt-1">
                  <HeroComposerModeSelector mode={mode} onChange={handleModeChange} t={t} />
                  <button
                    type="submit"
                    aria-label="Send"
                    className="w-11 h-11 rounded-full bg-brand text-white flex items-center justify-center hover:opacity-90 transition-opacity"
                  >
                    <ArrowUp size={18} strokeWidth={2.5} />
                  </button>
                </div>
              </div>
            </form>

            {/* Suggestion chips — prefill the input, no submit */}
            <div className="mt-5 flex flex-wrap justify-center gap-2">
              {[t.heroChip1, t.heroChip2, t.heroChip3].map((chip) => (
                <button
                  key={chip}
                  type="button"
                  onClick={() => handleChipClick(chip)}
                  className="px-3 py-1.5 text-xs rounded-full border border-text/15 bg-text/6 text-text/70 cursor-pointer transition-all duration-200 hover:bg-text/12 hover:border-text/25 hover:text-text active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
                >
                  {chip}
                </button>
              ))}
            </div>

            {/* Compressed privacy line — replaces Stage 2 privacy section */}
            <p className="mt-6 text-xs flex flex-wrap justify-center gap-x-3 gap-y-1" style={{ color: 'rgb(var(--color-text) / 0.45)' }}>
              <span>· {t.privacyPromise1}</span>
              <span>· {t.privacyPromise2}</span>
              <span>· {t.privacyPromise3} ·</span>
            </p>
          </div>
          </div>

          {/* Footer — light zone */}
          <div
            className="flex-shrink-0 flex flex-col items-center gap-2 px-4 md:px-10 py-5 text-sm"
            style={{ borderTop: '1px solid rgb(var(--color-text) / 0.07)', color: 'rgb(var(--color-text) / 0.3)' }}
          >
            <div className="flex items-center gap-3">
              <span>© {new Date().getFullYear()} Vela. {t.footerCopy} · <a href="https://an-tho.com" target="_blank" rel="noopener noreferrer" className="hover:text-text transition-colors">an-tho.com</a></span>
            </div>
            <div>{t.footerDisclaimer}</div>
            <div className="flex flex-wrap justify-center gap-4 text-xs">
              <Link href="/terms" className="hover:text-text transition-colors">{extra.termsLabel}</Link>
              <Link href="/privacy" className="hover:text-text transition-colors">{extra.privacyLabel}</Link>
              <Link href="/refund" className="hover:text-text transition-colors">{extra.refundLabel}</Link>
              <Link href="/faq" className="hover:text-text transition-colors">FAQ</Link>
              <a href="mailto:support@an-tho.com" className="hover:text-text transition-colors">support@an-tho.com</a>
            </div>
          </div>
        </div>
      </div>
      {showWizard && <OnboardingWizard onClose={() => setShowWizard(false)} />}
    </>
  );
}

// ─── Dashboard (authenticated) ────────────────────────────────────────────────
function Dashboard() {
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const { lang } = useLang();
  const extra = getExtra(lang);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('upgrade') === 'true') {
      // Remove ?upgrade=true from URL without adding to history
      window.history.replaceState({}, '', '/');
      // Only show modal for free users; pro users just clear the param
      const cached = localStorage.getItem('vela_status_cache');
      const cachedPlan = cached ? JSON.parse(cached).plan : null;
      const planCache = localStorage.getItem('vela_plan_cache');
      const planCachePlan = planCache ? JSON.parse(planCache).plan : null;
      const knownPlan = cachedPlan || planCachePlan;
      if (knownPlan !== 'pro') {
        setShowUpgradeModal(true);
      }
    }
  }, []);

  const DASHBOARD_CARDS = [
    {
      href: '/research', key: 'research', label: extra.dashResearchLabel, sub: extra.dashResearchSub,
      desc: extra.dashResearchDesc,
      color: 'rgb(var(--color-text) / 0.85)',
      hoverBg: 'rgb(var(--color-text) / 0.08)', hoverBorder: 'rgb(var(--color-text) / 0.2)',
    },
    {
      href: '/verify', key: 'verify', label: extra.dashVerifyLabel, sub: extra.dashVerifySub,
      desc: extra.dashVerifyDesc,
      color: 'rgb(var(--color-text) / 0.85)',
      hoverBg: 'rgb(var(--color-text) / 0.08)', hoverBorder: 'rgb(var(--color-text) / 0.2)',
    },
    {
      href: '/explain', key: 'explain', label: extra.dashExplainLabel, sub: extra.dashExplainSub,
      desc: extra.dashExplainDesc,
      color: 'rgb(var(--color-text) / 0.85)',
      hoverBg: 'rgb(var(--color-text) / 0.08)', hoverBorder: 'rgb(var(--color-text) / 0.2)',
    },
    {
      href: '/history', key: 'history', label: extra.dashHistoryLabel, sub: extra.dashHistorySub,
      desc: extra.dashHistoryDesc,
      color: 'rgb(var(--color-text) / 0.85)',
      hoverBg: 'rgb(var(--color-text) / 0.08)', hoverBorder: 'rgb(var(--color-text) / 0.2)',
    },
  ];

  return (
    <main className="min-h-screen pb-20 md:pb-0 bg-app-bg">
      <Navbar />

      <div className="container mx-auto px-4 md:px-10 py-8 max-w-4xl">
        <h1 className="text-3xl font-bold tracking-tight mb-2 text-center text-text">{extra.dashWelcome}</h1>
        <p className="text-xl mb-8 font-medium text-center bg-gradient-to-r from-[#ff6b6b] via-[#ff8e6e] to-[#ffb347] bg-clip-text text-transparent">
          {extra.dashWhatToResearch}
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {DASHBOARD_CARDS.map((f) => (
            <Link key={f.key} href={f.href}>
              <div
                data-onboarding={f.key}
                className="h-full min-h-[140px] rounded-2xl px-7 py-6 cursor-pointer transition-all duration-300"
                style={{ background: 'rgb(var(--color-text) / 0.05)', border: '1px solid rgb(var(--color-text) / 0.1)' }}
                onMouseEnter={e => {
                  const el = e.currentTarget as HTMLElement;
                  el.style.background = f.hoverBg;
                  el.style.border = `1px solid ${f.hoverBorder}`;
                  el.style.transform = 'translateY(-4px)';
                  el.style.boxShadow = `0 12px 40px ${f.hoverBg}`;
                }}
                onMouseLeave={e => {
                  const el = e.currentTarget as HTMLElement;
                  el.style.background = 'rgb(var(--color-text) / 0.05)';
                  el.style.border = '1px solid rgb(var(--color-text) / 0.1)';
                  el.style.transform = 'translateY(0)';
                  el.style.boxShadow = 'none';
                }}
              >
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xl font-semibold text-text">{f.label}</p>
                  <span
                    className="text-sm font-medium px-3 py-1 rounded-full"
                    style={{ background: f.hoverBg, color: f.color, border: `1px solid ${f.hoverBorder}` }}
                  >
                    {f.sub}
                  </span>
                </div>
                <p className="text-base leading-relaxed" style={{ color: 'rgb(var(--color-text) / 0.45)' }}>{f.desc}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div
        className="mt-12 flex flex-col items-center gap-2 px-4 md:px-10 py-6 text-sm"
        style={{ borderTop: '1px solid rgb(var(--color-text) / 0.07)', color: 'rgb(var(--color-text) / 0.3)' }}
      >
        <div>&copy; {new Date().getFullYear()} Vela. {extra.allRightsReserved}</div>
        <div className="flex flex-wrap justify-center gap-4 text-xs">
          <Link href="/terms" className="hover:text-text transition-colors">{extra.termsLabel}</Link>
          <Link href="/privacy" className="hover:text-text transition-colors">{extra.privacyLabel}</Link>
          <Link href="/refund" className="hover:text-text transition-colors">{extra.refundLabel}</Link>
          <Link href="/faq" className="hover:text-text transition-colors">{extra.faqLabel}</Link>
          <a href="mailto:support@an-tho.com" className="hover:text-text transition-colors">support@an-tho.com</a>
        </div>
      </div>

      <UpgradeModal isOpen={showUpgradeModal} onClose={() => setShowUpgradeModal(false)} />
      <OnboardingOverlay />
      <MobileNav />
    </main>
  );
}

// ─── Entry point ──────────────────────────────────────────────────────────────
// No isLoaded gate — during SSG `isSignedIn` is undefined, so LandingPage is
// pre-rendered and crawlers / LinkedIn see the real content. After client
// hydration Clerk updates the auth state and signed-in users see the Dashboard.
function useFromShareHandler() {
  // PRD § 4.5 PHASE B Step 7 — Public Query Page CTA lands here with
  // ?from_share={share_id}. We strip the param immediately so it
  // doesn't pollute downstream PostHog `$pageview` URLs, then fire a
  // `share_to_query_clicked` event. time_on_page_sec is best-effort:
  // the Jinja2 template sets a `vela_share_render_ts` cookie on
  // every visit (see api/templates/q_public.jinja2). If the cookie
  // is present we compute the dwell time; otherwise we send null.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const params = new URLSearchParams(window.location.search);
    const shareId = params.get('from_share');
    if (!shareId) return;

    let timeOnPageSec: number | null = null;
    try {
      const match = document.cookie.match(/(?:^|;\s*)vela_share_render_ts=(\d+)/);
      if (match) {
        const renderedAt = parseInt(match[1], 10);
        if (Number.isFinite(renderedAt) && renderedAt > 0) {
          timeOnPageSec = Math.max(0, Math.round((Date.now() - renderedAt) / 1000));
        }
        // Clear the cookie regardless so a later /?from_share for a
        // different share_id doesn't reuse a stale timestamp.
        document.cookie = 'vela_share_render_ts=; path=/; max-age=0; SameSite=Lax';
      }
    } catch {
      timeOnPageSec = null;
    }

    track('share_to_query_clicked', {
      share_id: shareId,
      time_on_page_sec: timeOnPageSec,
    });

    params.delete('from_share');
    const search = params.toString();
    const newUrl = window.location.pathname + (search ? `?${search}` : '');
    window.history.replaceState({}, '', newUrl);
  }, []);
}

export default function Home() {
  const { isSignedIn } = useUser();
  useFromShareHandler();
  if (isSignedIn) return <Dashboard />;
  return <LandingPage />;
}
