"use client"

import { useState, useEffect } from 'react';
import { useAuth, SignedIn, SignedOut, RedirectToSignIn, UserButton } from '@clerk/nextjs';
import Link from 'next/link';
import Image from 'next/image';

// ─── Design System ────────────────────────────────────────────────────────────
// 顏色對應跨頁面一致，首頁 card / 功能頁 accent / History 標籤全部同色
const FEATURE = {
    research: {
        label: 'Research',
        color: '#ff8e6e',
        bg: 'rgba(255,142,110,0.12)',
        border: 'rgba(255,142,110,0.5)',
        text: '#c0501a',
    },
    verify: {
        label: 'Verify',
        color: '#63b3ed',
        bg: 'rgba(99,179,237,0.12)',
        border: 'rgba(99,179,237,0.5)',
        text: '#1a6096',
    },
    explain: {
        label: 'Explain',
        color: '#68d391',
        bg: 'rgba(104,211,145,0.12)',
        border: 'rgba(104,211,145,0.5)',
        text: '#1a7a40',
    },
} as const;

type FeatureKey = keyof typeof FEATURE;

function getFeature(type: string) {
    return FEATURE[type as FeatureKey] ?? {
        label: type.charAt(0).toUpperCase() + type.slice(1),
        color: '#9ca3af',
        bg: 'rgba(156,163,175,0.12)',
        border: 'rgba(156,163,175,0.5)',
        text: '#4b5563',
    };
}
// ─────────────────────────────────────────────────────────────────────────────

interface HistoryItem {
    id: number;
    user_id: string;
    session_type: string;
    question: string;
    answer: string;
    created_at: string;
}

interface DrugInteraction {
    drug_pair: [string, string];
    severity: string;
    description: string;
    clinical_recommendation: string;
    source: string;
}

function TypeTag({ type }: { type: string }) {
    const f = getFeature(type);
    return (
        <span
            className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold tracking-wide"
            style={{ background: f.bg, color: f.text, border: `1px solid ${f.border}` }}
        >
            {f.label}
        </span>
    );
}

function HistoryList() {
    const { getToken } = useAuth();
    const [history, setHistory] = useState<HistoryItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [expandedId, setExpandedId] = useState<number | null>(null);

    const [verifyDetails, setVerifyDetails] = useState<{[key: number]: {
        interactions: DrugInteraction[];
        risk_level: string;
        loading: boolean;
    }}>({});

    useEffect(() => { loadHistory(); }, []);

    async function loadHistory() {
        try {
            const token = await getToken({ skipCache: true });
            const res = await fetch('http://127.0.0.1:8000/api/history', {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (!res.ok) throw new Error('Failed to load history');
            const data = await res.json();
            setHistory(data);
        } catch (err) {
            console.error('History load error:', err);
        } finally {
            setLoading(false);
        }
    }

    async function fetchVerifyDetails(item: HistoryItem) {
        const match = item.question.match(/Drugs:\s*(.+)/);
        if (!match) return;
        const drugs = match[1].split(',').map(d => d.trim());

        setVerifyDetails(prev => ({
            ...prev,
            [item.id]: { interactions: [], risk_level: 'Unknown', loading: true },
        }));

        try {
            const token = await getToken({ skipCache: true });
            const res = await fetch('http://127.0.0.1:8000/api/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ drugs, patient_context: null }),
            });
            if (!res.ok) throw new Error('Failed');
            const data = await res.json();
            setVerifyDetails(prev => ({
                ...prev,
                [item.id]: { interactions: data.interactions || [], risk_level: data.risk_level || 'Unknown', loading: false },
            }));
        } catch {
            setVerifyDetails(prev => ({
                ...prev,
                [item.id]: { interactions: [], risk_level: 'Unknown', loading: false },
            }));
        }
    }

    function handleToggle(item: HistoryItem) {
        if (expandedId === item.id) {
            setExpandedId(null);
        } else {
            setExpandedId(item.id);
            if (item.session_type === 'verify' && !verifyDetails[item.id]) {
                fetchVerifyDetails(item);
            }
        }
    }

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'Critical': return 'border-red-400 bg-red-50 text-red-800 dark:bg-red-900/20 dark:text-red-300';
            case 'Major':    return 'border-orange-400 bg-orange-50 text-orange-800 dark:bg-orange-900/20 dark:text-orange-300';
            case 'Moderate': return 'border-yellow-400 bg-yellow-50 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-300';
            case 'Minor':    return 'border-blue-300 bg-blue-50 text-blue-800 dark:bg-blue-900/20 dark:text-blue-300';
            default:         return 'border-gray-300 bg-gray-50 text-gray-700 dark:bg-gray-700 dark:text-gray-300';
        }
    };

    if (loading) {
        return (
            <div className="text-center py-16">
                <div className="animate-spin rounded-full h-10 w-10 border-2 border-gray-200 border-t-gray-500 mx-auto" />
                <p className="mt-4 text-sm text-gray-400">Loading history...</p>
            </div>
        );
    }

    if (history.length === 0) {
        return (
            <div className="text-center py-16">
                <p className="text-gray-400 mb-4">No history yet.</p>
                <Link href="/research" className="text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 underline underline-offset-4">
                    Start your first search →
                </Link>
            </div>
        );
    }

    return (
        <div className="space-y-3">
            {history.map(item => {
                const f = getFeature(item.session_type);
                const isExpanded = expandedId === item.id;

                return (
                    <div
                        key={item.id}
                        className="rounded-xl overflow-hidden transition-shadow"
                        style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", borderLeft: `3px solid ${f.color}` }}
                    >
                        {/* Header */}
                        <button
                            onClick={() => handleToggle(item)}
                            className="w-full px-6 py-4 flex items-center justify-between transition-colors text-left"
                            onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.05)"}
                            onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = "transparent"}
                        >
                            <div className="flex items-center gap-3 min-w-0">
                                <TypeTag type={item.session_type} />
                                <div className="min-w-0">
                                    <p className="font-medium truncate text-sm history-question" style={{ color: "rgba(255,255,255,0.85)" }}>
                                        {item.question.length > 80
                                            ? item.question.slice(0, 80) + '...'
                                            : item.question}
                                    </p>
                                    <p className="text-xs text-gray-400 mt-0.5">
                                        {new Date(item.created_at).toLocaleString('en-US', {
                                            year: 'numeric', month: 'short', day: 'numeric',
                                            hour: '2-digit', minute: '2-digit',
                                        })}
                                    </p>
                                </div>
                            </div>

                            <svg
                                className={`w-4 h-4 text-gray-400 flex-shrink-0 ml-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                                fill="none" stroke="currentColor" viewBox="0 0 24 24"
                            >
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                        </button>

                        {/* Expanded content */}
                        {isExpanded && (
                            <div className="px-6 py-5 border-t" style={{ borderColor: "rgba(255,255,255,0.08)" }}>

                                {/* Research */}
                                {item.session_type === 'research' && (
                                    <div className="prose prose-sm prose-gray dark:prose-invert max-w-none">
                                        <p className="whitespace-pre-wrap text-sm leading-relaxed" style={{ color: "rgba(255,255,255,0.75)" }}>
                                            {item.answer}
                                        </p>
                                    </div>
                                )}

                                {/* Explain */}
                                {item.session_type === 'explain' && (
                                    <div className="prose prose-sm prose-gray dark:prose-invert max-w-none">
                                        <p className="whitespace-pre-wrap text-sm leading-relaxed" style={{ color: "rgba(255,255,255,0.75)" }}>
                                            {item.answer}
                                        </p>
                                    </div>
                                )}

                                {/* Verify */}
                                {item.session_type === 'verify' && (
                                    <div className="space-y-4">
                                        <div className="rounded-lg p-4" style={{ background: "rgba(255,255,255,0.05)" }}>
                                            <p className="text-sm text-gray-700 dark:text-gray-300">{item.answer}</p>
                                        </div>

                                        {verifyDetails[item.id]?.loading && (
                                            <div className="text-center py-6">
                                                <div className="animate-spin rounded-full h-6 w-6 border-2 border-gray-200 border-t-blue-400 mx-auto" />
                                                <p className="mt-2 text-xs text-gray-400">Loading interaction details...</p>
                                            </div>
                                        )}

                                        {!verifyDetails[item.id]?.loading && (verifyDetails[item.id]?.interactions?.length ?? 0) > 0 && (
                                            <div className="space-y-3">
                                                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                                                    Interactions ({verifyDetails[item.id].interactions.length})
                                                </p>
                                                {verifyDetails[item.id].interactions.map((interaction, idx) => (
                                                    <div key={idx} className={`border-l-4 rounded-lg p-4 ${getSeverityColor(interaction.severity)}`}>
                                                        <div className="flex justify-between items-start mb-2">
                                                            <p className="font-semibold text-sm">
                                                                {interaction.drug_pair[0]} ↔ {interaction.drug_pair[1]}
                                                            </p>
                                                            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-white/60 dark:bg-black/20 ml-2 flex-shrink-0">
                                                                {interaction.severity}
                                                            </span>
                                                        </div>
                                                        <p className="text-xs leading-relaxed">{interaction.description}</p>
                                                        {interaction.clinical_recommendation && (
                                                            <p className="text-xs mt-2 opacity-80">
                                                                {interaction.clinical_recommendation}
                                                            </p>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}

export default function History() {
    return (
        <>
        <style>{`
            .history-question::selection { background: rgba(255,255,255,0.15); color: rgba(255,255,255,0.85); }
            .history-question::-moz-selection { background: rgba(255,255,255,0.15); color: rgba(255,255,255,0.85); }
        `}</style>
        <main className="min-h-screen" style={{ background: "linear-gradient(135deg, #0a1628 0%, #0f2040 45%, #1a1035 75%, #0d1a2e 100%)" }}>
            <nav className="border-b" style={{ background: "linear-gradient(135deg, #0a1628 0%, #0f2040 45%, #1a1035 75%, #0d1a2e 100%)", borderColor: "rgba(255,255,255,0.07)" }}>
                <div className="container mx-auto px-4 py-3">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-8">
                            <Link href="/" className="group relative flex items-center" title="Homepage">
                                <Image src="/coral_logo.png" alt="Vela" width={60} height={60} style={{ objectFit: 'contain' }} />
                                <span className="absolute -bottom-7 left-1/2 -translate-x-1/2 text-xs bg-gray-800 text-white px-2 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
                                  Homepage
                                </span>
                              </Link>
                            <div className="hidden md:flex items-center gap-6 text-sm">
                                <Link href="/research" className="text-gray-400 hover:text-white transition-colors">Research</Link>
                                <Link href="/verify"   className="text-gray-400 hover:text-white transition-colors">Verify</Link>
                                <Link href="/explain"  className="text-gray-400 hover:text-white transition-colors">Explain</Link>
                                <Link href="/history"  className="text-white font-medium">History</Link>
                            </div>
                        </div>
                        <UserButton showName={true} />
                    </div>
                </div>
            </nav>

            <SignedIn>
                <div className="container mx-auto px-4 py-10 max-w-3xl">
                    <h1 className="text-2xl font-bold mb-8 tracking-tight" style={{ color: "#ffffff" }}>
                        History
                    </h1>
                    <HistoryList />
                </div>
            </SignedIn>

            <SignedOut>
                <RedirectToSignIn />
            </SignedOut>
        </main>
        </>
    );
}