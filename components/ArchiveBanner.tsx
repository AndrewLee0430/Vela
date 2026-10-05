"use client"

import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';
import { RTL_LANGS } from '../utils/i18n';
import { ARCHIVE_MODE, SHOWCASE_URL } from '../utils/archiveMode';

/**
 * Archive car (2026-10-05): a slim banner above every page when the build
 * carries NEXT_PUBLIC_ARCHIVE_MODE=true. Renders nothing otherwise, so the
 * non-archive build is unchanged. Token colours only; in normal flow (not
 * fixed) so it never covers MobileNav or a page's own fixed chrome.
 */
export default function ArchiveBanner() {
    const { lang } = useLang();
    if (!ARCHIVE_MODE) return null;
    const ui = getUI(lang);
    return (
        <div
            role="note"
            dir={RTL_LANGS.includes(lang) ? 'rtl' : undefined}
            className="w-full px-4 py-1.5 text-center text-xs leading-relaxed border-b border-text/10 bg-text/5 text-text/70"
        >
            <span>{ui.archiveBanner}</span>{' '}
            <a href={SHOWCASE_URL} className="font-medium underline underline-offset-2 text-text/85 hover:text-text">
                {ui.archiveShowcaseLink}
            </a>
        </div>
    );
}
