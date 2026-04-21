import posthog from "posthog-js";

type PlanType = "free" | "pro";

export interface IdentifyTraits {
  plan_type?: PlanType;
  user_context_hash?: string | null;
  role_category?: string | null;
  work_language?: string | null;
  locale?: string | null;
  [key: string]: unknown;
}

const SESSION_ID_KEY = "vela_session_id";
const USER_CONTEXT_KEY = "vela_user_context";
const SUPER_PROP_KEYS = [
  "plan_type",
  "user_context_hash",
  "role_category",
  "work_language",
  "locale",
] as const;

let modulePlanType: PlanType = "free";
let moduleQueryId: string | null = null;

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

function isPosthogReady(): boolean {
  if (!isBrowser()) return false;
  return Boolean((posthog as unknown as { __loaded?: boolean }).__loaded);
}

function devWarn(msg: string, err?: unknown): void {
  if (process.env.NODE_ENV !== "production") {
    // eslint-disable-next-line no-console
    console.warn(`[analytics] ${msg}`, err ?? "");
  }
}

function getSessionId(): string | null {
  if (!isBrowser()) return null;
  try {
    let id = sessionStorage.getItem(SESSION_ID_KEY);
    if (!id) {
      id = crypto.randomUUID();
      sessionStorage.setItem(SESSION_ID_KEY, id);
    }
    return id;
  } catch (err) {
    devWarn("sessionStorage unavailable", err);
    return null;
  }
}

interface UserContext {
  user_context_hash: string | null;
  locale: string | null;
  work_language: string | null;
}

function readUserContext(): UserContext {
  const empty: UserContext = {
    user_context_hash: null,
    locale: null,
    work_language: null,
  };
  if (!isBrowser()) return empty;
  try {
    const raw = localStorage.getItem(USER_CONTEXT_KEY);
    if (!raw) return empty;
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) return empty;
    const obj = parsed as Record<string, unknown>;
    const pickString = (v: unknown): string | null =>
      typeof v === "string" && v.length > 0 ? v : null;
    return {
      user_context_hash: pickString(obj.user_context_hash),
      locale: pickString(obj.locale),
      work_language: pickString(obj.work_language),
    };
  } catch (err) {
    devWarn("failed to parse vela_user_context", err);
    return empty;
  }
}

/**
 * Session-scoped fingerprint for backend anonymous identity (Decision 001 v0.3 A2).
 * Returns the same UUID as PostHog session_id — correlating PostHog analytics
 * with backend anon_id (derived via SHA-256(salt + IP + fingerprint)[:16]).
 * SSR-safe: returns null when sessionStorage is unavailable.
 */
export function getAnonFingerprint(): string | null {
  return getSessionId();
}

function getQueryId(): string | null {
  return moduleQueryId;
}

export function setQueryId(id: string | null): void {
  moduleQueryId = id && id.length > 0 ? id : null;
}

export function getCurrentQueryId(): string | null {
  return moduleQueryId;
}

function buildCommonProps(): Record<string, unknown> {
  const ctx = readUserContext();
  return {
    query_id: getQueryId(),
    session_id: getSessionId(),
    user_context_hash: ctx.user_context_hash,
    locale: ctx.locale,
    plan_type: modulePlanType,
    work_language: ctx.work_language,
  };
}

export function track(
  eventName: string,
  properties?: Record<string, unknown>
): void {
  if (!isPosthogReady()) return;
  try {
    const payload = { ...buildCommonProps(), ...(properties ?? {}) };
    posthog.capture(eventName, payload);
  } catch (err) {
    devWarn(`track('${eventName}') failed`, err);
  }
}

export function identify(userId: string, traits?: IdentifyTraits): void {
  if (traits && traits.plan_type) {
    modulePlanType = traits.plan_type;
  }
  if (!isPosthogReady()) return;
  try {
    posthog.identify(userId, traits);
    if (traits) {
      const superProps: Record<string, unknown> = {};
      for (const key of SUPER_PROP_KEYS) {
        const val = traits[key];
        if (val !== null && val !== undefined) {
          superProps[key] = val;
        }
      }
      if (Object.keys(superProps).length > 0) {
        posthog.register(superProps);
      }
    }
  } catch (err) {
    devWarn(`identify('${userId}') failed`, err);
  }
}

export function reset(): void {
  modulePlanType = "free";
  moduleQueryId = null;
  if (!isPosthogReady()) return;
  try {
    posthog.reset();
  } catch (err) {
    devWarn("reset() failed", err);
  }
}
