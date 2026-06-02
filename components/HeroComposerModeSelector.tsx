"use client"

import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Check, Sparkles } from 'lucide-react';
import type { translations } from '../utils/i18n';

export type ComposerMode = 'research' | 'verify' | 'explain';

interface Props {
    mode: ComposerMode;
    onChange: (mode: ComposerMode) => void;
    t: typeof translations['en'];
}

/**
 * Claude-style in-input mode selector for the landing hero composer (S5.2).
 * Sits at the input wrapper's internal bottom-LEFT; the ArrowUp submit button
 * is its bottom-RIGHT sibling. Selecting a mode is state-only — it never
 * submits; submit routing reads `mode` in LandingPage.handleHeroSubmit.
 *
 * Surface mirrors LandingSettingsDropdown (white shell on the .light hero
 * zone — NOT the Navbar dark glass). Dropdown pops UPWARD (bottom-full) and is
 * left-aligned so it extends rightward into the input and never overflows the
 * left viewport edge on mobile (trigger is at the input's far left).
 */
export default function HeroComposerModeSelector({ mode, onChange, t }: Props) {
    const [open, setOpen] = useState(false);
    const ref = useRef<HTMLDivElement>(null);

    const modes: { key: ComposerMode; label: string; desc: string; pro?: boolean }[] = [
        { key: 'research', label: t.research, desc: t.composerModeDescResearch },
        { key: 'verify', label: t.verify, desc: t.composerModeDescVerify },
        { key: 'explain', label: t.explain, desc: t.composerModeDescExplain, pro: true },
    ];
    const current = modes.find(m => m.key === mode) ?? modes[0];

    // Outside-click + Escape close (same pattern as LandingSettingsDropdown).
    useEffect(() => {
        if (!open) return;
        function handleClick(e: MouseEvent) {
            if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
        }
        function handleKey(e: KeyboardEvent) {
            if (e.key === 'Escape') setOpen(false);
        }
        document.addEventListener('mousedown', handleClick);
        document.addEventListener('keydown', handleKey);
        return () => {
            document.removeEventListener('mousedown', handleClick);
            document.removeEventListener('keydown', handleKey);
        };
    }, [open]);

    const select = (key: ComposerMode) => {
        onChange(key);
        setOpen(false);
    };

    return (
        <div className="relative" ref={ref}>
            <button
                type="button"
                aria-haspopup="listbox"
                aria-expanded={open}
                onClick={() => setOpen(o => !o)}
                className="flex items-center gap-1 pl-3 pr-2 py-1.5 rounded-full text-sm font-medium text-text/70 border border-text/15 bg-text/5 transition-colors hover:bg-text/10 hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
            >
                <span>{current.label}</span>
                <ChevronDown size={14} strokeWidth={2} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
            </button>

            {open && (
                <div
                    role="listbox"
                    className="absolute bottom-full left-0 mb-2 rounded-xl shadow-2xl border border-text/10 p-1.5 z-50 w-72 max-w-[calc(100vw-2rem)]"
                    style={{ background: 'rgba(255, 255, 255, 0.97)', backdropFilter: 'blur(20px)' }}
                >
                    {modes.map(m => {
                        const active = m.key === mode;
                        return (
                            <button
                                key={m.key}
                                type="button"
                                role="option"
                                aria-selected={active}
                                onClick={() => select(m.key)}
                                className="w-full flex items-start gap-2.5 px-3 py-2.5 rounded-lg text-left transition-colors hover:bg-text/5 focus-visible:outline-none focus-visible:bg-text/5"
                            >
                                <span className="mt-0.5 flex-shrink-0 w-4">
                                    {active && <Check size={16} strokeWidth={2.5} className="text-brand" />}
                                </span>
                                <span className="min-w-0 flex-1">
                                    <span className="flex items-center gap-2">
                                        <span className="text-sm font-medium text-text">{m.label}</span>
                                        {m.pro && (
                                            <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium bg-brand/15 text-brand">
                                                <Sparkles size={11} strokeWidth={2} />
                                                Pro
                                            </span>
                                        )}
                                    </span>
                                    <span className="block text-sm text-text/60 leading-snug mt-0.5">{m.desc}</span>
                                </span>
                            </button>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
