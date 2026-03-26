import { useState, useEffect, useCallback, useRef } from 'react';

const STEPS = [
  {
    target: null as string | null,           // full-screen welcome, no spotlight
    title: 'Welcome to Vela!',
    body: 'You have 15 free credits to get started.\nLet\u2019s take a quick look at what you can do.',
  },
  {
    target: '[data-onboarding="research"]',
    title: 'Research',
    body: 'Ask any clinical question in any language \u2014 powered by PubMed 36M+ articles.',
  },
  {
    target: '[data-onboarding="verify"]',
    title: 'Verify',
    body: 'Check drug interactions against official FDA data with severity ratings.',
  },
];

export default function OnboardingOverlay() {
  const [step, setStep] = useState(0);
  const [visible, setVisible] = useState(false);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const popoverRef = useRef<HTMLDivElement>(null);

  // ── show only once ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (localStorage.getItem('hasSeenOnboarding')) return;
    // small delay so the dashboard cards are rendered & measurable
    const t = setTimeout(() => setVisible(true), 400);
    return () => clearTimeout(t);
  }, []);

  // ── measure spotlight target ────────────────────────────────────────────────
  const measure = useCallback(() => {
    const sel = STEPS[step]?.target;
    if (!sel) { setRect(null); return; }
    const el = document.querySelector(sel) as HTMLElement | null;
    if (!el) { setRect(null); return; }
    setRect(el.getBoundingClientRect());
  }, [step]);

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

  // ── handlers ────────────────────────────────────────────────────────────────
  const finish = () => {
    localStorage.setItem('hasSeenOnboarding', '1');
    setVisible(false);
  };

  const next = () => {
    if (step >= STEPS.length - 1) { finish(); return; }
    setStep(s => s + 1);
  };

  if (!visible) return null;

  const current = STEPS[step];
  const isFirst = step === 0;
  const isLast = step === STEPS.length - 1;
  const PAD = 10; // spotlight padding around the card

  // ── popover position (below or above the spotlight rect) ────────────────────
  let popoverStyle: React.CSSProperties = {};
  if (rect) {
    const spaceBelow = window.innerHeight - rect.bottom;
    if (spaceBelow > 200) {
      popoverStyle = { top: rect.bottom + PAD + 8, left: rect.left, maxWidth: rect.width };
    } else {
      popoverStyle = { bottom: window.innerHeight - rect.top + PAD + 8, left: rect.left, maxWidth: rect.width };
    }
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
            boxShadow: '0 0 0 2px rgba(255,142,110,0.5), 0 0 24px 4px rgba(255,142,110,0.15)',
            transition: 'all 0.35s cubic-bezier(.4,0,.2,1)',
          }}
        />
      )}

      {/* ── popover ── */}
      <div
        ref={popoverRef}
        className="absolute rounded-xl px-5 py-4 shadow-2xl"
        style={{
          background: 'linear-gradient(135deg, #1a2744 0%, #1e2a45 100%)',
          border: '1px solid rgba(255,255,255,0.12)',
          ...(rect
            ? popoverStyle
            : { top: '50%', left: '50%', transform: 'translate(-50%,-50%)', maxWidth: 380 }),
          transition: 'all 0.35s cubic-bezier(.4,0,.2,1)',
        }}
      >
        {/* step counter */}
        <div className="flex items-center gap-1.5 mb-2">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className="h-1 rounded-full transition-all duration-300"
              style={{
                width: i === step ? 24 : 8,
                background: i === step ? '#ff8e6e' : 'rgba(255,255,255,0.2)',
              }}
            />
          ))}
        </div>

        <p className="text-sm font-semibold text-white mb-1">{current.title}</p>
        <p className="text-xs leading-relaxed whitespace-pre-line" style={{ color: 'rgba(255,255,255,0.6)' }}>
          {current.body}
        </p>

        {/* buttons */}
        <div className="flex items-center justify-between mt-4">
          {!isFirst ? (
            <button
              onClick={() => setStep(s => s - 1)}
              className="text-xs px-3 py-1.5 rounded-lg transition-colors"
              style={{ color: 'rgba(255,255,255,0.5)' }}
            >
              Back
            </button>
          ) : (
            <button
              onClick={finish}
              className="text-xs px-3 py-1.5 rounded-lg transition-colors"
              style={{ color: 'rgba(255,255,255,0.5)' }}
            >
              Skip
            </button>
          )}
          <button
            onClick={next}
            className="text-xs font-medium px-4 py-1.5 rounded-lg transition-all"
            style={{
              background: '#ff8e6e',
              color: '#0a1628',
            }}
          >
            {isLast ? 'Done' : 'Next'}
          </button>
        </div>
      </div>
    </div>
  );
}
