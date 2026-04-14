"use client"

import Head from 'next/head';
import { useUser, SignInButton, UserButton } from '@clerk/nextjs';
import { SignedIn, SignedOut } from '@clerk/nextjs';
import Link from 'next/link';
import Image from 'next/image';
import { useState, useEffect, useRef } from 'react';
import MobileNav from '../components/MobileNav';
import PlanBadge from '../components/PlanBadge';
import UpgradeModal from '../components/UpgradeModal';
import Navbar from '../components/Navbar';
import OnboardingOverlay from '../components/OnboardingOverlay';
import { translations, LANGUAGES, RTL_LANGS, type LangCode } from '../utils/i18n';
import { useLang } from '../utils/LangContext';
import { getExtra } from '../utils/i18n-extra';

// ─── Design tokens ────────────────────────────────────────────────────────────
const BG = 'linear-gradient(135deg, #0a1628 0%, #0f2040 45%, #1a1035 75%, #0d1a2e 100%)';

const PROMPTS = [
  { text: 'Research Metformin interactions in renal impairment', color: '#ff8e6e' },
  { text: 'Verify Warfarin + Aspirin — is it safe?',            color: '#63b3ed' },
  { text: 'Explain my blood test results in plain language',    color: '#68d391' },
];

// ─────────────────────────────────────────────────────────────────────────────

function TypewriterPrompt() {
  const [index, setIndex] = useState(0);
  const [text, setText] = useState('');
  const [deleting, setDeleting] = useState(false);
  const current = PROMPTS[index];

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (!deleting && text.length < current.text.length) {
      timer = setTimeout(() => setText(current.text.slice(0, text.length + 1)), 50);
    } else if (!deleting && text.length === current.text.length) {
      timer = setTimeout(() => setDeleting(true), 2200);
    } else if (deleting && text.length > 0) {
      timer = setTimeout(() => setText(text.slice(0, -1)), 25);
    } else {
      setDeleting(false);
      setIndex((prev) => (prev + 1) % PROMPTS.length);
    }
    return () => clearTimeout(timer);
  }, [text, deleting, index, current.text]);

  return (
    <span style={{ color: current.color, transition: 'color 0.3s ease' }}>
      {text}
      <span
        style={{ background: current.color }}
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
        style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.12)', color: 'rgba(255,255,255,0.5)' }}
        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = 'white'; }}
        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,0.5)'; }}
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
            border: '1px solid rgba(255,255,255,0.12)',
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
                  background: l.code === lang ? 'rgba(255,142,110,0.12)' : 'transparent',
                  color: l.code === lang ? '#ff8e6e' : 'rgba(255,255,255,0.6)',
                }}
                onMouseEnter={e => {
                  if (l.code !== lang) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.06)';
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
      color: '#ff8e6e',
      borderColor: 'rgba(255,142,110,0.3)',
      hoverBorder: 'rgba(255,142,110,0.6)',
      topLabel: t.research,
      sub: t.researchSub,
      question: t.mockupResearchQuery,
      footer: `📄 ${t.mockupResearchSource}`,
      cta: t.tryResearch,
    },
    {
      href: '/verify',
      color: '#63b3ed',
      borderColor: 'rgba(99,179,237,0.3)',
      hoverBorder: 'rgba(99,179,237,0.6)',
      topLabel: t.verify,
      sub: t.verifySub,
      question: t.mockupVerifyDrugs,
      badge: `⚠️ ${t.mockupVerifyBadge}`,
      badgeBg: 'rgba(239,68,68,0.15)',
      badgeColor: '#f87171',
      footer: `📄 ${t.mockupVerifySource}`,
      cta: t.tryVerify,
    },
    {
      href: '/explain',
      color: '#4ade80',
      borderColor: 'rgba(74,222,128,0.3)',
      hoverBorder: 'rgba(74,222,128,0.6)',
      topLabel: t.explain,
      sub: t.explainSub,
      question: t.mockupExplainValue,
      highlight: `↑ ${t.mockupExplainStatus}`,
      highlightColor: '#f87171',
      footer: `📄 ${t.mockupExplainSource}`,
      cta: t.tryExplain,
    },
  ];

  return (
    <div className="w-full" style={{ maxWidth: '780px' }}>
      <p className="text-center text-sm font-medium mb-5" style={{ color: 'rgba(255,255,255,0.4)' }}>
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
                {/* Left color bar */}
                <div className="w-1 flex-shrink-0" style={{ background: c.color }} />
                <div className="flex flex-col p-4 gap-2.5 flex-1 min-w-0">
                  {/* Top label + source badge */}
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: c.color }}>{c.topLabel}</span>
                    <span
                      className="text-[9px] font-medium px-1.5 py-0.5 rounded-full"
                      style={{ background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.45)' }}
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
                  <p className="text-[10px] font-mono mt-auto" style={{ color: 'rgba(255,255,255,0.3)' }}>
                    {c.footer}
                  </p>
                  {/* CTA */}
                  <span
                    className="text-[11px] font-semibold mt-1 inline-flex items-center gap-1 transition-all duration-200 hover:gap-2"
                    style={{ color: c.color }}
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
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const { lang, setLang } = useLang();
  const t = translations[lang];
  const extra = getExtra(lang);
  const isRtl = RTL_LANGS.includes(lang);
  const arrow = isRtl ? t.arrowLeft : t.arrowRight;

  return (
    <>
      <Head>
        <title>Vela — Clinical AI for Healthcare Professionals</title>
        <meta name="description" content="Research PubMed 36M+, verify drug interactions against FDA, and explain lab results in any language." />
        <link rel="canonical" href="https://vela.an-tho.com" />
        <meta property="og:url" content="https://vela.an-tho.com" />
        <meta property="og:title" content="Vela — Clinical AI for Healthcare Professionals" />
        <meta property="og:description" content="Research PubMed 36M+, verify drug interactions against FDA, and explain lab results in any language." />
        <meta name="twitter:title" content="Vela — Clinical AI for Healthcare Professionals" />
        <meta name="twitter:description" content="Research PubMed 36M+, verify drug interactions against FDA, and explain lab results in any language." />
      </Head>
      <style>{`
        @keyframes float {
          0%   { transform: translateY(0px); }
          50%  { transform: translateY(-12px); }
          100% { transform: translateY(0px); }
        }
        .logo-float { animation: float 3.5s ease-in-out infinite; }
      `}</style>

      <div
        className="min-h-screen flex flex-col"
        style={{ background: BG }}
        dir={isRtl ? 'rtl' : undefined}
      >
        {/* Nav */}
        <nav className="flex-shrink-0 flex justify-end items-center gap-2 px-4 md:px-10 py-5">
          <PlanBadge onUpgrade={() => setShowUpgradeModal(true)} />
          <SignedIn><UserButton /></SignedIn>
          <SignedOut>
            <SignInButton mode="modal">
              <button
                className="px-5 py-2 text-sm font-medium text-white rounded-lg transition-all duration-200"
                style={{ border: '1px solid rgba(255,255,255,0.2)' }}
                onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.1)')}
                onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'transparent')}
              >
                {t.signIn}
              </button>
            </SignInButton>
          </SignedOut>
        </nav>
        <UpgradeModal isOpen={showUpgradeModal} onClose={() => setShowUpgradeModal(false)} />

        {/* Hero */}
        <div className="flex-1 flex flex-col items-center justify-start px-4 md:px-10 text-center pt-3 pb-4">
          <div className="flex flex-col items-center mb-2">
            <div className="logo-float">
              <Image src="/coral_logo.png" alt="Vela logo" width={120} height={120} style={{ objectFit: 'contain' }} priority />
            </div>
            <h1
              className="mt-1 font-black"
              style={{
                fontSize: 'clamp(3rem, 7vw, 5rem)',
                background: 'linear-gradient(90deg, #ff6b6b, #ff8e6e, #ffb347)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                letterSpacing: '0.08em',
                lineHeight: 1,
              }}
            >
              Vela
            </h1>
          </div>

          <p className="text-xl font-semibold text-white mb-1 tracking-tight">
            {t.heroTitle}
          </p>
          <p className="text-sm mb-4" style={{ color: 'rgba(255,255,255,0.35)' }}>
            ✦ {t.heroSub} &nbsp;·&nbsp; ✓ {t.everyCited}
          </p>

          {/* Typewriter */}
          <div
            className="w-full rounded-2xl px-7 py-5 mb-5 text-left"
            dir="ltr"
            style={{
              maxWidth: '680px',
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.12)',
              backdropFilter: 'blur(12px)',
            }}
          >
            <p className="text-xs uppercase tracking-widest mb-2 font-medium" style={{ color: 'rgba(255,255,255,0.35)' }}>
              {t.askVelaTo}
            </p>
            <p className="text-lg leading-relaxed min-h-[1.8rem] text-white">
              <TypewriterPrompt />
            </p>
          </div>

          {/* CTA */}
          <div className="flex gap-3 my-8">
            <SignedOut>
              <SignInButton mode="modal">
                <button
                  className="group px-6 py-2.5 text-white text-sm font-semibold rounded-xl transition-all duration-300 hover:scale-105 flex items-center gap-2"
                  style={{ background: 'linear-gradient(135deg, #ff6b6b, #ff8e6e)', boxShadow: '0 0 28px rgba(255,107,107,0.4)' }}
                >
                  {t.getStarted}
                  <span className="group-hover:translate-x-1 transition-transform">{arrow}</span>
                </button>
              </SignInButton>
            </SignedOut>
            <SignedIn>
              <Link href="/research">
                <button
                  className="group px-6 py-2.5 text-white text-sm font-semibold rounded-xl transition-all duration-300 hover:scale-105 flex items-center gap-2"
                  style={{ background: 'linear-gradient(135deg, #ff6b6b, #ff8e6e)', boxShadow: '0 0 28px rgba(255,107,107,0.4)' }}
                >
                  {t.openApp}
                  <span className="group-hover:translate-x-1 transition-transform">{arrow}</span>
                </button>
              </Link>
            </SignedIn>
            <Link
              href="/pricing"
              className="text-sm font-medium rounded-full px-4 py-2 transition-all duration-200"
              style={{ background: 'rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.55)', border: '1px solid rgba(255,255,255,0.1)' }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.15)'; (e.currentTarget as HTMLElement).style.color = 'white'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.08)'; (e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,0.55)'; }}
            >
              {t.seePricing} {arrow}
            </Link>
          </div>

          {/* Social proof */}
          <p className="text-sm mb-6" style={{ color: 'rgba(148,163,184,0.7)' }}>
            {t.socialProof}
          </p>

          {/* Product showcase */}
          <ProductShowcase t={t} />
        </div>

        {/* Footer */}
        <div
          className="flex-shrink-0 flex flex-col items-center gap-2 px-4 md:px-10 py-5 text-sm"
          style={{ borderTop: '1px solid rgba(255,255,255,0.07)', color: 'rgba(255,255,255,0.3)' }}
        >
          <div className="flex items-center gap-3">
            <span>© {new Date().getFullYear()} Vela. {t.footerCopy} · <a href="https://an-tho.com" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">an-tho.com</a></span>
            <LanguageSwitcher lang={lang} setLang={setLang} />
          </div>
          <div>{t.footerDisclaimer}</div>
          <div className="flex flex-wrap justify-center gap-4 text-xs">
            <Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link>
            <Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
            <Link href="/refund" className="hover:text-white transition-colors">Refund Policy</Link>
            <Link href="/faq" className="hover:text-white transition-colors">FAQ</Link>
            <a href="mailto:support@an-tho.com" className="hover:text-white transition-colors">support@an-tho.com</a>
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
      accentColor: '#ff8e6e', color: '#ff8e6e',
      hoverBg: 'rgba(255,142,110,0.12)', hoverBorder: 'rgba(255,142,110,0.45)',
    },
    {
      href: '/verify', key: 'verify', label: extra.dashVerifyLabel, sub: extra.dashVerifySub,
      desc: extra.dashVerifyDesc,
      accentColor: '#63b3ed', color: '#63b3ed',
      hoverBg: 'rgba(99,179,237,0.12)', hoverBorder: 'rgba(99,179,237,0.45)',
    },
    {
      href: '/explain', key: 'explain', label: extra.dashExplainLabel, sub: extra.dashExplainSub,
      desc: extra.dashExplainDesc,
      accentColor: '#68d391', color: '#68d391',
      hoverBg: 'rgba(104,211,145,0.12)', hoverBorder: 'rgba(104,211,145,0.45)',
    },
    {
      href: '/history', key: 'history', label: extra.dashHistoryLabel, sub: extra.dashHistorySub,
      desc: extra.dashHistoryDesc,
      accentColor: '#94a3b8', color: '#94a3b8',
      hoverBg: 'rgba(148,163,184,0.12)', hoverBorder: 'rgba(148,163,184,0.45)',
    },
  ];

  return (
    <main className="min-h-screen pb-20 md:pb-0" style={{ background: BG }}>
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
                style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)' }}
                onMouseEnter={e => {
                  const el = e.currentTarget as HTMLElement;
                  el.style.background = f.hoverBg;
                  el.style.border = `1px solid ${f.hoverBorder}`;
                  el.style.transform = 'translateY(-4px)';
                  el.style.boxShadow = `0 12px 40px ${f.hoverBg}`;
                }}
                onMouseLeave={e => {
                  const el = e.currentTarget as HTMLElement;
                  el.style.background = 'rgba(255,255,255,0.05)';
                  el.style.border = '1px solid rgba(255,255,255,0.1)';
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
                <p className="text-base leading-relaxed" style={{ color: 'rgba(255,255,255,0.45)' }}>{f.desc}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div
        className="mt-12 flex flex-col items-center gap-2 px-4 md:px-10 py-6 text-sm"
        style={{ borderTop: '1px solid rgba(255,255,255,0.07)', color: 'rgba(255,255,255,0.3)' }}
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
export default function Home() {
  const { isSignedIn, isLoaded } = useUser();

  if (!isLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: BG }}>
        <div
          className="w-6 h-6 border-2 rounded-full animate-spin"
          style={{ borderColor: 'rgba(255,255,255,0.15)', borderTopColor: '#ff8e6e' }}
        />
      </div>
    );
  }

  return isSignedIn ? <Dashboard /> : <LandingPage />;
}
