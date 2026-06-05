import { Html, Head, Main, NextScript } from 'next/document'

export default function Document() {
  return (
    <Html lang="en">
      <Head>
        {/* Theme-init (FOUC guard) — runs synchronously in <head> before any body
            paint, mirroring next-themes 0.4.x resolution (storageKey 'theme',
            defaultTheme 'light', attribute 'class', enableSystem). Pages-Router
            static export injects next-themes' own script at the top of <body>,
            which is too late and causes a flash; this sets the class first.
            The default fallback MUST match ThemeProvider's defaultTheme in
            pages/_app.tsx ('light') — if they disagree, a no-preference visitor's
            first paint flashes the wrong theme. Keep IN SYNC with _app.tsx. */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var d=document.documentElement,e=localStorage.getItem('theme')||'light';if(e==='system'){e=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}d.classList.remove('light','dark');d.classList.add(e);d.style.colorScheme=e;}catch(e){}})();`,
          }}
        />
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png" />
        <link rel="shortcut icon" href="/favicon.ico" />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  )
}