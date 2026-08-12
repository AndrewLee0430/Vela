"use client"

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { Settings } from 'lucide-react';
import { SignedOut } from '@clerk/nextjs';
import { useLang } from '../utils/LangContext';
import { translations } from '../utils/i18n';
import SettingsControls from './SettingsControls';

/**
 * Anon-trimmed settings dropdown for the landing top-right gear.
 * Surfaces Theme + Language (shared SettingsControls) plus a Sign In row and
 * a Privacy Policy link. No Pro/credits/shares/subscription/UserButton (anon).
 * Surface follows the theme (Stage 3.8): bg-1 token shell (white in light, navy in
 * dark) — the landing now respects the global theme, so this is no longer forced light.
 */
export default function LandingSettingsDropdown() {
    const { lang } = useLang();
    const t = translations[lang];
    const [open, setOpen] = useState(false);
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        function handleClick(e: MouseEvent) {
            if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
        }
        if (open) document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, [open]);

    return (
        <div className="relative" ref={ref}>
            <button
                type="button"
                aria-label="Settings"
                aria-expanded={open}
                onClick={() => setOpen(prev => !prev)}
                className="p-2.5 rounded-lg transition-all text-text/50 hover:text-text/80 hover:bg-text/8"
                style={open ? { color: 'rgb(var(--color-text))', background: 'rgb(var(--color-text) / 0.08)' } : undefined}
            >
                <Settings size={18} strokeWidth={1.8} />
            </button>

            {open && (
                /* fixed (not absolute) — gear is mid-nav, so absolute right-0 anchors to gear's
                   right edge ~180px from viewport, overflowing on mobile. fixed anchors to viewport.
                   top-[72px] matches the current single-row landing nav height; update if nav changes. */
                <div
                    className="fixed right-4 md:right-10 top-[72px] rounded-xl shadow-2xl border border-text/10 py-2 z-50 max-h-[calc(100vh-5rem)] overflow-y-auto w-[300px] max-w-[calc(100vw-2rem)]"
                    style={{
                        background: 'rgb(var(--color-bg-1) / 0.97)',
                        backdropFilter: 'blur(20px)',
                    }}
                >
                    <SettingsControls hideTheme /> {/* B4 D-B4-1: landing is light-only */}

                    {/* Sign In — anon entry point (matches the nav sign-in pill → /sign-in) */}
                    <SignedOut>
                        <Link
                            href="/sign-in"
                            onClick={() => setOpen(false)}
                            className="block w-full text-left px-4 py-2.5 text-sm font-medium transition-colors hover:bg-text/5"
                            style={{ color: 'rgb(var(--color-brand))' }}
                        >
                            {t.signIn}
                        </Link>
                    </SignedOut>

                    {/* Privacy Policy */}
                    <Link
                        href="/privacy"
                        onClick={() => setOpen(false)}
                        className="block w-full text-left px-4 py-2 text-xs transition-colors hover:bg-text/5 text-text/55"
                    >
                        {t.privacyPolicyLink}
                    </Link>
                </div>
            )}
        </div>
    );
}
