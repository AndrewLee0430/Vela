"use client"

import { useState, useRef, useEffect, useCallback, ReactNode } from 'react';
import UpgradeModal from './UpgradeModal';

interface ProFeatureOverlayProps {
    children: ReactNode;
    featureName: string;
    isLocked: boolean;
}

export default function ProFeatureOverlay({ children, featureName, isLocked }: ProFeatureOverlayProps) {
    const [showPopover, setShowPopover] = useState(false);
    const [showModal, setShowModal] = useState(false);
    const [above, setAbove] = useState(true);
    const wrapperRef = useRef<HTMLDivElement>(null);
    const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Close on outside click (mobile fallback)
    useEffect(() => {
        if (!showPopover) return;
        function handleClick(e: MouseEvent) {
            if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
                setShowPopover(false);
            }
        }
        document.addEventListener('mousedown', handleClick);
        return () => document.removeEventListener('mousedown', handleClick);
    }, [showPopover]);

    const updateDirection = useCallback(() => {
        if (wrapperRef.current) {
            const rect = wrapperRef.current.getBoundingClientRect();
            setAbove(rect.top > 120);
        }
    }, []);

    if (!isLocked) return <>{children}</>;

    function handleMouseEnter() {
        if (hoverTimer.current) clearTimeout(hoverTimer.current);
        hoverTimer.current = setTimeout(() => {
            updateDirection();
            setShowPopover(true);
        }, 200);
    }

    function handleMouseLeave() {
        if (hoverTimer.current) clearTimeout(hoverTimer.current);
        hoverTimer.current = setTimeout(() => {
            setShowPopover(false);
        }, 150);
    }

    // Mobile: click to toggle (no hover on touch devices)
    function handleChildClick(e: React.MouseEvent) {
        e.preventDefault();
        e.stopPropagation();
        updateDirection();
        setShowPopover(prev => !prev);
    }

    return (
        <>
            <div
                ref={wrapperRef}
                className="relative w-full"
                onMouseEnter={handleMouseEnter}
                onMouseLeave={handleMouseLeave}
            >
                {/* Children rendered with dimmed + blocked style */}
                <div
                    className="opacity-50 cursor-not-allowed"
                    onClick={handleChildClick}
                    onDragOver={e => { e.preventDefault(); e.stopPropagation(); }}
                    onDrop={e => { e.preventDefault(); e.stopPropagation(); }}
                >
                    <div style={{ pointerEvents: 'none' }}>
                        {children}
                    </div>
                </div>

                {/* Popover */}
                <div
                    className="absolute left-1/2 z-50"
                    style={{
                        transform: `translateX(-50%) translateY(${showPopover ? '0' : '4px'})`,
                        opacity: showPopover ? 1 : 0,
                        pointerEvents: showPopover ? 'auto' : 'none',
                        transition: 'opacity 200ms, transform 200ms',
                        ...(above
                            ? { bottom: '100%', marginBottom: '8px' }
                            : { top: '100%', marginTop: '8px' }),
                    }}
                >
                    <div
                        className="rounded-lg shadow-lg p-3 whitespace-nowrap"
                        style={{ background: '#1e293b', border: '1px solid #475569' }}
                    >
                        {/* Row 1: lock + label */}
                        <div className="flex items-center gap-1.5 mb-2">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fbbf24" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                            </svg>
                            <span className="text-sm font-medium" style={{ color: '#fbbf24' }}>Pro feature</span>
                        </div>
                        {/* Row 2: upgrade button */}
                        <button
                            onClick={(e) => { e.stopPropagation(); setShowPopover(false); setShowModal(true); }}
                            className="px-3 py-1 text-xs font-semibold rounded-full text-white transition-opacity hover:opacity-90"
                            style={{ background: '#ff8e6e' }}
                        >
                            Upgrade
                        </button>
                    </div>
                    {/* Arrow */}
                    <div
                        className="absolute left-1/2"
                        style={{
                            transform: 'translateX(-50%)',
                            ...(above
                                ? { top: '100%', marginTop: '-1px' }
                                : { bottom: '100%', marginBottom: '-1px' }),
                        }}
                    >
                        <div
                            style={{
                                width: 0, height: 0,
                                borderLeft: '6px solid transparent',
                                borderRight: '6px solid transparent',
                                ...(above
                                    ? { borderTop: '6px solid #475569' }
                                    : { borderBottom: '6px solid #475569' }),
                            }}
                        />
                        <div
                            className="absolute left-1/2"
                            style={{
                                transform: 'translateX(-50%)',
                                width: 0, height: 0,
                                borderLeft: '5px solid transparent',
                                borderRight: '5px solid transparent',
                                ...(above
                                    ? { top: '-7px', borderTop: '5px solid #1e293b' }
                                    : { bottom: '-7px', borderBottom: '5px solid #1e293b' }),
                            }}
                        />
                    </div>
                </div>
            </div>
            <UpgradeModal isOpen={showModal} onClose={() => setShowModal(false)} />
        </>
    );
}
