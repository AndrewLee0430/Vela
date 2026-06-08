import { useState, useEffect, useCallback } from 'react';
import { LANGUAGES, type LangCode } from '../utils/i18n';
import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';
import { track } from '../utils/analytics';
import { useAuth } from '@clerk/nextjs';
import {
  setWorkplace,
  setRole,
  setWorkLanguage,
  completeOnboarding,
} from '../utils/userContext';
import { postContextHash } from '../utils/contextSync';
import { WORKPLACES, ROLES_BY_WORKPLACE, FALLBACK_ROLES, nearestLang } from '../utils/contextOptions';

// PRD §3.2 — first-run context collector (workplace / role / answer-language) +
// a privacy card. SEPARATE from components/OnboardingOverlay.tsx (the signed-in
// Dashboard feature tour, gated on `hasSeenOnboarding`): this wizard is gated on
// `vela_user_context.onboarding_completed`, runs for anonymous L0 users (no auth),
// and writes context THROUGH utils/userContext.ts (no parallel writer). Option sets
// live in utils/contextOptions.ts (shared with the Settings My-Context tab).

export default function OnboardingWizard({ onClose }: { onClose: () => void }) {
  const { lang, setLang } = useLang();
  const { getToken } = useAuth();
  const ui = getUI(lang);

  const [step, setStep] = useState(0); // 0=workplace 1=role 2=language 3=privacy
  const [workplace, setWorkplaceSel] = useState<string | null>(null);
  const [role, setRoleSel] = useState<string | null>(null);
  const [langSel, setLangSel] = useState<LangCode>('en');
  const [completedCount, setCompletedCount] = useState(0);

  useEffect(() => {
    setLangSel(nearestLang());
  }, []);

  const roleOptions = workplace ? ROLES_BY_WORKPLACE[workplace] ?? FALLBACK_ROLES : FALLBACK_ROLES;

  // Mark done + emit the completion event, then close. Hash is already fresh from
  // the awaited per-step writes, so no recompute is needed here.
  const finishOnboarding = useCallback((stepsDone: number, wp: string | null) => {
    completeOnboarding();
    track('onboarding_completed', {
      total_steps_completed: stepsDone,
      workplace_category: wp, // coarse Step-1 enum or null; NOT role_category (PHASE E)
    });
    // PHASE E: sync the (already-fresh) hash to the backend. Pro-gated + silent
    // inside contextSync — anon/free users no-op (no token / not Pro-cached).
    void postContextHash(() => getToken({ skipCache: true }));
    onClose();
  }, [onClose, getToken]);

  // Step 1 — workplace
  const submitWorkplace = async (skipped: boolean) => {
    const value = skipped ? null : workplace;
    await setWorkplace(value); // awaited so the cached hash is fresh BEFORE the event
    track('onboarding_step_completed', { step: 1, skipped });
    if (skipped) setWorkplaceSel(null);
    else setCompletedCount((c) => c + 1);
    setStep(1);
  };

  // Step 2 — role
  const submitRole = async (skipped: boolean) => {
    const value = skipped ? null : role;
    await setRole(value);
    track('onboarding_step_completed', { step: 2, skipped });
    if (!skipped) setCompletedCount((c) => c + 1);
    setStep(2);
  };

  // Step 3 — answer language
  const submitLanguage = async (skipped: boolean) => {
    if (!skipped) {
      setLang(langSel);              // live UI switch + immediate vela_lang (LangContext)
      await setWorkLanguage(langSel); // awaited canonical dual-write + hash before the event
      setCompletedCount((c) => c + 1);
    }
    track('onboarding_step_completed', { step: 3, skipped });
    setStep(3);
  };

  const back = () => setStep((s) => Math.max(0, s - 1));

  // Esc / backdrop — skip the rest, mark done so it never re-pops.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') finishOnboarding(completedCount, workplace);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [finishOnboarding, completedCount, workplace]);

  const dot = (i: number) => (
    <div
      key={i}
      className="h-1.5 rounded-full transition-all duration-300"
      style={{ width: i === step ? 28 : 10, background: i === step ? 'rgb(var(--color-brand))' : 'rgb(var(--color-text) / 0.2)' }}
    />
  );

  const skipBtn = (onClick: () => void) => (
    <button onClick={onClick} className="text-sm px-4 py-2 rounded-lg transition-colors text-text/50">
      {ui.onboardingSkip}
    </button>
  );
  const backBtn = (
    <button onClick={back} className="text-sm px-4 py-2 rounded-lg transition-colors text-text/50">
      {ui.onboardingBack}
    </button>
  );
  const primaryBtn = (label: string, onClick: () => void) => (
    <button
      onClick={onClick}
      className="text-sm font-semibold px-6 py-2 rounded-lg transition-all"
      style={{ background: 'rgb(var(--color-brand))', color: '#0a1628' }}
    >
      {label}
    </button>
  );

  return (
    <div
      className="fixed inset-0 z-[9999] flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.72)' }}
      onClick={() => finishOnboarding(completedCount, workplace)}
    >
      <div
        className="relative rounded-2xl px-8 py-6 shadow-2xl w-full max-w-[460px] border border-text/12"
        style={{ background: 'rgb(var(--color-bg-2))' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 mb-4">{[0, 1, 2, 3].map(dot)}</div>

        {/* Step 1 — Workplace */}
        {step === 0 && (
          <>
            <p className="text-2xl font-semibold text-text mb-4">{ui.onboardingWorkplaceTitle}</p>
            <div className="grid grid-cols-2 gap-3 mb-3">
              {WORKPLACES.map(({ value, icon, labelKey }) => {
                const selected = workplace === value;
                return (
                  <button
                    key={value}
                    onClick={() => setWorkplaceSel(value)}
                    className={`flex flex-col items-center gap-2 px-3 py-4 rounded-xl border transition-all ${selected ? 'border-brand bg-brand/10 text-brand' : 'border-text/10 bg-text/[0.04] text-text/70 hover:bg-text/8 hover:border-text/20'}`}
                  >
                    <span className="text-2xl">{icon}</span>
                    <span className="text-sm font-medium">{ui[labelKey]}</span>
                  </button>
                );
              })}
            </div>
            {workplace === 'hospital' && (
              <p className="text-xs leading-relaxed text-text/50 mb-2">{ui.onboardingHospitalNudge}</p>
            )}
            <div className="flex items-center justify-between mt-6">
              {skipBtn(() => submitWorkplace(true))}
              {primaryBtn(ui.onboardingNext, () => submitWorkplace(false))}
            </div>
          </>
        )}

        {/* Step 2 — Role */}
        {step === 1 && (
          <>
            <p className="text-2xl font-semibold text-text mb-4">{ui.onboardingRoleTitle}</p>
            <div className="flex flex-col gap-2 mb-3 max-h-[46vh] overflow-y-auto">
              {roleOptions.map(({ value, labelKey }) => {
                const selected = role === value;
                return (
                  <button
                    key={value}
                    onClick={() => setRoleSel(value)}
                    className={`text-left px-4 py-2.5 rounded-lg border text-sm transition-all ${selected ? 'border-brand bg-brand/10 text-brand' : 'border-text/10 bg-text/[0.04] text-text/70 hover:bg-text/8 hover:border-text/20'}`}
                  >
                    {ui[labelKey]}
                  </button>
                );
              })}
            </div>
            <div className="flex items-center justify-between mt-6">
              {backBtn}
              <div className="flex items-center gap-1">
                {skipBtn(() => submitRole(true))}
                {primaryBtn(ui.onboardingNext, () => submitRole(false))}
              </div>
            </div>
          </>
        )}

        {/* Step 3 — Answer language */}
        {step === 2 && (
          <>
            <p className="text-2xl font-semibold text-text mb-4">{ui.onboardingLangTitle}</p>
            <select
              aria-label={ui.onboardingLangTitle}
              value={langSel}
              onChange={(e) => setLangSel(e.target.value as LangCode)}
              className="w-full bg-text/[0.05] border border-text/15 text-text/80 rounded-lg px-3 py-2.5 text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-brand/30 mb-3"
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>{l.label} ({l.code})</option>
              ))}
            </select>
            <p className="text-xs leading-relaxed text-text/50">{ui.onboardingLangHelper}</p>
            <div className="flex items-center justify-between mt-6">
              {backBtn}
              <div className="flex items-center gap-1">
                {skipBtn(() => submitLanguage(true))}
                {primaryBtn(ui.onboardingNext, () => submitLanguage(false))}
              </div>
            </div>
          </>
        )}

        {/* Step 4 — Privacy card (§3.4 touchpoint 2) */}
        {step === 3 && (
          <>
            <p className="text-2xl font-semibold text-text mb-4">{ui.onboardingPrivacyTitle}</p>
            <ul className="flex flex-col gap-2.5 mb-2">
              {[ui.onboardingPrivacyOnDevice, ui.onboardingPrivacyNotRecorded, ui.onboardingPrivacyEditable, ui.onboardingPrivacyNoAccount].map((line, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-text/70">
                  <span style={{ color: 'rgb(var(--color-success))' }}>✓</span>
                  <span>{line}</span>
                </li>
              ))}
            </ul>
            <div className="flex items-center justify-between mt-6">
              {backBtn}
              {primaryBtn(ui.onboardingDone, () => finishOnboarding(completedCount, workplace))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
