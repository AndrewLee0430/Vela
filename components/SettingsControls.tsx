"use client"

import { useState } from 'react';
import { Sun, Moon, Monitor } from 'lucide-react';
import { LANGUAGES, type LangCode } from '../utils/i18n';
import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';

interface SettingsControlsProps {
    /** Surface the controls render on — only affects native <option> styling.
     *  Theme card + select chrome use design tokens that resolve per .dark/.light zone. */
    surface?: 'dark' | 'light';
}

/**
 * Shared settings controls: Theme 3-card toggle + Language native <select>.
 * Reused by the functional-pages Navbar dropdown (surface="dark") and the
 * landing settings dropdown (surface="light").
 *
 * Theme toggle is COSMETIC ONLY — local useState, no persistence, no actual
 * theme switching. Stage 3 will replace `themePref` with next-themes useTheme()
 * in this one place.
 */
export default function SettingsControls({ surface = 'dark' }: SettingsControlsProps) {
    const { lang, setLang } = useLang();
    const ui = getUI(lang);
    const [themePref, setThemePref] = useState<'light' | 'dark' | 'system'>('light');

    const optionStyle = surface === 'light'
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
                        const selected = themePref === value;
                        return (
                            <button
                                key={value}
                                type="button"
                                role="radio"
                                aria-checked={selected}
                                onClick={() => setThemePref(value)}
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
