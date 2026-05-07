// contexts/ShareContext.tsx
// PRD § 4.5 UX polish 2/3 — lifts the Share button from per-page
// FeedbackBar adjacency to a single Navbar slot. The active answer
// page populates `shareData`; Navbar reads it and renders the button
// only when it's non-null. Streaming-in-progress = null. Completed
// answer = full payload ready for ShareModal.

import { createContext, useCallback, useContext, useState, type ReactNode } from 'react';

export interface ShareData {
    queryId: string;
    queryText: string;
    answerText: string;
    citations: unknown[];
    feature: 'research' | 'verify' | 'explain';
}

interface ShareContextValue {
    shareData: ShareData | null;
    setShareData: (data: ShareData) => void;
    clearShareData: () => void;
}

const ShareContext = createContext<ShareContextValue | null>(null);

export function ShareProvider({ children }: { children: ReactNode }) {
    const [shareData, setShareDataState] = useState<ShareData | null>(null);
    const setShareData = useCallback((data: ShareData) => setShareDataState(data), []);
    const clearShareData = useCallback(() => setShareDataState(null), []);
    return (
        <ShareContext.Provider value={{ shareData, setShareData, clearShareData }}>
            {children}
        </ShareContext.Provider>
    );
}

// Inert no-op fallback when the hook is consumed outside a provider
// tree. Prevents crashes on routes that don't mount PageShell (e.g.
// /q/{id} static SSR shell, landing page) and avoids forcing every
// future consumer to wrap itself in conditional checks.
const NOOP_VALUE: ShareContextValue = {
    shareData: null,
    setShareData: () => {},
    clearShareData: () => {},
};

export function useShareContext(): ShareContextValue {
    return useContext(ShareContext) ?? NOOP_VALUE;
}
