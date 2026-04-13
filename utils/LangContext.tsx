"use client"

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import type { LangCode } from './i18n';

const STORAGE_KEY = 'vela_lang';

interface LangContextValue {
  lang: LangCode;
  setLang: (l: LangCode) => void;
}

const LangCtx = createContext<LangContextValue>({ lang: 'en', setLang: () => {} });

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<LangCode>(() => {
    if (typeof window === 'undefined') return 'en';
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) return stored as LangCode;
    } catch {}
    return 'en';
  });

  const setLang = (l: LangCode) => {
    setLangState(l);
    try { localStorage.setItem(STORAGE_KEY, l); } catch {}
  };

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

  return <LangCtx.Provider value={{ lang, setLang }}>{children}</LangCtx.Provider>;
}

export function useLang() {
  return useContext(LangCtx);
}
