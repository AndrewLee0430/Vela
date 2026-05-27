import { ReactNode } from 'react';
import { SignedIn, SignedOut, RedirectToSignIn } from '@clerk/nextjs';
import Navbar from './Navbar';
import MobileNav from './MobileNav';
import BugReportButton from './BugReportButton';
import { ShareProvider } from '../contexts/ShareContext';

type ActivePage = 'research' | 'verify' | 'explain' | 'history' | 'settings';

interface PageShellProps {
    activePage: ActivePage;
    children: ReactNode;
    extraHead?: ReactNode;
    allowAnonymous?: boolean;
}

export default function PageShell({ activePage, children, extraHead, allowAnonymous = false }: PageShellProps) {
    return (
        <>
            {extraHead}
            <main className="min-h-screen pb-20 md:pb-0 bg-app-bg">
                <ShareProvider>
                    <Navbar activePage={activePage} />
                    {allowAnonymous ? (
                        children
                    ) : (
                        <>
                            <SignedIn>{children}</SignedIn>
                            <SignedOut><RedirectToSignIn /></SignedOut>
                        </>
                    )}
                    <MobileNav />
                    <BugReportButton />
                </ShareProvider>
            </main>
        </>
    );
}
