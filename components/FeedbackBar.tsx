"use client"

import { useState } from 'react';
import { useAuth } from '@clerk/nextjs';

interface FeedbackBarProps {
    query: string;
    response: string;
    category: 'research' | 'verify' | 'explain';
}

export default function FeedbackBar({ query, response, category }: FeedbackBarProps) {
    const { getToken } = useAuth();
    const [status, setStatus] = useState<'idle' | 'liked' | 'disliked'>('idle');

    const sendFeedback = async (rating: number) => {
        try {
            const token = await getToken({ skipCache: true });
            await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/feedback`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({ query, response, rating, feedback_text: null, category }),
            });
        } catch (err) {
            console.error('Feedback failed:', err);
        }
    };

    const handleLike = () => {
        if (status !== 'idle') return;
        setStatus('liked');
        sendFeedback(1);
    };

    const handleDislike = () => {
        if (status !== 'idle') return;
        setStatus('disliked');
        sendFeedback(-1);
    };

    return (
        <div className="flex items-center gap-1 mt-4 pt-3 border-t select-none" style={{ borderColor: 'rgba(255,255,255,0.08)' }}>
            <span className="text-xs mr-1" style={{ color: 'rgba(255,255,255,0.3)' }}>Helpful?</span>
            <button
                onClick={handleLike}
                disabled={status !== 'idle'}
                title="Helpful"
                className="w-7 h-7 flex items-center justify-center rounded-md transition-all text-sm disabled:cursor-default"
                style={{
                    background: status === 'liked' ? 'rgba(104,211,145,0.15)' : 'transparent',
                    color: status === 'liked' ? '#68d391' : 'rgba(255,255,255,0.3)',
                    opacity: status === 'disliked' ? 0.3 : 1,
                }}
            >
                👍
            </button>
            <button
                onClick={handleDislike}
                disabled={status !== 'idle'}
                title="Not helpful"
                className="w-7 h-7 flex items-center justify-center rounded-md transition-all text-sm disabled:cursor-default"
                style={{
                    background: status === 'disliked' ? 'rgba(252,129,129,0.15)' : 'transparent',
                    color: status === 'disliked' ? '#fc8181' : 'rgba(255,255,255,0.3)',
                    opacity: status === 'liked' ? 0.3 : 1,
                }}
            >
                👎
            </button>
        </div>
    );
}
