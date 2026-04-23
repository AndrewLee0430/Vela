# Vela TODO

## Roadmap (see PRD.md for full specs; also cross-referenced in CLAUDE.md "Current Development Status")

- [ ] §2.7 Explain 臨床推理強化 (1-2 days; execute after 1 week of
      baseline metrics — explain_locked_viewed %, L1 thumbs ratio,
      citation_clicked by source_type)
- [ ] §3.1 user_context write endpoint (minimal 2-3 days / DB-backed
      4-5 days; decide based on L1 signup volume)
- [ ] §2.1 Model Provider abstraction (5-7 days; Month 1-2, or earlier
      if VelaError LLM_* spike or OpenAI daily cost anomaly — see 維運 § 4.4)

## Round 3 follow-up (high priority)
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

      **Status verification 2026-04-23:** Not yet reproduced — prod
      testing so far has hit the quota_hit modal (full-screen) path,
      not the third_query soft-CTA (inline banner) path. Bug remains
      open. Reproduce per original investigation plan: send exactly 3
      successful Research queries, observe the inline soft-CTA, click
      any button, check PostHog Network tab for duplicate event fire.

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

      **Decision needed (review after sufficient PostHog data —
      anonymous_upgrade_cta_shown volume):**
      - Option A (minimal): change "queries" → "credits" in 16 locales.
        But users don't know what credits are.
      - Option B (clearer, recommended): drop numbers entirely.
        "You've reached today's free trial. Sign up to continue..."
        Frees up future per-feature cost changes from needing copy updates.

      **Related:** Decision 001 v0.3 § A6 authoritative reconciliation.
      Decision 001 v0.2 language in the same file should be marked
      superseded (separate todo if decided).
