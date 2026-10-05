import Head from 'next/head';
import Link from 'next/link';
import Image from 'next/image';
import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';
import { getExtra } from '../utils/i18n-extra';
import { RTL_LANGS } from '../utils/i18n';
import { SHOWCASE_URL } from '../utils/archiveMode';

/**
 * Archive car (2026-10-05): what a retired route (/verify, /explain, /pricing,
 * /sign-in, /sign-up) renders in an archive-mode build. Two exits — the one
 * live feature (Research) and the static showcase. noindex: these URLs no
 * longer describe a working page.
 */
export default function ArchivedFeatureNotice() {
    const { lang } = useLang();
    const ui = getUI(lang);
    const extra = getExtra(lang);
    return (
        <>
            <Head>
                <meta name="robots" content="noindex, nofollow" />
            </Head>
            <main
                dir={RTL_LANGS.includes(lang) ? 'rtl' : undefined}
                className="min-h-screen flex flex-col items-center justify-center px-4 text-center bg-app-bg"
            >
                <Link href="/" className="flex items-center">
                    <Image src="/coral_logo.png" alt="Vela" width={48} height={48} style={{ objectFit: 'contain' }} />
                </Link>
                <p className="mt-6 max-w-md text-base leading-relaxed text-text/80">
                    {ui.archivedFeatureNotice}
                </p>
                <div className="mt-6 flex flex-wrap justify-center gap-3 text-sm font-medium">
                    <Link
                        href="/research"
                        className="px-4 py-2 rounded-lg border border-brand/40 bg-brand/10 text-brand transition-opacity hover:opacity-90"
                    >
                        {extra.navResearch}
                    </Link>
                    <a
                        href={SHOWCASE_URL}
                        className="px-4 py-2 rounded-lg border border-text/20 text-text/80 transition-colors hover:bg-text/5"
                    >
                        {ui.archiveShowcaseLink}
                    </a>
                </div>
            </main>
        </>
    );
}
