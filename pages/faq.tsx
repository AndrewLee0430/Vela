import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import Head from 'next/head';

interface FAQItem {
    q: string;
    a: string;
}

interface FAQSection {
    title: string;
    items: FAQItem[];
}

const FAQ_SECTIONS: FAQSection[] = [
    {
        title: 'About Vela',
        items: [
            {
                q: 'What is Vela?',
                a: "Vela is a clinical knowledge engine for healthcare professionals. It searches PubMed's 36 million+ articles, checks drug interactions against official FDA data, and explains medical reports using LOINC, RxNorm, and MedlinePlus standards \u2014 all in 16 languages.",
            },
            {
                q: "Why are Vela's answers cited with sources?",
                a: 'Every answer in Vela is traced back to PubMed, FDA, or LOINC. You can verify any claim by clicking through to the original source. We believe medical information should always be traceable and independently verifiable.',
            },
            {
                q: 'What data sources does Vela use?',
                a: 'Vela integrates three authoritative medical databases: PubMed (36M+ peer-reviewed articles from the National Library of Medicine), FDA DailyMed (official drug label and interaction data), and LOINC/MedlinePlus (standardized lab test definitions and health information from NIH).',
            },
            {
                q: 'What languages does Vela support?',
                a: 'Vela supports 16 languages: English, Traditional Chinese, Simplified Chinese, Japanese, Korean, Thai, Spanish, French, German, Portuguese, Indonesian, Vietnamese, Arabic, Hindi, Bengali, and Hebrew. You can ask questions in any of these languages and receive answers in the same language.',
            },
        ],
    },
    {
        title: 'Features',
        items: [
            {
                q: 'What is Research?',
                a: 'Research lets you ask clinical questions in natural language. Vela searches PubMed, retrieves relevant peer-reviewed articles, and synthesizes an evidence-graded answer with full citations. Each source is linked so you can read the original paper.',
            },
            {
                q: 'What is Verify?',
                a: 'Verify checks drug interactions using official FDA DailyMed data. Enter two or more drug names and Vela returns the interaction severity level, clinical effects, and management recommendations \u2014 all sourced from FDA-approved drug labels.',
            },
            {
                q: 'What is Explain?',
                a: 'Explain helps you understand medical reports. Paste your lab results or upload a report (PDF or image), and Vela breaks down each value in plain language \u2014 what it measures, whether it\'s normal, and what it might mean. Sources include LOINC standards, RxNorm drug data, and MedlinePlus health information.',
            },
            {
                q: 'What does evidence strength mean?',
                a: 'Vela grades each section of a Research answer by the strength of the supporting evidence. Strong evidence (green) comes from systematic reviews or large clinical trials. Moderate evidence (yellow) comes from smaller studies. Limited evidence (red) means the supporting research is preliminary. This helps you quickly assess how reliable each part of the answer is.',
            },
        ],
    },
    {
        title: 'Privacy & Safety',
        items: [
            {
                q: 'Is Vela a medical device?',
                a: 'No. Vela is a research and reference tool. It does not diagnose, treat, or provide medical advice. All outputs include a disclaimer reminding users to consult a qualified healthcare professional for clinical decisions.',
            },
            {
                q: 'Does Vela protect my data?',
                a: 'Vela actively detects and blocks personal health identifiers (PHI) before processing any query. Chat history is automatically deleted after 180 days. Vela runs on secure, encrypted infrastructure. For full details, see our Privacy Policy.',
            },
            {
                q: 'Who built Vela?',
                a: 'Vela is built by an-tho (an-tho.com), a company focused on building evidence-driven decision support systems. Vela is the first product in this mission.',
            },
        ],
    },
    {
        title: 'Pricing',
        items: [
            {
                q: 'How much does Vela cost?',
                a: 'Vela offers a free plan with limited daily queries across all three features. The Pro plan is $9.99/month or $89.99/year (save 25%), which includes unlimited queries, PDF/image upload for Explain, and PDF export.',
            },
            {
                q: "What's included in the free plan?",
                a: 'The free plan includes access to all three features \u2014 Research, Verify, and Explain \u2014 with a limited number of queries per day. No credit card required.',
            },
            {
                q: "What's included in Pro?",
                a: 'Pro includes unlimited queries across all features, PDF and image upload for Explain, PDF export of results, and priority access to new features.',
            },
            {
                q: 'Can I cancel anytime?',
                a: 'Yes. You can cancel your Pro subscription at any time from your account settings. Your access continues until the end of the current billing period. No cancellation fees.',
            },
        ],
    },
];

function ChevronIcon({ open }: { open: boolean }) {
    return (
        <svg
            width="20" height="20" viewBox="0 0 20 20" fill="none"
            className="flex-shrink-0 transition-transform duration-300"
            style={{ transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}
        >
            <path d="M5 7.5L10 12.5L15 7.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
    );
}

function Accordion({ item, isOpen, onToggle }: { item: FAQItem; isOpen: boolean; onToggle: () => void }) {
    return (
        <div
            className="border-b"
            style={{ borderColor: 'rgba(255,255,255,0.07)' }}
        >
            <button
                onClick={onToggle}
                className="w-full flex items-center justify-between gap-4 py-5 text-left cursor-pointer transition-colors hover:text-white"
                style={{ color: isOpen ? '#fff' : 'rgba(255,255,255,0.85)' }}
            >
                <span className="text-sm sm:text-base font-medium">{item.q}</span>
                <ChevronIcon open={isOpen} />
            </button>
            <div
                className="overflow-hidden transition-all duration-300 ease-in-out"
                style={{
                    maxHeight: isOpen ? '500px' : '0',
                    opacity: isOpen ? 1 : 0,
                }}
            >
                <p
                    className="pb-5 text-sm leading-relaxed"
                    style={{ color: 'rgba(255,255,255,0.6)' }}
                >
                    {item.a}
                </p>
            </div>
        </div>
    );
}

export default function FAQ() {
    const [openId, setOpenId] = useState<string | null>(null);

    function toggle(id: string) {
        setOpenId(prev => prev === id ? null : id);
    }

    return (
        <>
            <Head>
                <title>FAQ — Vela | Clinical AI for Healthcare Professionals</title>
                <meta name="description" content="Frequently asked questions about Vela. Learn about our features, data sources, pricing, and privacy practices." />
            </Head>

            <main
                className="min-h-screen"
                style={{ background: 'linear-gradient(135deg, #0a1628 0%, #0f2040 45%, #1a1035 75%, #0d1a2e 100%)' }}
            >
                {/* Nav */}
                <nav className="border-b" style={{ background: 'transparent', borderColor: 'rgba(255,255,255,0.07)' }}>
                    <div className="container mx-auto px-4 py-3 flex items-center justify-between">
                        <Link href="/" className="flex items-center">
                            <Image src="/coral_logo.png" alt="Vela" width={40} height={40} style={{ objectFit: 'contain' }} />
                        </Link>
                        <Link
                            href="/sign-up"
                            className="text-sm font-medium px-4 py-1.5 rounded-lg transition-opacity hover:opacity-90"
                            style={{ background: '#ff8e6e', color: '#fff' }}
                        >
                            Get Started
                        </Link>
                    </div>
                </nav>

                {/* Header */}
                <div className="container mx-auto px-4 pt-16 pb-8 max-w-3xl text-center">
                    <h1 className="text-3xl sm:text-4xl font-bold text-white mb-3">
                        Frequently Asked Questions
                    </h1>
                    <p className="text-base" style={{ color: 'rgba(255,255,255,0.5)' }}>
                        Everything you need to know about Vela.
                    </p>
                </div>

                {/* FAQ Sections */}
                <div className="container mx-auto px-4 pb-16 max-w-3xl">
                    {FAQ_SECTIONS.map((section, si) => (
                        <div key={si} className={si > 0 ? 'mt-10' : ''}>
                            <h2 className="text-lg font-semibold text-white mb-2">{section.title}</h2>
                            <div>
                                {section.items.map((item, qi) => {
                                    const id = `${si}-${qi}`;
                                    return (
                                        <Accordion
                                            key={id}
                                            item={item}
                                            isOpen={openId === id}
                                            onToggle={() => toggle(id)}
                                        />
                                    );
                                })}
                            </div>
                        </div>
                    ))}

                    {/* CTA */}
                    <div
                        className="mt-16 text-center text-sm"
                        style={{ color: 'rgba(255,255,255,0.4)' }}
                    >
                        Still have questions? Contact us at{' '}
                        <a
                            href="mailto:support@an-tho.com"
                            className="hover:text-white transition-colors"
                            style={{ color: 'rgba(255,255,255,0.6)' }}
                        >
                            support@an-tho.com
                        </a>
                    </div>
                </div>

                {/* Footer */}
                <div
                    className="flex flex-col items-center gap-2 px-4 md:px-10 py-6 text-sm"
                    style={{ borderTop: '1px solid rgba(255,255,255,0.07)', color: 'rgba(255,255,255,0.3)' }}
                >
                    <div>&copy; {new Date().getFullYear()} Vela. All rights reserved.</div>
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
