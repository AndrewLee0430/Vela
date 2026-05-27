"use client"

import { useState, useRef, useEffect } from 'react';
import { LANGUAGES, type LangCode } from '../utils/i18n';
import { useLang } from '../utils/LangContext';

interface LanguageSwitcherProps {
  /** Render compact style for navbar dropdown */
  compact?: boolean;
}

export default function LanguageSwitcher({ compact }: LanguageSwitcherProps) {
  const { lang, setLang } = useLang();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const current = LANGUAGES.find(l => l.code === lang)!;

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  // Compact mode: inline expandable grid (for embedding inside another dropdown)
  if (compact) {
    return (
      <div>
        <button
          onClick={() => setOpen(o => !o)}
          className="flex items-center gap-1.5 w-full px-4 py-2 text-sm transition-colors text-text/70"
          onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.05)'; }}
          onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
        >
          <span>🌐</span>
          <span className="font-medium">{current.short}</span>
          <span className="ml-auto text-xs text-text/40">{current.label}</span>
          <svg
            width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
            style={{ transform: open ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
        {open && (
          <div className="grid grid-cols-2 gap-0.5 px-1 pb-1 max-h-48 overflow-y-auto">
            {LANGUAGES.map(l => (
              <button
                key={l.code}
                onClick={() => { setLang(l.code); setOpen(false); }}
                className="flex items-center gap-1.5 px-2 py-1.5 rounded text-xs text-left transition-colors"
                style={{
                  background: l.code === lang ? 'rgb(var(--color-brand) / 0.12)' : 'transparent',
                  color: l.code === lang ? 'rgb(var(--color-brand))' : 'rgb(var(--color-text) / 0.6)',
                }}
                onMouseEnter={e => {
                  if (l.code !== lang) (e.currentTarget as HTMLElement).style.background = 'rgb(var(--color-text) / 0.06)';
                }}
                onMouseLeave={e => {
                  if (l.code !== lang) (e.currentTarget as HTMLElement).style.background = 'transparent';
                }}
              >
                <span className="font-semibold w-6 text-right" style={{ opacity: 0.6, fontSize: '10px' }}>{l.short}</span>
                <span>{l.label}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Default mode: standalone button with floating popup (for footer etc.)
  return (
    <div ref={ref} className="relative inline-block">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1.5 rounded-lg text-xs transition-colors px-3 py-1.5 bg-text/8 border border-text/12 text-text/50"
        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = 'white'; }}
        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,0.5)'; }}
      >
        <span>🌐</span>
        <span className="font-medium">{current.short}</span>
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <polyline points="6 15 12 9 18 15" />
        </svg>
      </button>

      {open && (
        <div
          className="absolute z-50 rounded-xl p-3 bottom-full left-1/2 mb-2 border border-text/12"
          style={{
            transform: 'translateX(-50%)',
            background: '#0f1a2e',
            boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
            minWidth: '320px',
          }}
        >
          <div className="grid grid-cols-2 gap-1">
            {LANGUAGES.map(l => (
              <button
                key={l.code}
                onClick={() => { setLang(l.code); setOpen(false); }}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs text-left transition-colors"
                style={{
                  background: l.code === lang ? 'rgb(var(--color-brand) / 0.12)' : 'transparent',
                  color: l.code === lang ? 'rgb(var(--color-brand))' : 'rgb(var(--color-text) / 0.6)',
                }}
                onMouseEnter={e => {
                  if (l.code !== lang) (e.currentTarget as HTMLElement).style.background = 'rgb(var(--color-text) / 0.06)';
                }}
                onMouseLeave={e => {
                  if (l.code !== lang) (e.currentTarget as HTMLElement).style.background = 'transparent';
                }}
              >
                <span className="font-semibold w-8 text-right" style={{ opacity: 0.6 }}>{l.short}</span>
                <span>{l.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
