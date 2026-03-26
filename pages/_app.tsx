import { ClerkProvider } from '@clerk/nextjs';
import type { AppProps } from 'next/app';
import { DefaultSeo } from 'next-seo';
import posthog from 'posthog-js';
import { PostHogProvider } from 'posthog-js/react';
import { useEffect } from 'react';
import { useRouter } from 'next/router';
import 'react-datepicker/dist/react-datepicker.css';
import '../styles/globals.css';

if (typeof window !== 'undefined') {
  posthog.init(process.env.NEXT_PUBLIC_POSTHOG_KEY!, {
    api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://app.posthog.com',
    capture_pageview: false, // 手動追蹤，配合 Next.js 路由
  });
}

export default function MyApp({ Component, pageProps }: AppProps) {
  const router = useRouter();

  useEffect(() => {
    const handleRouteChange = () => posthog.capture('$pageview');
    router.events.on('routeChangeComplete', handleRouteChange);
    return () => router.events.off('routeChangeComplete', handleRouteChange);
  }, [router.events]);

  return (
    <PostHogProvider client={posthog}>
      <DefaultSeo
        titleTemplate="%s | Vela"
        defaultTitle="Vela — Clinical AI for Healthcare Professionals"
        description="Research PubMed 36M+, verify drug interactions against FDA, and explain lab results in any language."
        canonical="https://vela.an-tho.com"
        openGraph={{
          type: 'website',
          url: 'https://vela.an-tho.com',
          siteName: 'Vela',
          images: [{ url: 'https://vela.an-tho.com/og-image.png', width: 1200, height: 630 }],
        }}
      />
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
        <Component {...pageProps} />
      </ClerkProvider>
    </PostHogProvider>
  );
}
