"use client"

import { useState, FormEvent, useRef, useEffect, useCallback } from 'react';
import { useAuth, SignedIn, SignedOut, RedirectToSignIn, UserButton } from '@clerk/nextjs';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import Link from 'next/link';
import CitationPanel, { Citation } from '../components/CitationPanel';
import FeedbackBar from '../components/FeedbackBar';

const defaultSuggestions = [
    "What are the common side effects of Metformin?",
    "Which drugs interact with Warfarin?",
    "What should I know about NSAIDs in elderly patients?",
    "Medication safety for diabetic patients?",
    "Contraindications of ACE inhibitors in hypertension?",
    "How to manage statin-induced myopathy?",
    "DOACs vs Warfarin — key differences?",
    "Safety of antibiotics in pregnancy?",
    "When to use beta-blockers in heart failure?",
    "Long-term risks of proton pump inhibitors?",
];

// FatalError tells fetchEventSource to stop retrying
class FatalError extends Error {}

function ResearchForm() {
    const { getToken } = useAuth();

    const [question, setQuestion] = useState('');
    const [answer, setAnswer] = useState('');
    const [citations, setCitations] = useState<Citation[]>([]);
    const [loading, setLoading] = useState(false);
    const [queryTime, setQueryTime] = useState<number | null>(null);
    const [error, setError] = useState<string>('');

    const answerRef = useRef<HTMLDivElement>(null);
    const isRunningRef = useRef(false);

    useEffect(() => {
        if (answerRef.current && answer) {
            answerRef.current.scrollTop = answerRef.current.scrollHeight;
        }
    }, [answer]);

    const handleReset = () => {
        setQuestion('');
        setAnswer('');
        setCitations([]);
        setQueryTime(null);
        setError('');
    };

    const runSearch = useCallback(async (q: string) => {
        if (!q.trim()) return;
        if (isRunningRef.current) return;
        isRunningRef.current = true;

        setAnswer('');
        setCitations([]);
        setQueryTime(null);
        setLoading(true);
        setError('');

        const controller = new AbortController();

        try {
            const jwt = await getToken({ skipCache: true });

            if (!jwt) {
                setError('Authentication required. Please sign in again.');
                setLoading(false);
                isRunningRef.current = false;
                return;
            }

            await fetchEventSource('http://127.0.0.1:8000/api/research', {
                signal: controller.signal,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${jwt}`,
                },
                body: JSON.stringify({ question: q, max_results: 5 }),
                openWhenHidden: true,

                async onopen(response) {
                    if (response.ok) return;
                    if (response.status === 403 || response.status === 401) {
                        throw new FatalError('Session expired. Please refresh the page and sign in again.');
                    }
                    throw new FatalError(`Server error (${response.status}). Please try again.`);
                },

                onmessage(ev) {
                    try {
                        const data = JSON.parse(ev.data);
                        if (data.type === 'answer') {
                            setAnswer(prev => prev + data.content);
                        } else if (data.type === 'citations') {
                            setCitations(data.content);
                        } else if (data.type === 'error') {
                            setError(data.content);
                        } else if (data.type === 'done') {
                            setLoading(false);
                            if (data.query_time_ms) setQueryTime(data.query_time_ms);
                        }
                    } catch (e) {
                        console.error('Parse error:', e);
                    }
                },

                onclose() {
                    setLoading(false);
                },

                onerror(err) {
                    if (err instanceof FatalError) throw err;
                    throw new FatalError(
                        err instanceof Error ? err.message : 'Connection lost. Please try again.'
                    );
                },
            });

        } catch (err: any) {
            controller.abort();
            setLoading(false);
            setError(err instanceof Error ? err.message : 'Unknown error. Please try again.');
        } finally {
            isRunningRef.current = false;
        }
    }, [getToken]);

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        await runSearch(question);
    }

    async function handleSuggestionClick(suggestion: string) {
        setQuestion(suggestion);
        await runSearch(suggestion);
    }

    return (
        <div className="flex flex-col lg:flex-row gap-6 h-full">
            <div className="flex-1 flex flex-col">
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 flex flex-col flex-1">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
                            💬 Medical Research Assistant
                        </h2>
                        {(answer || question) && (
                            <button
                                onClick={handleReset}
                                className="text-sm text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors flex items-center gap-1"
                            >
                                🔄 New Search
                            </button>
                        )}
                    </div>

                    {error && !loading && (
                        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg border border-red-200 dark:border-red-800">
                            ❌ {error}
                        </div>
                    )}

                    <div
                        ref={answerRef}
                        className="flex-1 overflow-y-auto mb-4 min-h-[300px] max-h-[500px]"
                    >
                        {!answer && !loading && (
                            <div className="text-center py-12">
                                <p className="text-gray-500 dark:text-gray-400 mb-6">
                                    Ask a clinical question — answers are grounded in PubMed literature and FDA drug data.
                                    Ask in any language.
                                </p>
                                <div className="space-y-2">
                                    <p className="text-sm text-gray-400 dark:text-gray-500">Try these:</p>
                                    <div className="flex flex-wrap justify-center gap-2">
                                        {defaultSuggestions.map((suggestion, i) => (
                                            <button
                                                key={i}
                                                onClick={() => handleSuggestionClick(suggestion)}
                                                disabled={loading}
                                                className="px-3 py-1.5 text-sm bg-gray-100 dark:bg-gray-700
                                                         text-gray-700 dark:text-gray-300 rounded-full
                                                         hover:bg-blue-100 dark:hover:bg-blue-900
                                                         hover:text-blue-700 dark:hover:text-blue-300
                                                         disabled:opacity-50 disabled:cursor-not-allowed
                                                         transition-colors"
                                            >
                                                {suggestion}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        )}

                        {(answer || loading) && (
                            <div className="prose prose-blue dark:prose-invert max-w-none">
                                <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                                    {answer}
                                </ReactMarkdown>
                                {loading && (
                                    <span className="inline-block w-2 h-4 bg-blue-500 animate-pulse ml-1"></span>
                                )}
                                {!loading && answer && !error && (
                                    <FeedbackBar
                                        query={question}
                                        response={answer}
                                        category="research"
                                    />
                                )}
                            </div>
                        )}
                    </div>

                    {queryTime && (
                        <div className="text-xs text-gray-400 dark:text-gray-500 mb-2">
                            Query time: {(queryTime / 1000).toFixed(2)}s
                        </div>
                    )}

                    <form onSubmit={handleSubmit} className="flex gap-2">
                        <input
                            type="text"
                            value={question}
                            onChange={(e) => setQuestion(e.target.value)}
                            placeholder="Ask a clinical question in any language..."
                            className="flex-1 px-4 py-3 border border-gray-300 dark:border-gray-600
                                     rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent
                                     dark:bg-gray-700 dark:text-white"
                            disabled={loading}
                        />
                        <button
                            type="submit"
                            disabled={loading || !question.trim()}
                            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400
                                     text-white font-medium rounded-lg transition-colors
                                     flex items-center gap-2"
                        >
                            {loading ? (
                                <>
                                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                                    </svg>
                                    Searching
                                </>
                            ) : (
                                <>🔍 Search</>
                            )}
                        </button>
                    </form>

                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-3 text-center">
                        ⚠️ For reference only. Not a substitute for professional clinical judgment.
                    </p>
                </div>
            </div>

            <div className="lg:w-96">
                <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-6 h-full max-h-[700px] overflow-hidden">
                    <CitationPanel
                        citations={citations}
                        isLoading={loading && citations.length === 0}
                    />
                </div>
            </div>
        </div>
    );
}

export default function Research() {
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
                                <Link href="/research" className="text-blue-600 dark:text-blue-400 font-medium">Research</Link>
                                <Link href="/verify" className="text-gray-600 dark:text-gray-400 hover:text-blue-600">Verify</Link>
                                <Link href="/product" className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100">Document</Link>
                                <Link href="/history" className="text-gray-600 dark:text-gray-400 hover:text-blue-600">History</Link>
                            </div>
                        </div>
                        <UserButton showName={true} />
                    </div>
                </div>
            </nav>

            <SignedIn>
                <div className="container mx-auto px-4 py-8">
                    <ResearchForm />
                </div>
            </SignedIn>
            <SignedOut>
                <RedirectToSignIn />
            </SignedOut>
        </main>
    );
}