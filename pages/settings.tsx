"use client"

// pages/settings.tsx — PRD § 4.5 PHASE C
// /settings page hosting the 「我的分享」 tab. Tab-nav scaffolding is
// extensible — adding a future tab (e.g. user_context per §4.3 Phase
// 1A) is a one-line addition to the `tabs` array; no architectural
// change needed.
//
// PageShell handles signed-out redirect via the default
// allowAnonymous=false branch (RedirectToSignIn). Anonymous visitors
// land on /sign-in.

import { useState } from 'react';
import Head from 'next/head';
import PageShell from '../components/PageShell';
import MySharesTab from '../components/MySharesTab';
import { useLang } from '../utils/LangContext';
import { getShare } from '../utils/i18n-share';

type TabId = 'my-shares';

interface Tab {
    id: TabId;
    label: string;
    color: string;
}

export default function SettingsPage() {
    const { lang } = useLang();
    const t = getShare(lang);
    const [activeTab, setActiveTab] = useState<TabId>('my-shares');

    const tabs: Tab[] = [
        { id: 'my-shares', label: t.settingsTabTitle, color: '#ff8e6e' },
    ];

    return (
        <PageShell activePage="settings">
            <Head>
                <title>{t.settingsPageTitle} · Vela</title>
                <meta name="robots" content="noindex, nofollow" />
            </Head>

            <div className="container mx-auto px-4 py-8 max-w-3xl">
                <h1 className="text-2xl font-bold tracking-tight mb-6" style={{ color: '#ffffff' }}>
                    {t.settingsPageTitle}
                </h1>

                {/* Tab nav — single tab now; designed to scale. */}
                <div
                    className="flex gap-2 mb-6 border-b"
                    style={{ borderColor: 'rgba(255,255,255,0.08)' }}
                    role="tablist"
                >
                    {tabs.map(tab => {
                        const isActive = activeTab === tab.id;
                        return (
                            <button
                                key={tab.id}
                                type="button"
                                role="tab"
                                aria-selected={isActive}
                                onClick={() => setActiveTab(tab.id)}
                                className="px-4 py-2 text-sm font-medium transition-colors cursor-pointer"
                                style={{
                                    color: isActive ? tab.color : 'rgba(255,255,255,0.55)',
                                    borderBottom: `2px solid ${isActive ? tab.color : 'transparent'}`,
                                    marginBottom: '-1px',
                                }}
                                onMouseEnter={e => {
                                    if (!isActive) (e.currentTarget as HTMLElement).style.color = '#ffffff';
                                }}
                                onMouseLeave={e => {
                                    if (!isActive) (e.currentTarget as HTMLElement).style.color = 'rgba(255,255,255,0.55)';
                                }}
                            >
                                {tab.label}
                            </button>
                        );
                    })}
                </div>

                <div role="tabpanel">
                    {activeTab === 'my-shares' && <MySharesTab />}
                </div>
            </div>
        </PageShell>
    );
}
