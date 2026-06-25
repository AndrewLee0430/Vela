import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const nextConfig: NextConfig = {
  output: 'export',  // This exports static HTML/JS files
  images: {
    unoptimized: true  // Required for static export
  },
  // Lint is a STANDALONE safety net (`npm run lint`), not a build gate — `next build`
  // is the deploy gate (TypeScript + build errors). This preserves the pre-existing
  // behavior (build did not run ESLint while the flat config was missing) so adding
  // eslint.config.mjs does not suddenly fail the build on pre-existing lint debt.
  eslint: {
    ignoreDuringBuilds: true,
  },
  // PRD § 4.5 — dev quality-of-life: forward /q/* and /api/share/* to
  // FastAPI on :8000 so localhost:3000 (next dev) can render the
  // public Jinja2 page without a separate proxy. Production is static
  // export, so rewrites() does not run there — FastAPI catch-all
  // handles routing on the same domain. Gated on NODE_ENV so
  // `npm run build` (output: 'export') is unaffected.
  async rewrites() {
    if (process.env.NODE_ENV !== 'development') {
      return [];
    }
    const backend = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    return [
      { source: '/q/:share_id', destination: `${backend}/q/:share_id` },
      { source: '/explore/:slug', destination: `${backend}/explore/:slug` },
      { source: '/sitemap-explore.xml', destination: `${backend}/sitemap-explore.xml` },
      { source: '/api/share/:path*', destination: `${backend}/api/share/:path*` },
      { source: '/static/og/:filename', destination: `${backend}/static/og/:filename` },
      { source: '/static/og/explore/:filename', destination: `${backend}/static/og/explore/:filename` },
    ];
  },
};

export default withSentryConfig(nextConfig, {
  silent: true,
  sourcemaps: { disable: true },
  // tunnelRoute omitted: requires a Next.js server, incompatible with static export
});
