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
      **Priority:** Medium — data-driven bug, revisit on trigger
      condition, not on calendar schedule.

      Root cause unknown — 2 concurrent DOM instances observed
      via autocapture ("Maybe later" button clicked event fires
      twice for 1 user click). quota_hit and explain_locked
      do NOT exhibit this; only third_query.
      Investigation required with React DevTools Component tree
      while showThirdQueryCta === true. Not a functional bug
      (CTA displays and dismisses correctly, counter works,
      backend quota enforced independently). Telemetry impact
      only: third_query event count in PostHog is 2x actual.

      **Repro steps:** send 3 successful Verify queries (V+V+V) or
      V+V+R mix — 3 Research queries alone cannot trigger this CTA
      because 3×3=9 credits exceeds the 8-credit anonymous daily cap,
      and the 3rd query gets blocked by quota_hit modal instead. The
      CTA trigger sessionStorage key `vela_anon_query_count` only
      increments on successful query completion, not on 429.

      **Status verification 2026-04-24:** Investigated in dev
      environment. Bug NOT reproducible in dev — single DOM instance,
      single event fire per click. Bug is prod-only. Three candidate
      root causes remain:
      (a) PostHog autocapture enabled only in prod, firing alongside
          manual track()
      (b) Clerk auth latency in prod causing brief CTA remount,
          resetting firedRef
      (c) Production build reconciliation differences

      **Revisit trigger:** When PostHog shows ≥ 5 `anonymous_cta_shown`
      events with `trigger=third_query` in prod, return to this bug.
      Investigation steps:
      1. In PostHog, query for these 5+ events
      2. For each event, find its matching duplicate (same user, same
         session, within 5 seconds)
      3. Calculate timestamp delta between each pair
      4. If median delta < 100ms → hypothesis (a), autocapture + manual
         track double fire. Fix: update PostHog config to exclude the
         AnonymousUpgradeCTA selector from autocapture.
      5. If median delta > 500ms → hypothesis (b), remount issue. Fix:
         promote firedRef from useRef to module-level Set<string> keyed
         by trigger+query_id.
      6. If mixed or ambiguous → record findings, add 4th hypothesis,
         continue investigation.

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

- [ ] § 2.8 event name drift: `explain_locked_viewed` (PRD spec) vs `anonymous_cta_shown` with `trigger=explain_locked` (impl)
      **Priority:** Low — functional behavior matches PRD acceptance #11 (event fires when
      anonymous user attempts Explain), only the event name and payload shape differ.

      **Facts:**
      - PRD § 2.8 acceptance #11 spec'd standalone event `explain_locked_viewed`
      - `components/AnonymousUpgradeCTA.tsx` emits unified `anonymous_cta_shown`
        with `trigger: 'third_query' | 'quota_hit' | 'explain_locked'`
      - `components/ExplainLockedForAnonymous.tsx` is a thin wrapper passing `trigger="explain_locked"`
      - PostHog funnel still queryable via filter `trigger=explain_locked`

      **Decision needed (revisit when PRD § 2.8 retrospective runs, OR when adding new CTA trigger):**
      - Option A: rename event to match PRD spec — breaks existing PostHog dashboards / saved queries
      - Option B (recommended): keep unified event name, mark PRD § 2.8 acceptance #11 as
        "satisfied via `anonymous_cta_shown` with `trigger=explain_locked`" in next PRD revision
      - Option C: emit BOTH events (dual-write) — most expensive, only worth if dashboards depend on legacy name

      **Defer reason:** Not blocking soft launch. Funnel data still captureable.
      Revisit during Phase 0 Retrospective alongside PostHog event audit.

- [ ] /pricing page missing yearly plan CTA
      **Priority:** Medium — UX gap, not functional bug.

      **Facts:**
      - Yearly Dodo product exists: pdt_0NbELkno040P4wQSaQaam ($89.99/year)
      - Monthly Dodo product exists: pdt_0NbELHXiGodgawGwVaZ3t ($9.99/month)
      - UpgradeModal.tsx supports both (triggered on quota hit)
      - /pricing page only shows Monthly CTA, yearly mentioned as
        subtitle text only
      - Users cannot purchase yearly from /pricing directly

      **Scope for full fix (2-4 hours):**
      - Add Monthly/Yearly toggle on /pricing page
      - Add 4 i18n keys × 16 languages = 64 new strings
      - Remove redundant orYearly subtitle key (16 locales)
      - UpgradeModal reads ?plan=yearly from URL to pre-select
      - /pricing → direct Dodo checkout for signed-in users (not /sign-up)
      - Test: monthly→yearly upgrade, yearly→monthly downgrade, refund edge cases

      **Defer reason:** Out of current §2.7 scope. Revenue impact is small
      during soft launch (most users will hit quota_hit modal where
      UpgradeModal already surfaces yearly option). Full fix after §2.7
      completes.

## § 2.7 Step 4 follow-up (deferred from Step 4A scope)

- [ ] Per-item SourceBadge click tracking (parity with Research § 2.3 CitationPanel)
      **Priority:** Medium — Step 4A explicitly deferred to keep Step 4B/4C scope
      tight. Enables Phase 1A Week 4 review metrics on which sources users
      distrust most; deferring too long blinds the § 2.3 retrospective.

      **Facts:**
      - `components/CitationPanel.tsx` (Research) already emits
        `track('citation_clicked', { source_type, url, citation_position })`
      - `pages/explain.tsx` inline `SourceBadge` (L139-170) and `LoincBadge`
        (L64-137) emit no events
      - Source data shape sufficient: `{ source_type, label, url? }` already on
        `ExplainSource` — same fields Research uses
      - § 2.7 structured output adds a new dimension: citations belong to either
        `items[]` or `clinical_correlations[]`

      **Scope for full fix:**
      - Add `track('citation_clicked', { source_type, url, citation_position,
        category: 'explain', origin: 'item' | 'correlation' })` to SourceBadge /
        LoincBadge onClick handlers
      - `citation_position` = index within parent `citations[]` array
      - Test: verify PostHog funnel splits cleanly by `source_type`
        (LOINC vs RxNorm vs PubMed/FDA) and by `origin`

      **Defer reason:** Pure analytics polish; revisit after Step 4D ships and
      PostHog funnel data exposes which source types Explain users actually
      click. Pairs naturally with PRD § 2.3 retrospective.

- [ ] Copy-to-clipboard markdown serializer for structured Explain result
      **Priority:** Medium — Step 4A Q3 decision removed the Copy button from §2.7
      rendering. Real clinician workflow copies interpretation back to patient
      charts; absence of "no user request yet" reflects pre-launch state, not
      unimportance. If reinstated post-launch, the new serializer must walk the
      structured shape (`items[]` + `clinical_correlations[]` + `disclaimer`)
      rather than copying a flat markdown string.

      **Facts:**
      - Old `pages/explain.tsx` L626-629 Copy button used
        `navigator.clipboard.writeText(output)` — works only for flat
        markdown string from pre-§2.7 output state
      - Step 4 Q3 decision: drop Copy button entirely from §2.7 cards
      - `utils/exportPdf.ts` (Pro PDF export) is a natural co-consumer of any
        serializer added later

      **Scope for full fix:**
      - Add `utils/explainSerializer.ts`: takes `ExplainResponse`, outputs
        markdown with one section per item (term · value · risk_tier ·
        explanation · citations) and a Clinical Correlations section
      - Section headers language-aware (reuse `getUI(lang)` keys from Step 5)
      - Reinstate Copy button on Explain output card; emit
        `track('explain_copied', { items_count, correlations_count })`
      - Consider sharing serializer with `exportPdf.ts` for Pro export

      **Defer reason:** Structured cards ship Step 4D as the first end-to-end
      §2.7 surface; adding the serializer + Copy button + i18n'd headers
      expands Step 4 scope without product-required value before launch.
      Revisit when either: (a) FeedbackBar surfaces "I want to copy this"
      requests, or (b) Pro PDF export needs the same structured markdown —
      whichever arrives first.

- [ ] § 2.7 risk tier judgment may skew conservative (yellow-heavy)
      **Priority:** Medium — quality issue, not a functional bug.

      **Observation (2026-04-25 dev smoke test):**
      Test case "血紅素 10.2 g/dL (參考值 12-16)、白血球 12,500/μL (偏高)"
      produced all three risk_tier labels as 🟡 (yellow):
      - Hemoglobin 10.2 (moderate anemia by WHO classification)
      - WBC 12,500 (mild leukocytosis)
      - Anemia + leukocytosis correlation

      Per v2 prompt Section 4 rule 3: "Multi-item combination
      suggesting high combined risk → red on the correlation".
      Anemia + leukocytosis combined could indicate chronic
      inflammation, infection, or hematologic process — should
      arguably be 🔴.

      **Defer reason:** A single test case is not statistical
      evidence. Wait for Step 8 (20 acceptance cases) to determine
      if this is a systematic bias before modifying v2 prompt.
      Modifying prompt based on n=1 risks overfitting.

      **Trigger evaluation:** Evaluated as part of Step 8 acceptance
      protocol (see "§ 2.7 Step 8 acceptance protocol" section below).

      **Action when triggered:** If Step 8 risk tier distribution
      shows yellow > 70% systematic across 20 cases, refine v2 prompt
      Section 4 decision rules with more explicit thresholds (e.g.
      "WHO moderate anemia → yellow; severe → red; combined with
      infection markers → red").

- [ ] § 2.7 RiskBadge hover tooltip with tier definition
      **Priority:** Medium — UX gap, surfaced during dev smoke test.

      **Observation:**
      Risk badge labels ("Needs Attention", "Consult Immediately",
      "General Information") communicate tier but not WHY or WHAT
      to do. Users without medical context may not understand the
      threshold or action implication.

      **Scope for full fix:**
      - Add hover tooltip to RiskBadge.tsx (popover-style, similar
        to LoincBadge tooltip pattern)
      - Static tooltip content per tier (not LLM-generated):
        - 🟢: "一般資訊 — 此項目在參考範圍內或為衛教性內容。"
        - 🟡: "需要留意 — 此項目超出參考範圍但未達緊急閾值。建議與臨床
              表現合併判讀。"
        - 🔴: "建議立即諮詢 — 此項目跨越臨床警戒值或多項組合提示高風險。
              建議盡快諮詢主治醫師。"
      - i18n: 16 languages × 3 tier definitions = 48 new strings
      - Mobile: tap-triggered popover (same pattern as LoincBadge)

      **Defer reason:** Not in PRD § 2.7 explicit acceptance criteria.
      Step 4 scope is structured rendering, not interactive education
      polish. Better to ship § 2.7 first, gather user feedback, then
      add tooltip if confusion is real signal.

- [ ] § 2.7 SourceBadge upgrade: surface source_type (PubMed/FDA/etc)
      **Priority:** Medium — trust-building for medical TA.

      **Observation:**
      Citation chips currently show only the title (e.g. "Anemia in
      adults: a contemporary approach to diagnosis"). For medical
      professionals, the source authority (peer-reviewed PubMed vs
      FDA label vs general health info vs LOINC code lookup) is
      often more important than the title itself.

      **Scope for full fix:**
      - Modify inline SourceBadge in pages/explain.tsx to prepend
        source_type prefix (e.g. "PubMed · Anemia in adults...")
      - Or add small source_type badge alongside title (visual:
        small pill with source_type abbreviation)
      - Color-code by source authority tier (peer-reviewed = green,
        regulatory = blue, code lookup = gray)
      - Coordinate with existing TODO entry "Per-item SourceBadge
        click tracking" — both modify SourceBadge, do together

      **Defer reason:** Coordinated with existing § 2.7 Step 4
      follow-up. Combined work makes sense to batch.

- [ ] § 2.7 + § 2.9 LLM body language vs disclaimer language drift
      **Priority:** Low — UX edge case, not a functional bug.

      **Observation:**
      Both Verify § 2.9 and Explain § 2.7 (Step 5) use
      response_language for fixed-string injection (severity_label
      / disclaimer / downgrade notes), but the LLM-generated body
      content (description, recommendation, item.explanation,
      correlation.insight) uses entities.input_language
      auto-detected from the input text.

      Effect: user types English query but UI is set to Japanese
      → LLM body returns English, but disclaimer renders Japanese
      → mixed-language output.

      **Defer reason:** Edge case (most users type in their UI
      language). Mirrors existing Verify § 2.9 behavior —
      consistent across features. Phase 1A i18n mop-up is the
      natural place to harmonize all three features (Research,
      Verify, Explain) into a single response_language pattern
      that threads through both LLM prompts and fixed strings.

      **Scope for full fix:**
      - Decide single source of truth: response_language (UI
        language) wins over input_language detection
      - Thread response_language into LLM prompt for all 3 features
      - Or: keep auto-detect but add visible language picker in
        UI when detected ≠ UI lang
      - Update PRD § 2.7 + § 2.9 if behavior changes

      **Discovered:** 2026-04-26 during § 2.7 Step 5C-1
      implementation flag from Claude Code.

## § 2.7 Step 8 acceptance protocol

When Step 8 (20 case acceptance run) completes, before declaring
§ 2.7 fully done, execute these post-acceptance checks. This is
not optional polish — these are the integration points between
§ 2.7's automated quality and the broader TODO follow-up backlog.

1. **Risk tier distribution analysis**
   - Count green/yellow/red across 20 cases × N items per case
   - If yellow > 70% of all items → systematic conservative bias
     confirmed → execute "§ 2.7 risk tier judgment may skew
     conservative" entry in § 2.7 Step 4 follow-up above
   - If green > 80% → opposite bias (under-flagging) → equally
     a problem; refine v2 prompt to flag borderline values more
     readily

2. **Hedging compliance audit**
   - Sample 5 random items across the 20 cases
   - For each, verify explanation does NOT contain forbidden
     phrases per v2 prompt Section 2:
     「您有」「您的診斷是」「您需要」「這表示您得了」
     "You have", "Your diagnosis is", "You need",
     "This means you have"
   - Any violation → refine v2 prompt Section 2 hedging rules +
     re-run sampled cases until clean

3. **LOINC scope guard trigger rate (Step 3 effectiveness)**
   - grep dev/prod logs for "[Explain] Step 3 downgrade triggered"
   - Calculate trigger rate (downgrades / total successful runs):
     - < 5% → Step 3 functioning as designed safety net; v2 prompt
       self-check is working
     - 5-15% → v2 prompt Section 3 may need stronger self-check
       phrasing; consider iterating
     - > 15% → v2 prompt Citation strategy section needs major
       rewrite; LLM is systematically failing to discriminate
       code-lookup vs clinical-judgment scope

4. **TODO sweep**
   - grep TODO.md for entries containing "Step 8" or "acceptance"
   - For each: re-read the trigger condition, evaluate against
     this run's data
   - If trigger met → add to next session's task list with
     priority noted
   - If not met → leave as deferred, no action

5. **Update FEATURE_AUDIT.md § 2.7 entry**
   - Status: 🔧 → ✅ DONE
   - Body: append "Step 8 acceptance summary" sub-section with
     - Risk tier distribution: green X / yellow Y / red Z
     - Hedging compliance: clean / N violations corrected
     - Step 3 downgrade trigger rate: X%
     - Any v2 prompt revisions performed (cite commit SHA)
   - Bump "Generated:" date if updating same day, or include
     "Updated post-Step 8" annotation

This protocol exists because Step 8 is the natural integration
checkpoint where automated outputs (LLM judgments) meet design
intent (PRD § 2.7 quality bars). Skipping any item here means
shipping § 2.7 with unverified assumptions.
