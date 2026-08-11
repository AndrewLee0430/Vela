// components/LandingSections.tsx — B1 below-fold marketing sections (2026-08-11).
//
// Three sections + a hero scroll hint, rendered under the landing hero on
// pages/index.tsx. Anthropic-style density: one scroll each, typographic, no
// images, no carousels.
//
// HARD CONSTRAINTS (fly 219/220 regression class — see tests/test_landing_
// sections_tokens.py):
//   - TOKEN COLORS ONLY. Every color goes through the variable system
//     (text-text, bg-*, rgb(var(--color-text) / …)). No hex codes, no
//     alpha-color functions — hardcoded achromatics are exactly how
//     light-mode legibility broke on the share pages at fly 219.
//   - RTL-SAFE. The landing wrapper sets dir=rtl for ar/he; nothing here uses
//     direction-dependent absolute offsets. The scroll hint centers with
//     left-1/2 -translate-x-1/2 — physical centering, direction-agnostic.
//   - Gutters match the hero (px-4 md:px-10); headings sit one step below the
//     hero's scale (hero: 3xl→5xl; sections: 2xl→3xl).
//
// i18n: all strings come from landingContent (utils/i18n.ts, 16 locales) or
// are REUSED VERBATIM from already-shipped keys (privacyPromise1-3,
// footerDisclaimer) per ratified D2 — reused strings carry their existing
// review status; the new keys are MT baseline, not native-reviewed yet.

import { useEffect, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import type { LandingContent, Translations } from '../utils/i18n';

// ─── Scroll hint — chevron at the hero's bottom center, fades on first scroll ─
// Zero layout change to the hero: absolutely positioned inside the hero's
// (position:relative) first-viewport div. Clicking scrolls to §1.
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

// ─── The three sections ───────────────────────────────────────────────────────
interface Props {
  lc: LandingContent;
  t: Translations;
}

export default function LandingSections({ lc, t }: Props) {
  return (
    <>
      {/* §1 — Who Vela is for */}
      <section id="who" className="px-4 md:px-10 py-24 md:py-32">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-text mb-8">
            {lc.whoHeading}
          </h2>
          <div className="space-y-5 text-base sm:text-lg leading-relaxed" style={{ color: 'rgb(var(--color-text) / 0.7)' }}>
            <p>{lc.whoP1}</p>
            <p>{lc.whoP2}</p>
            <p className="font-medium text-text">{lc.whoP3}</p>
          </div>
        </div>
      </section>

      {/* §2 — How it works. NOTE: no explore CTA — P0.1 verdict was NOT
          safe-to-link (one published page, no index route; bare /explore
          serves the landing itself). Re-add when the explore corpus exists. */}
      <section id="how" className="px-4 md:px-10 py-24 md:py-32" style={{ background: 'rgb(var(--color-text) / 0.03)' }}>
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-text mb-12">
            {lc.howHeading}
          </h2>
          <ol className="grid grid-cols-1 md:grid-cols-3 gap-10 md:gap-8 list-none">
            {[
              { n: 1, title: lc.how1Title, body: lc.how1Body },
              { n: 2, title: lc.how2Title, body: lc.how2Body },
              { n: 3, title: lc.how3Title, body: lc.how3Body },
            ].map((step) => (
              <li key={step.n}>
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold mb-4"
                  style={{
                    background: 'rgb(var(--color-brand) / 0.12)',
                    color: 'rgb(var(--color-brand))',
                  }}
                  aria-hidden="true"
                >
                  {step.n}
                </div>
                <h3 className="text-base font-semibold text-text mb-2">{step.title}</h3>
                <p className="text-sm leading-relaxed" style={{ color: 'rgb(var(--color-text) / 0.6)' }}>
                  {step.body}
                </p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* §3 — Privacy. The three chips + the research-tool disclaimer are
          REUSED VERBATIM (already-shipped keys); only trustLine + founderNote
          are new copy here. */}
      <section id="privacy" className="px-4 md:px-10 py-24 md:py-32">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-semibold tracking-tight text-text mb-8">
            {lc.privacyHeading}
          </h2>
          <ul className="space-y-3 text-base sm:text-lg" style={{ color: 'rgb(var(--color-text) / 0.7)' }}>
            <li>{t.privacyPromise1}</li>
            <li>{t.privacyPromise2}</li>
            <li>{t.privacyPromise3}</li>
          </ul>
          <p className="mt-8 text-sm" style={{ color: 'rgb(var(--color-text) / 0.55)' }}>
            {t.footerDisclaimer}
          </p>
          <p className="mt-3 text-base font-medium text-text">{lc.trustLine}</p>
          <p className="mt-10 text-xs leading-relaxed" style={{ color: 'rgb(var(--color-text) / 0.4)' }}>
            {lc.founderNote}
          </p>
        </div>
      </section>
    </>
  );
}
