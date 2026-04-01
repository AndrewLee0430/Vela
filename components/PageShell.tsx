import { ReactNode } from 'react';
import { SignedIn, SignedOut, RedirectToSignIn } from '@clerk/nextjs';
import Navbar from './Navbar';
import MobileNav from './MobileNav';

type ActivePage = 'research' | 'verify' | 'explain' | 'history';

interface PageShellProps {
    activePage: ActivePage;
    children: ReactNode;
    extraHead?: ReactNode;
}

export default function PageShell({ activePage, children, extraHead }: PageShellProps) {
    return (
        <>
            {extraHead}
            <main
                className="min-h-screen pb-20 md:pb-0"
                style={{ background: "linear-gradient(135deg, #0a1628 0%, #0f2040 45%, #1a1035 75%, #0d1a2e 100%)" }}
            >
                <Navbar activePage={activePage} />
                <SignedIn>{children}</SignedIn>
                <SignedOut><RedirectToSignIn /></SignedOut>
                <MobileNav />
            </main>
        </>
    );
}
