// utils/archiveMode.ts — archive car (2026-10-05). Vela is an archived open work;
// the live demo serves anonymous Research only.
//
// ARCHIVE_MODE is a BUILD-TIME constant: NEXT_PUBLIC_* values are inlined by
// `next build` (fly.toml [build.args] → Dockerfile ARG/ENV). Default OFF, so a
// local `npm run build` without the variable ships the product unchanged.
// The backend twin is the ARCHIVE_MODE env flag in api/server.py (410 gate).
export const ARCHIVE_MODE = process.env.NEXT_PUBLIC_ARCHIVE_MODE === 'true';

// The archive page (closeout ruling R1, 2026-10-05): plain static HTML at
// public/about/ (exported to out/about/), served by the same FastAPI app on
// vela.an-tho.com — NOT a Next.js route, so link to it with a plain <a>, never
// next/link (the client router does not know the page).
export const SHOWCASE_URL = '/about/';
