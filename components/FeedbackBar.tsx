"use client"

import { useState } from 'react';
import { useAuth } from '@clerk/nextjs';

interface FeedbackBarProps {
    query: string;
    response: string;
    category: 'research' | 'verify';
}

export default function FeedbackBar({ query, response, category }: FeedbackBarProps) {
    const { getToken } = useAuth();
    const [status, setStatus] = useState<'idle' | 'liked' | 'disliked' | 'edited'>('idle');
    const [isEditing, setIsEditing] = useState(false);
    const [editedResponse, setEditedResponse] = useState(response);
    const [loading, setLoading] = useState(false);

    const sendFeedback = async (rating: number, text?: string) => {
        setLoading(true);
        try {
            const token = await getToken({ skipCache: true });
            const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/feedback`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({
                    query,
                    response,
                    rating,
                    feedback_text: text || null,
                    category,
                }),
            });
            if (!res.ok) throw new Error('Feedback failed');
        } catch (err) {
            console.error('Feedback failed:', err);
            setStatus('idle');
        } finally {
            setLoading(false);
        }
    };

    const handleLike = () => {
        if (status === 'liked') return;
        setStatus('liked');
        sendFeedback(1);
    };

    const handleDislike = () => {
        if (status === 'disliked') return;
        setStatus('disliked');
        sendFeedback(-1);
    };

    const handleCopy = () => {
        navigator.clipboard.writeText(response);
    };

    const handleSaveEdit = () => {
        setIsEditing(false);
        setStatus('edited');
        // Rating 2 = strong positive signal (user invested effort to correct)
        sendFeedback(2, editedResponse);
        alert('Thank you for your correction! This helps improve the accuracy of future responses.');
    };

    if (isEditing) {
        return (
            <div className="mt-4 border-t border-gray-100 dark:border-gray-700 pt-4 animate-fadeIn">
                <label className="block text-xs font-semibold text-gray-500 mb-2">
                    Suggest a correction:
                </label>
                <textarea
                    value={editedResponse}
                    onChange={(e) => setEditedResponse(e.target.value)}
                    className="w-full p-3 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                    rows={6}
                />
                <div className="flex justify-end gap-2 mt-3">
                    <button
                        onClick={() => setIsEditing(false)}
                        className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700 rounded-lg transition-colors"
                        disabled={loading}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSaveEdit}
                        className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                        disabled={loading}
                    >
                        {loading ? 'Saving...' : 'Submit Correction'}
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-wrap items-center gap-2 mt-6 pt-4 border-t border-gray-100 dark:border-gray-700 text-sm text-gray-500 select-none">
            <span className="text-xs mr-2">Was this helpful?</span>

            <button
                onClick={handleLike}
                disabled={status !== 'idle'}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg transition-all ${
                    status === 'liked'
                        ? 'text-green-700 bg-green-100 dark:bg-green-900/30 dark:text-green-400 font-medium'
                        : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400'
                } ${status !== 'idle' && status !== 'liked' ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
                👍 Helpful
            </button>

            <button
                onClick={handleDislike}
                disabled={status !== 'idle'}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg transition-all ${
                    status === 'disliked'
                        ? 'text-red-700 bg-red-100 dark:bg-red-900/30 dark:text-red-400 font-medium'
                        : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400'
                } ${status !== 'idle' && status !== 'disliked' ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
                👎 Incorrect
            </button>

            <div className="w-px h-4 bg-gray-300 dark:bg-gray-600 mx-2 hidden sm:block"></div>

            <button
                onClick={() => setIsEditing(true)}
                disabled={status === 'edited'}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg transition-all ${
                    status === 'edited'
                        ? 'text-blue-700 bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400 font-medium'
                        : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400'
                }`}
            >
                📝 {status === 'edited' ? 'Corrected' : 'Suggest Edit'}
            </button>

            <button
                onClick={handleCopy}
                className="flex items-center gap-1 px-3 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400 transition-colors"
            >
                📋 Copy
            </button>
        </div>
    );
}