## Round 3 follow-up (high priority, week 1 after soft launch)
- [ ] AnonymousUpgradeCTA third_query fires twice in PostHog.
      Root cause unknown — 2 concurrent DOM instances observed
      via autocapture ("Maybe later" button clicked event fires
      twice for 1 user click). quota_hit and explain_locked
      do NOT exhibit this; only third_query.
      Investigation required with React DevTools Component tree
      while showThirdQueryCta === true. Not a functional bug
      (CTA displays and dismisses correctly, counter works,
      backend quota enforced independently). Telemetry impact
      only: third_query event count in PostHog is 2x actual.

      **Status verification 2026-04-23:** Not yet reproduced in this
      session's prod smoke test — that test hit quota_hit modal (full-
      screen) path, not the third_query soft-CTA (inline banner) path.
      Bug is confirmed still open. Reproduce per original investigation
      plan: send exactly 3 successful Research queries, observe the inline
      soft-CTA, click any button, check PostHog Network tab for duplicate
      event fire.

- [ ] i18n-anonymous.ts copy drift: "free queries" vs actual unit "credits"
      **Priority:** Medium. Not a functional bug — core UX flow (modal
      display, CTA options, backend 429) all work. Only cognitive
      friction in the number shown to user.

      **Facts:**
      - ANONYMOUS_DAILY_LIMIT = 8 credits (not queries), correct per
        Decision 001 v0.3 § A6
      - CREDIT_COSTS: research=3, verify=1, explain=2 (L0 locked)
      - Modal copy "You've used {used} of {limit} free queries" uses
        credit values but calls them "queries" — confusing for users
        who do 1R+1V and see "4 of 8" instead of "2 of X"

      **Decision needed post-launch (review after 1 week of PostHog data):**
      - Option A (minimal): change "queries" → "credits" in 16 locales.
        But users don't know what credits are.
      - Option B (clearer, recommended): drop numbers entirely.
        "You've reached today's free trial. Sign up to continue..."
        Frees up future per-feature cost changes from needing copy updates.

      **Related:** Decision 001 v0.3 § A6 authoritative reconciliation.
      Decision 001 v0.2 language in the same file should be marked
      superseded (separate todo if decided).
