/**
 * Shared SSE (Server-Sent Events) utilities for fetchEventSource.
 * Extracts duplicated error handling from research.tsx and explain.tsx.
 */

export class FatalError extends Error {
    code?: string;
    constructor(message: string, code?: string) {
        super(message);
        this.code = code;
    }
}

interface SSEErrorHandlers {
    onPhiBlocked: (detail: string, suggestion: string) => void;
    onLimitReached: () => void;
    // Round 2B — L0 anonymous error handlers (all optional for back-compat).
    onSignupRequired?: (message?: string) => void;
    onAnonymousQuotaExceeded?: (
        message?: string,
        details?: { used?: number; limit?: number }
    ) => void;
    onBudgetExceeded?: (message?: string) => void;
    onInvalidFingerprint?: (message?: string) => void;
}

/**
 * Standard onopen handler for SSE connections.
 * Handles:
 *  - 400 phi_blocked, invalid_fingerprint
 *  - 403 signup_required, limit_reached
 *  - 429 anonymous_quota_exceeded, generic too_many_requests
 *  - 503 budget_exceeded
 * Uses dual-read `data.type ?? data.error` for back-compat with pre-Round 1B endpoints.
 */
export function makeOnOpen(handlers: SSEErrorHandlers) {
    return async (response: Response) => {
        if (response.ok) return;

        if (response.status === 400) {
            const data = await response.json().catch(() => ({}));
            // Unwrap FastAPI HTTPException's nested detail envelope.
            // phi_blocked uses a flat JSONResponse where detail is a string,
            // so guard on object-ness before unwrapping.
            const d = (typeof data.detail === 'object' && data.detail !== null) ? data.detail : data;
            const code = d.type ?? d.error;
            if (code === 'phi_blocked') {
                handlers.onPhiBlocked(d.detail, d.suggestion);
                throw new FatalError('');
            }
            if (code === 'invalid_fingerprint') {
                handlers.onInvalidFingerprint?.(d.message);
                throw new FatalError(d.message || 'Invalid session fingerprint.', 'invalid_fingerprint');
            }
        }
        if (response.status === 403) {
            const data = await response.json().catch(() => ({}));
            const d = (typeof data.detail === 'object' && data.detail !== null) ? data.detail : data;
            const code = d.type ?? d.error;
            if (code === 'signup_required') {
                handlers.onSignupRequired?.(d.message);
                throw new FatalError('');
            }
            if (code === 'limit_reached') {
                handlers.onLimitReached();
                throw new FatalError('');
            }
            throw new FatalError('Session expired. Please refresh and sign in again.', 'session_expired');
        }
        if (response.status === 429) {
            const data = await response.json().catch(() => ({}));
            const d = (typeof data.detail === 'object' && data.detail !== null) ? data.detail : data;
            const code = d.type ?? d.error;
            if (code === 'anonymous_quota_exceeded') {
                handlers.onAnonymousQuotaExceeded?.(d.message, { used: d.used, limit: d.limit });
                throw new FatalError('');
            }
            throw new FatalError('Too many requests. Please wait a moment and try again.', 'too_many_requests');
        }
        if (response.status === 503) {
            const data = await response.json().catch(() => ({}));
            const d = (typeof data.detail === 'object' && data.detail !== null) ? data.detail : data;
            const code = d.type ?? d.error;
            if (code === 'budget_exceeded') {
                handlers.onBudgetExceeded?.(d.message);
                throw new FatalError('');
            }
            throw new FatalError('Service temporarily unavailable. Please try again later.', 'server_error');
        }
        throw new FatalError(`Server error (${response.status}). Please try again.`, 'server_error');
    };
}

/**
 * Standard onerror handler for SSE connections.
 * Re-throws FatalError; wraps other errors with a user-friendly message.
 */
export function sseOnError(err: unknown) {
    if (err instanceof FatalError) throw err;
    if (err instanceof Error) throw new FatalError(err.message, (err as FatalError).code);
    throw new FatalError('Connection lost. Please try again.', 'connection_lost');
}
