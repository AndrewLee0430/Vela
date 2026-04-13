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
}

/**
 * Standard onopen handler for SSE connections.
 * Handles: 400 phi_blocked, 403 limit_reached, 429 rate limit, generic errors.
 */
export function makeOnOpen(handlers: SSEErrorHandlers) {
    return async (response: Response) => {
        if (response.ok) return;

        if (response.status === 400) {
            const data = await response.json().catch(() => ({}));
            if (data.type === 'phi_blocked') {
                handlers.onPhiBlocked(data.detail, data.suggestion);
                throw new FatalError('');
            }
        }
        if (response.status === 403) {
            const data = await response.json().catch(() => ({}));
            if (data.error === 'limit_reached') {
                handlers.onLimitReached();
                throw new FatalError('');
            }
            throw new FatalError('Session expired. Please refresh and sign in again.', 'session_expired');
        }
        if (response.status === 429) {
            throw new FatalError('Too many requests. Please wait a moment and try again.', 'too_many_requests');
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
