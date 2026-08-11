// components/LandingSections.tsx — B2 card-based below-fold sections (2026-08-11).
// Supersedes the B1 bare-text layout after the Gate 2 finding: functionally
// PASS, visually "reads as bare text".
//
// HARD CONSTRAINTS (fly 219/220 regression class — see tests/test_landing_
// sections_tokens.py):
//   - TOKEN COLORS ONLY. Every color goes through the variable system
//     (text-text, bg-bg-1, bg-brand/15, rgb(var(--color-text) / …)). No hex
//     codes, no alpha-color functions — hardcoded achromatics are exactly how
//     light-mode legibility broke on the share pages at fly 219.
//   - RTL-SAFE. dir=rtl is inherited for ar/he; grids auto-flip; the WHO
//     accent bar uses the LOGICAL borderInlineStart property; the scroll hint
//     centers physically (left-1/2 -translate-x-1/2 — direction-agnostic).
//   - Gutters match the hero (px-4 md:px-10); section headings one step below
//     the hero's scale.
//
// VISUAL SYSTEM (B2, founder-ratified):
//   - Cards: bg-bg-1 (light: white surface over the grayish app-bg gradient;
//     dark: the elevated navy), rounded-2xl, p-8, NO borders. shadow-sm in
//     light only (dark:shadow-none — a black drop shadow on the navy gradient
//     reads muddy, verified against the token values).
//   - ACCENT TREATMENT CHOSEN: the icon chip carries the coral tint (the
//     exact DNA of the B1 numbered step badges — bg-brand/12 circle,
//     text-brand glyph). Chosen over the 3px top hairline because it reuses
//     the Gate-2-approved badge DNA, keeps the no-border card rule intact,
//     and holds the coral accent count per card at exactly one.
//   - Icons: lucide-react (already a dependency — the hero imports ChevronDown,
//     the mode selector Sparkles/Check). currentColor via the chip's
//     text-brand, aria-hidden.
//
// i18n: strings come from landingContent (utils/i18n.ts, 16 locales) or are
// REUSED VERBATIM (feature titles/descriptions = the mode-selector keys; the
// privacy card sentences = privacyPromise1-3; Pro tag = same treatment as
// HeroComposerModeSelector). Per R3 there are NO invented short card titles —
// each privacy card is icon + the full shipped sentence, never stronger than
// the promise it reuses.

import { useEffect, useState } from 'react';
import {
  ChevronDown, Search, ShieldCheck, FlaskConical,
  Fingerprint, EyeOff, Lock, UserX, Sparkles,
} from 'lucide-react';
import type { LandingContent, Translations } from '../utils/i18n';

// ─── Scroll hint — unchanged from B1 (fades on first scroll, zero hero layout) ─
export function ScrollHint({ label }: { label: string }) {
  const [faded, setFaded] = useState(false);
  useEffect(() => {
    const onScroll = () => {
      if (window.scrollY > 40) {
        setFaded(true);
        window.removeEventListener('scroll', onScroll);
      }
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <button
      type="button"
      aria-label={label}
      onClick={() => document.getElementById('who')?.scrollIntoView({ behavior: 'smooth' })}
      className={`absolute bottom-5 left-1/2 -translate-x-1/2 p-2 rounded-full transition-opacity duration-700 ${
        faded ? 'opacity-0 pointer-events-none' : 'opacity-100'
      }`}
      style={{ color: 'rgb(var(--color-text) / 0.35)' }}
    >
      <ChevronDown size={22} strokeWidth={1.8} className="animate-bounce" aria-hidden="true" />
    </button>
  );
}

// ─── Shared card primitives ───────────────────────────────────────────────────
function IconChip({ children }: { children: React.ReactNode }) {
  // The B1 numbered-badge DNA: coral-tinted circle, brand-colored glyph.
  return (
    <div
      className="w-10 h-10 rounded-full flex items-center justify-center mb-5 text-brand"
      style={{ background: 'rgb(var(--color-brand) / 0.12)' }}
      aria-hidden="true"
    >
      {children}
    </div>
  );
}

const CARD = 'rounded-2xl p-8 bg-bg-1 shadow-sm dark:shadow-none';

// ─── The sections ─────────────────────────────────────────────────────────────
interface Props {
  lc: LandingContent;
  t: Translations;
}

export default function LandingSections({ lc, t }: Props) {
  const features = [
    { key: 'research', title: t.research, desc: t.composerModeDescResearch, Icon: Search, pro: false },
    { key: 'verify', title: t.verify, desc: t.composerModeDescVerify, Icon: ShieldCheck, pro: false },
    { key: 'explain', title: t.explain, desc: t.composerModeDescExplain, Icon: FlaskConical, pro: true },
  ];
  const privacyCards = [
    { key: 'p1', text: t.privacyPromise1, Icon: Fingerprint },
    { key: 'p2', text: t.privacyPromise2, Icon: EyeOff },
    { key: 'p3', text: t.privacyPromise3, Icon: Lock },
    { key: 'p4', text: lc.privacyPromise4, Icon: UserX },
  ];

  return (
    <>
      {/* §1 — WHO. Deliberately NOT carded (a manifesto). Two touches only:
          the inline-start coral accent bar (logical property — RTL-safe) and
          the final line stepped up + brand-colored. */}
      <section id="who" className="px-4 md:px-10 py-24 md:py-32">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-text mb-8">
            {lc.whoHeading}
          </h2>
          <div
            className="space-y-5 text-base sm:text-lg leading-relaxed"
            style={{
              color: 'rgb(var(--color-text) / 0.7)',
              borderInlineStart: '3px solid rgb(var(--color-brand))',
              paddingInlineStart: '1.5rem',
            }}
          >
            <p>{lc.whoP1}</p>
            <p>{lc.whoP2}</p>
            <p className="text-lg sm:text-xl font-medium" style={{ color: 'rgb(var(--color-brand))' }}>
              {lc.whoP3}
            </p>
          </div>
        </div>
      </section>

      {/* §2 — FEATURES (replaces the B1 how-steps per R1). Card content is
          REUSED keys only (R2): titles = the mode-selector labels,
          descriptions = composerModeDesc* verbatim, Explain carries the same
          Pro tag treatment the selector uses. Band background = the B1 tint
          (text/3%) so the white/elevated cards read one step off in BOTH
          schemes — bg-bg-1 as the band itself would equal the cards in light. */}
      <section id="features" className="px-4 md:px-10 py-24 md:py-32" style={{ background: 'rgb(var(--color-text) / 0.03)' }}>
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-text mb-2">
            {lc.featuresHeading}
          </h2>
          <p className="text-base mb-12" style={{ color: 'rgb(var(--color-text) / 0.55)' }}>
            {lc.featuresIntro}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
            {features.map(({ key, title, desc, Icon, pro }) => (
              <div key={key} className={`${CARD} flex flex-col`}>
                <IconChip><Icon size={20} strokeWidth={2} /></IconChip>
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="text-base font-semibold text-text">{title}</h3>
                  {pro && (
                    <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium bg-brand/15 text-brand">
                      <Sparkles size={11} strokeWidth={2} />
                      Pro
                    </span>
                  )}
                </div>
                <p className="text-sm leading-relaxed" style={{ color: 'rgb(var(--color-text) / 0.6)' }}>
                  {desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* §3 — PRIVACY: four cards (the three shipped promises verbatim +
          privacyPromise4), then the honest-limits sub-block (R5 — a quiet
          register, not a fourth content band), then trustLine / disclaimer /
          founderNote in their B1 placement. */}
      <section id="privacy" className="px-4 md:px-10 py-24 md:py-32">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-text mb-10">
            {lc.privacyHeading}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch">
            {privacyCards.map(({ key, text, Icon }) => (
              <div key={key} className={CARD}>
                <IconChip><Icon size={20} strokeWidth={2} /></IconChip>
                <p className="text-base leading-relaxed" style={{ color: 'rgb(var(--color-text) / 0.75)' }}>
                  {text}
                </p>
              </div>
            ))}
          </div>

          {/* Honest-limits sub-block — small heading + three quiet lines. */}
          <div className="mt-12 max-w-2xl">
            <h3 className="text-sm font-semibold mb-3" style={{ color: 'rgb(var(--color-text) / 0.55)' }}>
              {lc.privacyLimitsHeading}
            </h3>
            <ul className="space-y-2 text-sm leading-relaxed" style={{ color: 'rgb(var(--color-text) / 0.5)' }}>
              <li>{lc.privacyLimit1}</li>
              <li>{lc.privacyLimit2}</li>
              <li>{lc.privacyLimit3}</li>
            </ul>
          </div>

          <div className="mt-12 max-w-2xl">
            <p className="text-sm" style={{ color: 'rgb(var(--color-text) / 0.55)' }}>
              {t.footerDisclaimer}
            </p>
            <p className="mt-3 text-base font-medium text-text">{lc.trustLine}</p>
            <p className="mt-10 text-xs leading-relaxed" style={{ color: 'rgb(var(--color-text) / 0.4)' }}>
              {lc.founderNote}
            </p>
          </div>
        </div>
      </section>
    </>
  );
}
