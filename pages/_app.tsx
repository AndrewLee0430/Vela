import { ClerkProvider } from '@clerk/nextjs';
import type { AppProps } from 'next/app';
import Head from 'next/head';
import posthog from 'posthog-js';
import { PostHogProvider } from 'posthog-js/react';
import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { LangProvider } from '../utils/LangContext';
import '../styles/globals.css';

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
    <PostHogProvider client={posthog}>
      <Head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta key="description" name="description" content="Research PubMed 36M+, verify drug interactions against FDA, and explain lab results in any language." />
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
        appearance={{
          baseTheme: undefined,
          variables: {
            colorPrimary: '#2563eb', // 藍色主題
          }
        }}
      >
        <LangProvider>
          <Component {...pageProps} />
        </LangProvider>
      </ClerkProvider>
    </PostHogProvider>
  );
}
