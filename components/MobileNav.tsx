"use client"

import Link from 'next/link';
import { useRouter } from 'next/router';
import { useLang } from '../utils/LangContext';
import { getExtra } from '../utils/i18n-extra';

const TABS = [
  {
    href: '/research',
    labelKey: 'research' as const,
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
    ),
  },
  {
    href: '/verify',
    labelKey: 'verify' as const,
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <polyline points="9 12 11 14 15 10" />
      </svg>
    ),
  },
  {
    href: '/explain',
    labelKey: 'explain' as const,
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
    ),
  },
  {
    href: '/history',
    labelKey: 'history' as const,
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="12 8 12 12 14 14" />
        <path d="M3.05 11a9 9 0 1 0 .5-4" />
        <polyline points="3 3 3 7 7 7" />
      </svg>
    ),
  },
];

export default function MobileNav() {
  const { pathname } = useRouter();
  const { lang } = useLang();
  const extra = getExtra(lang);
  const labelMap = {
    research: extra.navResearch,
    verify: extra.navVerify,
    explain: extra.navExplain,
    history: extra.navHistory,
  } as const;

  return (
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 z-50 flex"
      style={{
        background: 'rgba(6, 12, 30, 0.95)',
        borderTop: '1px solid rgb(var(--color-text) / 0.08)',
        backdropFilter: 'blur(16px)',
        paddingBottom: 'env(safe-area-inset-bottom, 0px)',
      }}
    >
      {TABS.map((tab) => {
        const isActive = pathname === tab.href;
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className="flex-1 flex flex-col items-center justify-center py-3 gap-1 transition-all duration-200"
            style={{ color: isActive ? 'rgb(var(--color-brand))' : 'rgb(var(--color-text) / 0.35)' }}
          >
            {tab.icon}
            <span className="text-[10px] font-medium tracking-wide">
              {labelMap[tab.labelKey]}
            </span>
            {isActive && (
              <span
                className="absolute top-0 block h-0.5 w-8 rounded-full"
                style={{ background: 'rgb(var(--color-brand))' }}
              />
            )}
          </Link>
        );
      })}
    </nav>
  );
}
