// components/Toast.tsx
"use client"

import { useEffect } from 'react';

interface ToastProps {
    message: string;
    onClose: () => void;
    duration?: number;
    type?: 'success' | 'warning' | 'error';
}

export default function Toast({ message, onClose, duration = 3000, type = 'success' }: ToastProps) {
    useEffect(() => {
        const timer = setTimeout(onClose, duration);
        return () => clearTimeout(timer);
    }, [duration, onClose]);

    const styles = {
        success: { bg: '#16a34a', icon: '✅' },
        warning: { bg: '#d97706', icon: '⚠️' },
        error:   { bg: '#dc2626', icon: '❌' },
    };

    const { bg, icon } = styles[type];

    return (
        <div className="fixed bottom-4 right-4 z-50 animate-slideUp">
            <div
                className="text-white px-6 py-3 rounded-lg shadow-lg flex items-center gap-2 max-w-sm"
                style={{ background: bg }}
            >
                <span>{icon}</span>
                <span className="text-sm">{message}</span>
            </div>
        </div>
    );
}
