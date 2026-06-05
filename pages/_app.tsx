import { ClerkProvider, useUser } from '@clerk/nextjs';
import { ThemeProvider } from 'next-themes';
import type { AppProps } from 'next/app';
import Head from 'next/head';
import { Noto_Sans } from 'next/font/google';
import posthog from 'posthog-js';
import { PostHogProvider } from 'posthog-js/react';
import { useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import { LangProvider } from '../utils/LangContext';
import { reset as resetAnalytics, identify, track, type Tier } from '../utils/analytics';
import '../styles/globals.css';

const notoSans = Noto_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-sans',
  display: 'swap',
});

const ANON_ALIASED_KEY = 'vela_anon_aliased';

if (typeof window !== 'undefined') {
  posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://app.posthog.com',
    capture_pageview: false, // 手動追蹤，配合 Next.js 路由
  });
}

const HREFLANG_CODES = [
  'en', 'zh-TW', 'zh-CN', 'ja', 'ko', 'es', 'fr', 'de',
  'it', 'pt', 'th', 'ar', 'hi', 'bn', 'he', 'vi',
];

// Bridges Clerk auth state to PostHog analytics identity.
// - signedOut -> signedIn (first time on device): alias anon distinct_id to Clerk user_id, then identify.
// - signedOut -> signedIn (subsequent): identify only.
// - signedIn -> signedOut: reset analytics identity + super properties.
// Rendered inside ClerkProvider so useUser() is available.
function AnalyticsAuthBridge() {
  const { isLoaded, isSignedIn, user } = useUser();
  const prevSignedIn = useRef<boolean | null>(null);

  useEffect(() => {
    if (!isLoaded) return;
    const current = Boolean(isSignedIn);
    // First-mount: hydrate analytics identity so tier super-prop isn't
    // stuck at L0 when the user opens a fresh tab with an existing Clerk
    // session. This path is NOT a signedOut → signedIn transition, so
    // do NOT alias and do NOT fire anonymous_to_registered — those are
    // reserved for the real transition branch below (guarded by the
    // vela_anon_aliased localStorage flag).
    if (prevSignedIn.current === null) {
      if (current) {
        const clerkUserId = user?.id;
        if (clerkUserId) {
          const plan = (user?.publicMetadata as { plan?: string } | undefined)?.plan;
          const tier: Tier = plan === 'pro' ? 'L2' : 'L1';
          identify(clerkUserId, { tier });
        }
      }
      prevSignedIn.current = current;
      return;
    }
    if (prevSignedIn.current && !current) {
      resetAnalytics();
    }
    if (!prevSignedIn.current && current) {
      const clerkUserId = user?.id;
      if (!clerkUserId) {
        // eslint-disable-next-line no-console
        console.warn('[analytics] signIn transition but user.id is undefined — skipping alias/identify');
        prevSignedIn.current = current;
        return;
      }

      // Derive tier from Clerk publicMetadata.plan if available; default to L1.
      // Downstream plan-cache fetch (per-feature page) may call identify() again
      // with a concrete plan_type once the /api/user/status response resolves.
      const plan = (user?.publicMetadata as { plan?: string } | undefined)?.plan;
      const tier: Tier = plan === 'pro' ? 'L2' : 'L1';

      let aliased = false;
      try { aliased = localStorage.getItem(ANON_ALIASED_KEY) === '1'; } catch {}

      if (!aliased) {
        let anonId: string | null = null;
        try { anonId = posthog.get_distinct_id?.() ?? null; } catch {}
        try { posthog.alias(clerkUserId, anonId ?? undefined); } catch (err) {
          // eslint-disable-next-line no-console
          console.warn('[analytics] alias failed', err);
        }
        identify(clerkUserId, { tier });
        track('anonymous_to_registered', { signup_method: 'clerk', anon_id: anonId });
        try { localStorage.setItem(ANON_ALIASED_KEY, '1'); } catch {}
      } else {
        identify(clerkUserId, { tier });
      }
    }
    prevSignedIn.current = current;
  }, [isLoaded, isSignedIn, user]);

  return null;
}

export default function MyApp({ Component, pageProps }: AppProps) {
  const router = useRouter();

  useEffect(() => {
    const handleRouteChange = () => posthog.capture('$pageview');
    router.events.on('routeChangeComplete', handleRouteChange);
    return () => router.events.off('routeChangeComplete', handleRouteChange);
  }, [router.events]);

  const path = router.asPath.split('?')[0].split('#')[0];
  const canonicalUrl = `https://vela.an-tho.com${path}`;

  return (
    <div className={`${notoSans.variable} font-sans`}>
    <PostHogProvider client={posthog}>
      <Head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta key="description" name="description" content="Research PubMed 40M+, verify drug interactions against FDA, and explain lab results in any language." />
        <meta key="og:type" property="og:type" content="website" />
        <meta key="og:site_name" property="og:site_name" content="Vela" />
        <meta key="og:image" property="og:image" content="https://vela.an-tho.com/og-image.png" />
        <meta key="og:image:width" property="og:image:width" content="1200" />
        <meta key="og:image:height" property="og:image:height" content="630" />
        <meta key="twitter:card" name="twitter:card" content="summary_large_image" />
        <meta key="twitter:image" name="twitter:image" content="https://vela.an-tho.com/og-image.png" />
        <link key="canonical" rel="canonical" href={canonicalUrl} />
        {HREFLANG_CODES.map((code) => (
          <link key={code} rel="alternate" hrefLang={code} href={canonicalUrl} />
        ))}
        <link rel="alternate" hrefLang="x-default" href={canonicalUrl} />
      </Head>
      <ClerkProvider
        {...pageProps}
        publishableKey={process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}
        signInUrl="/sign-in"
        signUpUrl="/sign-up"
        signInFallbackRedirectUrl="/research"
        signUpFallbackRedirectUrl="/research"
        appearance={{
          baseTheme: undefined,
          variables: {
            colorPrimary: '#2563eb', // 藍色主題
          }
        }}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          enableSystem
          disableTransitionOnChange
        >
          <LangProvider>
            <AnalyticsAuthBridge />
            <Component {...pageProps} />
          </LangProvider>
        </ThemeProvider>
      </ClerkProvider>
    </PostHogProvider>
    </div>
  );
}
