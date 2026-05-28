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
import OnboardingOverlay from '../components/OnboardingOverlay';
import { translations, LANGUAGES, RTL_LANGS, landingContent, type LangCode } from '../utils/i18n';
import { useLang } from '../utils/LangContext';
import { getExtra } from '../utils/i18n-extra';
import { track } from '../utils/analytics';

// ─── Design tokens ────────────────────────────────────────────────────────────

function TypewriterPrompt() {
  const { lang } = useLang();
  const t = translations[lang];
  const prompts = [
    t.heroPlaceholderResearch,
    t.heroPlaceholderVerify,
    t.heroPlaceholderExplain,
  ];
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

  useEffect(() => {
    setText('');
    setDeleting(false);
    setIndex(0);
  }, [lang]);

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

// ─── Language Switcher ──────────────────────────────────────────────────────
function LanguageSwitcher({ lang, setLang }: { lang: LangCode; setLang: (l: LangCode) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const current = LANGUAGES.find(l => l.code === lang)!;

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <div ref={ref} className="relative inline-block">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors"
        style={{ background: 'rgb(var(--color-text) / 0.08)', border: '1px solid rgb(var(--color-text) / 0.12)', color: 'rgb(var(--color-text) / 0.5)' }}
        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = 'white'; }}
        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = 'rgb(var(--color-text) / 0.5)'; }}
      >
        <span>🌐</span>
        <span className="font-medium">{current.short}</span>
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <polyline points="6 15 12 9 18 15" />
        </svg>
      </button>

      {open && (
        <div
          className="absolute bottom-full left-1/2 mb-2 rounded-xl p-3 z-50"
          style={{
            transform: 'translateX(-50%)',
            background: '#0f1a2e',
            border: '1px solid rgb(var(--color-text) / 0.12)',
            boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
            minWidth: '320px',
          }}
        >
          <div className="grid grid-cols-2 gap-1">
            {LANGUAGES.map(l => (
              <button
                key={l.code}
                onClick={() => { setLang(l.code); setOpen(false); }}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-left transition-colors"
                style={{
                  background: l.code === lang ? 'rgb(var(--color-brand) / 0.12)' : 'transparent',
                  color: l.code === lang ? 'rgb(var(--color-brand))' : 'rgb(var(--color-text) / 0.6)',
                }}
                onMouseEnter={e => {
                  if (l.code !== lang) (e.currentTarget as HTMLElement).style.background = 'rgb(var(--color-text) / 0.06)';
                }}
                onMouseLeave={e => {
                  if (l.code !== lang) (e.currentTarget as HTMLElement).style.background = 'transparent';
                }}
              >
                <span className="font-semibold w-8 text-right" style={{ opacity: 0.6 }}>{l.short}</span>
                <span>{l.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Product Showcase Cards ─────────────────────────────────────────────────
function ProductShowcase({ t }: { t: typeof translations['en'] }) {
  const cards = [
    {
      href: '/research',
      color: 'rgb(var(--color-text) / 0.85)',
      borderColor: 'rgb(var(--color-text) / 0.15)',
      hoverBorder: 'rgb(var(--color-text) / 0.3)',
      topLabel: t.research,
      sub: t.researchSub,
      question: t.mockupResearchQuery,
      footer: `📄 ${t.mockupResearchSource}`,
      cta: t.tryResearch,
    },
    {
      href: '/verify',
      color: 'rgb(var(--color-text) / 0.85)',
      borderColor: 'rgb(var(--color-text) / 0.15)',
      hoverBorder: 'rgb(var(--color-text) / 0.3)',
      topLabel: t.verify,
      sub: t.verifySub,
      question: t.mockupVerifyDrugs,
      badge: `⚠️ ${t.mockupVerifyBadge}`,
      badgeBg: 'rgb(var(--color-danger) / 0.15)',
      badgeColor: 'rgb(var(--color-danger))',
      footer: `📄 ${t.mockupVerifySource}`,
      cta: t.tryVerify,
    },
    {
      href: '/explain',
      color: 'rgb(var(--color-text) / 0.85)',
      borderColor: 'rgb(var(--color-text) / 0.15)',
      hoverBorder: 'rgb(var(--color-text) / 0.3)',
      topLabel: t.explain,
      sub: t.explainSub,
      question: t.mockupExplainValue,
      highlight: `↑ ${t.mockupExplainStatus}`,
      highlightColor: 'rgb(var(--color-danger))',
      footer: `📄 ${t.mockupExplainSource}`,
      cta: t.tryExplain,
    },
  ];

  return (
    <div className="w-full" style={{ maxWidth: '780px' }}>
      <p className="text-center text-sm font-medium mb-5" style={{ color: 'rgb(var(--color-text) / 0.4)' }}>
        {t.seeHow}
      </p>
      <div className="flex flex-col sm:flex-row gap-3">
        {cards.map(c => (
          <Link key={c.href} href={c.href} className="flex-1">
            <div
              className="h-full rounded-xl overflow-hidden cursor-pointer transition-all duration-300"
              style={{ background: 'rgba(15,23,42,0.6)', border: `1px solid ${c.borderColor}` }}
              onMouseEnter={e => {
                const el = e.currentTarget as HTMLElement;
                el.style.transform = 'scale(1.03)';
                el.style.borderColor = c.hoverBorder;
                el.style.boxShadow = `0 8px 24px rgba(0,0,0,0.3)`;
              }}
              onMouseLeave={e => {
                const el = e.currentTarget as HTMLElement;
                el.style.transform = 'scale(1)';
                el.style.borderColor = c.borderColor;
                el.style.boxShadow = 'none';
              }}
            >
              <div className="flex h-full">
                {/* Left color bar — neutral after C3 feature-accent collapse */}
                <div className="w-1 flex-shrink-0" style={{ background: 'rgb(var(--color-text) / 0.15)' }} />
                <div className="flex flex-col p-4 gap-2.5 flex-1 min-w-0">
                  {/* Top label + source badge */}
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: 'rgb(var(--color-text) / 0.7)' }}>{c.topLabel}</span>
                    <span
                      className="text-[9px] font-medium px-1.5 py-0.5 rounded-full"
                      style={{ background: 'rgb(var(--color-text) / 0.08)', color: 'rgb(var(--color-text) / 0.45)' }}
                    >
                      {c.sub}
                    </span>
                  </div>
                  {/* Question */}
                  <p className="text-xs font-mono font-medium text-white leading-snug">{c.question}</p>
                  {/* Status badge / highlight */}
                  {'badge' in c && (
                    <span
                      className="inline-block self-start text-xs font-semibold px-2.5 py-1 rounded-md"
                      style={{ background: c.badgeBg, color: c.badgeColor }}
                    >
                      {c.badge}
                    </span>
                  )}
                  {'highlight' in c && (
                    <p className="text-xs font-mono font-semibold" style={{ color: c.highlightColor }}>
                      {c.highlight}
                    </p>
                  )}
                  {/* Footer */}
                  <p className="text-[10px] font-mono mt-auto" style={{ color: 'rgb(var(--color-text) / 0.3)' }}>
                    {c.footer}
                  </p>
                  {/* CTA */}
                  <span
                    className="text-[11px] font-semibold mt-1 inline-flex items-center gap-1 transition-all duration-200 hover:gap-2"
                    style={{ color: 'rgb(var(--color-text) / 0.85)' }}
                  >
                    {c.cta}
                  </span>
                </div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

// ─── Landing Page (unauthenticated) ──────────────────────────────────────────
function LandingPage() {
  const router = useRouter();
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [query, setQuery] = useState<string>('');
  const [isFocused, setIsFocused] = useState<boolean>(false);
  const { lang, setLang } = useLang();
  const t = translations[lang];
  const lc = landingContent[lang];
  const extra = getExtra(lang);
  const isRtl = RTL_LANGS.includes(lang);
  const arrow = isRtl ? t.arrowLeft : t.arrowRight;

  const handleHeroSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    router.push(`/research?q=${encodeURIComponent(trimmed)}`);
    setQuery('');
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

        {/* Light zone — Stage 2 first viewport (warm-orange gradient) */}
        <div
          className="light min-h-screen flex flex-col"
          style={{ background: 'linear-gradient(180deg, #ffffff 0%, #fff3ec 50%, #ffd9c4 100%)' }}
        >
          {/* Top bar */}
          <nav className="flex-shrink-0 flex justify-between items-center gap-2 px-4 md:px-10 py-4">
            <Link href="/" className="flex items-center gap-2">
              <Image src="/coral_logo.png" alt="Vela" width={28} height={28} style={{ objectFit: 'contain' }} priority />
              <span className="font-semibold text-text text-lg tracking-tight">Vela</span>
            </Link>
            <div className="flex items-center gap-2">
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
          <div className="flex-1 flex flex-col items-center justify-center px-4 text-center pb-12">
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-semibold tracking-tight text-text mb-3 max-w-2xl">
              {lc.tagline}
            </h1>
            <p className="text-base sm:text-lg max-w-xl mb-8" style={{ color: 'rgb(var(--color-text) / 0.6)' }}>
              {lc.subtitle}
            </p>

            <form onSubmit={handleHeroSubmit} className="w-full max-w-2xl" dir="ltr">
              <div className="relative">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onFocus={() => setIsFocused(true)}
                  onBlur={() => setIsFocused(false)}
                  className="w-full bg-bg-1 text-text rounded-2xl border border-text/15 shadow-sm px-5 py-4 pr-16 text-base focus:outline-none focus:ring-2 focus:ring-brand/30"
                />
                {query === '' && !isFocused && (
                  <div
                    aria-hidden="true"
                    className="pointer-events-none absolute inset-0 px-5 py-4 pr-16 flex items-center text-base"
                  >
                    <TypewriterPrompt />
                  </div>
                )}
                <button
                  type="submit"
                  aria-label="Send"
                  className="absolute right-2 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-brand text-white flex items-center justify-center hover:opacity-90 transition-opacity"
                >
                  <ArrowUp size={18} strokeWidth={2.5} />
                </button>
              </div>
            </form>

            {/* Scroll hint */}
            <p className="mt-8 text-sm" style={{ color: 'rgb(var(--color-text) / 0.5)' }}>{t.seeHow}</p>
          </div>
        </div>

        {/* Dark island — below-fold preserved at today's appearance (Step 4 redesigns) */}
        <div className="dark bg-app-bg flex flex-col">
          <div className="flex flex-col items-center px-4 md:px-10 text-center pt-12 pb-4">
            {/* CTA */}
            <div className="flex flex-wrap justify-center gap-3 my-8">
              <Link href="/research">
                <button
                  className="group px-6 py-2.5 text-white text-sm font-semibold rounded-xl transition-all duration-300 hover:scale-105 flex items-center gap-2"
                  style={{ background: 'linear-gradient(135deg, #ff6b6b, #ff8e6e)', boxShadow: '0 0 28px rgba(255,107,107,0.4)' }}
                >
                  {lc.ctaPrimary}
                  <span className="group-hover:translate-x-1 transition-transform">{arrow}</span>
                </button>
              </Link>
              <Link
                href="/pricing"
                className="text-sm font-medium rounded-full px-4 py-2 transition-all duration-200 inline-flex items-center"
                style={{ background: 'rgb(var(--color-text) / 0.08)', color: 'rgb(var(--color-text) / 0.55)', border: '1px solid rgb(var(--color-text) / 0.1)' }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgb(var(--color-text) / 0.15)'; (e.currentTarget as HTMLElement).style.color = 'white'; }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'rgb(var(--color-text) / 0.08)'; (e.currentTarget as HTMLElement).style.color = 'rgb(var(--color-text) / 0.55)'; }}
              >
                {t.seePricing} {arrow}
              </Link>
            </div>

            {/* v1.1 Value Props */}
            <div className="w-full grid grid-cols-1 md:grid-cols-3 gap-4 mb-10" style={{ maxWidth: '900px' }}>
              {[
                { label: lc.valueProp.language.label, body: lc.valueProp.language.body },
                { label: lc.valueProp.sources.label, body: lc.valueProp.sources.body },
                { label: lc.valueProp.anonymous.label, body: lc.valueProp.anonymous.body },
              ].map((vp) => (
                <div
                  key={vp.label}
                  className="rounded-2xl p-5 text-left"
                  style={{ background: 'rgb(var(--color-text) / 0.04)', border: '1px solid rgb(var(--color-text) / 0.1)' }}
                >
                  <div className="text-xs font-semibold tracking-wider mb-2" style={{ color: 'rgb(var(--color-text) / 0.5)' }}>{vp.label}</div>
                  <p className="text-sm leading-relaxed" style={{ color: 'rgb(var(--color-text) / 0.7)' }}>{vp.body}</p>
                </div>
              ))}
            </div>

            {/* Social proof */}
            <p className="text-sm mb-6" style={{ color: 'rgba(148,163,184,0.7)' }}>
              {t.socialProof}
            </p>

            {/* Product showcase */}
            <ProductShowcase t={t} />

            {/* v1.1 Privacy-first transparent definition */}
            <section className="w-full mt-14 mb-4 text-left" style={{ maxWidth: '780px' }}>
              <h2 className="text-xl font-semibold text-white mb-4 text-center">
                {t.privacyTitle}
              </h2>
              <ul className="space-y-2.5 mb-5">
                {[t.privacyPromise1, t.privacyPromise2, t.privacyPromise3].map((item) => (
                  <li key={item} className="flex items-start gap-2.5 text-sm" style={{ color: 'rgb(var(--color-text) / 0.75)' }}>
                    <span className="mt-0.5 font-bold" style={{ color: 'rgb(var(--color-success))' }} aria-hidden>✓</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
              <div className="text-center">
                <Link
                  href="/privacy"
                  className="text-sm hover:text-white transition-colors"
                  style={{ color: 'rgb(var(--color-text) / 0.55)' }}
                >
                  {t.privacyPolicyLink}
                </Link>
              </div>
            </section>
          </div>

          {/* Footer */}
          <div
            className="flex-shrink-0 flex flex-col items-center gap-2 px-4 md:px-10 py-5 text-sm"
            style={{ borderTop: '1px solid rgb(var(--color-text) / 0.07)', color: 'rgb(var(--color-text) / 0.3)' }}
          >
            <div className="flex items-center gap-3">
              <span>© {new Date().getFullYear()} Vela. {t.footerCopy} · <a href="https://an-tho.com" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">an-tho.com</a></span>
              <LanguageSwitcher lang={lang} setLang={setLang} />
            </div>
            <div>{t.footerDisclaimer}</div>
            <div className="flex flex-wrap justify-center gap-4 text-xs">
              <Link href="/terms" className="hover:text-white transition-colors">{extra.termsLabel}</Link>
              <Link href="/privacy" className="hover:text-white transition-colors">{extra.privacyLabel}</Link>
              <Link href="/refund" className="hover:text-white transition-colors">{extra.refundLabel}</Link>
              <Link href="/faq" className="hover:text-white transition-colors">FAQ</Link>
              <a href="mailto:support@an-tho.com" className="hover:text-white transition-colors">support@an-tho.com</a>
            </div>
          </div>
        </div>
      </div>
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
        <h1 className="text-3xl font-bold tracking-tight mb-2 text-center text-white">{extra.dashWelcome}</h1>
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
                  <p className="text-xl font-semibold text-white">{f.label}</p>
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
          <Link href="/terms" className="hover:text-white transition-colors">{extra.termsLabel}</Link>
          <Link href="/privacy" className="hover:text-white transition-colors">{extra.privacyLabel}</Link>
          <Link href="/refund" className="hover:text-white transition-colors">{extra.refundLabel}</Link>
          <Link href="/faq" className="hover:text-white transition-colors">{extra.faqLabel}</Link>
          <a href="mailto:support@an-tho.com" className="hover:text-white transition-colors">support@an-tho.com</a>
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
