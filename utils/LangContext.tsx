"use client"

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { LANGUAGES, type LangCode } from './i18n';

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
    try { localStorage.setItem(STORAGE_KEY, l); } catch {}
  };

  // Post-mount: hydrate from localStorage if a valid preference is stored.
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) return;
      const isValid = LANGUAGES.some((l) => l.code === stored);
      if (!isValid) return;
      setLangState((prev) => (stored !== prev ? (stored as LangCode) : prev));
    } catch {}
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
