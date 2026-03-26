"use client"

import { useState } from 'react';
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/nextjs';
import Link from 'next/link';
import Image from 'next/image';
import PlanBadge from './PlanBadge';
import UpgradeModal from './UpgradeModal';

const BG = 'linear-gradient(135deg, #0a1628 0%, #0f2040 45%, #1a1035 75%, #0d1a2e 100%)';

const LINK_COLORS: Record<string, string> = {
    research: '#ff8e6e',
    verify:   '#63b3ed',
    explain:  '#68d391',
    history:  '#ffffff',
};

type ActivePage = 'research' | 'verify' | 'explain' | 'history';

interface NavbarProps {
    activePage?: ActivePage;
}

export default function Navbar({ activePage }: NavbarProps) {
    const [showUpgradeModal, setShowUpgradeModal] = useState(false);

    return (
        <>
            <nav className="border-b" style={{ background: BG, borderColor: 'rgba(255,255,255,0.07)' }}>
                <div className="container mx-auto px-4 py-3">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-8">
                            <Link href="/" className="group relative flex items-center" title="Homepage">
                                <Image src="/coral_logo.png" alt="Vela" width={60} height={60} style={{ objectFit: 'contain' }} />
                                <span className="absolute -bottom-7 left-1/2 -translate-x-1/2 text-xs bg-gray-800 text-white px-2 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none z-10">
                                    Homepage
                                </span>
                            </Link>
                            <div className="hidden md:flex items-center gap-6 text-sm">
                                {(['research', 'verify', 'explain', 'history'] as const).map(page => (
                                    <Link
                                        key={page}
                                        href={`/${page}`}
                                        className={activePage === page ? 'font-medium transition-colors' : 'text-gray-400 hover:text-white transition-colors'}
                                        style={activePage === page ? { color: LINK_COLORS[page] } : {}}
                                    >
                                        {page.charAt(0).toUpperCase() + page.slice(1)}
                                    </Link>
                                ))}
                            </div>
                        </div>
                        <div className="flex items-center gap-0">
                            <PlanBadge onUpgrade={() => setShowUpgradeModal(true)} />
                            <SignedIn><UserButton showName={true} /></SignedIn>
                            <SignedOut>
                                <SignInButton mode="modal">
                                    <button
                                        className="px-4 py-1.5 text-sm font-medium text-white rounded-lg transition-all duration-200"
                                        style={{ border: '1px solid rgba(255,255,255,0.2)' }}
                                        onMouseEnter={e => ((e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.1)')}
                                        onMouseLeave={e => ((e.currentTarget as HTMLElement).style.background = 'transparent')}
                                    >
                                        Sign In
                                    </button>
                                </SignInButton>
                            </SignedOut>
                        </div>
                    </div>
                </div>
            </nav>
            <UpgradeModal isOpen={showUpgradeModal} onClose={() => setShowUpgradeModal(false)} />
        </>
    );
}
