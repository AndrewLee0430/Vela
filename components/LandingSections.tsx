// components/LandingSections.tsx — B4.1b (local iteration, 2026-08-12/13):
// panel content REPLACED — the intro state and the three tool segments (and
// their pills) are retired; the panel now carries THREE CLAIM TAGLINES with a
// word-level scrub-linked reveal. Tool entry points live in the cards below —
// the double-pathway is deliberately dissolved. Cards: pure-white sheets with
// a split card-border token and a deepened shadow.
//
// SYSTEM RULES (unchanged from B4):
//   - LIGHT-ONLY LANDING (D-B4-1); no `dark:` variants in this file.
//   - TOKEN COLORS ONLY (guard: tests/test_landing_sections_tokens.py).
//   - RTL-SAFE: card pill arrows rotate + hover-shift flips via rtl: variants;
//     panel word order follows DOM order = reading order in either direction.
//   - MOTION: GSAP ScrollTrigger pins the panel on desktop; scrub is native
//     in both directions. Mobile (<md) + prefers-reduced-motion: static stack
//     of the three lines, no dots. ALL text is in the SSG DOM in every mode.
//   - PIN LENGTH (B4.1b addendum — re-derived, not inherited): B4's +=350%
//     covered 5 dwell units (width expand + 4 content states). B4.1b has 4
//     (expand + 3 lines); keeping per-unit scroll depth constant:
//     350% × 4/5 = +=280%.
//   - Word-level reveal degrades to LINE-level for space-less scripts
//     (zh/ja/th split to a single "word") — expected, not a defect.

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

// ─── Ink pill — card use only since B4.1b (the panel has no pills) ───────────
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
// B4.1a lesson: clears ALL inline styles on completion — residue transforms
// near ScrollTrigger pins paint later-DOM sections over fixed elements.
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

interface Props {
  lc: LandingContent;
  t: Translations;
}

export default function LandingSections({ lc, t }: Props) {
  const panelSectionRef = useRef<HTMLElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const cardsRef = useRef<HTMLElement | null>(null);
  const [activeLine, setActiveLine] = useState(-1); // -1 = pre-reveal/static
  const [animated, setAnimated] = useState(false);
  useFadeIn(cardsRef);

  const lines = [lc.panelLine1, lc.panelLine2, lc.panelLine3];

  useEffect(() => {
    const desktop = window.matchMedia('(min-width: 768px)').matches;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!desktop || reduced) return; // static stack — GSAP never loads

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
      const lineEls = Array.from(panel.querySelectorAll<HTMLElement>('[data-panel-line]'));
      if (lineEls.length !== 3) return;

      setAnimated(true);
      ctx = gsap.context(() => {
        gsap.set(panel, { width: '70vw', maxWidth: 'none', margin: '0 auto' });
        // Animated mode: stack the three lines; nothing visible pre-reveal.
        gsap.set(lineEls, { position: 'absolute', inset: 0, display: 'flex', opacity: 0 });

        const tl = gsap.timeline({
          scrollTrigger: {
            trigger: section,
            start: 'top top',
            // B4.1b addendum: re-derived — 4 dwell units × B4's per-unit depth
            // (350%/5) = 280%, not an inherited figure.
            end: '+=280%',
            scrub: 0.5,
            pin: true,
            onUpdate: (self: { progress: number }) => {
              const p = self.progress;
              setActiveLine(p < 0.25 ? -1 : p < 0.5 ? 0 : p < 0.75 ? 1 : 2);
            },
          },
        });
        // 0→25%: width breakout 70vw → 95vw
        tl.to(panel, { width: '95vw', ease: 'none', duration: 0.25 }, 0);
        // Each line: container visible for its third; WORDS stagger-reveal
        // (fade + rise) scrub-linked inside it; container fades out at the
        // end of its third (lines 1-2) — line 3 stays until unpin.
        const phases = [
          { el: lineEls[0], start: 0.25, out: 0.47 },
          { el: lineEls[1], start: 0.5, out: 0.72 },
          { el: lineEls[2], start: 0.75, out: null as number | null },
        ];
        for (const { el, start, out } of phases) {
          const words = Array.from(el.querySelectorAll<HTMLElement>('[data-word]'));
          gsap.set(words, { opacity: 0, y: 14 });
          tl.set(el, { opacity: 1 }, start);
          tl.to(words, { opacity: 1, y: 0, duration: 0.1, stagger: { amount: 0.08 }, ease: 'none' }, start + 0.01);
          if (out !== null) tl.to(el, { opacity: 0, duration: 0.03 }, out);
        }
        // TEMP local-iteration diagnostic — remove before stabilization deploy.
        (window as unknown as Record<string, unknown>).__panelDiag = {
          st: tl.scrollTrigger, tl, ScrollTrigger,
        };
      }, section);
    })();

    return () => {
      cancelled = true;
      ctx?.revert();
      setAnimated(false);
      setActiveLine(-1);
    };
    // Re-init when the locale swaps (post-hydration en → stored locale
    // replaces the word <span>s; a [] dep would leave the timeline tweening
    // detached nodes). ctx.revert() in the cleanup restores DOM state first.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lc.panelLine1, lc.panelLine2, lc.panelLine3]);

  return (
    <>
      {/* §1 — BLACK PANEL: three claim taglines, word-level reveal. No pills
          (tool entry = the cards below). Static/SSR: all three lines stacked
          and visible — SEO text never absent. */}
      <section
        id="panel"
        ref={panelSectionRef}
        className="px-4 md:px-10 py-32 md:py-40 md:min-h-screen md:flex md:items-center"
      >
        <div
          ref={panelRef}
          className="relative w-full max-w-7xl mx-auto rounded-3xl bg-text text-paper overflow-hidden md:min-h-[70vh]"
        >
          {lines.map((line, i) => (
            <p
              key={i}
              data-panel-line={i + 1}
              className="flex flex-wrap items-center justify-center content-center text-center gap-x-0 px-6 py-12 md:py-0 font-serif text-3xl sm:text-4xl md:text-5xl leading-tight"
            >
              {line.split(/\s+/).map((w, j, arr) => (
                <span key={j} data-word className="inline-block">
                  {w}
                  {j < arr.length - 1 ? ' ' : ''}
                </span>
              ))}
            </p>
          ))}
          {/* progress dots — one per line, animated mode only */}
          <div
            aria-hidden="true"
            className={`absolute bottom-6 left-1/2 -translate-x-1/2 flex gap-2 transition-opacity duration-300 ${
              animated && activeLine >= 0 ? 'opacity-100' : 'opacity-0'
            } ${animated ? '' : 'hidden'}`}
          >
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-2 h-2 rounded-full"
                style={{ background: i === activeLine ? 'rgb(var(--color-paper))' : 'rgb(var(--color-paper) / 0.3)' }}
              />
            ))}
          </div>
        </div>
      </section>

      {/* §2 — CARDS ("What Vela does"): B4.1b — pure-white sheets (paper-2
          token now full white), split card-border token, deepened shadow. */}
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
              <div key={key} className="rounded-2xl p-8 bg-paper-2 border border-card-border shadow-card flex flex-col">
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
