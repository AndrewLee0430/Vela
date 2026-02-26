"use client"

import { useState, FormEvent, useRef } from 'react';
import { useAuth, SignedIn, SignedOut, RedirectToSignIn, UserButton } from '@clerk/nextjs';
import Link from 'next/link';
import FeedbackBar from '../components/FeedbackBar';

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

    const [drugs, setDrugs] = useState('');
    const [result, setResult] = useState<VerifyResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // ✅ Prevent duplicate submissions
    const isRunningRef = useRef(false);

    const handleReset = () => {
        setDrugs('');
        setResult(null);
        setError('');
    };

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        if (isRunningRef.current) return;

        const drugList = drugs.split('\n').map(d => d.trim()).filter(Boolean);
        if (drugList.length < 2) {
            setError('Please enter at least 2 drug names.');
            return;
        }

        isRunningRef.current = true;
        setLoading(true);
        setError('');
        setResult(null);

        try {
            // ✅ skipCache: true — always fetch a fresh token
            const token = await getToken({ skipCache: true });

            if (!token) {
                setError('Authentication required. Please sign in again.');
                return;
            }

            const res = await fetch('http://127.0.0.1:8000/api/verify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({ drugs: drugList, patient_context: null }),
            });

            if (res.status === 403 || res.status === 401) {
                setError('Session expired. Please refresh the page and sign in again.');
                return;
            }

            if (!res.ok) {
                throw new Error(`Server error (${res.status}). Please try again.`);
            }

            const data: VerifyResponse = await res.json();
            setResult(data);

        } catch (err: any) {
            setError(err.message || 'Analysis failed. Please try again.');
        } finally {
            setLoading(false);
            isRunningRef.current = false;
        }
    }

    const getRiskColor = (level: string) => {
        switch (level) {
            case 'Critical': return 'bg-red-100 text-red-800 border-red-300';
            case 'Major':    return 'bg-orange-100 text-orange-800 border-orange-300';
            case 'Moderate': return 'bg-yellow-100 text-yellow-800 border-yellow-300';
            case 'Minor':    return 'bg-blue-100 text-blue-800 border-blue-300';
            case 'Low':      return 'bg-green-100 text-green-800 border-green-300';
            default:         return 'bg-gray-100 text-gray-800 border-gray-300';
        }
    };

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'Critical': return 'bg-red-50 border-red-300 text-red-800';
            case 'Major':    return 'bg-orange-50 border-orange-300 text-orange-800';
            case 'Moderate': return 'bg-yellow-50 border-yellow-300 text-yellow-800';
            case 'Minor':    return 'bg-blue-50 border-blue-300 text-blue-800';
            default:         return 'bg-gray-50 border-gray-300 text-gray-800';
        }
    };

    return (
        <div className="container mx-auto px-4 py-8 max-w-5xl">
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                    💊 Drug Interaction Checker
                </h1>
                {(result || drugs) && !loading && (
                    <button
                        onClick={handleReset}
                        className="text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors flex items-center gap-1"
                    >
                        🔄 New Check
                    </button>
                )}
            </div>

            {/* Privacy notice */}
            <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
                <div className="flex items-start gap-3">
                    <span className="text-xl">🔒</span>
                    <div>
                        <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
                            Privacy: Do not enter real patient names or identifying information
                        </h3>
                        <p className="text-sm text-blue-800 dark:text-blue-200">
                            Enter drug names only (e.g. Metformin, Aspirin, Warfarin) to analyze interactions.
                            Queries are not stored. Sources are FDA Official.
                        </p>
                    </div>
                </div>
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
                {/* Left: Input */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
                    <form onSubmit={handleSubmit} className="space-y-6">
                        <div className="space-y-2">
                            <label htmlFor="drugs" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                                Drug List (one per line)
                            </label>
                            <textarea
                                id="drugs"
                                required
                                rows={12}
                                value={drugs}
                                onChange={(e) => setDrugs(e.target.value)}
                                disabled={loading}
                                className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-lg
                                         focus:ring-2 focus:ring-blue-500 focus:border-transparent
                                         dark:bg-gray-700 dark:text-white font-mono text-sm disabled:opacity-60"
                                placeholder={"Metformin\nAspirin\nWarfarin"}
                            />
                            <p className="text-xs text-gray-500 dark:text-gray-400">
                                Enter at least 2 drug names in English, one per line.
                            </p>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400
                                     text-white font-semibold py-3 px-6 rounded-lg transition-colors"
                        >
                            {loading ? 'Analyzing...' : 'Analyze Interactions'}
                        </button>
                    </form>

                    {error && (
                        <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg border border-red-200 dark:border-red-800">
                            ❌ {error}
                        </div>
                    )}
                </div>

                {/* Right: Results */}
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6">
                    {!result && !loading && (
                        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                            Results will appear here after analysis.
                        </div>
                    )}

                    {loading && (
                        <div className="text-center py-12">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                            <p className="mt-4 text-gray-500 dark:text-gray-400">Analyzing interactions...</p>
                        </div>
                    )}

                    {result && (
                        <div className="space-y-6">
                            {/* Summary */}
                            <div>
                                <div className="flex justify-between items-start mb-2">
                                    <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
                                        Analysis Summary
                                    </h2>
                                    <span className={`px-3 py-1 rounded-full text-sm font-medium border ${getRiskColor(result.risk_level)}`}>
                                        Risk Level: {result.risk_level}
                                    </span>
                                </div>

                                <p className="text-gray-700 dark:text-gray-300 mb-4">
                                    {result.summary}
                                </p>

                                <FeedbackBar
                                    query={`Drugs: ${result.drugs_analyzed.join(', ')}`}
                                    response={result.summary}
                                    category="verify"
                                />

                                <p className="text-xs text-gray-400 dark:text-gray-500 mt-3">
                                    Drugs analyzed: {result.drugs_analyzed.join(', ')} ·
                                    Query time: {(result.query_time_ms / 1000).toFixed(2)}s
                                </p>
                            </div>

                            {/* Interactions */}
                            {result.interactions.length > 0 && (
                                <div>
                                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">
                                        Drug Interactions ({result.interactions.length})
                                    </h3>

                                    <div className="space-y-4">
                                        {result.interactions.map((interaction, idx) => (
                                            <div
                                                key={idx}
                                                className={`border-l-4 rounded-lg p-4 ${getSeverityColor(interaction.severity)}`}
                                            >
                                                <div className="flex justify-between items-start mb-2">
                                                    <h4 className="font-semibold text-base">
                                                        {interaction.drug_pair[0]} ↔ {interaction.drug_pair[1]}
                                                    </h4>
                                                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                                                        interaction.severity === 'Critical' ? 'bg-red-200 text-red-900' :
                                                        interaction.severity === 'Major'    ? 'bg-orange-200 text-orange-900' :
                                                        interaction.severity === 'Moderate' ? 'bg-yellow-200 text-yellow-900' :
                                                        'bg-blue-200 text-blue-900'
                                                    }`}>
                                                        {interaction.severity}
                                                    </span>
                                                </div>

                                                <div className="space-y-2 text-sm">
                                                    <div>
                                                        <strong className="text-gray-700">Interaction</strong>
                                                        <p className="text-gray-600 mt-1">{interaction.description}</p>
                                                    </div>

                                                    {interaction.clinical_recommendation && (
                                                        <div>
                                                            <strong className="text-gray-700">Clinical Recommendation</strong>
                                                            <p className="text-gray-600 mt-1">
                                                                💡 {interaction.clinical_recommendation}
                                                            </p>
                                                        </div>
                                                    )}

                                                    <p className="text-xs text-gray-500 italic flex items-center gap-2">
                                                        <span>Source:</span>
                                                        {interaction.source_url ? (
                                                            <a
                                                                href={interaction.source_url}
                                                                target="_blank"
                                                                rel="noopener noreferrer"
                                                                className="text-blue-600 hover:text-blue-800 underline flex items-center gap-1"
                                                            >
                                                                {interaction.source} 🔗
                                                            </a>
                                                        ) : (
                                                            <span>{interaction.source}</span>
                                                        )}
                                                    </p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Disclaimer */}
                            {result.disclaimer && (
                                <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4 text-xs text-gray-600 dark:text-gray-400">
                                    <p>⚠️ {result.disclaimer}</p>
                                </div>
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
        <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800">
            <nav className="bg-white dark:bg-gray-800 shadow-sm">
                <div className="container mx-auto px-4 py-3">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-6">
                            <Link href="/" className="text-xl font-bold text-gray-800 dark:text-gray-200">
                                🏥 MediNotes
                            </Link>
                            <div className="hidden md:flex items-center gap-4">
                                <Link href="/research" className="text-gray-600 dark:text-gray-400 hover:text-blue-600">Research</Link>
                                <Link href="/verify" className="text-blue-600 dark:text-blue-400 font-medium">Verify</Link>
                                <Link href="/product" className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100">Document</Link>
                                <Link href="/history" className="text-gray-600 dark:text-gray-400 hover:text-blue-600">History</Link>
                            </div>
                        </div>
                        <UserButton showName={true} />
                    </div>
                </div>
            </nav>

            <SignedIn>
                <VerifyForm />
            </SignedIn>
            <SignedOut>
                <RedirectToSignIn />
            </SignedOut>
        </main>
    );
}