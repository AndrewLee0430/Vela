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
//   - height     md:h-[92vh] + md:max-h-[92vh] (B4.3 R2). A DEFINITE height,
//                NOT a min-height: `flex-1` on the media needs one, and a
//                min-height is exactly how B4.2 ended up 111.3vh tall.
//                (This line read `md:min-h-[80vh] (B4.1d)` until B4.5 — stale
//                since B4.3 R2 removed that token.)
//   - headline   solid paper, BOLD (B4.5 C). The `.panel-gradient-text` ramp
//                and its ::selection / forced-colors fallbacks were deleted;
//                see the tombstone at the end of styles/globals.css.
//   - media      B4.3 R4: the Research demo VIDEO, poster-first. It plays only
//                when ALL of md+, motion-allowed and in-viewport hold; see
//                usePanelVideo. Everywhere else the poster is the media.
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
import Link from 'next/link';
import Image from 'next/image';
import { ChevronDown, ArrowRight } from 'lucide-react';
import type { LandingContent, Translations } from '../utils/i18n';
import { ARCHIVE_MODE, SHOWCASE_URL } from '../utils/archiveMode';

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

// ─── Pill ─────────────────────────────────────────────────────────────────────
// Two tones, same shape. `ink` (default) is the cards' pill on the paper page;
// `paper` is B4.3's panel CTA — the SAME pill inverted, which is what keeps it
// distinct from the cards without inventing a second component. Measured
// 12.13:1 either way, since both are the paper/panel pair swapped.
function Pill({
  href,
  label,
  tone = 'ink',
  plain = false,
}: {
  href: string;
  label: string;
  tone?: 'ink' | 'paper';
  // Archive car closeout (2026-10-05): a target outside the Next.js router (the
  // static /about/ page) gets a plain <a> — next/link would try a client-side
  // route the export does not have.
  plain?: boolean;
}) {
  const className = `group inline-flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium transition-opacity duration-200 hover:opacity-90 ${
    tone === 'paper' ? 'bg-paper text-panel' : 'bg-text text-paper'
  }`;
  const content = (
    <>
      <span>{label}</span>
      <ArrowRight
        size={16}
        strokeWidth={2}
        aria-hidden="true"
        className="transition-transform duration-200 group-hover:translate-x-1 rtl:rotate-180 rtl:group-hover:-translate-x-1"
      />
    </>
  );
  return plain ? (
    <a href={href} className={className}>{content}</a>
  ) : (
    <Link href={href} className={className}>{content}</Link>
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

// ─── Panel demo video: viewport-gated playback ───────────────────────────────
// B4.3 R4. Three states, and the video plays in exactly one of them:
//   md+, no reduced-motion  → an IntersectionObserver drives play/pause
//   prefers-reduced-motion  → never autoplays; gains `controls` so the demo
//                             stays reachable by the user's own input
//   below md                → never autoplays; poster + controls (B4.5 D2), so
//                             a phone can actually start the demo on a tap
//
// Playback is driven ENTIRELY by the observer, and the element deliberately
// carries no `autoplay` attribute. The attribute starts the video as soon as
// the element is parseable, which would leave "never plays off-screen" resting
// on a browser heuristic — Chrome defers off-screen muted autoplay, Firefox
// does not. Observer-driven, the guarantee is ours and holds everywhere.
// The cost is that with JS disabled the poster never advances; that is the
// state <md already ships deliberately, so it degrades into a design we accept
// rather than into a broken one.
//
// `preload="none"` means the 1.92 MB never leaves the server until the panel
// is actually scrolled to — on mobile, where we never play, it is never
// fetched at all and the 95 KB poster is the whole cost.
function usePanelVideo(videoRef: React.RefObject<HTMLVideoElement | null>) {
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;

    const wide = window.matchMedia('(min-width: 768px)');
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    let io: IntersectionObserver | null = null;

    const apply = () => {
      if (io) {
        io.disconnect();
        io = null;
      }
      // React applies `muted` as a DOM PROPERTY on the client, not as an
      // attribute, and the property is what the autoplay policy reads. Assert
      // it before any play() so a policy rejection is impossible by construction.
      v.muted = true;

      if (!wide.matches || reduced.matches) {
        v.pause();
        // B4.5 D2 — controls in BOTH non-playing states, not just reduced
        // motion. Below md the video never autoplays by design, so without
        // controls a phone could only ever see the poster — and phones are the
        // primary traffic. The browser chrome is worth strictly more than a
        // demo nobody can start. `preload="none"` still holds: controls do not
        // fetch the media, so the 1.92 MB is still only paid on a real tap.
        v.setAttribute('controls', '');
        return;
      }

      v.removeAttribute('controls');
      io = new IntersectionObserver(
        (entries) => {
          for (const e of entries) {
            if (e.isIntersecting) {
              // play() rejects when the tab is hidden or the policy blocks it.
              // Unhandled that is a console error on the landing page, and
              // there is nothing to recover — the poster stays up. Swallow it.
              void v.play().catch(() => {});
            } else {
              v.pause();
            }
          }
        },
        { threshold: 0.25 },
      );
      io.observe(v);
    };

    apply();
    // Re-evaluate when the user crosses the md breakpoint or flips the OS
    // motion preference mid-session; otherwise a resize past 768px would leave
    // a permanently-paused video, and enabling reduced-motion would not stop one.
    wide.addEventListener('change', apply);
    reduced.addEventListener('change', apply);
    return () => {
      if (io) io.disconnect();
      wide.removeEventListener('change', apply);
      reduced.removeEventListener('change', apply);
      v.pause();
    };
  }, [videoRef]);
}

// ── 2f (redesign ruling E, 2026-08-28) + Gate 8 row 5 (founder ruling,
// 2026-09-01): the demo poster is DELETED and the poster attribute is gone
// from the <video>; the pre-play treatment is `preload="metadata"`, now
// HARDCODED — the review toggle and the losing 'none' branch are deleted.
//
// WHY 'metadata' and not 'none': with the poster gone, 'none' would leave
// mobile a BLANK bordered box until a tap — the opposite of the poster-first
// UX that Gate 6 row 8 validated on a real iPhone, and below md the video
// never autoplays by design, so the blank box would be the whole experience
// for most traffic. 'metadata' has browsers paint the first frame instead.
// Its cost is bounded and known, not unknown: the server ships no HTTP
// byte-range support ([OTHER][P2] TECH_DEBT, fix path filed — fastapi
// 0.115.2 minimum), so a browser MAY fetch the whole 2.3 MB to obtain that
// frame. The ACTUAL transfer is deliberately left to be measured at the prod
// re-check, where a real host serves the file; the local static server is
// not evidence about production behaviour.
const VIDEO_PRELOAD = 'metadata' as const;

interface Props {
  lc: LandingContent;
  t: Translations;
}

export default function LandingSections({ lc, t }: Props) {
  const panelSectionRef = useRef<HTMLElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const bandRef = useRef<HTMLElement | null>(null);
  const demoVideoRef = useRef<HTMLVideoElement | null>(null);
  useFadeIn(bandRef);
  usePanelVideo(demoVideoRef);
  usePanelScroll(panelSectionRef, panelRef, `${lc.panelHeadline} ${lc.panelSub}`);

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
        {/* B4.3 — SINGLE VIEWPORT. md:h-[92vh] (not min-h) is what lets the
            media claim the leftover space: `flex-1` needs a DEFINITE parent
            height, and a min-height leaves the panel content-sized, which is
            how B4.2 ended up 111.3vh tall. md:max-h-[92vh] states the cap
            explicitly even though h- already equals it.
            This also fixes the B4.2 side effect where the panel GREW 111px
            during the width expand: height is now viewport-derived, and the
            media is height-driven with width:auto, so expanding changes width
            ONLY. Below md the panel stays content-sized and the media is
            width-driven, per the stacked mobile treatment. */}
        <div
          ref={panelRef}
          className="w-full max-w-5xl mx-auto rounded-3xl bg-panel text-paper px-6 py-10 md:h-[92vh] md:max-h-[92vh] flex flex-col items-center justify-center text-center gap-4"
        >
          {/* B4.5 C — SOLID paper, BOLD. The gradient is gone (globals.css
              tombstone explains what went with it). No color class here on
              purpose: the panel wrapper sets `text-paper`, so the headline
              inherits the full-strength token — 17.95:1 on the near-black
              panel. The word spans stay; the reveal writes opacity/transform
              on them and never depended on the gradient class. */}
          <h2 className="font-serif font-bold text-3xl sm:text-4xl md:text-5xl leading-tight max-w-3xl">
            <Words text={lc.panelHeadline} />
          </h2>
          <p className="text-base md:text-lg max-w-2xl" style={{ color: 'rgb(var(--color-paper) / 0.7)' }}>
            <Words text={lc.panelSub} />
          </p>

          {/* B4.3 R3 — Research CTA, between the sub and the media. Reuses the
              existing tryResearch key (zero new strings); the paper tone is the
              cards' pill inverted, 12.13:1 on the new panel. */}
          <Pill href="/research" label={lc.tryResearch} tone="paper" />

          {/* B4.3 R2/R4 — the media takes whatever height is left.
              md:flex-1 + md:min-h-0 claims the remainder of the 92vh panel;
              the media itself is HEIGHT-driven (md:h-full, w-auto) so the
              width expand never changes the panel's height. Below md it falls
              back to the stacked, width-driven treatment.
              The border goes BACK to paper/15 at B4.5. The /15 -> /20 raise was
              compensation for B4.3 lightening the panel, and that cause is gone:
              the B4.5 near-black panel is DARKER than the ink the /15 hairline
              originally sat on (measured 1.52:1 on near-black vs 1.55:1 on the
              old ink, i.e. the original look restored; /20 would read 1.82:1).
              It is a decorative separator, not text, so no AA floor applies.
              The literal lives in styles/globals.css, the sanctioned home for
              raw color — naming it here would trip this file's token guard,
              which reads comments too (verified: it caught exactly that).

              B4.3 R4 — the still is now the demo VIDEO. ZERO CLS is carried
              across from B4.2 rather than assumed: width/height are the
              encode's REAL output dimensions, read from ffprobe rather than
              assumed — B4.6 re-cut a NEW master (1646x946, not the first
              take's 1662x938) and the output moved 1440x812 -> 1440x828, so
              these three numbers are re-derived per encode, never carried
              over. Reusing a stale pair squashes the frame silently. And the
              explicit aspectRatio restates it in CSS so the reservation does
              not depend on UA behaviour for <video>. Playback gating lives in
              usePanelVideo; the reveal below is untouched and still off <md
              and under reduced-motion. */}
          <div
            data-reveal-media
            className="w-full md:flex-1 md:min-h-0 flex items-center justify-center"
          >
            {/* Iteration 5 A1/A4 (2026-08-31).
                A4 — the CLS pair is the DERIVED decode size, 1441x828, read
                from the stream itself (HTMLVideoElement.videoWidth) rather
                than the 1440 that had been carried in these attributes and
                the aspectRatio. One pixel, but the house rule is that these
                three numbers are re-derived per encode, never carried.
                A1 — the width is CAPPED at 62.5% of the panel's inner width,
                which is the video's 2x-exhaustion point (1441 native / 2 =
                720.5px, and the panel's inner width is 1152px at 1280). The
                cap is a MAXIMUM, not a fixed width: `h-auto` + `max-h-full`
                keeps the old height-adaptive behaviour, so a short window
                still shrinks the video instead of overflowing the fixed-
                height panel (Gate 6 row 4). The cap also fixes BY
                CONSTRUCTION the locale-dependent softness measured in
                iteration 5 Part 1: Arabic's shorter text used to give the
                video 0.634 of the container and 1.973x, i.e. under 2x purely
                because of how tall the translated copy happened to be. */}
            <video
              ref={demoVideoRef}
              src="/media/research-demo.mp4"
              width={1441}
              height={828}
              muted
              loop
              playsInline
              preload={VIDEO_PRELOAD}
              aria-label={lc.panelDemoAlt}
              style={{ aspectRatio: '1441 / 828' }}
              className="rounded-xl border border-paper/15 object-contain w-full h-auto md:w-auto md:h-auto md:max-h-full md:max-w-[62.5%]"
            />
          </div>
        </div>
      </section>

      {/* §2 — VERIFY SHOWCASE (2026-08-28 landing build car). Replaces the
          three-card "What Vela does" section (rulings F/G: cards removed;
          cardDesc x3, tryExplain, featuresHeading retired; footer #features
          link deleted). A warm-gray BAND (bg-paper-band — NEW token, ruling C,
          founder eyeballs the value on localhost) directly after the black
          Research panel, same container geometry as the panel (px-4 md:px-10 /
          max-w-5xl / rounded-3xl); the panel section's bottom padding is the
          gap between the two bands. CTA reuses tryVerify (card-pill DNA, ink
          tone); the demo image is the 2e WebP with its encode-derived dims as
          the CLS reservation (house rule: dims re-derived per encode, never
          carried over — iteration 1 re-derived 2020x1225 from the founder's
          new wider capture). Fade-in reuses the cards' useFadeIn. */}
      <section ref={bandRef} className="px-4 md:px-10 pb-16 md:pb-20">
        {/* Iteration 1: the band matches the panel's WIDENED width, not its
            resting 64rem — usePanelScroll interpolates the panel's max-width
            to `Math.min(1280, window.innerWidth * 0.94)`, and p is clamped at
            1 (fully widened) by the time the band is on screen, so the CSS
            mirror of that final state is `min(80rem, 94vw)`. Static here — no
            script. Known edge, accepted: under prefers-reduced-motion or <md
            the panel handler never runs and the panel rests at 64rem, so the
            two edges only match in the normal-motion desktop flow the founder
            reviews. */}
        <div className="w-full max-w-[min(80rem,94vw)] mx-auto rounded-3xl bg-paper-band px-6 py-10 md:py-14 flex flex-col items-center text-center gap-5">
          <h2 className="font-serif font-bold text-3xl sm:text-4xl leading-tight max-w-3xl text-text">
            {lc.verifyHeadline}
          </h2>
          <p className="text-base md:text-lg max-w-2xl" style={{ color: 'rgb(var(--color-text) / 0.7)' }}>
            {lc.verifySub}
          </p>
          {/* Archive car (2026-10-05): the band stays as showcase content; in an archive-mode
              build its CTA leads to the static showcase, not the retired /verify. */}
          <Pill href={ARCHIVE_MODE ? SHOWCASE_URL : '/verify'} label={lc.tryVerify} plain={ARCHIVE_MODE} />
          {/* Iteration 5 A2: 0.778 -> 0.85 of the band's inner width (was
              max-w-4xl = 896px against a 1152px container). Ceiling derived,
              not chosen by feel: 2020 natural / (0.85 * 1152 = 979.2) =
              2.06x, so it still clears 2x at DPR 2, with little to spare —
              0.877 is where this capture goes soft. `md:` only; mobile keeps
              full width. */}
          <Image
            src="/media/Verify_Landing_Demo.webp"
            alt={lc.verifyDemoAlt}
            width={2020}
            height={1225}
            loading="lazy"
            className="rounded-xl border border-card-border w-full h-auto md:max-w-[85%]"
          />
        </div>
      </section>

      {/* §3 — EXPLAIN SHOWCASE (iteration 2, 2026-08-28). Same container
          geometry as the Verify band; background = paper-band-2 (one step
          whiter, derivation in globals.css — founder eyeballs). Composition is
          a founder-chosen SIDE-BY-SIDE row (iteration 4, replacing iterations
          2–3's overlapping stagger): INPUT capture inline-start, RESULT
          capture inline-end, TOPS ALIGNED, no overlap, no layering. The result
          is the taller image and simply extends further down — nothing is
          cropped, stretched, or forced to equal height, and each keeps its own
          encode-derived width/height attributes (1294x954 / 1173x1204).
          GRID, not flex, and `fr` columns rather than percentage widths: with
          a gap, `w-[48%] + w-[52%]` sums past 100% and the two would silently
          shrink by unequal amounts, so the stated split would not be the
          rendered one. `grid-cols-[48fr_52fr]` subtracts the gap first and
          splits what remains exactly 48:52 — the number in the class is the
          number on screen.
          RTL is structural here: grid column placement follows the writing
          direction, so the input starts from the right in ar with no ms-/me-
          overrides (verified by measurement, not assumed).
          Below md the row collapses to `grid-cols-1` — vertical stack, input
          above result, full width, no overlap, unchanged from iteration 2.
          Both images carry the Verify band's image treatment (rounded-xl +
          card-border, NO shadow); the stagger's z-10 and shadow-card are gone
          with the composition that needed them. */}
      <section className="px-4 md:px-10 pb-16 md:pb-20">
        <div className="w-full max-w-[min(80rem,94vw)] mx-auto rounded-3xl bg-paper-band-2 px-6 py-10 md:py-14 flex flex-col items-center text-center gap-5">
          <h2 className="font-serif font-bold text-3xl sm:text-4xl leading-tight max-w-3xl text-text">
            {lc.explainHeadline}
          </h2>
          <p className="text-base md:text-lg max-w-2xl" style={{ color: 'rgb(var(--color-text) / 0.7)' }}>
            {lc.explainSub}
          </p>
          <Pill href={ARCHIVE_MODE ? SHOWCASE_URL : '/explain'} label={lc.tryExplain} plain={ARCHIVE_MODE} />
          {/* Iteration 5 C2: tops-aligned -> items-center, so the two captures
              balance optically instead of leaving the shorter one hanging
              from the top edge.
              Iteration 6: the founder re-captured both images from the
              NEUTRAL-COLOUR /explain UI, CROPPED to their key regions, so the
              landing no longer advertises a screen the product does not have
              (verified by reading the captures, not assumed). Dims re-derived
              per encode, never carried: 1174x685 and 1188x841.
              Container raised max-w-4xl (0.778) -> 0.85 of the band's inner
              width, matching the Verify image's iteration-5 fraction so the
              two bands share one media rhythm.
              SPLIT STAYS 48/52, re-derived rather than inherited: the old
              48/52 existed to restrain a PORTRAIT result capture (0.974)
              beside a landscape input (1.356). Both are landscape now (1.714
              / 1.413), so that reason is gone — but the founder's standing
              emphasis (the result is the payoff, "paste this -> get this")
              still wants the result larger, and 48/52 delivers it on both
              axes: 458.5x267.5 vs 496.7x351.5. The equal-HEIGHT split the new
              ratios permit is 55/45, which would make the INPUT the bigger
              image and invert that emphasis — derived, then rejected. */}
          <div className="w-full grid grid-cols-1 gap-4 md:max-w-[85%] md:grid-cols-[48fr_52fr] md:gap-6 md:items-center">
            <Image
              src="/media/Explain_Landing_Demo_1.webp"
              alt={lc.explainDemoAlt1}
              width={1174}
              height={685}
              loading="lazy"
              className="block rounded-xl border border-card-border w-full h-auto"
            />
            <Image
              src="/media/Explain_Landing_Demo_2.webp"
              alt={lc.explainDemoAlt2}
              width={1188}
              height={841}
              loading="lazy"
              className="block rounded-xl border border-card-border w-full h-auto"
            />
          </div>
        </div>
      </section>
    </>
  );
}
