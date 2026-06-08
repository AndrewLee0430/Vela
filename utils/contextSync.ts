// utils/contextSync.ts
//
// PRD §3.1 PHASE E — the FIRST-EVER caller of the PHASE B endpoints
// (POST/GET /api/user/context/hash, live since v167 but never called). This is
// the Pro-gated, SILENT server-sync layer for the user-context hash. It is the
// network boundary ONLY — local storage + hashing stay in utils/userContext.ts
// (kept pure). Privacy (v1.6): only { user_context_hash, locale } leave the
// device; raw workplace/role/work_language never do.
//
// Silent by design: a free user's 403 {type:"pro_required"} and a 429
// {type:"RATE_LIMITED_USER"} are swallowed (no throw, no upgrade modal) — context
// sync is a background nicety, NOT a gated feature. (Contrast explain.tsx, which
// throws pro_required to surface the upgrade modal — do NOT reuse that here.)

import { readRaw } from "./userContext";

const PLAN_CACHE_KEY = "vela_plan_cache";
const PLAN_TTL_MS = 5 * 60 * 1000;

type TokenGetter = () => Promise<string | null>;

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

/**
 * Frontend Pro gate (G4): read the optimistic plan cache that PlanBadge /
 * feature pages populate from /api/user/status. The backend 403 is the
 * authoritative defense-in-depth — this just avoids a doomed call for free users.
 * Cold/absent cache → treat as not-Pro (free-safe; a Pro user simply skips one
 * sync until the cache warms).
 */
function isProCached(): boolean {
  if (!isBrowser()) return false;
  try {
    const raw = localStorage.getItem(PLAN_CACHE_KEY);
    if (!raw) return false;
    const { plan, ts } = JSON.parse(raw);
    if (Date.now() - ts < PLAN_TTL_MS) return plan === "pro";
  } catch {
    /* ignore */
  }
  return false;
}

/**
 * UPSERT the cached user_context_hash (+ locale) to the backend. Pro-gated and
 * silent. Triggered on deliberate context-commit points (Settings save +
 * onboarding completion) — NOT on every language toggle (rate-limit / noise).
 * Any non-OK (403 pro_required / 429 RATE_LIMITED_USER / 5xx) or network error
 * is swallowed.
 */
export async function postContextHash(getToken: TokenGetter): Promise<void> {
  if (!isBrowser() || !isProCached()) return;
  try {
    const ctx = readRaw();
    const hash = ctx.user_context_hash;
    if (!hash) return; // nothing to sync yet
    const token = await getToken();
    if (!token) return;
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/user/context/hash`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ user_context_hash: hash, locale: ctx.locale ?? null }),
    });
    // intentionally ignore the response — success {ok:true} and every error are no-ops.
  } catch {
    /* network/error → silent */
  }
}

/**
 * Read back the server-stored hash (+ locale) for the signed-in Pro user.
 * Returns null silently on 404 {type:"not_found"} (never POSTed), 403, or any
 * error. Used by the sign-in restore banner (§4.3 需求5 Trigger A).
 */
export async function getContextHash(
  getToken: TokenGetter
): Promise<{ hash: string; locale: string | null } | null> {
  if (!isBrowser() || !isProCached()) return null;
  try {
    const token = await getToken();
    if (!token) return null;
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/user/context/hash`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return null; // 404 not_found / 403 pro_required → silent
    const data = await res.json();
    if (typeof data?.user_context_hash !== "string") return null;
    return { hash: data.user_context_hash, locale: data.locale ?? null };
  } catch {
    return null;
  }
}
