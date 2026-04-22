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
