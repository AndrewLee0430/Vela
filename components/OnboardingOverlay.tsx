import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@clerk/nextjs';

interface Step {
  target: string | null;
  title: string;
  body: string;
}

function buildSteps(plan: 'free' | 'pro'): Step[] {
  return [
    {
      target: null,
      title: 'Welcome to Vela!',
      body: plan === 'pro'
        ? 'You have unlimited* access to all features.\nLet\u2019s take a quick look at what you can do.'
        : 'You have 15 free credits to get started.\nLet\u2019s take a quick look at what you can do.',
    },
    {
      target: '[data-onboarding="research"]',
      title: 'Research',
      body: 'Ask any clinical question in any language \u2014 powered by official medical resources.',
    },
    {
      target: '[data-onboarding="verify"]',
      title: 'Verify',
      body: 'Check drug interactions against official FDA data to identify risks.',
    },
    {
      target: '[data-onboarding="explain"]',
      title: 'Explain Medical Reports',
      body: 'Understand any lab result or medical report in plain language, backed by official sources.',
    },
  ];
}

export default function OnboardingOverlay() {
  const { getToken } = useAuth();
  const [step, setStep] = useState(0);
  const [visible, setVisible] = useState(false);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const [plan, setPlan] = useState<'free' | 'pro'>('pro'); // optimistic default
  const popoverRef = useRef<HTMLDivElement>(null);

  const steps = buildSteps(plan);

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
    if (localStorage.getItem('hasSeenOnboarding')) return;
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
    localStorage.setItem('hasSeenOnboarding', '1');
    setVisible(false);
  };

  const next = () => {
    if (step >= steps.length - 1) { finish(); return; }
    setStep(s => s + 1);
  };

  if (!visible) return null;

  const current = steps[step];
  const isFirst = step === 0;
  const isLast = step === steps.length - 1;
  const PAD = 12;

  // ── popover position ─────────────────────────────────────────────────────
  let popoverStyle: React.CSSProperties = {};
  if (rect) {
    const spaceBelow = window.innerHeight - rect.bottom;
    if (spaceBelow > 240) {
      popoverStyle = { top: rect.bottom + PAD + 10, left: rect.left, maxWidth: Math.max(rect.width, 420) };
    } else {
      popoverStyle = { bottom: window.innerHeight - rect.top + PAD + 10, left: rect.left, maxWidth: Math.max(rect.width, 420) };
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
        className="absolute rounded-2xl px-8 py-6 shadow-2xl min-w-[420px]"
        style={{
          background: 'linear-gradient(135deg, #1a2744 0%, #1e2a45 100%)',
          border: '1px solid rgba(255,255,255,0.12)',
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
                background: i === step ? '#ff8e6e' : 'rgba(255,255,255,0.2)',
              }}
            />
          ))}
        </div>

        <p className="text-2xl font-semibold text-white mb-2">{current.title}</p>
        <p className="text-base leading-relaxed whitespace-pre-line" style={{ color: 'rgba(255,255,255,0.6)' }}>
          {current.body}
        </p>

        {/* buttons */}
        <div className="flex items-center justify-between mt-6">
          {!isFirst ? (
            <button
              onClick={() => setStep(s => s - 1)}
              className="text-sm px-4 py-2 rounded-lg transition-colors"
              style={{ color: 'rgba(255,255,255,0.5)' }}
            >
              Back
            </button>
          ) : (
            <button
              onClick={finish}
              className="text-sm px-4 py-2 rounded-lg transition-colors"
              style={{ color: 'rgba(255,255,255,0.5)' }}
            >
              Skip
            </button>
          )}
          <button
            onClick={next}
            className="text-sm font-semibold px-6 py-2 rounded-lg transition-all"
            style={{ background: '#ff8e6e', color: '#0a1628' }}
          >
            {isLast ? 'Done' : 'Next'}
          </button>
        </div>
      </div>
    </div>
  );
}
