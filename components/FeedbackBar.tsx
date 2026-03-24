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
        <div className="flex items-center gap-2 mt-4 pt-3 border-t select-none" style={{ borderColor: 'rgba(255,255,255,0.12)' }}>
            <span className="text-xs" style={{ color: 'rgba(255,255,255,0.5)' }}>Was this helpful?</span>
            <button
                onClick={handleLike}
                disabled={status !== 'idle'}
                title="Helpful"
                className="w-8 h-8 flex items-center justify-center rounded-lg transition-all text-base disabled:cursor-default"
                style={{
                    background: status === 'liked' ? 'rgba(104,211,145,0.2)' : 'rgba(255,255,255,0.06)',
                    border: `1px solid ${status === 'liked' ? 'rgba(104,211,145,0.5)' : 'rgba(255,255,255,0.12)'}`,
                    opacity: status === 'disliked' ? 0.35 : 1,
                }}
            >
                👍
            </button>
            <button
                onClick={handleDislike}
                disabled={status !== 'idle'}
                title="Not helpful"
                className="w-8 h-8 flex items-center justify-center rounded-lg transition-all text-base disabled:cursor-default"
                style={{
                    background: status === 'disliked' ? 'rgba(252,129,129,0.2)' : 'rgba(255,255,255,0.06)',
                    border: `1px solid ${status === 'disliked' ? 'rgba(252,129,129,0.5)' : 'rgba(255,255,255,0.12)'}`,
                    opacity: status === 'liked' ? 0.35 : 1,
                }}
            >
                👎
            </button>
            {status !== 'idle' && (
                <span className="text-xs ml-1" style={{ color: 'rgba(255,255,255,0.4)' }}>Thanks!</span>
            )}
        </div>
    );
}
