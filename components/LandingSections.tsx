// components/LandingSections.tsx — B4.1c (local iteration, 2026-08-13):
// panel SIMPLIFIED — the slideshow is gone (no pin, no line switching, no
// word reveal, no dots). Content = one static H1 + one subheadline, white on
// ink. The founder-praised expand-on-scroll FEEL is kept, but GSAP is
// RETIRED: a lightweight rAF scroll handler interpolates the panel's
// max-width (64rem → min(80rem, 94vw)) as the section traverses the
// viewport — both directions, no pin, no added scroll length. Card pills
// carry the try* labels.
//
// SYSTEM RULES (unchanged):
//   - LIGHT-ONLY LANDING (D-B4-1); no `dark:` variants in this file.
//   - TOKEN COLORS ONLY (guard: tests/test_landing_sections_tokens.py).
//   - RTL-SAFE: pill arrows rotate + hover-shift flips via rtl: variants.
//   - MOTION: width interpolation only, disabled under prefers-reduced-motion
//     and <md (static 64rem). H1/sub are NEVER animated per-word — the
//     locale-swap tween-on-detached-nodes bug class is structurally gone, so
//     no locale-dependent effect deps are needed.
//   - Gap rhythm (B4.1c supersedes B4's ≥120px-clearance rule): panel section
//     pt-12 md:pt-16 / pb-16 md:pb-20; hero is min-h-[90vh] (index.tsx) so
//     the panel top peeks above the fold as a scroll cue.

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

// ─── Ink pill (cards) ─────────────────────────────────────────────────────────
function Pill({ href, label }: { href: string; label: string }) {
  return (
    <Link
      href={href}
      className="group inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium bg-text text-paper transition-opacity duration-200 hover:opacity-90"
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
// B4.1a lesson: clears ALL inline styles on completion.
function useFadeIn(ref: React.RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 600ms ease, transform 600ms ease';
    const clear = () => {
      el.style.removeProperty('opacity');
      el.style.removeProperty('transform');
      el.style.removeProperty('transition');
      el.removeEventListener('transitionend', clear);
    };
    const io = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          el.addEventListener('transitionend', clear);
          el.style.opacity = '1';
          el.style.transform = 'translateY(0)';
          io.disconnect();
        }
      },
      { threshold: 0.15 },
    );
    io.observe(el);
    return () => {
      io.disconnect();
      el.removeEventListener('transitionend', clear);
    };
  }, [ref]);
}

// ─── B4.1c width interpolation — the expand feel without GSAP ─────────────────
// max-width goes 64rem → min(80rem, 94vw) as the section top travels from the
// viewport bottom to the viewport top. Pure function of scroll position, so
// reversing the scroll reverses the width. Disabled <md and under
// reduced-motion (panel stays at the resting 64rem via its className).
function usePanelExpand(
  sectionRef: React.RefObject<HTMLElement | null>,
  panelRef: React.RefObject<HTMLDivElement | null>,
) {
  useEffect(() => {
    const desktop = window.matchMedia('(min-width: 768px)').matches;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!desktop || reduced) return;
    const section = sectionRef.current;
    const panel = panelRef.current;
    if (!section || !panel) return;

    let raf = 0;
    const update = () => {
      const r = section.getBoundingClientRect();
      // progress 0 → section top at viewport bottom; 1 → section top at viewport top
      const p = Math.min(1, Math.max(0, (window.innerHeight - r.top) / window.innerHeight));
      const from = 1024; // 64rem
      const to = Math.min(1280, window.innerWidth * 0.94); // min(80rem, 94vw)
      panel.style.maxWidth = `${Math.round(from + p * (to - from))}px`;
    };
    const onScroll = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(update);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    update();
    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
      cancelAnimationFrame(raf);
      panel.style.removeProperty('max-width');
    };
  }, [sectionRef, panelRef]);
}

interface Props {
  lc: LandingContent;
  t: Translations;
}

export default function LandingSections({ lc, t }: Props) {
  const panelSectionRef = useRef<HTMLElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const cardsRef = useRef<HTMLElement | null>(null);
  useFadeIn(cardsRef);
  usePanelExpand(panelSectionRef, panelRef);

  return (
    <>
      {/* §1 — BLACK PANEL: one static H1 + sub, centered, white on ink.
          Resting width 64rem; scroll interpolates toward min(80rem, 94vw). */}
      <section
        id="panel"
        ref={panelSectionRef}
        className="px-4 md:px-10 pt-12 md:pt-16 pb-16 md:pb-20"
      >
        <div
          ref={panelRef}
          className="w-full max-w-5xl mx-auto rounded-3xl bg-text text-paper px-6 py-20 md:py-28 flex flex-col items-center justify-center text-center gap-5"
        >
          <h2 className="font-serif text-3xl sm:text-4xl md:text-5xl leading-tight max-w-3xl">
            {lc.panelHeadline}
          </h2>
          <p className="text-base md:text-lg max-w-2xl" style={{ color: 'rgb(var(--color-paper) / 0.7)' }}>
            {lc.panelSub}
          </p>
        </div>
      </section>

      {/* §2 — CARDS ("What Vela does"): white sheets, card-border, shadow;
          pills relabeled to the try* keys. Container narrowed to 64rem. */}
      <section id="features" ref={cardsRef} className="px-4 md:px-10 py-32 md:py-40">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-text mb-12">
            {lc.featuresHeading}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
            {[
              { key: 'research', title: t.research, desc: lc.cardDescResearch, href: '/research', pill: lc.tryResearch },
              { key: 'verify', title: t.verify, desc: lc.cardDescVerify, href: '/verify', pill: lc.tryVerify },
              { key: 'explain', title: t.explain, desc: lc.cardDescExplain, href: '/explain', pill: lc.tryExplain },
            ].map(({ key, title, desc, href, pill }) => (
              <div key={key} className="rounded-2xl p-8 bg-paper-2 border border-card-border shadow-card flex flex-col">
                <h3 className="text-lg font-bold text-text mb-3">{title}</h3>
                <p className="font-serif text-lg leading-relaxed" style={{ color: 'rgb(var(--color-text) / 0.7)' }}>
                  {desc}
                </p>
                <div className="flex-grow" aria-hidden="true" />
                <div className="mt-8">
                  <Pill href={href} label={pill} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
