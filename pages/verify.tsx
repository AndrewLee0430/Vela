"use client"

import { useState, FormEvent, useRef } from 'react';
import { useAuth, SignedIn, SignedOut, RedirectToSignIn, UserButton } from '@clerk/nextjs';
import Link from 'next/link';
import Image from 'next/image';
import FeedbackBar from '../components/FeedbackBar';

// Verify accent color
const ACCENT = '#63b3ed';

interface DrugInteraction {
    drug_pair: [string, string];
    severity: string;
    description: string;
    clinical_recommendation: string;
    source: string;
    source_url?: string;
}

interface VerifyResponse {
    drugs_analyzed: string[];
    interactions: DrugInteraction[];
    summary: string;
    risk_level: string;
    query_time_ms: number;
    disclaimer?: string;
}

function VerifyForm() {
    const { getToken } = useAuth();

    const [drugs, setDrugs]   = useState('');
    const [result, setResult] = useState<VerifyResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError]   = useState('');

    const isRunningRef = useRef(false);

    const handleReset = () => { setDrugs(''); setResult(null); setError(''); };

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        if (isRunningRef.current) return;

        const drugList = drugs.split('\n').map(d => d.trim()).filter(Boolean);
        if (drugList.length < 2) {
            setError('Please enter at least 2 drug names.');
            return;
        }

        isRunningRef.current = true;
        setLoading(true); setError(''); setResult(null);

        try {
            const token = await getToken({ skipCache: true });
            if (!token) { setError('Authentication required. Please sign in again.'); return; }

            const res = await fetch('http://127.0.0.1:8000/api/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ drugs: drugList, patient_context: null }),
            });

            if (res.status === 403 || res.status === 401) {
                setError('Session expired. Please refresh and sign in again.');
                return;
            }
            if (!res.ok) throw new Error(`Server error (${res.status}). Please try again.`);

            const data: VerifyResponse = await res.json();
            setResult(data);

        } catch (err: any) {
            setError(err.message || 'Analysis failed. Please try again.');
        } finally {
            setLoading(false);
            isRunningRef.current = false;
        }
    }

    const getRiskBadge = (level: string) => {
        const map: Record<string, string> = {
            Critical: 'bg-red-50 text-red-700 border-red-200',
            Major:    'bg-orange-50 text-orange-700 border-orange-200',
            Moderate: 'bg-yellow-50 text-yellow-700 border-yellow-200',
            Minor:    'bg-blue-50 text-blue-700 border-blue-200',
            Low:      'bg-green-50 text-green-700 border-green-200',
        };
        return map[level] ?? 'bg-gray-50 text-gray-700 border-gray-200';
    };

    const getSeverityStyle = (severity: string) => {
        const map: Record<string, string> = {
            Critical: 'border-red-400 bg-red-50 dark:bg-red-900/20',
            Major:    'border-orange-400 bg-orange-50 dark:bg-orange-900/20',
            Moderate: 'border-yellow-400 bg-yellow-50 dark:bg-yellow-900/20',
            Minor:    'border-blue-300 bg-blue-50 dark:bg-blue-900/20',
        };
        return map[severity] ?? 'border-gray-300 bg-gray-50 dark:bg-gray-700';
    };

    const getSeverityBadge = (severity: string) => {
        const map: Record<string, string> = {
            Critical: 'bg-red-100 text-red-800',
            Major:    'bg-orange-100 text-orange-800',
            Moderate: 'bg-yellow-100 text-yellow-800',
            Minor:    'bg-blue-100 text-blue-800',
        };
        return map[severity] ?? 'bg-gray-100 text-gray-800';
    };

    return (
        <div className="container mx-auto px-4 py-8 max-w-5xl">
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h1 className="text-2xl font-bold tracking-tight" style={{ color: "#ffffff" }}>Drug Interaction Checker</h1>
                    <p className="text-sm mt-1" style={{ color: "rgba(255,255,255,0.5)" }}>FDA Official · Evidence-based</p>
                </div>
                {(result || drugs) && !loading && (
                    <button onClick={handleReset} className="text-sm text-gray-400 hover:text-white transition-colors">
                        New check
                    </button>
                )}
            </div>

            {/* Privacy notice */}
            <div className="rounded-lg p-4 mb-6 border" style={{ background: 'rgba(99,179,237,0.06)', borderColor: 'rgba(99,179,237,0.3)' }}>
                <p className="text-sm" style={{ color: 'rgba(99,179,237,0.95)' }}>
                    <strong>Privacy:</strong> Enter drug names only — no patient names or identifying information.
                    Queries are not stored. Example: Metformin, Aspirin, Warfarin.
                </p>
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
                {/* Input */}
                <div className="rounded-xl p-6" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}>
                    <form onSubmit={handleSubmit} className="space-y-5">
                        <div className="space-y-3">
                            <label className="block text-sm font-medium" style={{ color: "rgba(255,255,255,0.8)" }}>
                                Drug list <span className="font-normal" style={{ color: "rgba(255,255,255,0.4)" }}>(one per line, or click to add)</span>
                            </label>
                            {/* Quick-add chips */}
                            <div className="flex flex-wrap gap-2">
                                {["Warfarin","Aspirin","Metformin","Lisinopril","Atorvastatin",
                                  "Amiodarone","Clopidogrel","Fluoxetine","Omeprazole","Metoprolol",
                                  "Tramadol","Simvastatin","Clarithromycin","Ibuprofen","Digoxin"].map(drug => (
                                    <button
                                        key={drug}
                                        type="button"
                                        onClick={() => setDrugs(prev => prev ? prev + '\n' + drug : drug)}
                                        className="px-3 py-1 text-xs rounded-full transition-all duration-200"
                                        style={{ background: "rgba(99,179,237,0.1)", border: "1px solid rgba(99,179,237,0.3)", color: "rgba(99,179,237,0.9)" }}
                                        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = "rgba(99,179,237,0.22)"; }}
                                        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = "rgba(99,179,237,0.1)"; }}
                                    >
                                        + {drug}
                                    </button>
                                ))}
                            </div>
                            <textarea
                                id="drugs"
                                required
                                rows={6}
                                value={drugs}
                                onChange={(e) => setDrugs(e.target.value)}
                                disabled={loading}
                                className="w-full px-4 py-3 rounded-lg focus:outline-none focus:ring-2 font-mono text-sm disabled:opacity-60 transition-shadow"
                                style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.15)", color: "rgba(255,255,255,0.85)" }}
                                placeholder={"Metformin\nAspirin\nWarfarin"}
                            />
                            <p className="text-xs" style={{ color: "rgba(255,255,255,0.4)" }}>At least 2 drug names in English.</p>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full text-white font-medium py-2.5 px-6 rounded-lg transition-opacity disabled:opacity-50 text-sm"
                            style={{ background: ACCENT }}
                        >
                            {loading ? 'Analyzing...' : 'Analyze Interactions'}
                        </button>
                    </form>

                    {error && (
                        <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg border border-red-100 text-sm">
                            {error}
                        </div>
                    )}
                </div>

                {/* Results */}
                <div className="rounded-xl p-6" style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)" }}>
                    {!result && !loading && (
                        <div className="text-center py-16 text-sm" style={{ color: "rgba(255,255,255,0.4)" }}>
                            Results will appear here after analysis.
                        </div>
                    )}

                    {loading && (
                        <div className="text-center py-16">
                            <div className="w-8 h-8 border-2 border-gray-200 border-t-blue-400 rounded-full animate-spin mx-auto" />
                            <p className="mt-4 text-sm text-gray-400">Analyzing interactions...</p>
                        </div>
                    )}

                    {result && (
                        <div className="space-y-6">
                            {/* Summary */}
                            <div>
                                <div className="flex justify-between items-start mb-3">
                                    <h2 className="text-base font-semibold" style={{ color: "#ffffff" }}>
                                        Analysis Summary
                                    </h2>
                                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${getRiskBadge(result.risk_level)}`}>
                                        {result.risk_level}
                                    </span>
                                </div>
                                <p className="text-sm text-gray-700 dark:text-gray-300 mb-4 leading-relaxed">
                                    {result.summary}
                                </p>
                                <FeedbackBar
                                    query={`Drugs: ${result.drugs_analyzed.join(', ')}`}
                                    response={result.summary}
                                    category="verify"
                                />
                                <p className="text-xs text-gray-300 dark:text-gray-600 mt-3">
                                    {result.drugs_analyzed.join(', ')} · {(result.query_time_ms / 1000).toFixed(2)}s
                                </p>
                            </div>

                            {/* Interactions */}
                            {result.interactions.length > 0 && (
                                <div>
                                    <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
                                        Interactions ({result.interactions.length})
                                    </p>
                                    <div className="space-y-3">
                                        {result.interactions.map((interaction, idx) => (
                                            <div key={idx} className={`border-l-4 rounded-lg p-4 ${getSeverityStyle(interaction.severity)}`}>
                                                <div className="flex justify-between items-start mb-2">
                                                    <p className="font-semibold text-sm" style={{ color: "#ffffff" }}>
                                                        {interaction.drug_pair[0]} ↔ {interaction.drug_pair[1]}
                                                    </p>
                                                    <span className={`px-2 py-0.5 rounded text-xs font-medium ml-2 flex-shrink-0 ${getSeverityBadge(interaction.severity)}`}>
                                                        {interaction.severity}
                                                    </span>
                                                </div>
                                                <div className="space-y-2 text-xs leading-relaxed text-gray-700 dark:text-gray-300">
                                                    <p>{interaction.description}</p>
                                                    {interaction.clinical_recommendation && (
                                                        <p className="opacity-80">{interaction.clinical_recommendation}</p>
                                                    )}
                                                    <p className="text-gray-400 italic">
                                                        Source:{' '}
                                                        {interaction.source_url ? (
                                                            <a href={interaction.source_url} target="_blank" rel="noopener noreferrer"
                                                               className="underline hover:opacity-80">
                                                                {interaction.source}
                                                            </a>
                                                        ) : interaction.source}
                                                    </p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {result.disclaimer && (
                                <p className="text-xs text-gray-400 pt-2 border-t border-gray-100 dark:border-gray-700">
                                    ⚠️ {result.disclaimer}
                                </p>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default function Verify() {
    return (
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
                                <Link href="/verify"   className="font-medium transition-colors" style={{ color: ACCENT }}>Verify</Link>
                                <Link href="/explain"  className="text-gray-400 hover:text-white transition-colors">Explain</Link>
                                <Link href="/history"  className="text-gray-400 hover:text-white transition-colors">History</Link>
                            </div>
                        </div>
                        <UserButton showName={true} />
                    </div>
                </div>
            </nav>

            <SignedIn><VerifyForm /></SignedIn>
            <SignedOut><RedirectToSignIn /></SignedOut>
        </main>
    );
}