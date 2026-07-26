// utils/userContext.ts
//
// PRD §3.1 PHASE C — the WRITER for the canonical user-context blob that
// `utils/analytics.ts` has READ since 2026-04-18 but nothing ever populated
// (retrospective §2 Finding A — analytics silent-loss). It targets the EXACT
// same store analytics reads: a single JSON blob at localStorage key
// `vela_user_context`, with nested fields. analytics' read is SYNCHRONOUS, so
// the derived `user_context_hash` is computed at WRITE time (async
// crypto.subtle) and CACHED into the blob — the sync read never awaits.
//
// PHASE C scope (locked): writer + work_language dual-write + hash cache + the
// §2.9 canonical-first read order. NO backend POST, NO fetch, NO token, NO
// locale write, NO identify() change, NO onboarding fields — those are PHASE D/E.

import type { LocaleSetting } from "./country";

const USER_CONTEXT_KEY = "vela_user_context";
const LEGACY_LANG_KEY = "vela_lang";

// SHA-256("")[:16] — the deterministic hash of an all-null context.
const EMPTY_CONTEXT_HASH = "e3b0c44298fc1c14";

/**
 * Canonical user-context shape (PRD §3.1). `work_language`, `user_context_hash`,
 * and `version` were PHASE C; `locale` (the COUNTRY field, Phase 1B 在地差異 b1) is
 * written by `setLocale`. `locale` is NOT a `user_context_hash` input — it is posted
 * as a separate field by contextSync — so setLocale does not recompute the hash.
 */
export interface UserContextData {
  workplace: string | null;
  role: string | null;
  work_language: string | null;
  locale: LocaleSetting | null;   // COUNTRY (or 'OTHER'). NOT a language — see utils/country.ts.
  onboarding_completed: boolean;
  onboarding_completed_at: string | null;
  version: number;
  user_context_hash: string;
}

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

/** Read the raw blob as a partial (unknown/missing fields stay undefined). */
export function readRaw(): Partial<UserContextData> {
  if (!isBrowser()) return {};
  try {
    const raw = localStorage.getItem(USER_CONTEXT_KEY);
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) return {};
    return parsed as Partial<UserContextData>;
  } catch {
    return {};
  }
}

/**
 * Merge a patch into the blob, preserving any pre-existing fields written by
 * other phases. Always stamps `version: 1`. SSR-safe no-op off-browser.
 */
export function writeMerge(patch: Partial<UserContextData>): void {
  if (!isBrowser()) return;
  try {
    const next = { ...readRaw(), ...patch, version: 1 };
    localStorage.setItem(USER_CONTEXT_KEY, JSON.stringify(next));
  } catch {
    /* localStorage unavailable / quota — non-fatal */
  }
}

/**
 * user_context_hash = SHA-256( [workplace, role, work_language]
 *   .filter(f => f != null).join('|') )  → hex → first 16 chars.
 * Null fields are excluded; an all-null context hashes to EMPTY_CONTEXT_HASH.
 * Async (crypto.subtle.digest); callers cache the result into the blob.
 */
export async function computeHash(
  workplace: string | null,
  role: string | null,
  work_language: string | null
): Promise<string> {
  const input = [workplace, role, work_language]
    .filter((f): f is string => f != null)
    .join("|");
  if (input.length === 0) return EMPTY_CONTEXT_HASH;
  try {
    const bytes = new TextEncoder().encode(input);
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(digest))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("")
      .slice(0, 16);
  } catch {
    // crypto.subtle unavailable (insecure context) — fall back to the empty
    // sentinel rather than caching a wrong/partial value.
    return EMPTY_CONTEXT_HASH;
  }
}

/**
 * Canonical-first read of the work language (§2.9 read-order fix):
 * `vela_user_context.work_language` first, legacy `vela_lang` as fallback.
 * Returns null when neither is set (a never-chose user — no default injected).
 */
export function getWorkLanguage(): string | null {
  if (!isBrowser()) return null;
  const fromBlob = readRaw().work_language;
  if (typeof fromBlob === "string" && fromBlob.length > 0) return fromBlob;
  try {
    const legacy = localStorage.getItem(LEGACY_LANG_KEY);
    return legacy && legacy.length > 0 ? legacy : null;
  } catch {
    return null;
  }
}

/**
 * Explicit language change: dual-write `vela_lang` (legacy) AND
 * `vela_user_context.work_language` (canonical), then recompute + cache the
 * hash from the current workplace/role (preserved) + the new work_language.
 */
export async function setWorkLanguage(lang: string): Promise<void> {
  if (!isBrowser()) return;
  try {
    localStorage.setItem(LEGACY_LANG_KEY, lang);
  } catch {
    /* non-fatal */
  }
  const cur = readRaw();
  const hash = await computeHash(cur.workplace ?? null, cur.role ?? null, lang);
  writeMerge({ work_language: lang, user_context_hash: hash });
}

/**
 * Settings My Context — persist the COUNTRY field (在地差異 b1). `null` clears it
 * (fall through to the waterfall); 'OTHER' = the user's explicit "international" choice.
 * NOT a `user_context_hash` input (locale is posted separately by contextSync), so the
 * hash is NOT recomputed here.
 */
export function setLocale(locale: LocaleSetting | null): void {
  if (!isBrowser()) return;
  writeMerge({ locale });
}

/**
 * Onboarding Step 1 — persist workplace + recompute/cache the hash from
 * (workplace, current role, current work_language). Pass null on skip. PRD §3.2.
 */
export async function setWorkplace(workplace: string | null): Promise<void> {
  if (!isBrowser()) return;
  const cur = readRaw();
  const hash = await computeHash(workplace, cur.role ?? null, cur.work_language ?? null);
  writeMerge({ workplace, user_context_hash: hash });
}

/**
 * Onboarding Step 2 — persist role + recompute/cache the hash from
 * (current workplace, role, current work_language). Pass null on skip. PRD §3.2.
 */
export async function setRole(role: string | null): Promise<void> {
  if (!isBrowser()) return;
  const cur = readRaw();
  const hash = await computeHash(cur.workplace ?? null, role, cur.work_language ?? null);
  writeMerge({ role, user_context_hash: hash });
}

/**
 * Mark onboarding finished (PRD §3.2). onboarding_completed / _at are NOT hash
 * inputs, so the hash is NOT recomputed here. This flag is device-level and
 * intentionally NOT cleared on sign-out (unlike the tour's `hasSeenOnboarding`)
 * — context is on-device/local-first per the privacy stance, so a different
 * account on the same browser keeps the collected context. Do not "fix" this.
 */
export function completeOnboarding(): void {
  if (!isBrowser()) return;
  writeMerge({
    onboarding_completed: true,
    onboarding_completed_at: new Date().toISOString(),
  });
}

/**
 * Self-repair: recompute the hash from the blob's CURRENT fields and write it
 * back if it is missing or drifted (prevents stale-hash drift, F1). Creates the
 * blob with the all-null sentinel hash for a context that has no real signals
 * yet — so `user_context_hash` stops shipping null — WITHOUT inventing a
 * work_language (stays null until a real signal arrives). Async; lives here,
 * never inside analytics' synchronous track() read.
 */
export async function ensureFresh(): Promise<void> {
  if (!isBrowser()) return;
  const cur = readRaw();
  const expected = await computeHash(
    cur.workplace ?? null,
    cur.role ?? null,
    cur.work_language ?? null
  );
  if (cur.user_context_hash !== expected) {
    writeMerge({ user_context_hash: expected });
  }
}
