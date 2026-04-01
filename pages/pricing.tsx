import Link from 'next/link';
import Image from 'next/image';
import Head from 'next/head';

const ACCENT = '#ff8e6e';

const FREE_FEATURES = [
    '10 credits per day (resets daily)',
    'Research: 3 credits per query',
    'Verify: 1 credit per query',
    'Explain: 2 credits per query',
    'PubMed 36M+ literature search',
    'FDA drug label data',
    '10 languages supported',
];

const PRO_FEATURES = [
    'Up to 100 credits per day*',
    'Everything in Free, plus:',
    'Unlimited research depth',
    'Priority response time',
    '7-day money-back guarantee',
];

function CheckIcon() {
    return (
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="flex-shrink-0 mt-0.5">
            <path d="M3 8.5L6.5 12L13 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
    );
}

export default function Pricing() {
    return (
        <>
            <Head>
                <title>Pricing - Vela</title>
                <meta name="description" content="Simple, transparent pricing for healthcare professionals. Start free, upgrade when you need more." />
            </Head>

            <main className="min-h-screen flex flex-col" style={{ background: "linear-gradient(135deg, #0a1628 0%, #0f2040 45%, #1a1035 75%, #0d1a2e 100%)" }}>
                {/* Nav */}
                <nav className="border-b" style={{ background: "transparent", borderColor: "rgba(255,255,255,0.07)" }}>
                    <div className="container mx-auto px-4 py-3 flex items-center justify-between">
                        <Link href="/" className="flex items-center">
                            <Image src="/coral_logo.png" alt="Vela" width={40} height={40} style={{ objectFit: 'contain' }} />
                        </Link>
                        <Link
                            href="/sign-up"
                            className="text-sm font-medium px-4 py-1.5 rounded-lg transition-opacity hover:opacity-90"
                            style={{ background: ACCENT, color: '#fff' }}
                        >
                            Get Started
                        </Link>
                    </div>
                </nav>

                {/* Header */}
                <div className="container mx-auto px-4 pt-16 pb-10 text-center">
                    <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-white">Pricing</h1>
                    <p className="mt-3 text-base" style={{ color: 'rgba(255,255,255,0.5)' }}>
                        Simple, transparent pricing for healthcare professionals.
                    </p>
                </div>

                {/* Cards */}
                <div className="container mx-auto px-4 pb-20 flex-1">
                    <div className="max-w-3xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6">

                        {/* Free Plan */}
                        <div
                            className="rounded-xl p-6 flex flex-col"
                            style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)' }}
                        >
                            <h2 className="text-lg font-semibold text-white">Free</h2>
                            <div className="mt-4 mb-6">
                                <span className="text-3xl font-bold text-white">$0</span>
                                <span className="text-sm ml-1" style={{ color: 'rgba(255,255,255,0.4)' }}>/ month</span>
                            </div>

                            <ul className="space-y-3 flex-1">
                                {FREE_FEATURES.map((f, i) => (
                                    <li key={i} className="flex items-start gap-2.5 text-sm" style={{ color: 'rgba(255,255,255,0.7)' }}>
                                        <CheckIcon />{f}
                                    </li>
                                ))}
                            </ul>

                            <Link
                                href="/sign-up"
                                className="mt-8 block text-center text-sm font-medium py-2.5 rounded-lg transition-all"
                                style={{ border: '1px solid rgba(255,255,255,0.2)', color: 'rgba(255,255,255,0.8)', background: 'transparent' }}
                            >
                                Get Started Free
                            </Link>
                        </div>

                        {/* Pro Plan */}
                        <div
                            className="rounded-xl p-6 flex flex-col relative"
                            style={{ background: 'rgba(255,142,110,0.06)', border: `1px solid rgba(255,142,110,0.35)` }}
                        >
                            {/* Badge */}
                            <span
                                className="absolute -top-3 right-6 text-xs font-semibold px-3 py-1 rounded-full"
                                style={{ background: ACCENT, color: '#fff' }}
                            >
                                Recommended
                            </span>

                            <h2 className="text-lg font-semibold text-white">Pro</h2>
                            <div className="mt-4 mb-1">
                                <span className="text-3xl font-bold text-white">$9.99</span>
                                <span className="text-sm ml-1" style={{ color: 'rgba(255,255,255,0.4)' }}>/ month</span>
                            </div>
                            <p className="text-xs mb-6" style={{ color: 'rgba(255,255,255,0.4)' }}>
                                or $89.99 / year <span style={{ color: ACCENT }}>(save 25%)</span>
                            </p>

                            <ul className="space-y-3 flex-1">
                                {PRO_FEATURES.map((f, i) => (
                                    <li key={i} className="flex items-start gap-2.5 text-sm" style={{ color: 'rgba(255,255,255,0.7)' }}>
                                        <CheckIcon />{f}
                                    </li>
                                ))}
                            </ul>

                            <Link
                                href="/sign-up"
                                className="mt-8 block text-center text-sm font-medium py-2.5 rounded-lg transition-opacity hover:opacity-90 text-white"
                                style={{ background: ACCENT }}
                            >
                                Upgrade to Pro
                            </Link>

                            <p className="mt-3 text-xs text-center" style={{ color: 'rgba(255,255,255,0.3)' }}>
                                *Subject to fair use policy
                            </p>
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div
                    className="flex-shrink-0 flex flex-col items-center gap-2 px-4 py-5 text-sm"
                    style={{ borderTop: '1px solid rgba(255,255,255,0.07)', color: 'rgba(255,255,255,0.3)' }}
                >
                    <div>Vela is a research tool, not a medical device. It does not provide medical advice.</div>
                    <div className="flex flex-wrap justify-center gap-4 text-xs">
                        <Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link>
                        <Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
                        <Link href="/refund" className="hover:text-white transition-colors">Refund Policy</Link>
                        <a href="mailto:support@an-tho.com" className="hover:text-white transition-colors">support@an-tho.com</a>
                    </div>
                </div>
            </main>
        </>
    );
}
