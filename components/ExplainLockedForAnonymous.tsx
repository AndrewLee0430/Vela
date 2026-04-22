// components/ExplainLockedForAnonymous.tsx
// Round 3 — Decision 001 v0.4 § 2 acceptance #5.
// Thin wrapper around AnonymousUpgradeCTA for the Explain page's signed-out view.
// Explain is free but requires a Vela account (no PHI-risk anonymous access).

import AnonymousUpgradeCTA from './AnonymousUpgradeCTA';

export default function ExplainLockedForAnonymous() {
    return <AnonymousUpgradeCTA trigger="explain_locked" />;
}
