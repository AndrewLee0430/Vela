import type { NextConfig } from "next";
import { withSentryConfig } from "@sentry/nextjs";

const nextConfig: NextConfig = {
  output: 'export',  // This exports static HTML/JS files
  images: {
    unoptimized: true  // Required for static export
  }
};

export default withSentryConfig(nextConfig, {
  silent: true,
  sourcemaps: { disable: true },
  // tunnelRoute omitted: requires a Next.js server, incompatible with static export
});
