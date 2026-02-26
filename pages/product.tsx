"use client"

import { useState, FormEvent, useRef } from 'react';
import { useAuth, SignedIn, SignedOut, RedirectToSignIn, UserButton } from '@clerk/nextjs';
import DatePicker from 'react-datepicker';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { fetchEventSource } from '@microsoft/fetch-event-source';
import Link from 'next/link';
import Toast from '../components/Toast';

class FatalError extends Error {}

function PatientLetterForm() {
    const { getToken } = useAuth();

    const [visitDate, setVisitDate] = useState<Date | null>(new Date());
    const [notes, setNotes] = useState('');
    const [output, setOutput] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [showToast, setShowToast] = useState(false);

    const isRunningRef = useRef(false);

    async function handleSubmit(e: FormEvent) {
        e.preventDefault();
        if (isRunningRef.current) return;
        isRunningRef.current = true;

        setOutput('');
        setError('');
        setLoading(true);

        const controller = new AbortController();

        try {
            const jwt = await getToken({ skipCache: true });

            if (!jwt) {
                setError('Authentication required. Please sign in again.');
                setLoading(false);
                isRunningRef.current = false;
                return;
            }

            let accumulated = '';

            await fetchEventSource('http://127.0.0.1:8000/api/consultation', {
                signal: controller.signal,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${jwt}`,
                },
                body: JSON.stringify({
                    patient_name: '[Patient Name]',
                    date_of_visit: visitDate?.toISOString().slice(0, 10) || '[Visit Date]',
                    notes: notes,
                }),
                openWhenHidden: true,

                async onopen(response) {
                    if (response.ok) return;
                    if (response.status === 403 || response.status === 401) {
                        throw new FatalError('Session expired. Please refresh the page and sign in again.');
                    }
                    throw new FatalError(`Server error (${response.status}). Please try again.`);
                },

                onmessage(ev) {
                    if (ev.data && ev.data.trim() !== '') {
                        accumulated += ev.data + '\n';
                        setOutput(accumulated);
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
    }

    return (
        <div className="container mx-auto px-4 py-8 max-w-3xl">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
                ✉️ Patient Education Letter
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
                Translate your clinical notes into a clear, plain-language letter for your patient.
                The letter only reflects what you documented — no clinical information is added.
            </p>

            {/* How it works */}
            <div className="bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg p-4 mb-6">
                <div className="flex items-start gap-3">
                    <span className="text-xl">💡</span>
                    <div>
                        <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
                            What this tool does
                        </h3>
                        <p className="text-sm text-blue-800 dark:text-blue-200">
                            Converts medical jargon into patient-friendly language. For example:{' '}
                            <em>"eGFR 41, consider adjusting Metformin"</em> becomes{' '}
                            <em>"Your kidney filtering function has recently decreased, and we will review whether your current diabetes medication remains appropriate."</em>
                        </p>
                        <p className="text-sm text-blue-800 dark:text-blue-200 mt-2">
                            🔒 Use de-identified notes only. Do not include real patient names or medical record numbers.
                        </p>
                    </div>
                </div>
            </div>

            {error && (
                <div className="mb-6 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-lg border border-red-200 dark:border-red-800">
                    ❌ {error}
                </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6 bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8">

                <div className="space-y-2">
                    <label htmlFor="date" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Date of Visit
                    </label>
                    <DatePicker
                        id="date"
                        selected={visitDate}
                        onChange={(d: Date | null) => setVisitDate(d)}
                        dateFormat="yyyy-MM-dd"
                        placeholderText="Select date"
                        required
                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white"
                    />
                </div>

                <div className="space-y-2">
                    <label htmlFor="notes" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Clinical Notes
                    </label>
                    <textarea
                        id="notes"
                        required
                        rows={12}
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        disabled={loading}
                        className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:text-white disabled:opacity-60 font-mono text-sm"
                        placeholder="Paste your clinical notes here. Use de-identified information only.

Example:
68yo male, T2DM x 15yr, HTN.
eGFR dropped from 62 to 41 last month.
Currently on Metformin 1000mg BD, Lisinopril 10mg.
Patient complains of mild leg swelling. HbA1c 7.8%.
Plan to review medications and repeat renal function in 4 weeks."
                    />
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                        The letter will only contain information present in your notes. Nothing will be added.
                    </p>
                </div>

                <button
                    type="submit"
                    disabled={loading || !notes.trim()}
                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold py-3 px-6 rounded-lg transition-colors duration-200"
                >
                    {loading ? 'Generating letter...' : 'Generate Patient Letter'}
                </button>
            </form>

            {/* Output */}
            {output && (
                <section className="mt-8 bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8">
                    <div className="flex justify-between items-center mb-4">
                        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                            Patient Letter
                        </h2>
                        <button
                            onClick={() => {
                                navigator.clipboard.writeText(output);
                                setShowToast(true);
                            }}
                            className="text-sm text-blue-600 dark:text-blue-400 hover:underline flex items-center gap-1"
                        >
                            📋 Copy to Clipboard
                        </button>
                    </div>

                    <div className="bg-yellow-50 dark:bg-yellow-900/30 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3 mb-6">
                        <p className="text-sm text-yellow-800 dark:text-yellow-200">
                            ⚠️ <strong>Please review before sending.</strong>{' '}
                            Replace <code className="bg-yellow-100 dark:bg-yellow-800 px-1 rounded">[Patient Name]</code> with the patient's name,
                            and verify the content accurately reflects your clinical intent.
                        </p>
                    </div>

                    <div className="markdown-content prose prose-blue dark:prose-invert max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
                            {output}
                        </ReactMarkdown>
                    </div>

                    {loading && (
                        <span className="inline-block w-2 h-4 bg-blue-500 animate-pulse ml-1 mt-2"></span>
                    )}
                </section>
            )}

            <div className="mt-8 text-center text-xs text-gray-500 dark:text-gray-400">
                <p>This tool translates your notes only. It does not provide clinical recommendations.</p>
                <p className="mt-1">🔒 De-identified data only · No PHI stored</p>
            </div>

            {showToast && (
                <Toast
                    message="✓ Copied to clipboard"
                    onClose={() => setShowToast(false)}
                />
            )}
        </div>
    );
}

export default function Product() {
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
                                <Link href="/research" className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100">Research</Link>
                                <Link href="/verify" className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100">Verify</Link>
                                <Link href="/product" className="text-blue-600 dark:text-blue-400 font-medium">Document</Link>
                                <Link href="/history" className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100">History</Link>
                            </div>
                        </div>
                        <UserButton showName={true} />
                    </div>
                </div>
            </nav>

            <SignedIn>
                <PatientLetterForm />
            </SignedIn>
            <SignedOut>
                <RedirectToSignIn />
            </SignedOut>
        </main>
    );
}