import Link from 'next/link';
import Image from 'next/image';
import Head from 'next/head';
import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';

const ACCENT = 'rgb(var(--color-brand))';

function CheckIcon() {
    return (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="flex-shrink-0 mt-0.5">
            <path d="M3 8.5L6.5 12L13 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
    );
}

export default function Pricing() {
    const { lang } = useLang();
    const ui = getUI(lang);

    const FREE_FEATURES = [
        ui.pricingFree1, ui.pricingFree2, ui.pricingFree3,
        ui.pricingFree4, ui.pricingFree5, ui.pricingFree6,
    ];
    const PRO_FEATURES = [
        ui.pricingPro1, ui.pricingPro2, ui.pricingPro3,
        ui.pricingPro4, ui.pricingPro5, ui.pricingPro6,
    ];

    return (
        <>
            <Head>
                <title>Pricing - Vela</title>
                <meta name="description" content="Simple, transparent pricing for healthcare professionals. Start free, upgrade when you need more." />
            </Head>

            <main className="min-h-screen flex flex-col bg-app-bg">
                {/* Nav */}
                <nav className="border-b border-text/7">
                    <div className="container mx-auto px-4 py-3 flex items-center justify-between">
                        <Link href="/" className="flex items-center">
                            <Image src="/coral_logo.png" alt="Vela" width={40} height={40} style={{ objectFit: 'contain' }} />
                        </Link>
                        <Link
                            href="/sign-up"
                            className="text-sm font-medium px-4 py-1.5 rounded-lg transition-opacity hover:opacity-90"
                            style={{ background: ACCENT, color: '#fff' }}
                        >
                            {ui.getStarted}
                        </Link>
                    </div>
                </nav>

                {/* Header */}
                <div className="container mx-auto px-4 pt-16 pb-10 text-center">
                    <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-text">{ui.pricingTitle}</h1>
                    <p className="mt-3 text-base text-text/50">
                        {ui.pricingSubtitle}
                    </p>
                </div>

                {/* Cards */}
                <div className="container mx-auto px-4 pb-20 flex-1">
                    <div className="max-w-3xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6">

                        {/* Free Plan */}
                        <div className="rounded-xl p-6 flex flex-col bg-text/4 border border-text/10">
                            <h2 className="text-lg font-semibold text-text">Free</h2>
                            <div className="mt-4 mb-6">
                                <span className="text-3xl font-bold text-text">$0</span>
                                <span className="text-sm ml-1 text-text/40">{ui.perMonth}</span>
                            </div>

                            <ul className="space-y-3 flex-1">
                                {FREE_FEATURES.map((f, i) => (
                                    <li key={i} className="flex items-start gap-2.5 text-sm text-text/70">
                                        <CheckIcon />{f}
                                    </li>
                                ))}
                            </ul>

                            <Link
                                href="/sign-up"
                                className="mt-8 block text-center text-sm font-medium py-2.5 rounded-lg transition-all cursor-pointer border border-text/20 text-text/80"
                                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgb(var(--color-text) / 0.1)'; }}
                                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
                            >
                                {ui.getStartedFree}
                            </Link>
                        </div>

                        {/* Pro Plan */}
                        <div
                            className="rounded-xl p-6 flex flex-col relative"
                            style={{ background: 'rgb(var(--color-brand) / 0.06)', border: `1px solid rgb(var(--color-brand) / 0.35)` }}
                        >
                            {/* Badge */}
                            <span
                                className="absolute -top-3 right-6 text-xs font-semibold px-3 py-1 rounded-full"
                                style={{ background: ACCENT, color: '#fff' }}
                            >
                                {ui.recommended}
                            </span>

                            <h2 className="text-lg font-semibold text-text">Pro</h2>
                            <div className="mt-4 mb-1">
                                <span className="text-3xl font-bold text-text">$9.99</span>
                                <span className="text-sm ml-1 text-text/40">{ui.perMonth}</span>
                            </div>
                            <p className="text-xs mb-6 text-text/40">
                                {ui.orYearly}
                            </p>

                            <ul className="space-y-3 flex-1">
                                {PRO_FEATURES.map((f, i) => (
                                    <li key={i} className="flex items-start gap-2.5 text-sm text-text/70">
                                        <CheckIcon />{f}
                                    </li>
                                ))}
                            </ul>

                            {/* text-white KEPT deliberately on the next line: this CTA sits on the
                                CONSTANT brand background (ACCENT), scheme-invariant — the guard
                                allow-lists exactly this line. Same class as the nav button's inline #fff. */}
                            <Link
                                href="/sign-up"
                                className="mt-8 block text-center text-sm font-medium py-2.5 rounded-lg transition-opacity hover:opacity-90 text-white"
                                style={{ background: ACCENT }}
                            >
                                {ui.upgradeToPro}
                            </Link>

                            <p className="mt-3 text-xs text-center text-text/30">
                                {ui.subjectToFairUse}
                            </p>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="flex-shrink-0 flex flex-col items-center gap-2 px-4 py-5 text-sm border-t border-t-text/7 text-text/30">
                    <div>{ui.pricingDisclaimer}</div>
                    <div className="flex flex-wrap justify-center gap-4 text-xs">
                        <Link href="/terms" className="hover:text-text transition-colors">{ui.termsOfService}</Link>
                        <Link href="/privacy" className="hover:text-text transition-colors">{ui.privacyPolicy}</Link>
                        <Link href="/refund" className="hover:text-text transition-colors">{ui.refundPolicy}</Link>
                        <a href="mailto:support@an-tho.com" className="hover:text-text transition-colors">support@an-tho.com</a>
                    </div>
                </div>
            </main>
        </>
    );
}
