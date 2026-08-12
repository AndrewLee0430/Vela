// components/LandingSections.tsx — B4 FINAL-FORM landing below-fold
// (2026-08-12): black interactive panel + simplified cards. Supersedes B3's
// paper editorial sections; the WHO and PRIVACY sections are REMOVED
// (founder-ratified reversal ledger in STATE — PRD §0.3 amended; the
// research-tool disclaimer keeps its footer render point, verified P0.1).
//
// SYSTEM RULES:
//   - LIGHT-ONLY LANDING (D-B4-1): no `dark:` variants anywhere in this file;
//     the logged-out tree is wrapped in a `.light` token scope in index.tsx.
//   - TOKEN COLORS ONLY (guard: tests/test_landing_sections_tokens.py). The
//     panel is the INK token; pills invert (paper-on-ink / ink-on-paper);
//     card shadow via the `shadow-card` utility (rgba lives in globals.css).
//   - RTL-SAFE: pill arrows rotate + hover-shift flips via rtl: variants.
//   - MOTION: GSAP ScrollTrigger (3.15, Standard no-charge license) drives
//     the desktop panel: width 70vw→95vw scrub, then PIN through
//     intro→seg1→seg2→seg3 with progress dots. Mobile (<md) and
//     prefers-reduced-motion get the static stack. ALL text + pills are in
//     the SSG DOM in every mode — animation only controls visibility.
//     Elsewhere: one-time fade-in on viewport entry, reduced-motion-disabled.

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { ChevronDown, ArrowRight } from 'lucide-react';
import type { LandingContent, Translations } from '../utils/i18n';

// ─── Scroll hint — unchanged (fades on first scroll) ─────────────────────────
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
      onClick={() => document.getElementById('panel')?.scrollIntoView({ behavior: 'smooth' })}
      className={`absolute bottom-5 left-1/2 -translate-x-1/2 p-2 rounded-full transition-opacity duration-700 ${
        faded ? 'opacity-0 pointer-events-none' : 'opacity-100'
      }`}
      style={{ color: 'rgb(var(--color-text) / 0.35)' }}
    >
      <ChevronDown size={22} strokeWidth={1.8} className="animate-bounce" aria-hidden="true" />
    </button>
  );
}

// ─── Shared: ink pill (paper text) / white pill (ink text, panel use) ─────────
function Pill({ href, label, onPanel }: { href: string; label: string; onPanel?: boolean }) {
  return (
    <Link
      href={href}
      className={`group inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition-opacity duration-200 hover:opacity-90 ${
        onPanel ? 'bg-paper text-text' : 'bg-text text-paper'
      }`}
    >
      <span>{label}</span>
      <ArrowRight
        size={16}
        strokeWidth={2}
        aria-hidden="true"
        className="transition-transform duration-200 group-hover:translate-x-1 rtl:rotate-180 rtl:group-hover:-translate-x-1"
      />
    </Link>
  );
}

// ─── One-time fade-in on viewport entry (reduced-motion: off) ────────────────
function useFadeIn(ref: React.RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 600ms ease, transform 600ms ease';
    const io = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          el.style.opacity = '1';
          el.style.transform = 'translateY(0)';
          io.disconnect();
        }
      },
      { threshold: 0.15 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [ref]);
}

interface Props {
  lc: LandingContent;
  t: Translations;
}

export default function LandingSections({ lc, t }: Props) {
  const panelSectionRef = useRef<HTMLElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const cardsRef = useRef<HTMLElement | null>(null);
  const [activeSeg, setActiveSeg] = useState(-1); // -1 = intro/static
  const [animated, setAnimated] = useState(false);
  useFadeIn(cardsRef);

  // Panel content — ALL states in the DOM in every mode (SEO text never
  // absent). In animated mode GSAP absolutely-stacks and cross-fades them;
  // in static mode they flow normally.
  const segments = [
    { tag: lc.panelTag1, desc: lc.panelDesc1, href: '/research', label: t.research },
    { tag: lc.panelTag2, desc: lc.panelDesc2, href: '/verify', label: t.verify },
    { tag: lc.panelTag3, desc: lc.panelDesc3, href: '/explain', label: t.explain },
  ];

  useEffect(() => {
    const desktop = window.matchMedia('(min-width: 768px)').matches;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!desktop || reduced) return; // static stack — no GSAP at all

    let ctx: { revert: () => void } | undefined;
    let cancelled = false;
    (async () => {
      const gsapMod = await import('gsap');
      const stMod = await import('gsap/ScrollTrigger');
      if (cancelled) return;
      const gsap = gsapMod.gsap ?? gsapMod.default;
      const ScrollTrigger = stMod.ScrollTrigger ?? stMod.default;
      gsap.registerPlugin(ScrollTrigger);

      const section = panelSectionRef.current;
      const panel = panelRef.current;
      if (!section || !panel) return;
      const states = Array.from(panel.querySelectorAll<HTMLElement>('[data-panel-state]'));
      if (states.length !== 4) return;

      setAnimated(true);
      ctx = gsap.context(() => {
        // Animated mode: stack the four states; only intro visible initially.
        gsap.set(panel, { width: '70vw', maxWidth: 'none', margin: '0 auto' });
        gsap.set(states, { position: 'absolute', inset: 0, display: 'flex', opacity: 0 });
        gsap.set(states[0], { opacity: 1 });

        const tl = gsap.timeline({
          scrollTrigger: {
            trigger: section,
            start: 'top top',
            end: '+=350%',
            scrub: 0.5,
            pin: true,
            onUpdate: (self: { progress: number }) => {
              const p = self.progress;
              setActiveSeg(p < 0.3 ? -1 : p < 0.53 ? 0 : p < 0.76 ? 1 : 2);
            },
          },
        });
        // 0→25%: width breakout 70vw → 95vw
        tl.to(panel, { width: '95vw', ease: 'none', duration: 0.25 }, 0);
        // 25→30%: intro → seg1; then seg cross-fades
        tl.to(states[0], { opacity: 0, duration: 0.04 }, 0.26);
        tl.to(states[1], { opacity: 1, duration: 0.04 }, 0.3);
        tl.to(states[1], { opacity: 0, duration: 0.04 }, 0.49);
        tl.to(states[2], { opacity: 1, duration: 0.04 }, 0.53);
        tl.to(states[2], { opacity: 0, duration: 0.04 }, 0.72);
        tl.to(states[3], { opacity: 1, duration: 0.04 }, 0.76);
      }, section);
    })();

    return () => {
      cancelled = true;
      ctx?.revert();
      setAnimated(false);
      setActiveSeg(-1);
    };
  }, []);

  const stateBlock = (children: React.ReactNode, key: string) => (
    <div
      key={key}
      data-panel-state={key}
      className="flex flex-col items-center justify-center text-center gap-4 px-6 py-16 md:py-0"
    >
      {children}
    </div>
  );

  return (
    <>
      {/* §1 — BLACK PANEL (replaces WHO). The only large dark block on the
          page; ink token, 24px radius; ≥120px clearance both sides via
          section padding. Text is white via the paper-token inversion
          (panel bg = text token → white text = paper... on the ink panel the
          readable color is the PAGE token pair: we use literal token classes
          text-paper for body on ink). */}
      <section
        id="panel"
        ref={panelSectionRef}
        className="px-4 md:px-10 py-32 md:py-40 md:min-h-screen md:flex md:items-center"
      >
        <div
          ref={panelRef}
          className="relative w-full max-w-7xl mx-auto rounded-3xl bg-text text-paper overflow-hidden md:min-h-[70vh]"
        >
          {/* intro */}
          {stateBlock(
            <>
              <h2 className="font-serif text-3xl sm:text-4xl md:text-5xl leading-tight">{lc.panelIntroTitle}</h2>
              <p className="text-base md:text-lg" style={{ color: 'rgb(var(--color-paper) / 0.7)' }}>{lc.panelIntroSub}</p>
            </>,
            'intro',
          )}
          {/* segments */}
          {segments.map((s, i) =>
            stateBlock(
              <>
                <h3 className="font-serif text-2xl sm:text-3xl md:text-4xl leading-tight">{s.tag}</h3>
                <p className="max-w-xl text-base md:text-lg" style={{ color: 'rgb(var(--color-paper) / 0.7)' }}>{s.desc}</p>
                <div className="mt-2">
                  <Pill href={s.href} label={s.label} onPanel />
                </div>
              </>,
              `seg${i + 1}`,
            ),
          )}
          {/* progress dots — animated mode only, during the segs */}
          <div
            aria-hidden="true"
            className={`absolute bottom-6 left-1/2 -translate-x-1/2 flex gap-2 transition-opacity duration-300 ${
              animated && activeSeg >= 0 ? 'opacity-100' : 'opacity-0'
            } ${animated ? '' : 'hidden'}`}
          >
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-2 h-2 rounded-full"
                style={{ background: i === activeSeg ? 'rgb(var(--color-paper))' : 'rgb(var(--color-paper) / 0.3)' }}
              />
            ))}
          </div>
        </div>
      </section>

      {/* §2 — CARDS ("What Vela does"): paper-2 sheets, hairline border,
          shadow-card, no icons, no metadata rows, no intro line. */}
      <section id="features" ref={cardsRef} className="px-4 md:px-10 py-32 md:py-40">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-text mb-12">
            {lc.featuresHeading}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
            {[
              { key: 'research', title: t.research, desc: lc.cardDescResearch, href: '/research' },
              { key: 'verify', title: t.verify, desc: lc.cardDescVerify, href: '/verify' },
              { key: 'explain', title: t.explain, desc: lc.cardDescExplain, href: '/explain' },
            ].map(({ key, title, desc, href }) => (
              <div key={key} className="rounded-2xl p-8 bg-paper-2 border border-hairline shadow-card flex flex-col">
                <h3 className="text-lg font-bold text-text mb-3">{title}</h3>
                <p className="font-serif text-lg leading-relaxed" style={{ color: 'rgb(var(--color-text) / 0.7)' }}>
                  {desc}
                </p>
                <div className="flex-grow" aria-hidden="true" />
                <div className="mt-8">
                  <Pill href={href} label={title} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
