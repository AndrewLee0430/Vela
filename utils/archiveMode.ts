// utils/archiveMode.ts — archive car (2026-10-05). Vela is an archived open work;
// the live demo serves anonymous Research only.
//
// ARCHIVE_MODE is a BUILD-TIME constant: NEXT_PUBLIC_* values are inlined by
// `next build` (fly.toml [build.args] → Dockerfile ARG/ENV). Default OFF, so a
// local `npm run build` without the variable ships the product unchanged.
// The backend twin is the ARCHIVE_MODE env flag in api/server.py (410 gate).
export const ARCHIVE_MODE = process.env.NEXT_PUBLIC_ARCHIVE_MODE === 'true';

// The static showcase (showcase/ at the repo root, deployed separately to
// Cloudflare Pages). PLACEHOLDER until the founder picks the hostname — the
// ONE place to fill it (archive-car baton, founder checklist).
export const SHOWCASE_URL = '{{SHOWCASE_URL}}';
