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

      **Prod confirmed (2026-04-28 during Phase 0 deploy verify):**

      Reproduction with input "eGFR 45 mL/min (ref >60), HbA1c
      7.8%, Metformin 1000mg BID" + UI=zh-TW:
      - Disclaimer rendered in zh-TW (繁中) ✓
        — i18n key lookup works
      - Item card body content rendered in English ✗
        — LLM follows input language, not response_language

      Backend log evidence (fly logs 2026-04-28T03:28:13):
        [Explain] entities.input_language = en

      Confirms hypothesis from 753b27d: backend detects input
      language at Stage 1 entity extraction, then Stage 3 LLM
      generates body in detected language regardless of
      response_language parameter intent.

      Earlier observation 2026-04-26 with input "血紅素 9.2 g/dL,
      白血球 14000,血壓 145/95,心跳 102" + UI=zh-TW:
      - LLM body rendered in 簡體中文 (Simplified Chinese),
        not 繁中 (Traditional Chinese as expected from UI lang)

      **Refined fix scope (replaces vague v0 scope):**
      - explain_system.md prompt v3 → v4: explicit instruction
        "Body content (descriptions, recommendations, clinical
        correlations) MUST be in {response_language}, regardless
        of detected input language. Input language detection is
        for entity normalization only, not output language."
      - Verify with: zh-TW input → en UI → expect en body,
        en input → zh-TW UI → expect zh-TW body, zh input →
        zh-TW UI → expect zh-TW body (not zh-CN)
      - Add to § 2.7 Step 8 acceptance protocol: 4-locale ×
        2-input-language matrix (en/zh-TW/ja/ko UI ×
        en-input/zh-input)

## Phase 1A polish — telemetry & SSE contract follow-ups

These items emerged during § 2.7 Step 6 + Phase 1A completion-event
rollout (commits e63c231, 6a53dfc, dd128e2). The completion-event
backfill itself shipped in those three commits; entries below are
follow-up tightenings discovered during implementation.

- [ ] Backend SSE payload type contract for streaming features
      **Priority:** Medium — defensive coding tax, not a functional
      bug.

      **Observation (2026-04-26 during § 2.7 Step 6 Phase 6B-2
      Research telemetry implementation):**

      Frontend SSE listeners trust backend event payloads as their
      expected types without explicit validation:
      - data.lang assumed string (case 'language' branch)
      - data.content assumed string for chunks (case 'answer' branch)
      - data.content assumed array for citations (case 'citations'
        branch)
      - data.query_time_ms assumed number (case 'done' branch)

      During 6B-2 implementation, defensive coercions were added at
      the SSE boundary in pages/research.tsx:
      - typeof data.lang === 'string' ? data.lang : null
      - typeof data.content === 'string' ? data.content : ''
      - Array.isArray(data.content) ? data.content : []
      - typeof data.query_time_ms === 'number' ? ... : null

      One coercion (the answer chunk string-guard) revealed a latent
      bug in the pre-existing setAnswer logic: 'foo' + undefined ===
      'fooundefined' would have rendered literally if backend ever
      sent a non-string content. New coercion treats non-string as
      empty.

      **Defer reason:** Current backend code paths emit correct
      types in practice; defensive coercions are belt-and-suspenders
      for unknown-future cases. No production incidents observed.
      Phase 1A polish should formalize the contract rather than
      sprinkling more coercions.

      **Scope for full fix:**
      - Define a TypeScript discriminated union for SSE event
        payloads in utils/sse.ts:
            type SSEEvent =
              | { type: 'query_id'; query_id: string }
              | { type: 'language'; lang: string }
              | { type: 'answer'; content: string }
              | { type: 'fallback' }
              | { type: 'citations'; content: Citation[] }
              | { type: 'identified'; language: string; items: ... }
              | { type: 'explain_result'; content: ExplainResponse }
              | { type: 'error'; code?: string; error?: string;
                  message?: string; content?: string }
              | { type: 'done'; query_time_ms?: number }
              | { type: 'status'; content: string }
      - Update SSE listener typings in pages/research.tsx +
        pages/explain.tsx to use this union; eliminate ad-hoc
        defensive coercions
      - Backend (api/services/explain_service.py + api/rag/*):
        export matching Pydantic models for SSE payloads, validate
        before yield (or runtime assert)
      - Decide error event shape uniformly: code-first vs error-
        first (Phase 1A polish entry below tracks this separately
        for HTTP error responses, but SSE error events are also
        inconsistent — Research uses .error first, Explain uses
        .code first)

      **Discovered:** 2026-04-26 during § 2.7 Step 6 Phase 6B-2
      Research telemetry implementation. Inline coercions in
      pages/research.tsx (commits 6a53dfc Citation guards) flagged
      this as a pattern needing formalization rather than expansion.

- [ ] Verify: surface spelling_corrections as structured response field
      **Priority:** Low — already user-visible via summary string
      prefix, but limits telemetry granularity.

      **Observation (2026-04-26 during § 2.7 Step 6 Phase 6B-3
      Verify telemetry implementation):**

      The Verify backend collects spelling_corrections: list[str]
      (api/server.py L734) when Levenshtein spell correction fires
      on user-typed drug names (e.g. "metfromin" → "Metformin").
      These corrections are surfaced to users by prefixing
      VerifyResponse.summary with a "Note: 'X' was interpreted as
      'Y'..." sentence.

      However, the corrections are NOT exposed as a structured
      field on VerifyResponse. To detect "did spelling correction
      fire on this query" from the frontend (for telemetry purposes),
      one would have to scrape the summary string for the "Note:"
      prefix and "was interpreted as" substring — a brittle heuristic
      that breaks if the prefix wording is i18n'd or rephrased.

      During 6B-3 implementation, the had_correction telemetry field
      was DROPPED rather than implemented via heuristic, per the
      decision tree:
        Q2 (had_correction): DROP. Backend spelling_corrections is
        not surfaced as structured field; summary-prefix heuristic
        is too brittle.

      **Defer reason:** Verify works correctly today; spelling
      corrections ARE displayed to users (via summary prefix). The
      gap is purely structural — telemetry visibility into how often
      Levenshtein fires. Not blocking soft launch.

      **Scope for full fix:**
      - Add corrections: list[str] field to VerifyResponse Pydantic
        model (api/models/schemas.py)
      - Backend: assign corrections list to response BEFORE building
        the summary prefix (so structured field is independent of
        summary text)
      - Frontend: read result.corrections, render as a separate UI
        chip / badge below the drug input rather than embedding in
        summary text
      - Frontend telemetry: re-enable had_correction in
        verify_completed payload as: had_correction:
        result.corrections.length > 0
      - Optional: also expose correction_count: result.corrections.length
        for richer signal
      - Backwards compatibility: keep summary-prefix injection during
        transition; remove after frontend ships the structured
        rendering

      **Discovered:** 2026-04-26 during § 2.7 Step 6 Phase 6B-3
      schema decisions. had_correction was the only proposed Verify
      telemetry field that couldn't be implemented cleanly without
      backend support.

- [ ] Verify prompt example value "嚴重" causes severity_label /
      risk_level_label leak in non-zh locales
      **Priority:** Medium — pre-existing bug since 2026-04-20
      (commit ee055d4 introduced verify_system.md v2.1); ~40%
      reproduction rate (2/5 manual tests on 2026-04-28).

      **Observation (2026-04-28 during Phase 0 deploy smoke test):**

      Verify with UI=en + drug pair input occasionally returns
      severity_label / risk_level_label as "嚴重" (Traditional
      Chinese) instead of "Severe" / "Critical". Drug pair example:
      atorvastatin + clarithromycin. Frontend fallback in
      pages/verify.tsx (getSeverityLabel/getRiskLevelLabel) is
      bypassed because backend DOES return a value (just the wrong
      language).

      **Root cause (verified by Claude Code grep):**
      api/prompts/verify_system.md L66 + L73 hardcode "嚴重" as
      severity_label / risk_level_label values inside the JSON
      schema example block. gpt-4.1-mini occasionally mimics
      example values verbatim, ignoring the "Respond in
      {response_language}" instruction at L25.

      **Why § 2.9 prod verification missed this 2026-04-20:**
      § 2.9 testing likely covered zh-TW / zh-CN paths (where
      "嚴重" output is correct). en / ja / ko paths either
      weren't tested or rolled lucky on LLM sampling that day.

      **Fix scope:**
      - Replace hardcoded "嚴重" in schema examples with
        placeholder like "<localized severity matching
        response_language>" or split into per-locale examples
      - Bump verify_system.md v2.1 → v2.2
      - Add to § 2.7 Step 8 acceptance protocol or
        Phase 0 retrospective: explicit en + ja + ko smoke
        tests for severity label localization

      **Defer reason:** Pre-existing in production since 2026-04-20.
      Not introduced by today's 22-commit deploy. Frontend label
      fallback (getSeverityLabel) handles missing-from-backend case
      but not wrong-language-from-backend case. Acceptable for soft
      launch since label is informational, not safety-critical.

- [ ] deploy.ps1 "All machines running" false negative when Fly
      machines are stopped
      **Priority:** Low — cosmetic, deploy itself functions correctly.

      **Observation (2026-04-28 deploy x2 same day):**

      When `fly status` output contains a stopped machine row,
      deploy.ps1 Step 3 prints "All machines running." (green) even
      though the table clearly shows `STATE: stopped` for one machine.
      Both deploys today (8a943c3 + earlier morning) had the same
      pattern: machine 2879720c66d478 stopped, machine 683d447c2e5428
      started, deploy.ps1 missed the stopped one.

      **Likely cause:**
      PowerShell encoding mismatch on the box-drawing characters (│)
      in fly CLI table output (CP950/CP1252 vs UTF-8). The regex at
      deploy.ps1 L20-22 doesn't match the encoded character, so the
      stopped row is silently skipped in the script's check loop.

      **Why benign:**
      Fly's `auto_start_machines = true` config means stopped
      machines wake on first traffic. Both machines run the same
      version (157 today), so wake-on-traffic still serves correct
      code. The script's "All machines running" claim is just a
      false negative — not a service availability issue.

      **Fix scope (one of):**
      - Update deploy.ps1 regex to handle Unicode box-drawing chars
      - OR switch to `fly status --json` for structured parsing
        (preferred — survives any future CLI output format changes)
      - Add explicit `fly machine start <id>` step for any machine
        in stopped state (defensive, not strictly necessary)

      **Defer reason:** Deploy works correctly despite the
      misleading message. Cosmetic only. Good Phase 0 retrospective
      candidate when reviewing deploy tooling.

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

## § 4.5 / § 4.6 Phase 0 末段 development queue

> **Note on file ordering:** TODO.md sections are appended in
> chronological order of when entries were logged, not execution
> order. § 4.5 / § 4.6 execute AFTER § 2.7 Step 8 acceptance
> protocol (above in this file) but BEFORE Phase 0 Retrospective.
> See PRD.md § 4.5 / § 4.6 + Phase 0 v1.3 NOTE for execution
> sequence.

Inserted into Phase 0 execution order per PRD v1.3 (commit 06a9605).
Execution sequence:

§ 2.7 Step 7 (LLM judge) → § 2.7 Step 8 (20-case acceptance) →
§ 4.5 Share Answer → § 4.6 SEO Explore Pages → Phase 0 Retrospective

### § 4.5 Share Answer 公開連結

- [ ] Implement § 4.5 per PRD v1.3 spec
      **Reference:** PRD.md § 4.5 (full functional spec — 9 functional
      requirements + SharedQuery schema + privacy gate + anti-abuse +
      6 PostHog events + i18n 16 languages + legal/ToS impacts +
      acceptance criteria)

      **Pre-implementation gates:**
      - § 2.7 Step 8 acceptance protocol passed
      - Backend Postgres migration capability confirmed (SharedQuery
        table creation)
      - Public Query Page renderer scope confirmed (shared with § 4.6)
      - Sensitive-pattern detection rules (i18n / locale-aware)
        prepared for 繁中 / 英 / 日 (other locales fallback to stronger
        warning)

      **Implementation phases (detailed at execution time):**
      Phase A: Public Query Page renderer (shared infra — SSR + OG +
              JSON-LD pipeline reused by § 4.6)
      Phase B: Share Modal + privacy gate + sensitive detection
      Phase C: Settings 「我的分享」tab (list + revoke only; analytics
              like view_count deferred per PRD § 4.5 需求 5)
      Phase D: Legal ToS / Privacy Policy revision (parallel — does
              not block engineering ship)
      Phase E: i18n 16 languages + integration test (LinkedIn Post
              Inspector / Twitter Card Validator / Google Rich
              Results Test per PRD § 4.5 驗收標準)

### § 4.6 SEO Explore Pages

- [ ] Implement § 4.6 per PRD v1.3 spec
      **Reference:** PRD.md § 4.6 (full functional spec — 8 functional
      requirements + ExplorePage schema + content workflow + 3
      PostHog events + sitemap/hreflang + acceptance criteria)

      **Pre-implementation gates:**
      - § 4.5 Phase A (Public Query Page renderer) shipped — § 4.6
        reuses it
      - Content team has provided initial topic list (5-10 published
        entries before launch — empty-shell pages get GSC penalty)
      - GSC + Bing Webmaster Tools access configured per 維運計畫
        v3 § 9.1

      **Implementation phases:**
      Phase A: ExplorePage schema + slug routing (`/explore/{slug}`
              + hreflang group support)
      Phase B: Sitemap auto-generation (sitemap-explore.xml) +
              hreflang logic (group siblings + missing-locale
              skip rule per PRD § 4.6 需求 6)
      Phase C: Content import CLI / Notion sync tool
      Phase D: Related queries + breadcrumb UI (PRD § 4.6 需求 4)
      Phase E: Integration test (Google Rich Results Test /
              robots.txt / hreflang validator)

      **Note:** PRD § 4.4 處方解析 MVP 的 share / explore 機制
      v1.3 不啟用 (per § 4.5 + § 4.6 對既有 PRD 章節的影響 § 4.4
      crossref). Share button 在處方解析 answer block 不顯示。
