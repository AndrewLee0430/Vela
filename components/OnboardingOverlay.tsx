import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';

// Browser-global "already onboarded" flag. Single-sourced so _app.tsx can clear
// it on sign-out (so a different account on the same browser re-onboards).
export const ONBOARDING_SEEN_KEY = 'hasSeenOnboarding';

interface Step {
  target: string | null;
  titleKey: 'onboardingWelcome' | 'onboardingResearch' | 'onboardingVerify' | 'onboardingExplain';
  bodyKey: 'onboardingProBody' | 'onboardingFreeBody' | 'onboardingResearchBody' | 'onboardingVerifyBody' | 'onboardingExplainBody';
  usePlanBody?: boolean;
}

const STEP_DEFS: Step[] = [
  { target: null, titleKey: 'onboardingWelcome', bodyKey: 'onboardingProBody', usePlanBody: true },
  { target: '[data-onboarding="research"]', titleKey: 'onboardingResearch', bodyKey: 'onboardingResearchBody' },
  { target: '[data-onboarding="verify"]', titleKey: 'onboardingVerify', bodyKey: 'onboardingVerifyBody' },
  { target: '[data-onboarding="explain"]', titleKey: 'onboardingExplain', bodyKey: 'onboardingExplainBody' },
];

export default function OnboardingOverlay() {
  const { getToken } = useAuth();
  const { lang } = useLang();
  const ui = getUI(lang);
  const [step, setStep] = useState(0);
  const [visible, setVisible] = useState(false);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const [plan, setPlan] = useState<'free' | 'pro'>('free'); // default free; corrected by /api/user/status
  const popoverRef = useRef<HTMLDivElement>(null);

  const steps = STEP_DEFS;

  // ── fetch plan ────────────────────────────────────────────────────────────
  useEffect(() => {
    (async () => {
      try {
        const token = await getToken({ skipCache: true });
        if (!token) return;
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/user/status`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        const data = await res.json();
        setPlan(data.plan_type === 'pro' ? 'pro' : 'free');
      } catch { /* keep optimistic default */ }
    })();
  }, [getToken]);

  // ── show only once ────────────────────────────────────────────────────────
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (localStorage.getItem(ONBOARDING_SEEN_KEY)) return;
    const t = setTimeout(() => setVisible(true), 400);
    return () => clearTimeout(t);
  }, []);

  // ── measure spotlight target ──────────────────────────────────────────────
  const measure = useCallback(() => {
    const sel = steps[step]?.target;
    if (!sel) { setRect(null); return; }
    const el = document.querySelector(sel) as HTMLElement | null;
    if (!el) { setRect(null); return; }
    setRect(el.getBoundingClientRect());
  }, [step, steps]);

  useEffect(() => {
    if (!visible) return;
    measure();
    window.addEventListener('resize', measure);
    window.addEventListener('scroll', measure, true);
    return () => {
      window.removeEventListener('resize', measure);
      window.removeEventListener('scroll', measure, true);
    };
  }, [visible, measure]);

  // ── handlers ──────────────────────────────────────────────────────────────
  const finish = () => {
    localStorage.setItem(ONBOARDING_SEEN_KEY, '1');
    setVisible(false);
  };

  const next = () => {
    if (step >= steps.length - 1) { finish(); return; }
    setStep(s => s + 1);
  };

  if (!visible) return null;

  const currentDef = steps[step];
  const currentTitle = ui[currentDef.titleKey];
  const currentBody = currentDef.usePlanBody
    ? (plan === 'pro' ? ui.onboardingProBody : ui.onboardingFreeBody)
    : ui[currentDef.bodyKey];
  const isFirst = step === 0;
  const isLast = step === steps.length - 1;
  const PAD = 12;

  // ── popover position (horizontally centered on spotlight) ────────────────
  let popoverStyle: React.CSSProperties = {};
  if (rect) {
    const POPOVER_W = 420;
    const centerX = rect.left + rect.width / 2;
    const rawLeft = centerX - POPOVER_W / 2;
    // clamp so popover stays within viewport with 12px margin
    const margin = 12;
    const clampedLeft = Math.max(margin, Math.min(rawLeft, window.innerWidth - POPOVER_W - margin));

    const spaceBelow = window.innerHeight - rect.bottom;
    const vertPos = spaceBelow > 240
      ? { top: rect.bottom + PAD + 10 }
      : { bottom: window.innerHeight - rect.top + PAD + 10 };

    popoverStyle = { ...vertPos, left: clampedLeft, width: POPOVER_W };
  }

  return (
    <div className="fixed inset-0 z-[9999]" style={{ pointerEvents: 'auto' }}>
      {/* ── backdrop with spotlight cutout ── */}
      <svg className="absolute inset-0 w-full h-full" style={{ pointerEvents: 'none' }}>
        <defs>
          <mask id="onboarding-mask">
            <rect width="100%" height="100%" fill="white" />
            {rect && (
              <rect
                x={rect.left - PAD} y={rect.top - PAD}
                width={rect.width + PAD * 2} height={rect.height + PAD * 2}
                rx={18} fill="black"
              />
            )}
          </mask>
        </defs>
        <rect
          width="100%" height="100%"
          fill="rgba(0,0,0,0.72)"
          mask="url(#onboarding-mask)"
          style={{ pointerEvents: 'auto' }}
          onClick={finish}
        />
      </svg>

      {/* ── spotlight ring ── */}
      {rect && (
        <div
          className="absolute rounded-2xl pointer-events-none"
          style={{
            top: rect.top - PAD, left: rect.left - PAD,
            width: rect.width + PAD * 2, height: rect.height + PAD * 2,
            boxShadow: '0 0 0 2px rgb(var(--color-brand) / 0.5), 0 0 24px 4px rgb(var(--color-brand) / 0.15)',
            transition: 'all 0.35s cubic-bezier(.4,0,.2,1)',
          }}
        />
      )}

      {/* ── popover ── */}
      <div
        ref={popoverRef}
        className="absolute rounded-2xl px-8 py-6 shadow-2xl min-w-[420px] border border-text/12"
        style={{
          background: 'rgb(var(--color-bg-2))',
          ...(rect
            ? popoverStyle
            : { top: '50%', left: '50%', transform: 'translate(-50%,-50%)', maxWidth: 480 }),
          transition: 'all 0.35s cubic-bezier(.4,0,.2,1)',
        }}
      >
        {/* step indicator */}
        <div className="flex items-center gap-2 mb-3">
          {steps.map((_, i) => (
            <div
              key={i}
              className="h-1.5 rounded-full transition-all duration-300"
              style={{
                width: i === step ? 28 : 10,
                background: i === step ? 'rgb(var(--color-brand))' : 'rgb(var(--color-text) / 0.2)',
              }}
            />
          ))}
        </div>

        <p className="text-2xl font-semibold text-text mb-2">{currentTitle}</p>
        <p className="text-base leading-relaxed whitespace-pre-line text-text/60">
          {currentBody}
        </p>

        {/* buttons */}
        <div className="flex items-center justify-between mt-6">
          {!isFirst ? (
            <button
              onClick={() => setStep(s => s - 1)}
              className="text-sm px-4 py-2 rounded-lg transition-colors text-text/50"
            >
              {ui.onboardingBack}
            </button>
          ) : (
            <button
              onClick={finish}
              className="text-sm px-4 py-2 rounded-lg transition-colors text-text/50"
            >
              {ui.onboardingSkip}
            </button>
          )}
          <button
            onClick={next}
            className="text-sm font-semibold px-6 py-2 rounded-lg transition-all"
            style={{ background: 'rgb(var(--color-brand))', color: '#0a1628' }}
          >
            {isLast ? ui.onboardingDone : ui.onboardingNext}
          </button>
        </div>
      </div>
    </div>
  );
}
