// components/LandingSections.tsx — B4.1d (local iteration, 2026-08-13):
// the static panel gains a SCROLL-LINKED WORD REVEAL and a gradient headline.
// GSAP stays RETIRED — the reveal is driven by the SAME rAF progress value the
// width interpolation already computes, so there is one handler, one scroll
// listener and no animation library.
//
// Panel behaviour, in one place:
//   - width      max-width 64rem → min(80rem, 94vw), linear in progress p
//   - reveal     per-word opacity 0→1 + translateY 14px→0, staggered across
//                H1 words then sub words, mapped from a slice of the same p
//   - height     md:min-h-[80vh] (B4.1d), content vertically centered
//   - gradient   .panel-gradient-text per H1 word span (globals.css)
// All of it is a PURE FUNCTION of scroll position, so reversing the scroll
// reverses the animation exactly — there is no timeline and no hysteresis.
//
// SYSTEM RULES (unchanged):
//   - LIGHT-ONLY LANDING (D-B4-1); no `dark:` variants in this file.
//   - TOKEN COLORS ONLY (guard: tests/test_landing_sections_tokens.py). The
//     headline gradient is a globals.css class, itself token-only.
//   - RTL-SAFE: pill arrows rotate + hover-shift flips via rtl: variants. Word
//     spans split on spaces only, which never breaks Arabic joining (joining
//     already breaks at spaces) and leaves bidi ordering to the paragraph.
//   - MOTION: reveal + width are a VISUAL LAYER ONLY. Under
//     prefers-reduced-motion and <md the handler never runs, so the words keep
//     their default styles — full text, fully visible — which is also exactly
//     what the static export ships.

import { Fragment, useEffect, useLayoutEffect, useRef, useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { ChevronDown, ArrowRight } from 'lucide-react';
import type { LandingContent, Translations } from '../utils/i18n';

// Layout effect on the client, plain effect during the static export — avoids
// both the SSR warning and a one-frame flash of un-revealed words.
const useIsomorphicLayoutEffect = typeof window !== 'undefined' ? useLayoutEffect : useEffect;

const clamp01 = (v: number) => (v < 0 ? 0 : v > 1 ? 1 : v);

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

// ─── Word splitter for the scroll reveal ─────────────────────────────────────
// Splits on spaces ONLY. Space-less scripts (zh, ja, th) therefore yield ONE
// unit per line and the reveal degrades to a line-level fade — expected and
// accepted, the same degradation B4.1b documented for the retired word-scrub.
// Splitting further would need Intl.Segmenter and would break CJK line-breaking.
//
// Spans are inline-block so translateY applies to them; the separator is a real
// space text node, so wrapping and justification behave exactly as they do for
// unsplit text. No initial hidden style — the words render VISIBLE and the
// handler is what hides them, which keeps the static export readable.
function Words({ text, spanClassName = '' }: { text: string; spanClassName?: string }) {
  const words = text.split(' ');
  return (
    <>
      {words.map((word, i) => (
        <Fragment key={i}>
          <span data-reveal-word className={`inline-block ${spanClassName}`}>
            {word}
          </span>
          {i < words.length - 1 ? ' ' : ''}
        </Fragment>
      ))}
    </>
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

// ─── Panel scroll handler: width interpolation + word reveal ─────────────────
// p = 0 when the section's top sits at the viewport bottom, 1 when it reaches
// the viewport top.
//
// The reveal consumes the SLICE p ∈ [0.32, 0.86] rather than all of p. That
// window is derived from the layout, not picked by feel: the hero is 90vh and
// the panel is 80vh, so the headline (vertically centered) only crosses into
// view around p ≈ 0.36 and is comfortably mid-screen by p ≈ 0.86. Because every
// term is vh-relative, the window holds across viewport heights. Starting the
// reveal at p = 0 would finish it entirely below the fold — the user would
// scroll to an already-revealed headline and see nothing happen.
const REVEAL_START = 0.32;
const REVEAL_END = 0.86;
const WORD_DURATION = 0.35; // share of the reveal window one word occupies; the
                            // overlap is what makes it read as a wave, not a queue
const RISE_PX = 14;

// B4.2 — the demo image gets its OWN later slice so it lands after the sub has
// finished (text ends at 0.86). It is not word-revealed; it is one fade+rise.
// Window derived from layout like the text one: with the image in place the
// panel content puts the image top on screen around p ≈ 0.51, and p clamps at 1
// when the section top reaches the viewport top, so [0.78, 1.0] is the widest
// slice that both starts after the image is approaching view and completes
// while the user can still see it happen.
const MEDIA_START = 0.78;
const MEDIA_END = 1.0;
const MEDIA_RISE_PX = 24;

// `copyKey` exists ONLY to re-run the effect when the panel copy changes. The
// locale swap is post-hydration (LangContext seeds 'en' for SSR parity, then
// swaps in a passive effect), and Words() keys by index with no style prop, so
// React reuses the surviving spans IN PLACE — inline styles written for the old
// copy survive, and any spans beyond the old count mount with none at all.
// Without this dep the handler would not re-run and the panel would sit in a
// mixed state until the next scroll event. Re-running is cheap: cleanup wipes
// every span's inline style, then update() re-derives the whole set.
function usePanelScroll(
  sectionRef: React.RefObject<HTMLElement | null>,
  panelRef: React.RefObject<HTMLDivElement | null>,
  copyKey: string,
) {
  useIsomorphicLayoutEffect(() => {
    const desktop = window.matchMedia('(min-width: 768px)').matches;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!desktop || reduced) return;
    const section = sectionRef.current;
    const panel = panelRef.current;
    if (!section || !panel) return;

    let raf = 0;
    const update = () => {
      const r = section.getBoundingClientRect();
      const p = clamp01((window.innerHeight - r.top) / window.innerHeight);

      // (1) width — 64rem → min(80rem, 94vw)
      const from = 1024;
      const to = Math.min(1280, window.innerWidth * 0.94);
      panel.style.maxWidth = `${Math.round(from + p * (to - from))}px`;

      // (2) word reveal. Queried FRESH every frame, so the handler can never
      // write to DETACHED nodes after a locale swap — that half of the B4.1b
      // bug class is structurally impossible here. Keeping the REVEAL STATE
      // consistent across a swap is a separate problem, and it is the `copyKey`
      // dep below that solves it, not the fresh query.
      const words = panel.querySelectorAll<HTMLElement>('[data-reveal-word]');
      const n = words.length;
      // NOT an early return: the media reveal below must still run even if the
      // copy ever renders zero word spans.
      if (n > 0) {
        const q = clamp01((p - REVEAL_START) / (REVEAL_END - REVEAL_START));
        const step = n > 1 ? (1 - WORD_DURATION) / (n - 1) : 0;
        for (let i = 0; i < n; i++) {
          const local = clamp01((q - i * step) / WORD_DURATION);
          const eased = 1 - Math.pow(1 - local, 3); // ease-out cubic
          const s = words[i].style;
          // Epsilon, not `=== 1`: the cubic approaches 1 asymptotically, so an
          // exact test leaves a `translateY(0.00px)` on any word that is visually
          // finished but numerically 0.9999 — an inline transform, and therefore
          // a stacking context, exactly the residue the B4.1a defect was made of.
          if (eased > 0.999) {
            // Settled = NO inline styles, identical to the reduced-motion and
            // static-export state. Also avoids leaving a transform behind, which
            // is what created the stacking context in the B4.1a defect.
            s.removeProperty('opacity');
            s.removeProperty('transform');
          } else {
            s.opacity = eased.toFixed(3);
            s.transform = `translateY(${((1 - eased) * RISE_PX).toFixed(2)}px)`;
          }
        }
      }

      // (3) demo image — ONE fade+rise on a later slice, so it lands after the
      // sub. Queried fresh for the same locale-swap reason as the words.
      const media = panel.querySelector<HTMLElement>('[data-reveal-media]');
      if (media) {
        const mp = clamp01((p - MEDIA_START) / (MEDIA_END - MEDIA_START));
        const eased = 1 - Math.pow(1 - mp, 3);
        const s = media.style;
        if (eased > 0.999) {
          s.removeProperty('opacity');
          s.removeProperty('transform');
        } else {
          s.opacity = eased.toFixed(3);
          s.transform = `translateY(${((1 - eased) * MEDIA_RISE_PX).toFixed(2)}px)`;
        }
      }
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
      panel.querySelectorAll<HTMLElement>('[data-reveal-word],[data-reveal-media]').forEach((w) => {
        (w as HTMLElement).style.removeProperty('opacity');
        (w as HTMLElement).style.removeProperty('transform');
      });
    };
  }, [sectionRef, panelRef, copyKey]);
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
  usePanelScroll(panelSectionRef, panelRef, `${lc.panelHeadline} ${lc.panelSub}`);

  return (
    <>
      {/* §1 — BLACK PANEL: one static H1 + sub, centered, white on ink.
          Resting width 64rem; scroll interpolates toward min(80rem, 94vw) and
          reveals the words. B4.1d: md:min-h-[80vh]. */}
      <section
        id="panel"
        ref={panelSectionRef}
        className="px-4 md:px-10 pt-12 md:pt-16 pb-16 md:pb-20"
      >
        <div
          ref={panelRef}
          className="w-full max-w-5xl mx-auto rounded-3xl bg-text text-paper px-6 py-20 md:py-28 md:min-h-[80vh] flex flex-col items-center justify-center text-center gap-5"
        >
          <h2 className="font-serif text-3xl sm:text-4xl md:text-5xl leading-tight max-w-3xl">
            <Words text={lc.panelHeadline} spanClassName="panel-gradient-text" />
          </h2>
          <p className="text-base md:text-lg max-w-2xl" style={{ color: 'rgb(var(--color-paper) / 0.7)' }}>
            <Words text={lc.panelSub} />
          </p>

          {/* B4.2 — Research demo still. Layout A: stacked under the sub.
              SIZED BY ASPECT-RATIO, not by the image's pixel height, so the
              planned swap to <video> is a tag change and not a layout change.
              `aspect-[1975/1114]` is the asset's exact intrinsic ratio (1.7729,
              near-16:9 but not exactly, so the literal ratio avoids squashing).
              Explicit width/height on the <img> too — between them there is
              zero layout shift on load.
              Hairline border at paper/15: the screenshot has its own near-white
              chrome, and without a border it bleeds into the ink panel. No
              shadow — the panel is already the page's only dark block.
              Top gap = this margin PLUS the parent's gap-5 (20px): 32px mobile,
              52px desktop. Mobile is full width minus the panel's own px-6. */}
          <div
            data-reveal-media
            className="mt-3 md:mt-8 w-full md:w-[85%] aspect-[1975/1114] rounded-xl overflow-hidden border border-paper/15"
          >
            <Image
              src="/media/demo-research-20260814.png"
              alt={lc.panelDemoAlt}
              width={1975}
              height={1114}
              loading="lazy"
              decoding="async"
              className="w-full h-full object-cover"
            />
          </div>
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
