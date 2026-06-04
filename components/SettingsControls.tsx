"use client"

import { useState, useEffect } from 'react';
import { useTheme } from 'next-themes';
import { Sun, Moon, Monitor } from 'lucide-react';
import { LANGUAGES, type LangCode } from '../utils/i18n';
import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';

interface SettingsControlsProps {
    /** Force the native <option> palette to a fixed surface. Omit to follow the
     *  live resolved theme (functional pages). The landing passes "light" to force
     *  light options because it is forced-light via its `.light` wrapper while the
     *  global resolvedTheme may be dark — the override decouples the two.
     *  Only affects native <option> styling; the <select> chrome + theme cards use
     *  design tokens that resolve per .dark/.light zone. */
    surface?: 'dark' | 'light';
}

/**
 * Shared settings controls: Theme 3-card toggle + Language native <select>.
 * Reused by the functional-pages Navbar dropdown (surface="dark") and the
 * landing settings dropdown (surface="light").
 *
 * Theme toggle is wired to next-themes `useTheme()` (Stage 3.2) — selecting a
 * card persists + switches the theme (`attribute="class"`, defaultTheme="dark").
 * Selected state derives from `theme` (the user's choice, so "system" highlights
 * correctly) — NOT `resolvedTheme`. A `mounted` guard avoids a hydration mismatch
 * since `theme` is undefined on the server (preserves 3.1's zero-warning state).
 */
export default function SettingsControls({ surface }: SettingsControlsProps) {
    const { lang, setLang } = useLang();
    const ui = getUI(lang);
    const { theme, setTheme, resolvedTheme } = useTheme();
    const [mounted, setMounted] = useState(false);
    useEffect(() => setMounted(true), []);
    // Pre-mount (SSR + first client render) shows 'dark' selected to match
    // defaultTheme="dark"; post-mount reflects the real stored theme.
    const current = mounted ? (theme ?? 'dark') : 'dark';

    // Native <option> palette: explicit `surface` (landing forced-light) wins;
    // otherwise follow the actual resolved theme. Pre-mount = dark to match
    // defaultTheme="dark", so SSR and first client render agree (no hydration
    // drift); options only become visible after the dropdown opens (post-mount).
    const optionSurface = surface ?? (mounted && resolvedTheme === 'light' ? 'light' : 'dark');
    const optionStyle = optionSurface === 'light'
        ? { background: '#ffffff', color: '#171717' }
        : { background: '#0f172a', color: '#fff' };

    return (
        <>
            {/* Theme toggle — cosmetic only (Stage 3 wires next-themes useTheme()) */}
            <div className="px-4 py-3 border-b border-text/7">
                <p className="text-xs font-semibold mb-2" style={{ color: 'rgb(var(--color-text) / 0.5)' }}>{ui.theme}</p>
                <div role="radiogroup" aria-label={ui.theme} className="flex gap-2">
                    {([
                        { value: 'light' as const, label: ui.themeLight, Icon: Sun },
                        { value: 'dark' as const, label: ui.themeDark, Icon: Moon },
                        { value: 'system' as const, label: ui.themeSystem, Icon: Monitor },
                    ]).map(({ value, label, Icon }) => {
                        const selected = current === value;
                        return (
                            <button
                                key={value}
                                type="button"
                                role="radio"
                                aria-checked={selected}
                                onClick={() => setTheme(value)}
                                className={`flex-1 flex flex-col items-center gap-1 px-2 py-2 rounded-lg border text-xs transition-all duration-200 ${selected ? 'border-brand bg-brand/10 text-brand' : 'border-text/10 bg-text/[0.04] text-text/60 hover:bg-text/8 hover:border-text/20'}`}
                            >
                                <Icon size={16} strokeWidth={1.8} />
                                <span className="font-medium">{label}</span>
                            </button>
                        );
                    })}
                </div>
            </div>

            {/* Language */}
            <div className="px-4 py-3 border-b border-text/7">
                <select
                    aria-label="Language"
                    value={lang}
                    onChange={(e) => setLang(e.target.value as LangCode)}
                    className="w-full bg-text/[0.05] border border-text/15 text-text/80 rounded-lg px-3 py-2 text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-brand/30"
                >
                    {LANGUAGES.map(l => (
                        <option key={l.code} value={l.code} style={optionStyle}>
                            {l.label} ({l.code})
                        </option>
                    ))}
                </select>
            </div>
        </>
    );
}
