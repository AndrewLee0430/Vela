"use client"

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { LANGUAGES, type LangCode } from './i18n';
import { getWorkLanguage, setWorkLanguage, ensureFresh, readRaw } from './userContext';

const STORAGE_KEY = 'vela_lang';

interface LangContextValue {
  lang: LangCode;
  setLang: (l: LangCode) => void;
}

const LangCtx = createContext<LangContextValue>({ lang: 'en', setLang: () => {} });

export function LangProvider({ children }: { children: ReactNode }) {
  // First render must match SSR output ('en') to avoid hydration mismatch.
  // localStorage is read post-mount in the effect below.
  const [lang, setLangState] = useState<LangCode>(() => {
    if (typeof window === 'undefined') return 'en';
    return 'en';
  });

  const setLang = (l: LangCode) => {
    setLangState(l);
    try { localStorage.setItem(STORAGE_KEY, l); } catch {} // immediate legacy write — UI stays instant
    // Dual-write the canonical blob + cache the recomputed hash (async, fire-and-forget;
    // analytics reads the cached hash synchronously). PRD §3.1 PHASE C / G3.
    void setWorkLanguage(l);
  };

  // Post-mount: hydrate from the canonical store. Read order (§2.9 fix):
  // vela_user_context.work_language first, legacy vela_lang as fallback.
  useEffect(() => {
    try {
      const stored = getWorkLanguage();
      if (!stored) return;
      const isValid = LANGUAGES.some((l) => l.code === stored);
      if (!isValid) return;
      setLangState((prev) => (stored !== prev ? (stored as LangCode) : prev));
    } catch {}
  }, []);

  // Post-mount migration + self-repair (PRD §3.1 PHASE C). If a legacy vela_lang
  // exists but the canonical blob has no work_language, migrate it (dual-write +
  // hash). Otherwise just self-repair the cached hash. No default 'en' is ever
  // injected — a user who never chose a language keeps work_language null (PHASE
  // D onboarding populates it); only the derived hash is cached (sentinel when
  // the context is all-null) so user_context_hash stops shipping null.
  useEffect(() => {
    (async () => {
      try {
        const legacy = localStorage.getItem(STORAGE_KEY);
        const blobWorkLang = readRaw().work_language;
        if (legacy && !blobWorkLang && LANGUAGES.some((l) => l.code === legacy)) {
          await setWorkLanguage(legacy);
        } else {
          await ensureFresh();
        }
      } catch {}
    })();
  }, []);

  // Sync across tabs
  useEffect(() => {
    function onStorage(e: StorageEvent) {
      if (e.key === STORAGE_KEY && e.newValue) {
        setLangState(e.newValue as LangCode);
      }
    }
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  useEffect(() => {
    if (typeof document !== 'undefined') {
      document.documentElement.lang = lang;
    }
  }, [lang]);

  return <LangCtx.Provider value={{ lang, setLang }}>{children}</LangCtx.Provider>;
}

export function useLang() {
  return useContext(LangCtx);
}
