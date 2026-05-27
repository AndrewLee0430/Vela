import { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import Head from 'next/head';
import { useLang } from '../utils/LangContext';
import { getUI } from '../utils/i18n-ui';
import { faqSectionsI18n } from '../utils/i18n-faq';

interface FAQItem {
    q: string;
    a: string;
}

interface FAQSection {
    title: string;
    items: FAQItem[];
}

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
        <div className="border-b border-text/7">
            <button
                onClick={onToggle}
                className="w-full flex items-center justify-between gap-4 py-5 text-left cursor-pointer transition-colors hover:text-white"
                style={{ color: isOpen ? 'rgb(var(--color-text))' : 'rgb(var(--color-text) / 0.85)' }}
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
                <p className="pb-5 text-sm leading-relaxed text-text/60">
                    {item.a}
                </p>
            </div>
        </div>
    );
}

export default function FAQ() {
    const { lang } = useLang();
    const ui = getUI(lang);
    const sections = faqSectionsI18n[lang] || faqSectionsI18n['en'];
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

            <main className="min-h-screen bg-app-bg">
                {/* Nav */}
                <nav className="border-b border-text/7">
                    <div className="container mx-auto px-4 py-3 flex items-center justify-between">
                        <Link href="/" className="flex items-center">
                            <Image src="/coral_logo.png" alt="Vela" width={40} height={40} style={{ objectFit: 'contain' }} />
                        </Link>
                        <Link
                            href="/sign-up"
                            className="text-sm font-medium px-4 py-1.5 rounded-lg transition-opacity hover:opacity-90"
                            style={{ background: 'rgb(var(--color-brand))', color: '#fff' }}
                        >
                            {ui.getStarted}
                        </Link>
                    </div>
                </nav>

                {/* Header */}
                <div className="container mx-auto px-4 pt-16 pb-8 max-w-3xl text-center">
                    <h1 className="text-3xl sm:text-4xl font-bold text-white mb-3">
                        {ui.faqTitle}
                    </h1>
                    <p className="text-base text-text/50">
                        {ui.faqSubtitle}
                    </p>
                </div>

                {/* FAQ Sections */}
                <div className="container mx-auto px-4 pb-16 max-w-3xl">
                    {sections.map((section: FAQSection, si: number) => (
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
                        className="mt-16 text-center text-sm text-text/40"
                        dangerouslySetInnerHTML={{ __html: ui.faqCta }}
                    />
                </div>

                {/* Footer */}
                <div className="flex flex-col items-center gap-2 px-4 md:px-10 py-6 text-sm border-t border-t-text/7 text-text/30">
                    <div>{ui.faqCopyright.replace('{year}', String(new Date().getFullYear()))}</div>
                    <div className="flex flex-wrap justify-center gap-4 text-xs">
                        <Link href="/terms" className="hover:text-white transition-colors">{ui.termsOfService}</Link>
                        <Link href="/privacy" className="hover:text-white transition-colors">{ui.privacyPolicy}</Link>
                        <Link href="/refund" className="hover:text-white transition-colors">{ui.refundPolicy}</Link>
                        <a href="mailto:support@an-tho.com" className="hover:text-white transition-colors">support@an-tho.com</a>
                    </div>
                </div>
            </main>
        </>
    );
}
