// components/LandingSections.tsx — B3 paper redesign (editorial/print register,
// 2026-08-12). Supersedes the B2 card system after the Gate 3 aesthetic FAIL.
// All copy is IDENTICAL to B2 except the four B3 metadata keys.
//
// THE PAPER SYSTEM (founder-ratified R1-R9):
//   - Light is ONE CONTINUOUS PAPER PAGE (bg-paper on the wrapper in
//     pages/index.tsx); layering comes from cards (bg-paper-2), hairlines
//     (border-hairline) and spacing. NO shadows, NO gradients, NO band tints
//     below the fold. Dark maps the same tokens onto the existing dark family
//     — new layout + type, today's palette ("day is paper, night is ink").
//   - CORAL BELOW THE FOLD = ZERO (R3). No icon chips, no brand accents; the
//     WHO bar and whoP3 are ink. (Above-the-fold coral is out of scope.)
//   - TOKEN COLORS ONLY (the fly 219/220 regression class — see
//     tests/test_landing_sections_tokens.py). Raw hex lives solely in the
//     globals.css token definitions.
//   - RTL-SAFE: logical properties for the WHO bar; the pill arrow flips and
//     its hover shift flips (rtl: variants — Tailwind 3.4, dir-attribute
//     driven; the wrapper sets dir=rtl for ar/he).
//   - Type: sans = Noto Sans (headings, bold 32-40px, >=48px space below);
//     serif = Source Serif 4 via --font-serif (body 18-20px, lh ~1.6);
//     10 of 16 locales render serif via the deliberate system fallback.
//   - Container max-w-7xl; rhythm py-32 md:py-40; gutters px-4 md:px-10.
//
// HONESTY (R4, encoded in the ACCESS metadata row): Research/Verify =
// accessNoAccount (anonymous-usable, server.py anon paths); Explain =
// accessFreeAccount (anon blocked at server.py:1524-1525; signed-in Free CAN
// use text Explain — Pro gates only image upload, :1654-1658). The B2 Pro tag
// OVERSTATED the restriction and is removed.

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ChevronDown, ArrowRight } from 'lucide-react';
import type { LandingContent, Translations } from '../utils/i18n';

// ─── Scroll hint — unchanged from B1/B2 (fades on first scroll) ───────────────
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

// ─── Metadata row (R5.4): hairline-topped, UPPERCASE label / value ───────────
function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 py-3 border-t border-hairline">
      <span
        className="text-[13px] font-medium uppercase tracking-[0.05em]"
        style={{ color: 'rgb(var(--color-text) / 0.5)' }}
      >
        {label}
      </span>
      <span className="text-sm text-text">{value}</span>
    </div>
  );
}

interface Props {
  lc: LandingContent;
  t: Translations;
}

export default function LandingSections({ lc, t }: Props) {
  const features = [
    { key: 'research', title: t.research, desc: t.composerModeDescResearch, href: '/research', access: lc.accessNoAccount },
    { key: 'verify', title: t.verify, desc: t.composerModeDescVerify, href: '/verify', access: lc.accessNoAccount },
    // Explain: accessFreeAccount is the HONEST value (R4) — the sign-in wall
    // is declared before the click, and no Pro tag overstates the restriction.
    { key: 'explain', title: t.explain, desc: t.composerModeDescExplain, href: '/explain', access: lc.accessFreeAccount },
  ];
  const promises = [t.privacyPromise1, t.privacyPromise2, t.privacyPromise3, lc.privacyPromise4];

  return (
    <>
      {/* §1 — WHO (R8): serif manifesto, 2px INK bar (logical, RTL-safe),
          final line bold ink one size up. Prose sits in a narrower measure
          inside the max-w-7xl container — a 1280px paragraph is unreadable. */}
      <section id="who" className="px-4 md:px-10 py-32 md:py-40">
        <div className="max-w-7xl mx-auto">
          <div className="max-w-2xl">
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-text mb-12">
              {lc.whoHeading}
            </h2>
            <div
              className="space-y-6 font-serif text-xl leading-relaxed"
              style={{
                color: 'rgb(var(--color-text) / 0.75)',
                borderInlineStart: '2px solid rgb(var(--color-text))',
                paddingInlineStart: '1.5rem',
              }}
            >
              <p>{lc.whoP1}</p>
              <p>{lc.whoP2}</p>
              <p className="text-2xl font-semibold text-text">{lc.whoP3}</p>
            </div>
          </div>
        </div>
      </section>

      {/* §2 — FEATURES (R5): paper-2 cards, no icons, no shadows. Anatomy:
          bold sans title → serif description → spacer → hairline metadata
          rows (LANGUAGES / ACCESS) → ink pill with arrow. */}
      <section id="features" className="px-4 md:px-10 py-32 md:py-40">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-text mb-2">
            {lc.featuresHeading}
          </h2>
          <p className="font-serif text-lg mb-12" style={{ color: 'rgb(var(--color-text) / 0.55)' }}>
            {lc.featuresIntro}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
            {features.map(({ key, title, desc, href, access }) => (
              <div key={key} className="rounded-2xl p-8 bg-paper-2 flex flex-col">
                <h3 className="text-lg font-bold text-text mb-3">{title}</h3>
                <p className="font-serif text-lg leading-relaxed" style={{ color: 'rgb(var(--color-text) / 0.7)' }}>
                  {desc}
                </p>
                <div className="flex-grow" aria-hidden="true" />
                <div className="mt-8">
                  <MetaRow label={lc.metaLanguages} value="16" />
                  <MetaRow label={lc.metaAccess} value={access} />
                </div>
                <div className="mt-6">
                  <Link
                    href={href}
                    className="group inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium bg-text text-paper transition-opacity duration-200 hover:opacity-90"
                  >
                    <span>{title}</span>
                    <ArrowRight
                      size={16}
                      strokeWidth={2}
                      aria-hidden="true"
                      className="transition-transform duration-200 group-hover:translate-x-1 rtl:rotate-180 rtl:group-hover:-translate-x-1"
                    />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* §3 — PRIVACY (R7): editorial two-column. Left: trustLine RELOCATED
          as the bold declaration (moved, not duplicated). Right: the four
          promises as hairline-separated rows, then the limits block in quiet
          serif, then disclaimer + founderNote. Mobile: declaration stacks
          above the rows. */}
      <section id="privacy" className="px-4 md:px-10 py-32 md:py-40">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold tracking-tight text-text mb-12">
            {lc.privacyHeading}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-10 md:gap-16">
            <div className="md:col-span-1">
              <p className="text-3xl font-bold leading-snug text-text">{lc.trustLine}</p>
            </div>
            <div className="md:col-span-2">
              <div className="border-t border-hairline">
                {promises.map((text) => (
                  <p key={text} className="py-6 text-lg font-semibold text-text border-b border-hairline">
                    {text}
                  </p>
                ))}
              </div>

              <div className="mt-12 max-w-2xl">
                <h3 className="text-sm font-semibold mb-3" style={{ color: 'rgb(var(--color-text) / 0.55)' }}>
                  {lc.privacyLimitsHeading}
                </h3>
                <ul className="space-y-2 font-serif text-base leading-relaxed" style={{ color: 'rgb(var(--color-text) / 0.55)' }}>
                  <li>{lc.privacyLimit1}</li>
                  <li>{lc.privacyLimit2}</li>
                  <li>{lc.privacyLimit3}</li>
                </ul>
              </div>

              <div className="mt-12 max-w-2xl">
                <p className="font-serif text-sm" style={{ color: 'rgb(var(--color-text) / 0.55)' }}>
                  {t.footerDisclaimer}
                </p>
                <p className="mt-8 text-xs leading-relaxed" style={{ color: 'rgb(var(--color-text) / 0.4)' }}>
                  {lc.founderNote}
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
