"use client"

import { useState, ReactNode } from 'react';
import UpgradeModal from './UpgradeModal';

interface ProFeatureOverlayProps {
    children: ReactNode;
    featureName: string;
    isLocked: boolean;
}

export default function ProFeatureOverlay({ children, featureName, isLocked }: ProFeatureOverlayProps) {
    const [showModal, setShowModal] = useState(false);
    const [hovered, setHovered] = useState(false);

    if (!isLocked) return <>{children}</>;

    return (
        <>
            <div
                className="relative"
                onMouseEnter={() => setHovered(true)}
                onMouseLeave={() => setHovered(false)}
            >
                {children}
                <div
                    className="absolute inset-0 rounded-lg flex flex-col items-center justify-center gap-2 transition-opacity duration-200"
                    style={{
                        background: 'rgba(0,0,0,0.6)',
                        backdropFilter: 'blur(4px)',
                        WebkitBackdropFilter: 'blur(4px)',
                        opacity: hovered ? 1 : 0,
                        pointerEvents: hovered ? 'auto' : 'none',
                    }}
                >
                    {/* Lock icon */}
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                    <span className="text-xs font-medium" style={{ color: '#fbbf24' }}>
                        {featureName} — Pro Feature
                    </span>
                    <button
                        onClick={(e) => { e.stopPropagation(); setShowModal(true); }}
                        className="px-4 py-1.5 text-xs font-semibold rounded-full text-white transition-opacity hover:opacity-90"
                        style={{ background: '#ff8e6e' }}
                    >
                        Upgrade to Pro
                    </button>
                </div>
            </div>
            <UpgradeModal isOpen={showModal} onClose={() => setShowModal(false)} />
        </>
    );
}
