import { useEffect, useRef, useState } from 'react';
import { useUser, useAuth } from '@clerk/nextjs';
import { useRouter } from 'next/router';
import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';
import { readRaw } from '../utils/userContext';
import { getContextHash } from '../utils/contextSync';

// PRD §4.3 需求5 Trigger A — passive sign-in restore. Fires GET once on the
// sign-in transition (Pro only, silent on 404/403). Shows a DISMISSABLE info
// banner ONLY when the server has a context hash that DIFFERS from this device's
// — i.e. preferences were set on another device. Since the server stores only
// hash+locale (raw context is unrecoverable), the CTA re-opens the OnboardingWizard
// (via /?reonboard=1) rather than "restoring" fields. Locale is ignored (no locale
// UI until Phase 1C). NOT a blocking modal.
export default function ContextRestoreBanner() {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuth();
  const router = useRouter();
  const { lang } = useLang();
  const ui = getUI(lang);
  const prevSignedIn = useRef<boolean | null>(null);
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (!isLoaded) return;
    const cur = Boolean(isSignedIn);
    const prev = prevSignedIn.current;
    prevSignedIn.current = cur;
    if (!cur) return;
    if (prev === true) return; // already signed-in render, not a transition
    let cancelled = false;
    (async () => {
      const remote = await getContextHash(() => getToken({ skipCache: true }));
      if (cancelled || !remote) return; // 404 / 403 / free / error → silent
      const local = readRaw().user_context_hash ?? null;
      if (remote.hash && remote.hash !== local) setShow(true);
    })();
    return () => { cancelled = true; };
  }, [isLoaded, isSignedIn, getToken]);

  if (!show) return null;

  return (
    <div
      className="fixed top-0 inset-x-0 z-[9998] flex items-center justify-center gap-3 px-4 py-2.5 text-sm border-b border-text/10"
      style={{ background: 'rgb(var(--color-bg-2))', color: 'rgb(var(--color-text) / 0.8)' }}
      role="status"
    >
      <span>{ui.contextRestoreBody}</span>
      <button
        type="button"
        onClick={() => { setShow(false); router.push('/?reonboard=1'); }}
        className="font-semibold px-3 py-1 rounded-md transition-all"
        style={{ background: 'rgb(var(--color-brand))', color: '#0a1628' }}
      >
        {ui.contextRestoreCta}
      </button>
      <button
        type="button"
        onClick={() => setShow(false)}
        className="px-2 py-1 rounded-md text-text/50 hover:text-text transition-colors"
      >
        {ui.contextRestoreDismiss}
      </button>
    </div>
  );
}
