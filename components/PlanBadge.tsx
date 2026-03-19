// components/PlanBadge.tsx
"use client"

import { useEffect, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import Link from 'next/link';

export default function PlanBadge() {
    const { getToken } = useAuth();
    const [plan, setPlan] = useState<'free' | 'pro' | null>(null);

    useEffect(() => {
        const fetchPlan = async () => {
            try {
                const token = await getToken({ skipCache: true });
                if (!token) return;
                const res = await fetch('http://127.0.0.1:8000/api/user/status', {
                    headers: { Authorization: `Bearer ${token}` }
                });
                const data = await res.json();
                setPlan(data.plan_type);
            } catch {
                // 靜默失敗
            }
        };
        fetchPlan();
    }, [getToken]);

    if (!plan) return null;

    if (plan === 'pro') {
        return (
            <span
                className="text-xs font-bold tracking-widest px-2 py-0.5 rounded"
                style={{ color: '#ffb347', letterSpacing: '0.12em' }}
            >
                PRO
            </span>
        );
    }

    // Free 用戶：顯示 FREE + Upgrade 連結
    return (
        <div className="flex items-center gap-1.5">
            <span
                className="text-xs font-medium px-2 py-0.5 rounded"
                style={{
                    color: 'rgba(255,255,255,0.4)',
                    background: 'rgba(255,255,255,0.06)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    letterSpacing: '0.08em',
                    fontSize: '0.65rem'
                }}
            >
                FREE
            </span>
            <Link
                href="#"
                onClick={(e) => {
                    e.preventDefault();
                }}
                className="font-semibold transition-colors"
                style={{ color: '#ff8e6e', fontSize: '0.8rem' }}
            >
                Upgrade
            </Link>
        </div>
    );
}
