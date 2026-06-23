# BACKLOG.md — Vela Open Future Work

Open tasks not actively in progress. New items captured here, moved to STATE.md when in focus, removed when shipped (git log records it).

For active focus see STATE.md. For tech debt see TECH_DEBT.md.

## Categories below
- Round 3 follow-ups (post §2.8 anon flow)
- §2.7 Step 4 follow-ups (post Step 8 re-eval, 4 items remaining; 2 archived as resolved/evaluated)
- Phase 1A polish — telemetry & SSE contract
- §4.5 / §4.6 Phase 0 末段 development queue

---

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

- [x] Verify prompt example value "嚴重" causes severity_label /
      risk_level_label leak in non-zh locales
      **RESOLVED 2026-06-04** (frontend-authority fix): `pages/verify.tsx` now
      derives severity/risk labels ONLY from the canonical enum via i18n-verify
      (`getSeverityLabel`/`getRiskLevelLabel`/`formatInteractionSummary`), no
      longer trusting the LLM's `severity_label`/`risk_level_label` free-text —
      deterministic, locale-correct, immune to LLM mis-localization. Backend
      hygiene also landed: verify_system.md v2.1→v2.2 + server.py fallback
      replaced the hardcoded "嚴重" schema example with `<localized … matching
      {response_language}>` placeholders. Schema fields kept Optional/None.
      **Priority:** ~~Medium~~ DONE — pre-existing bug since 2026-04-20
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

- [ ] **i18n enhancement (not a bug): expand Verify severity/risk dict to 16 locales**
      `utils/i18n-verify.ts` covers 7/16 locales (en, zh-TW, zh-CN, ja, ko, es,
      de); the other 9 fall back to the English dict. After the 2026-06-04
      frontend-authority bugfix, severity/risk labels derive ONLY from this dict,
      so those 9 locales now show ENGLISH severity terms (correct but not
      localized — safer than the prior unreliable LLM free-text, just untranslated).
      Add severity (Critical/Major/Moderate/Minor) + riskLevel (those + Low/Unknown)
      + the `formatSummary` function for: fr, it, pt, th, ar, hi, bn, he, vi.
      Romance (fr/it/pt) are higher-confidence; **th/ar/hi/bn/he/vi need native
      medical-terminology review** (severity grading vocabulary, not transliteration
      — same review gate as the Stage 5 i18n translations). Distinct from the
      RESOLVED bug above: that fixed wrong-LANGUAGE output; this closes the
      missing-LANGUAGE coverage gap. Discovered 2026-06-04 during the bugfix.

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

- [ ] Path 2 — Real PubMed retrieval for Explain (replaces Path 1 
      defensive degradation)
      **Priority:** High — Path 1 (commit bebf099) ships defensive 
      degradation that strips fabricated PubMed citations. Result: 
      Explain shows only LOINC/RxNorm/MedlinePlus citations + 
      "based on general medical knowledge" banner. This is honest 
      but thin — Vela's core "evidence-based" positioning needs 
      real clinical guideline citations to fully deliver.
      
      **Discovered:** 2026-04-29 during Path 1 RAG diagnose. The 
      decoupling: Explain prompt requires PubMed/FDA/NICE/Cochrane 
      citations for clinical-judgment content, but Explain's 
      retrieve_context() only fetches LOINC/RxNorm/MedlinePlus. 
      LLM faced with hard requirement and permissive schema → 
      fabricated PMIDs.
      
      **Reference architecture:** Research feature already has 
      working PubMed retrieval via api/rag/retriever.py 
      HybridRetriever (instantiated server.py:421 with 
      enable_pubmed=True). Pattern is portable to Explain.
      
      **Design decisions needed (warrant ADR):**
      - Query construction: per-entity? combined? LLM-rewritten 
        like Research's rewrite_query?
      - top_k: how many PubMed results to retrieve per entity?
      - Relevance filter: reuse Research's LLM relevance filter 
        or simpler title-match heuristic?
      - Cost / latency budget: each PubMed call ~200-400ms; with 
        4 entities × 3 queries that's 2-4s additional latency on 
        top of existing Stage 1+2+3 pipeline
      - Cache strategy: PubMed rate limits (3 req/sec without API 
        key, 10 with PUBMED_API_KEY)
      - Timeout / fallback: if PubMed unreachable, degrade to 
        Path 1 behavior (LOINC-only) gracefully
      
      **Fix scope (post-ADR):**
      - api/services/explain_service.py: add 
        _lookup_pubmed_clinical() to retrieve_context()
      - api/data_sources/pubmed.py: likely already importable 
        (used by Research)
      - api/prompts/explain_system.md: revert v5 → v6 with prompt 
        re-allowing PubMed citations (with whitelist guard against 
        retrieved PMIDs)
      - api/models/explain_schemas.py: re-enable PUBMED in 
        SourceType enum (currently commented out per Path 1)
      - api/services/explain_service.py Layer 3 validator: keep 
        URL whitelist check (now whitelist will include retrieved 
        PMIDs; before it would always reject all PubMed)
      - Tests: 5+ acceptance cases verifying retrieved PMIDs 
        appear in citations and fabricated PMIDs do not
      - Frontend: remove or update citationScopeBanner since 
        PubMed citations are now real
      
      **Defer reason:** Needs design review on 4-5 architectural 
      decisions above. Solo founder can implement after ADR 
      written. Phase 0 retrospective candidate, or Phase 1A first 
      polish slot.

- [ ] Generic error UX — observe top 3 failure modes in prod and 
      tighten messages
      **Priority:** Low-Medium — UX iteration based on real data, 
      not pre-emptive design.
      
      **Context:** Generic error UX shipped 2026-04-29 (commit 
      a8eb6e8) with 6 error codes (empty_input, no_values_in_input, 
      input_too_long, openai_api_error, schema_validation_failed, 
      generic). Messages designed without prod data on which 
      failure mode is most common.
      
      **Action plan:**
      1. After ~1 week of soft launch traffic, query PostHog 
         explain_failed events grouped by error_code
      2. Identify top 3 failure modes by frequency
      3. Tighten message specificity for top 3 (e.g. if 
         openai_api_error is 60% of failures, current "服務暫時忙線" 
         may need more guidance like "請稍後 5-10 分鐘再試")
      4. Sub-categorize generic catchall if it's >10% of failures 
         (currently any unexpected exception → "如問題持續，請聯繫
         客服")
      
      **Required before action:**
      - Verify PostHog explain_failed event payload includes 
        error_code field (added in a8eb6e8)
      - Sufficient prod traffic (~100+ explain_failed events) for 
        meaningful distribution
      - Optional: add error_id / sentry trace ID to user-facing 
        message for support escalation
      
      **Defer reason:** Don't design UX without data. Wait until 
      Phase 1A first or second week.

- [ ] Explain — E22/E24 must_contain keyword-coverage LLM variance
      **Priority:** Low — Phase 1A polish item; not affecting product quality.
      
      **Context:** Discovered during § 2.7 Step 8 acceptance protocol (2026-04-30). 
      E22 ("dense multi-system PDF-style report") and E24 ("urgent values K 6.8 + 
      Na 128") flip between PASS and WARN across acceptance runs. Both have 
      must_contain criteria with specific keyword expectations:
      - E22: "mentions Furosemide is a diuretic" — LLM sometimes describes
        Furosemide's effect without explicitly using "diuretic"
      - E24: "explains potassium is critically elevated or dangerously high" — 
        LLM sometimes says "above the typical reference range" hedged version
      
      Both are LLM stochasticity reflecting must_contain keyword strictness, 
      not product capability gaps. Hard floor (citation_source_types_valid + 
      no_fabricated_citations) and ExplainJudge per-dimension assessment 
      consistently pass.
      
      **Action plan:**
      Two options when revisited (Phase 1A polish):
      - (a) Loosen must_contain criteria: "mentions Furosemide" (no diuretic 
        keyword); "explains potassium is significantly or critically elevated"
      - (b) Strengthen prompt explain_system.md to emit specific keywords for 
        well-known clinical concepts (Furosemide=diuretic, K>6.5=critical)
      
      **Defer reason:** Not affecting users. Not blocking § 2.7 結案.

- [ ] Test infra — multilingual response_language assertion completeness
      **Priority:** Low — Phase 1A polish.
      
      **Context:** Commit fa80ff9 fixed runner not threading response_language 
      to /api/explain for multilingual category cases (M06/M07). Backend 
      defaults to en when missing, causing M07 to fail "responds in Thai" 
      assertion before fix.
      
      **Action plan:**
      Run an audit script that flags any case in golden_dataset.json where 
      endpoint=explain but response_language is missing. Should be zero 
      after fa80ff9 — but pin this as a regression net before adding new 
      cases in future.

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

- [~] Implement § 4.5 per PRD v1.3 spec — PHASE A-D shipped, E deferred to post-deploy
      **Reference:** PRD.md § 4.5 (full functional spec — 9 functional
      requirements + SharedQuery schema + privacy gate + anti-abuse +
      6 PostHog events + i18n 16 languages + legal/ToS impacts +
      acceptance criteria + Production Deploy Checklist)

      **Pre-implementation gates** (all met):
      - § 2.7 Step 8 acceptance protocol passed
      - Backend Postgres migration capability confirmed (SharedQuery
        table creation)
      - Public Query Page renderer scope confirmed (shared with § 4.6)
      - Sensitive-pattern detection rules (i18n / locale-aware)
        prepared for 繁中 / 英 / 日 (other locales fallback to stronger
        warning)

      **Implementation phases:**
      Phase A: Public Query Page renderer — SHIPPED 2026-05-05 (ef0d375)
      Phase B: Share Modal + privacy gate + sensitive detection +
              ShareButton mounts on 4 surfaces — SHIPPED 2026-05-06 (f04068d)
      Phase B-followup: 9 commits — Next.js dev rewrites for /q/* +
              /api/share/* + /static/og/*, UX polish 1/3 + 2/3 + 2.5 +
              3/3, Verify disclaimer i18n bug fix, PRD §2.10 source
              strategy housekeeping, BACKLOG WHO API entry —
              e042efc / a5da1c5 / 30bd0b5 / ca571ce / b378659 / 768dc0b /
              4fe0d7b / 92dbe9b
      Phase C: Settings 「我的分享」 tab + Navbar gear-dropdown
              integration — SHIPPED 2026-05-07 (6f7a154)
      Phase D: Legal ToS / Privacy share clauses (en) + dropdown
              menu label fix + legal i18n TECH_DEBT — SHIPPED
              2026-05-08 (ad506db)
      Phase E: Acceptance + LinkedIn Post Inspector / Twitter Card
              Validator / Google Rich Results Test + real anon 403
              verification + OG image production render check +
              PostHog 6-event verification — DEFERRED to post-deploy.
              Detailed checklist in PRD §4.5 "Production Deploy
              Checklist (PHASE E.2)". E.1 documentation closeout
              shipped 2026-05-08 (this commit).

### § 4.6 SEO Explore Pages

- [~] Implement § 4.6 per PRD v1.3 spec — PHASE A shipped, B-E pending
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
              + hreflang group support) — SHIPPED 2026-05-11 (bc171a1)
              followups: d324389 (dev rewrites) + ce2225a (seed script)
      Phase B: Sitemap auto-generation (sitemap-explore.xml) +
              hreflang logic (group siblings + missing-locale
              skip rule per PRD § 4.6 需求 6) — SHIPPED 2026-05-11 (8fb10ca)
      Phase C: Content import CLI (markdown → DB sync) — SHIPPED
              2026-05-11 (TBD SHA). Notion sync DEFERRED indefinitely
              per editorial decision (markdown + git workflow preferred).
              Admin UI DEFERRED indefinitely (CLI sufficient).
      Phase D: Breadcrumb + Category listing (/explore/category/{cat})
              + Related queries (3-tier hreflang/category) UI +
              3 PostHog events (explore_page_visited /
              explore_to_query_clicked / explore_related_clicked)
              wired via inline window.posthog (no-op until init
              exposed) — SHIPPED 2026-05-12 (SHA pending). Known gap:
              /explore index page (breadcrumb 'Explore' link target)
              not built — defer to PHASE E follow-up.
      Phase E: Integration test (Google Rich Results Test /
              robots.txt / hreflang validator) + 4-week GSC monitoring
              after deploy. Follow-ups: /explore index page; expose
              NEXT_PUBLIC_POSTHOG_KEY to Jinja2 template context so
              PHASE D event snippet actually fires capture (currently
              no-op).

      **Note:** PRD § 4.4 處方解析 MVP 的 share / explore 機制
      v1.3 不啟用 (per § 4.5 + § 4.6 對既有 PRD 章節的影響 § 4.4
      crossref). Share button 在處方解析 answer block 不顯示。

---

## Task-A direction-of-effect reversal — durable-fix candidates (2026-06-15)

Follow-ups to the **TECH_DEBT P0 "Direction-of-effect reversal on counterintuitive findings (CONTRADICTS)"** entry. Status 2026-06-15: both "reduce-bad-generation" paths are tried-and-insufficient for B2C — the prompt-fix (`96806b5`) measured PARTIAL (neutral-framed C01/C13 resolved, loaded-framing B01 still CONTRADICTS PMID 35268461) AND the o4-mini model-swap measured NEGATIVE (0/3 fidelity on B01-loaded; see (a) below). The active path is now the defensive circuit-breaker (b)+(c), elevated to a B2C-launch precondition. Gate the OPEN B2C decision; cross-ref the TECH_DEBT P0 entry's "Resolution DIRECTION".

- [x] **(a) Stronger-model vs framing-sensitivity validation — DONE 2026-06-15 (NEGATIVE)** — evaluate a stronger generation model via the existing §2.1 **Provider abstraction** (`GENERATOR_PROVIDER` / `GENERATOR_MODEL`; a binding swap, no code rewrite) against the framing-sensitivity failure. Cheapest durable-fix candidate to validate first. **Method:** a PRECISE small set (B01 loaded-premise + C01 neutral control + C15 conflicting + a few holdout), **3 runs**, before any full 24-case spend; reuse `scripts/citation_truth_check.py --adversarial` + the B01 Stage-2 recheck. **PREREQUISITE:** OpenAI auto-recharge ON / balance sufficient (TECH_DEBT P0 ops — credit-zero voids runs with `[ERROR]`). Success = B01 loaded-framing stops contradicting while C01/holdout stay faithful and `same` does not collapse into `not_directional`. This is STATE "Next Up TOP".
  - **2026-06-15 — BLOCKED — not a config-only eval.** Validated this session: swapping `GENERATOR_MODEL` to a stronger model is NOT an env-only swap for any current-generation model. o4-mini (and the GPT-5 family) reject the generator's hardcoded `max_tokens=2500` + `temperature=0.2` — they require `max_completion_tokens` and only accept the default temperature (o4-mini probe returned HTTP 400 'Unsupported parameter: max_tokens … use max_completion_tokens'; GPT-5 series documented with the identical contract). gpt-4.1's old parameter contract (max_tokens + arbitrary temperature) is shared by the provider layer, so only same-generation (non-stronger) models swap cleanly. PREREQUISITE for this item: make the provider layer parameter-contract-aware (conditional max_tokens→max_completion_tokens + temperature handling for GPT-5/o-series) — a product-code change to api/providers/ + generator.py, needs plan-back, and touches the shared Explain generation path (recon item 2 — §2.7 care). Only after that can GPT-5 + o4-mini be evaluated against B01 framing-sensitivity. No credit was wasted (the 400 occurred pre-generation).
  - **2026-06-15 — DONE — NEGATIVE.** The provider param-contract was built (`455bcb5`/`22ab342`) and o4-mini was evaluated against framing-sensitivity. Result: **model-swap insufficient.** On the loaded query B01 (`recheck_20260615_225242.json`, judge gpt-4.1, full prose persisted via `--recheck` `f072a7f`): **0/3 fidelity, 2/3 CONTRADICTS PMID 35268461** (asserted higher all-cause death "OR 1.82" while citing the OR-0.78-lower source — conflated multimorbidity ORs onto polypharmacy; the 1 non-contradict run was a multimorbidity-attribution evasion, judge PARTIAL — no run stated OR 0.78). On the NEUTRAL query C01 the SAME o4-mini stated the OR-0.78 lower-death finding faithfully (even flagging the paradox). **Framing-sensitivity is systemic / model-swap-resistant.** ① gpt-4.1 no-op smoke = no regression; ② finish_reason=stop; no `[ERROR]`. **Scope caveat:** ONE loaded query, 2/3 — same small-sample limit as the prior optimistic read; not generalized. **Optional last check (LOW EV):** a GPT-5.4 model-swap comparison (failure looks systemic, not compute-limited). With both (a) prompt-fix and model-swap insufficient, the active path is (b)+(c) below.
- [ ] **(b) Post-hoc direction checker (coarse ③ / C1) — BUILT + SHADOW-VALIDATED → FAILED real-data validation 2026-06-17; needs FUNDAMENTAL REWORK or REROUTE (see (b-C1-shadow) below)** — compares each answer claim against the cited source's direction of effect and flags reversals. **Constraint (per TECH_DEBT "Contradiction / NLI gate" entry):** post-hoc / **flag-only** — streaming streams answer tokens before citations resolve, so there is **no clean pre-return chokepoint** to hard-block; abstract-only judging can't reliably separate `contradicts` from terse-abstract (false-positive killer) → needs **full-text**, not abstract-only. One half of the advisor's Phase-2 contradiction circuit-breaker (with (c)). Build size M–L. **Elevated from "later" to a B2C precondition** now that both reduce-bad-generation paths ((a) prompt-fix PARTIAL + model-swap NEGATIVE) are exhausted.
  - **2026-06-16 scope limit (two-failure-mode split, see (d)):** this checker defends **ONLY generation-reversal** — it compares an answer claim against a source the answer **cites**. It is **BLIND to retrieval-recall failure**: when the protective source is never retrieved (obesity OB-L2 = 0/10 in pool; OB-L0 reranked out 7/10, see `retrieval_recall_20260616_133331.json` / `4248dfd`), there is no cited source to compare against and the answer reads as confidently wrong. (b) covers the polypharmacy-type case (source-in-hand 10/10) but not the obesity-type case → pair it with (d).
  - **2026-06-16 prototype (3 rounds, cheap gpt-4.1-mini + factor-focused prompt; `recheck_20260615_225242.json` + adversarial JSONs): the direction-comparison CORE is validated; the per-claim WRAPPER is the risk.** Synthetic single-sentence claims: detection 8/8, 0 FP, **conflation-trap 4/4 cross-topic** (correctly compares the claim's factor to *that factor's* abstract direction even when both directions are co-reported), terse abstracts 6/6. **Real messy multi-claim answers (decompose→anchor→aggregate): detection 3/4 (one FALSE NEGATIVE), FP 1/2 — all failures in the wrapper, not the direction logic:**
    - **(b-fail-1) DECOMPOSITION-ANCHORING FALSE NEGATIVE — the gating risk.** A naive LLM decomposer propagates citation markers **inconsistently**: B01-run2's real reversal slipped through (claim extracted with **empty `cited_pmids`** → nothing compared → not flagged), while the *identical* claim in B01-run3 was caught (PMID propagated). Same reversal, opposite outcome → **false safety**. Reliable claim-decomposition + citation-anchoring is itself a hard problem (MedRAGChecker-style pipelines inherit it).
    - **(b-fail-2) AGGREGATION OVER-FLAG FALSE POSITIVE.** "ANY claim contradicts ANY cited source → flag" is too aggressive: a faithful answer (C01-115632, correctly stated OR 0.78 lower) was flagged on a *different* sub-claim ("polypharmacy increases composite thrombotic events") that contradicts one cited source (32509316, null on stroke/SE) while agreeing with another (36495662). The aggregation rule needs to be **less aggressive than any-contradicts** (e.g. weight by claim centrality / require the contradicted source to be the answer's primary anchor for that factor).
    - **(b-fail-3) OVER-SPLITTING** — real answers → 13–21 atomic claims (spurious comorbidity splits), inflating FN/FP surface.
    - **→ "Path b-coarse" (whole-answer vs anchor) — EVALUATED 2026-06-16, fixes the FN.** Instead of per-claim decompose→anchor→aggregate, compare the answer's overall directional stance on the key factor against the protective anchor's effect statistic directly, **bypassing per-claim citation propagation** (the FN source). Result on the same 7 real answers: **detection 4/4 — caught B01-run2 (the reversal per-claim MISSED)**; 1 FP, on a genuinely-mixed answer (C01-115632 leads "higher HR 1.36-1.84", footnotes OR 0.78) so the flag is defensible. **Trade-off (what coarse can't see):** only the main-factor-vs-ONE-anchor reversal — **blind to secondary-factor/outcome reversals** (e.g. C01-110750's "no-effect on stroke" vs 36495662) and to reversals against non-anchor sources; and it needs an **anchor-selection** step.
    - **(b-coarse-component) ANCHOR-SELECTION — the last gating risk (validated 2026-06-16):** **naive selection ("the source the answer's main claim is based on") is CIRCULAR + WHITEWASHING — 0/3 on the confusion cases** (answers citing BOTH protective 35268461-lower + a higher source like 32509316): it picks the **higher** source agreeing with the answer's reversed claim → whitewashes the reversal into a **FALSE NEGATIVE** (all wrong picks opposite-direction; would gut the 4/4). The circularity **defaults to whitewash** (auto-finds the source that makes a reversed answer look fine) — to pick the protective anchor it must already know the true direction. **ESCAPE that works (non-circular): select by COUNTERINTUITIVENESS-vs-clinical-prior** (which cited source reports the most surprising finding vs common medical assumption, judged by the source's OWN finding + the model's prior, INDEPENDENT of the answer) → recovered **3/3**; the prior is used only for selection, the direction judgment still comes from answer-vs-source. **FOOTGUN: requires FULL abstracts** — 700-char truncation gave 0/3 (the OR-0.78 sentence is buried in a stat-dense abstract that leads with the higher finding); full abstracts → 3/3.
    - **VERDICT (③ feasibility): coarse ③ is VIABLE, but ONLY under (counterintuitiveness-based anchor-selection + full-abstract direction-check + flag-only) — never naive selection.** **Open deps:** (a) cross-topic prior reliability — **DONE/VALIDATED**; (b) **answers citing multiple competing counterintuitive sources** — still untested. NEXT: pressure-test (b), then production-integrate.
      - **(a) DONE — VALIDATED 2026-06-17 (`anchor_prior_crosstab_20260617.json`, 6 topics across crisp-control / crisp-paradox / fuzzy / fp-control bins, gpt-4.1-mini).** Cross-tab P(prior correct) × conf × S(selected correct anchor): **S = 5/5 on all confusion topics** (A polypharmacy, B1 obesity-paradox, B2 ACCORD inverted-direction, C1 HRT-fuzzy, C2 alcohol-fuzzy), **0 mis-picks** (no whitewash, no unrelated); D (β-blocker faithful) → selector correctly found "no opposing source." Bare prior correct 5/6 (the miss = C1 HRT, said "decreases" conf 0.8 vs a "contested" GT — **debatable GT-labeling artifact**: factor framed "started near menopause" makes "reduces CV" defensible). **Key: selection was MORE robust than the bare prior** — it reads the source's explicit effect statistic, so the one prior-miss still selected the right anchor (S-fails-only-where-P-wrong did NOT occur; S-fails-even-where-P-correct = none).
      - **Confidence gate — NOT recommended.** Zero selection failures to gate, AND confidence wouldn't discriminate: the shaky HRT prior was high-confidence (0.8) while the most-contested topic (alcohol) correctly drew the lowest (0.7). So a confidence gate would have *missed* the one debatable-prior case. The residual risk = a prior-miss that *propagates* to a selection error (not observed in this test) — confidence can't catch it; breadth (dep (b) + more topics) is the mitigation, not a gate.
      - **Verdict on (a): counterintuitiveness-selection is cross-topic-reliable as-is in this directional test** (5/5, incl. 2 crisp paradoxes + 2 fuzzy topics). Caveats: 6 topics, synthetic answers (only polypharmacy real), one model, single-source-per-direction.
      - **(b) DONE — competing counterintuitive sources, MEDIUM threshold — PASS 2026-06-17 (`dep_b_competing_sources_20260617.json`).** The source-multiplicity stressor dep (a) didn't cover: an answer citing TWO opposite-direction sources. 4 two-source bundles (1 real polypharmacy reversal + 3 cross-topic synthetic, full abstracts): **(a) correct-pick 4/4 · (b) whitewash 0 · (c) fail-safe 0 → MEDIUM PASS** (bar = pick right OR fail safe; met by picking right every time). Handled the hardest: **glucose** (counterintuitive anchor = the *higher*-mortality ACCORD, INVERTED) + **HRT** (true fuzzy-prior competing) — the rule reads each source's explicit effect size + prior, so the competing opposite-direction source did NOT confuse it. **Residual:** the **fail-safe (abstain/low-conf) leg was never exercised** → unproven; confidence uniformly 0.9 even on contested HRT (reinforces the existing [P2 calibration] debt → the fail-safe backstop is unreliable IF a future competing case stumps the selector). Caveats: synthetic answers except polypharmacy, 4 bundles, one model. **→ With dep (b) passing, selection ACCURACY is validated (dep a 5/5 + dep b 4/4). BUT the MEDIUM-threshold fail-safe leg (selector abstains/low-confidence when it cannot cleanly pick) was NEVER exercised — selection was accurate every time — and dep (a)+(b) both show the selector is OVERCONFIDENT on contested topics (uniform 0.9, wrong-but-0.8 on HRT). So the fail-safe safety net is UNVALIDATED and likely UNRELIABLE. DESIGN CONSTRAINT for production ③ (carry into the build spec): the flag/withhold trigger must NOT depend on the selector's self-reported confidence (it won't abstain — it will mis-pick confidently = the dangerous whitewash mode). Instead, trigger flag STRUCTURALLY — detect the *situation* 'answer cites ≥2 opposite-direction counterintuitive sources on the same factor→outcome' and flag unconditionally, regardless of selector confidence. Safety rests on situation-detection, not on the selector grading itself. What remains is PRODUCTION BUILD (the (b2) front-end neutralization mechanism + coarse ③ integration, both unbuilt product code requiring plan-back + golden re-baseline).**
      - **(b-C1-shadow) C1 SHADOW BUILD → FAILED real-data validation 2026-06-17 (`direction_shadow_20260617_143022.json` + `_rescore_nostruct`; plan-back `C1_inrepo_planback.md`; `api/services/direction_checker.py` + `server.py` hook `DIRECTION_CHECK_SHADOW` default OFF + `scripts/direction_shadow_eval.py`; committed locally, NOT pushed, Fly deploy DEFERRED).** First prod-code touch. Gate 1 (real provider probe) HEALTHY; Gate 2 push no-op (`96806b5`/`fdd624c` already on origin). Corpus frozen pre-gen (`tests/direction_shadow_corpus.json`): full 127 golden + 24 adversarial; live subset 43 = 25 targeted + 18 clean (clean criterion frozen first). **REAL: structural-trigger ON → detection 11/11 BUT FP 12/16 (75%), flags 37/43 (86%); structural OFF (primary path only) → detection 0/11, FP 1/16.** The structural detector (the dep-(b) "≥2 opposite counterintuitive sources" trigger above) **rubber-stamps on real 4–5-source retrievals** (no precision); the primary whole-answer-vs-anchor path detects nothing because **C1's own anchor-scorer fell into the B01 conflation trap** (read multimorbidity OR 2.04 not polypharmacy OR 0.78 from the multi-stat abstract) and the deterministic `_opposite` can't handle "mixed" anchors. **The dep(a)/dep(b)/coarse feasibility 5/5·4/4·4/4 (hand-curated synthetic bundles + curated answers) did NOT generalize.** C1 is unusable in BOTH configs → **fundamental rework, not tuning** (precise-or-removed structural detector; a scorer that doesn't conflate multi-stat abstracts — likely a stronger model, undercutting the "cheap backstop" premise; LLM direction-comparator robust to "mixed") OR pivot to (b2) front-end neutralization / the B2B-interim route. Founder decision pending (STATE TOP NEXT + TECH_DEBT P0 C1 entry). `DIRECTION_CHECK_SHADOW` stays OFF.
    - **Caveats:** one topic (polypharmacy), 7 real answers; the FP + VAGUE flag are debatable sub-claim tensions (1/2 FP is a ceiling — the protective-reversal was never falsely flagged); tooling needed a mid-run fix (first attempt VOID, decomposition truncated at max_tokens=600).
- [ ] **(b2) Front-end question-neutralization PRE-FILTER — NEW (division-of-labor finding, 2026-06-17)** — a generation-stage neutralization probe (`neutralization_generation_20260617_105516.json`, polypharmacy/35268461, RETRIEVE-ONCE-FREEZE-CONTEXT — **NOT** the failed (i) retrieval-query neutralization; retrieval query untouched, recall preserved) showed that **neutralizing ONLY the question fed to the generator** (with the protective anchor already retrieved) **eliminates the reversal: loaded→neutral 3/10 → 0/10** (neutral arm 10/10 faithful, robust across 2 neutral phrasings on polypharmacy (single topic; cross-topic neutralization untested)). The in-run loaded control reproduced reversal (3/10 — fix `96806b5` did NOT fully solve it; control valid). **KEY NUANCE: the loaded reversal is WORDING-SPECIFIC** — L1 (B01's vague "serious problem") reverses 3/5 but L2 ("worsen survival") is faithful 5/5 (the explicit premise self-corrected) → "loaded→reversal" is not uniform.
  - **Division of labor (sets the §706a (b) design):** **bin 1 — framing is the MAIN cause** of the reversals that occur → a **front-end question-neutralization pre-filter is a cheap, effective first line; ③ (coarse direction-checker) is a THIN BACKSTOP** for residual reversal. Implementation note: neutralize the question fed *internally* to the generator (the user still sees their question answered), then ③ backstops.
  - **Implication for dep (b): pass-threshold = MEDIUM (corrected 2026-06-17).** The earlier "RELAXES" transfer was WRONG: the neutralization relaxation applies to the **framing-induced-reversal path** only; dep (b) measures the **source-multiplicity path** (an answer citing TWO opposite-direction counterintuitive sources, where anchor-selection must pick the right one) — which occurs **even under a fully neutral question** and which front-end neutralization does NOT touch. So the relaxation does NOT transfer. **MEDIUM = selection must pick right OR fail SAFE (abstain/low-confidence/flag), never confidently whitewash the opposite-direction source.** dep (b) still RUNS — this sets its threshold/weight, not whether to run.
  - **(b2) applicability — THREE hard limits (do not over-read):** (i) **single topic** (polypharmacy only); (ii) **conditional on the protective anchor being RETRIEVED** → structurally inapplicable to retrieval-miss topics (e.g. obesity, source never-seen — that's (d)'s domain); (iii) **effective only against the VAGUE-loaded premise wording** — the explicit-loaded L2 ("worsen survival") self-corrected, so this is **"vague-loaded + source-in-hand," NOT generation-reversal in general.**
  - **(b2) PRODUCTION-MECHANISM gap (unbuilt dependency, not a solved pre-filter):** using front-end neutralization in production requires **auto-detecting "this user question is vague-loaded" and rewriting the INTERNAL generator question without losing the user's intent** — itself unbuilt and untested (parallel to ③'s feasibility→production gap). Treat the pre-filter as a **dependency to build/validate**, not a done mitigation.
  - **(b2-BUILT) Lever 2 A/B SHADOW BUILT + VALIDATED 2026-06-18 → SAFE + EFFECTIVE-where-reversal-occurs, but NARROW (`question_neutralization_20260618_110411.json` + de-risk `_104531.json`; plan-back `question_neutralization_planback.md`; `api/services/question_neutralization.py` + `server.py` flag `QUESTION_NEUTRALIZATION_SHADOW` default OFF + `scripts/question_neutralization_eval.py` + corpus `tests/question_neutralization_corpus.json`; committed locally, NOT pushed).** Built the production mechanism the gap above named: `is_loaded` detector + intent/qualifier-preserving `neutralize` rewriter (detect-then-neutralize, the confirmed design — detector 0/16 over-trigger on clean). A/B harness (retrieve-once-freeze, both arms, reused `judge_direction`/probe fidelity judge). **REAL per-topic (loaded→neutral REVERSED /10): polypharmacy 4/10→0/10 (ELIMINATED); beta_blockers_hfref 0/10→0/10; beta_carotene 0/10→0/10; cast 0/10→0/10; peanut retrieval-miss.** **Reversal-reduction demonstrated on POLYPHARMACY ONLY** — the other source-in-hand topics do NOT reverse under loaded framing (verified REAL faithful answers). So limit (i) above (single-topic) is now a measured finding, not just untested: **source-in-hand loaded-framing reversal is largely confined to the conflation-trap structure** (co-located opposing stats), not a general phenomenon — Lever 2's addressable surface is narrow. **Over-neutralization (the gating risk) PASSES: detector over-trigger 0/16, intent/qualifier-retention failures 0/16 (qualifiers always preserved), 0 REAL clean-regressions (both "regressions" were generation-stochasticity artifacts — one had an IDENTICAL neutralized question).** Cost $1.56. **NEXT before enabling:** (1) the narrow benefit (≈polypharmacy-type) may not justify production complexity — founder/A2 decision; (2) if pursued, broaden to more conflation-trap topics; (3) detector tuning for weak benefit-presupposing framings (missed BCAR-LA). Flag stays OFF. Two-lever coverage now = Lever 1 (retrieval-miss, obesity-type, PASS) + Lever 2 (source-in-hand loaded reversal, polypharmacy-type, narrow).
  - **Caveats:** single topic (polypharmacy), N=5/variant, one generator model, 1 frozen-context realization, synthetic neutralization phrasings; the effect is **conditional on the anchor being retrieved** (proven polypharmacy, unknown elsewhere — the retrieval-miss case is still (d)'s domain). Directional division-of-labor signal, NOT a production metric.
- [ ] **(c) Structural-citation fallback — ACTIVE (other half of the circuit-breaker)** — for high-stakes direction claims, prefer a structured "the source reports <effect measure> (<direction>)" rendering anchored to the retrieved effect statistic (OR/HR/RR) rather than free-text prose, so the answer cannot assert a direction the cited statistic contradicts. Pairs with (b) (detect) as the advisor's Phase-2 contradiction circuit-breaker (prevent). The o4-mini audit showed the failure mode is "conflate a different cohort's OR onto the claim" — a structural binding of claim↔cited-statistic targets exactly that. Also partially covers the **retrieval-miss** path (no protective coverage retrieved → low-confidence / withhold). Cross-ref (b), (d) + the TECH_DEBT P0 "Resolution DIRECTION".
- [ ] **(d) Retrieval-stabilization — DEFERRED (Path B); prompt-rewrite sub-approach TRIED-AND-FAILED 2026-06-16** — established by the N=10 retrieval-recall diagnostic (`retrieval_recall_20260616_133331.json`, script `4248dfd`): for some topics the protective anchor is **never retrieved**, so no generation-side or NLI fix can help. Two distinct sub-fixes: **(i) query-rewrite loaded-premise bias** — obesity OB-L2 (loaded "why is obesity a serious problem") rewrote to "obesity heart failure pathophysiology/impact" → PubMed returned harm-mechanism/HFpEF papers, the BMI-survival paradox doc (37290898) **0/10 in pool**; the rewrite must not inherit the premise's harm-direction. **(ii) rerank recency/score bias** — obesity OB-L0 (neutral): the anchor entered the pool 7/10 but as a **low-scored older candidate (~0.73, rank 14)** and the reranker kept 5 newer higher-scored papers → **0/10 final**; rerank/scoring shouldn't bury an older-but-on-point paper under newer ones. Contrast: polypharmacy 35268461 is **reliably retrieved (10/10 pool+final at L1/L2, rank 2)** — NOT a retrieval problem (that's the (b)/(c) generation-reversal case). **Caveat:** single query-wording per topic, N=10, 2 topics — directional signal, not generalized; the title-wording driver (neutral "Body mass index and survival" drifts off a loaded rewrite) is a **hypothesis**. Cross-ref TECH_DEBT P0 "two-failure-mode split (2026-06-16)".
  - **2026-06-16 — (i) query-rewrite prompt-fix FAILED + reverted (NOT VIABLE).** Tried a valence-neutral query-rewrite instruction in `_rewrite_query` (`retrieval_recall_20260616_141620.json` vs `_133331.json`; retriever.py reverted to HEAD, no commit). **Did NOT fix the target** (OB-L2 0/10→0/10 — root cause is a **terminology mismatch**, lay "obesity" vs the anchor's title "*Body mass index and survival*", not valence) **AND regressed** P-L1 (10/10→0/10, deterministic/prompt-caused) + OB-L0 (pool 7/10→0/10), while P-L0 *improved* 5→10 under the SAME edit. **Lesson: a prompt-level "be neutral" instruction is too BLUNT** — anchor recall is hyper-sensitive to the exact term string; one global instruction perturbs every query unpredictably (no single rewrite instruction optimizes recall across topics). **→ the prompt-rewrite sub-approach (the old (i)) is closed.**
  - **Remaining = "Path B, DEFERRED" (real engineering, only if retrieval-stabilization is revisited):** **(B1) lay→MeSH/measurement term-expansion** (e.g. obesity↔BMI synonym table so the anchor's terminology is matched) · **(B2) two-sided retrieval for counterintuitive topics** (deliberately fetch both directions + merge). Both need a synonym table / merge logic, not a prompt tweak.
  - **(d-probe) Path B FEASIBILITY PROBE — GO via B1 (term-expansion); B2 (two-sided) NOT supported (2026-06-18, `scripts/pathb_recall_probe.py`, `pathb_recall_probe_20260618_131306.json`; standalone diagnostic, NO build/flags/server changes; committed locally, NOT pushed).** Real new retrieval actions (not captured pools) on the obesity retrieval-miss cases (anchor 37290898). Gate 1 HEALTHY. **REAL — anchor in POOL/FINAL (/2 reps): baseline OB-L0 2/2 P **0/2 F**, OB-L1 0/2, OB-L2 0/2 (reproduces the miss); (M1) TERM-EXPANSION [obesity→{BMI, body mass index, overweight, adiposity} measurement synonyms] recovers it into FINAL **6/6** (OB-L0/1/2 all 2/2 pool AND final); (M2) TWO-SIDED [baseline + counter-framed paradox/benefit queries, merged] does NOT (0/2 final all cases; counter-framing doesn't match the anchor's neutral title + the rerank against the original query re-buries it).** **VERDICT: GO** — the obesity miss is a TERMINOLOGY mismatch recoverable by structured lay→measurement-synonym expansion (M1 fixes BOTH the search-miss OB-L1/L2 AND the rerank-burial OB-L0, because the cleaner BMI-survival pool reranks the anchor in). So Path B's durable form = **B1 term-expansion (a lay→measurement/MeSH synonym table)**, NOT B2 two-sided retrieval. Build shape (later, only if pursued): detect retrieval-miss (Lever 1 already does) → fetch via term-expanded query → merge. **Caveat: obesity-ONLY (the one captured retrieval-miss topic); M1 works because the anchor's TITLE carries the measurement synonym (obesity↔BMI) — a miss topic whose anchor uses entirely different terminology may not be synonym-recoverable; recovery on other miss topics is untested.** Cost: not token-instrumented in the probe; estimated <$0.05 (mini-model rewrite/filter/rerank + free PubMed E-utilities + local embeddings). Lever 1 still covers the residual (detect→refuse) for whatever term-expansion cannot recover.
  - **(d-probe STAGE 2) Path B SCOPE-MAP — B1 coverage by miss-type; QUALIFIED-GO, NOT a simple synonym table (2026-06-18, `scripts/pathb_scope_probe.py`, `pathb_scope_probe_20260618_141524.json`; standalone, NO build/flags; committed locally, NOT pushed; cost INSTRUMENTED this time = $0.0194).** 4 confirmed-miss topics spanning miss-types (anchors verified to the correct papers; each gated by a real baseline miss = F 0/2): T-A clean-synonym obesity (37290898), sodium/salt (25119607); T-B non-synonym intensive-glucose/ACCORD (18539917), CAST (1900101). **REAL — B1 term-expansion, anchor in POOL/FINAL (/2):** obesity P2/2 **F2/2 ✓**, sodium **P2/2 F0/2** (recalled but RERANKED OUT), glucose_accord P2/2 **F2/2 ✓**, cast P2/2 **F2/2 ✓**. **By miss-type FINAL-recovery: clean-synonym 1/2, non-synonym 2/2 — so miss-type does NOT predict recovery.** **The real findings (overturn the simple synonym-table hypothesis): (1) term-expansion recalls the anchor into the POOL in 4/4 cases across BOTH miss-types — broader ceiling than "clean-synonym only"; (2) BUT recovery requires the expansion to carry the anchor's ACTUAL terminology, and the KIND varies by topic — measurement synonym (obesity BMI), named-entity/drug (CAST "encainide flecainide"), title-phrase+outcome (ACCORD "intensive glucose lowering…mortality") — so a single obesity-style lay→measurement synonym table does NOT generalize; durable B1 needs broader expansion (named entities + outcome terms + MeSH); (3) final-recovery is RERANK-GATED (sodium recalled into pool but reranked out 0/2) — pool-recall ≠ final-recovery; (4) over-expansion FP-analog: my probe REPLACED the query with the expansion → beta-blockers (29040525) clean control DROPPED from F2/2 → pool 0/2 (the reworded query retrieves differently and LOSES a baseline find), polypharmacy control invalid (anchor not in final at baseline this run). The replace→loss signals production B1 must ADD/MERGE the expanded fetch with the baseline pool, NOT replace; a proper additive over-expansion test is the follow-up.** **VERDICT: QUALIFIED GO — Path B can recover missed anchors beyond the clean-synonym subset, but the durable mechanism is NOT a simple synonym table: it needs (a) topic-aware expansion (synonyms + named entities + outcomes), (b) ADDITIVE merge (never replace the query), and (c) a rerank fix for recalled-but-buried anchors (sodium). Lever 1 (detect→refuse) covers the residual (rerank-buried / non-recoverable).** Caveats: 4 miss topics + 2 valid clean controls, REPLACE-design (additive untested), single run/2 reps, hand-built expansions (a human chose the right terms — in production the expansion logic must derive them).
  - **DIRECTION CHANGE (2026-06-16):** the **retrieval-miss case is now ABSORBED by (c) ① structural-citation fallback** (detect missing protective coverage → low-confidence/withhold/flag, rather than guaranteeing retrieval). The **active build focus moves to the generation-side (b)+(c)** for the source-in-hand reversal; (d)/Path B is deferred. The (ii) rerank sub-fix was already deferred (its "recency" label is imprecise — it's the rerank LLM's relevance judgment, not YEAR_BOOST).
  - **(d-refusal) RETRIEVAL-RECALL REFUSAL detector — SHADOW DETECTION BUILT + VALIDATED 2026-06-18 (the retrieval-miss absorption above, now a concrete validated mechanism).** Plan-back `retrieval_refusal_planback.md`; `api/services/retrieval_refusal.py` + `server.py` hook `_run_retrieval_refusal_background` (flag `RETRIEVAL_REFUSAL_SHADOW`, default OFF) + `scripts/retrieval_refusal_eval.py` + `_prior_probe.py`; corpus `tests/retrieval_refusal_corpus.json`. Committed locally, NOT pushed. **Design H1 = pool-STANCE-spread × CONTESTED-prior: refuse = (final pool one-sided on factor→outcome valence) AND (a counter-direction is genuinely contested in CURRENT literature).** Reads the FINAL pool the generator saw (`documents`), gpt-4.1 (mini conflates). **REAL (`retrieval_refusal_20260618_095609.json` + `_prior_probe_095754.json`): DETECTION 3/3 obesity retrieval-miss cases (by run 7/9; 2 non-fires correctly had paradox-conveying pools); OVER-REFUSAL 0/9 (8/9 one-sided pools = prior leg stressed, incl. counterintuitive-but-SETTLED CAST/LEAP/smoking-PD); complete-pool 0/2; PRIOR generalization 10/10 contested-vs-settled; $0.16.** The C1 "flag-everything" failure did NOT recur — the prior leg discriminates genuinely-contested from settled. H2 (counter-query probe) / H3 (registry) NOT needed. **NEXT before enabling:** (1) broaden end-to-end DETECTION to MORE contested topics on LIVE retrieval (validated on obesity only — the sole retrieval-miss topic captured); (2) A2/enforcement decision (refuse vs downgrade-to-literature-display vs flag); (3) consider H3 curated registry to backstop the gpt-4.1-world-knowledge dependency of the prior leg. **DEPLOYED shadow-ON v181 (2026-06-18): `RETRIEVAL_REFUSAL_SHADOW=true` LIVE in prod — collecting real signed-in-traffic would-refuse data (logs only, touches no answer). FIRING VERIFIED on real traffic (2 signed-in obesity queries: `[RetrievalRefusal] refuse=True/one_sided=True` on a one-sided pool, `refuse=False/one_sided=False` on a two-sided pool; answers unchanged, H1 discrimination works live). Still LOGS-ONLY — users NOT protected; A2/ENFORCE (refuse vs downgrade vs flag) deferred pending shadow data + route decision. Burn-rate watch: gpt-4.1/signed-in-query (TECH_DEBT P0 ops).**

## Phase 1B (post Phase 0 Retrospective) — per advisor discussion + ADR 003+004

Phase 1B work items per advisor discussion 2026-05-04 (preserved in git commit 394545e) and ADR 003+004. Slot ranges from Week 4-8 of Phase 1B (5-week timeline).

### [P1] Explain risk-tier over-escalation — magnitude-aware tiering
- **Source**: production observation 2026-05-21 (solo-founder review)
- **Observed**: a panel with AST 68 / ALT 92 / Total Bilirubin 2.1 (all mild-moderate elevations, ALT ~2.2× ULN) produced a RED "Consult Immediately" clinical-correlation tier. Individual items correctly showed yellow "Needs Attention", but the correlation escalated to the highest tier purely from multiple simultaneous abnormalities, not from magnitude.
- **Why this matters**:
  - (a) risks alarming users / "boy who cried wolf" trust fatigue on a trust-critical medical product
  - (b) signal mismatch — the correlation's own text said "Further evaluation is recommended" (mild/objective) while the UI badge was RED (emergency)
- **Fix DIRECTION (not yet designed)**: the risk-tier upgrade logic in `api/prompts/explain_system.md` should weight deviation magnitude (multiples of ULN) — e.g. LFTs <3× ULN → yellow/orange (monitor / outpatient), reserve RED for very high multiples or critical values — rather than escalating on "multiple abnormalities stacked". Consider symptom-conditional escalation (give yellow + a dynamic prompt "if you also have severe abdominal pain / jaundice, seek care now") instead of a static red.
- **CAUTION**: this edits `api/prompts/explain_system.md` which is covered by the §2.7 20-case ExplainJudge acceptance baseline — any change must re-run that baseline (per PRD §2.7 Step 8 + CLAUDE.md Rule 17).
- **Slot**: Phase 1B Week 4 (alongside Verify system prompt polish — both touch prompts and share the §2.7 re-baseline gate)
- **Estimated**: 0.5–1d design + 0.5d re-baseline

### [P0] Verify 強制英文 + 友善引導 + system prompt polish
- **Source**: ADR 003 (advisor discussion notes preserved in git commit 394545e § 5.1) + dogfooding TECH_DEBT entry 2026-05-06
- **Implementation**:
  - Frontend input field guard + non-English detection + inline warning UI + 7 i18n keys × 16 languages + 4 PostHog events (per ADR 003)
  - System prompt polish (per dogfooding TECH_DEBT 2026-05-06 issues #1, #2, #4, #5):
    - Citation scope mismatch flagging (LLM 在使用每個 citation 前須 explicit assess population scope match)
    - 廣域地理 query 須明確列出 evidence 涵蓋區域 vs 缺口區域
    - Counterintuitive finding 須附 plausible mechanism，不能只給 statistical association
    - 禁止 LLM 自評引用品質 (例如「證據屬於近期且具代表性」字句)
- **Estimated**: 2-2.5 days (原 1.5-2 days + system prompt polish 0.5 day)
- **Slot**: Phase 1B Week 4
- **External help links**: TFDA / Drugs.com / PMDA / MFDS (read-only links, NOT API integration)

### [P0] DailyMed API integration
- **Source**: advisor discussion notes (git commit 394545e § 5.2)
- **Why**: Augment Research/Verify retrieval — DailyMed is 主檔 vs OpenFDA's sparse mirror; free, no rate limit, no API key
- **Implementation**: Add as 4th retrieval source for Research; replace/augment FDA OpenFDA in Verify; Citation ⓘ tooltip update
- **Estimated**: 2-3 days
- **Slot**: Phase 1B Week 4-5
- **UX sub-tasks 整合時順手做 (per PRD §2.10):**
  - Citation ⓘ tooltip 加 4 source 短說明 (PubMed / DailyMed / WHO 預留位 / FDA fallback),16 語言。預留 WHO 條目 (Phase 1C 啟用) 避免日後重做 i18n。
  - Verify pipeline FDA OpenFDA → DailyMed 主從切換的 retrieval ranking 驗證 (5 個典型藥物交互作用 query 比對 before/after)
  - PRD §2.3 source_type enum 'DailyMed' 啟用 + Citation chip 顏色 token 確認
- **Evidence tier classification at retrieve-time (per PRD §2.10.6, 2026-05-08 顧問 dogfooding 回饋):**
  - PubMed retrieval 增加 `publication_type` metadata extraction (e.g. `Practice Guideline` / `Systematic Review` / `Randomized Controlled Trial` / `Observational Study`)
  - 實作 5-tier classifier:Tier 1 (international guideline) / Tier 2 (systematic review + meta-analysis) / Tier 3 (RCT + large cohort) / Tier 4 (observational + commentary) / Tier 5 (survey + knowledge research)
  - Retrieval ranking 加入 tier_weight 因子 (Tier 1 × 2.0, Tier 2 × 1.5, Tier 3 × 1.2, Tier 4 × 1.0 baseline, Tier 5 × 0.7) 與既有 source_weight 複合
  - Frontend CitationPanel 顯示 Tier label 取代之前的 5 星 UI (e.g. 「Tier 2 / Systematic Review」)
  - i18n keys: 5 個 tier label × 16 語言 (可 repurpose 現有 dormant credibilityLabel 系列 keys)

### [P2] Full-site DailyMed over-claim sweep (honesty) — NEAR-TERM, independent of DailyMed integration
- **Source**: v184 post-deploy (C) check (2026-06-23) — the founder saw a signed-in Explain result whose footer "Data Sources & Attribution" still claims **"Drug label data from DailyMed (FDA/NLM)."** But DailyMed is **NOT integrated** — the real source is OpenFDA / FDA drug labels. Same overclaim already fixed in `/llms.txt` earlier today (`6d4ff86`, "FDA DailyMed" → "FDA drug labels"); that fix was **incomplete** — the Explain page footer (likely a SHARED component) + probably other surfaces still claim DailyMed.
- **Why it matters**: honesty / accuracy — claiming an unintegrated data source misleads users / crawlers / B2B clients (same principle as `6d4ff86`). Doubly irrelevant on **Explain**, which interprets lab reports (LOINC / MedlinePlus / RxNorm) and does NOT use drug labels at all.
- **Scope (FULL-SITE sweep, not page-by-page)**: grep the whole codebase for "DailyMed" overclaims (footer component, Verify page, landing, any served copy / attribution) and remove/soften each to the real sources (OpenFDA / FDA drug labels). One sweep — `/llms.txt` was fixed while the Explain footer was missed, so do it once across all surfaces.
- **⚠️ TIMING — two SEPARATE sweeps doing OPPOSITE things; do NOT conflate or defer this to the integration:**
  - **NOW (this item):** a current FALSE claim live in prod → REMOVE / soften the DailyMed attribution everywhere. Independent near-term honesty fix. **Do NOT wait for DailyMed integration** (Phase 1C+, may be reprioritized or never happen if OpenFDA suffices → deferring would leave a false claim live indefinitely).
  - **LATER (when DailyMed is actually integrated — the [P0] DailyMed API integration item above):** the REVERSE — ADD/UPDATE real DailyMed attribution + `source_type` enum + frontend labels. This is **inherent to that integration task** (a feature launch updates its own public copy), so no separate task is recorded for it — but note this "removal" fix will be **SUPERSEDED** by a "correct attribution" step at integration time.
- **Slot**: near-term (next docs/copy pass); cross-ref TECH_DEBT 2026-06-23 + `6d4ff86`.

### [P0] 在地差異提示 Tier 1 (TW/JP/KR/SG/MY/TH)
- **Source**: ADR 004 (advisor discussion in git commit 394545e § 5.3 — advanced from Phase 1C to 1B per 護城河 rebalance)
- **Why advanced**: Removing prescription parser frees 5-7 days; 在地差異 is core 護城河 (per ADR 004 wedge 2)
- **Implementation**: YAML schema design + 6-country data curation + backend retrieval integration + frontend UI (side panel + tooltip) + 16-lang i18n
- **Estimated**: 6-7 days
- **Slot**: Phase 1B Week 5-6
- **Integration scope**: Augments Research/Verify/Explain (not new tab) — show "在地差異提示" alongside results

### [P1] Anonymous Trial Flow polish
- **Source**: advisor discussion notes (git commit 394545e § 5.4)
- **Implementation**: L0→L1 upgrade prompt timing optimization (PostHog signal-driven) + Paywall UI polish + Onboarding 16-lang polish
- **Estimated**: 2 days
- **Slot**: Phase 1B Week 7

### [P2] Citation retrieval ranking evaluation
- **Source**: dogfooding TECH_DEBT entry 2026-05-06 issue #3
- **Why**: 對 query 最 match 的 citation 沒被推到 anchor 位置 (e.g. 「亞洲社區老年人 polypharmacy」最 match 的 PMID 37574369 排名在 PMID 38368398 之後)
- **Implementation**: 評估 RAG retrieval ranking 是否需要加入 population × setting × geography match score，weight 高於單純 recency
- **Risk**: 改 ranking 演算法會影響所有 query 的答案，需要 regression test
- **Estimated**: 1-2 days evaluate + 視結果 1 週實作
- **Slot**: Phase 1B Week 7-8 evaluate；視 risk 決定 Phase 1B 內 ship 或延 Phase 1C
- **Pre-requisite**: 累積 5-10 個 dogfooding query 樣本，確認 issue 是系統性
- **Dogfooding test plan (per PRD §2.10.3 設計原則 #3):**
  Trigger: DailyMed integration shipped (Phase 1B Week 4-5 結束)。
  4 條 evaluation:
  1. **Candidate pool 分布測試**: 5 個典型 query × 4 個 feature (Research / Verify / Explain / Share-from-history) = 20 條測試,看 candidate pool 從 9 → 12 之後 top 8 evidence 的 source 分布是否合理
  2. **禁忌 / 黑框警告類專測**: 「Warfarin + Aspirin 安全嗎」「metformin 禁忌症」等,確認 DailyMed FDA label 沒被 PubMed studies 擠下去
  3. **最新研究類專測**: 「最新阿茲海默症療法」「SGLT2 inhibitor 心衰研究」等,確認 PubMed 沒被 DailyMed/FDA 靜態 label 擠下去
  4. **跨語言 query**: 5 query × 3 locale (zh-TW / ja / ko),確認語言切換後 retrieval source 分布不退化
  5. **International guideline vs single-country research test** (per 2026-05-08 顧問 dogfooding case): query about pediatric topic (e.g. fluoride toothpaste concentration for children) — verify retrieval surfaces AAPD / NHS / EAPD international guidelines in top 3, NOT single-country observational studies (e.g. Israel Avidana 2025). Test against the actual dogfooding case "小孩牙膏如何挑選" as baseline.
- **Source weight 初始假設 (待 dogfooding 驗證):**
  - DailyMed / FDA: × 1.5 (權威 source 加權)
  - WHO 全球指引: × 1.3 (Phase 1C 才適用)
  - PubMed (RCT / meta-analysis): × 1.0 (baseline)
  - PubMed (個別 case report): × 0.7 (低證據等級)
  - 風險: 上述為 hypothesis,實際數值需看 dogfooding 結果調整
  - **2026-05-08 修訂**: 證據 tier weight 加入 ranking formula 後,完整公式為:
    `semantic_similarity × source_weight × tier_weight × recency_factor`
    Tier weights: Tier 1 × 2.0, Tier 2 × 1.5, Tier 3 × 1.2, Tier 4 × 1.0, Tier 5 × 0.7
    詳見 PRD §2.10.6.
- **Decision tree (evaluate 完看):**
  - 若 4 條測試全部 source 分布合理 → 不動 reranker,只記文件 (low priority Phase 1C)
  - 若僅 「禁忌 / 黑框」類失準 → 動 source-weighted scoring,不動 BM25
  - 若 「跨語言」類失準 → 先檢查 query rewrite 階段,不一定動 reranker
  - 若全面失準 → 考慮 BM25 / hybrid search,排 Phase 1C

## Phase 1C — per advisor discussion (護城河 deepening)

### [P1] WHO ICD-11 API integration
- **Source**: advisor discussion notes (git commit 394545e § 6.1)
- **Why**: Cross-language bridging anchor — multilingual disease name alignment ("糖尿病" / "diabetes" / "당뇨병" → 5A11)
- **Implementation**: OAuth 2.0 client_id (3-5 day approval, file early) + RESTful integration; 14 official languages
- **Estimated**: 2-3 days
- **Slot**: Phase 1C Week 9
- **Pre-action**: Apply for OAuth client_id NOW (per advisor discussion git commit 394545e § 10.1)

### [P2] Taiwan brand-name → ingredient grounding (deterministic lookup, NOT LLM memory) — NOT near-term
- **Source**: TECH_DEBT 2026-06-22 (post-deploy click-test of piece (A): 「冠脂妥」 confidently mis-identified as Simvastatin; it is rosuvastatin).
- **Problem**: even with piece (A)'s force-English guard, the "仍要送出（不建議）" proceed-anyway path lets the LLM confident-wrong map a Chinese brand→ingredient and present the wrong-drug analysis as authoritative. Brand→ingredient is a **factual-lookup** problem, not a reasoning one — LLM memory on Taiwan long-tail brands is inherently unreliable.
- **Fix-direction**: ground brand→ingredient in a REAL table — TFDA drug-license data (商品名↔成分) if a dataset/API exists (deterministic); else a hand-curated Taiwan-common brand→ingredient YAML (same pattern as 在地差異). **GUARDRAIL: do NOT model-swap or prompt-tune — it changes the error rate, not the reliability.** See TECH_DEBT 2026-06-22.
- **Slot**: **Phase 1C (or whenever 在地差異 grows a drug-name component) — FOLD into the 在地差異 / local-augmentation effort; do NOT insert as a near-term Phase 1B task (breaks current 1B ordering).**

### [P1] 在地差異提示 Tier 1 expansion (VN/PH/ID/HK/SA/AE)
- **Source**: advisor discussion notes (git commit 394545e § 6.2)
- **Implementation**: Same YAML schema as Tier 1 initial 6; backend/frontend already built in Phase 1B
- **Estimated**: 4-5 days
- **Slot**: Phase 1C Week 9-10

### [P1] 跨語言橋接面板 MVP
- **Source**: advisor discussion notes (git commit 394545e § 6.3 — Wedge 3 of 4-wedge 護城河)
- **Implementation**: ICD-11 anchor data structure + cross-language query backend + bridging panel UI + 4-5 language alignment logic
- **Estimated**: 3-4 days
- **Slot**: Phase 1C Week 11

### [P2] WHO API integration — RAG source for global treatment guidelines
- **Background**: PRD §2.3 CitationPanel `source_type` enum already includes 'WHO', but no work item exists for actually ingesting WHO data as a retrievable RAG source. Currently 'WHO' is a valid display label only — no document ingest pipeline produces WHO-tagged citations.
- **Scope**: integrate one or more WHO data endpoints (Essential Medicines List / treatment guidelines / global pharmaceutical reference) into the existing retriever pipeline (`api/rag/retriever.py` + `api/services/*`). Treat WHO as a baseline global reference that complements local-authority sources (§5.1 Tier 1 6國).
- **Why Phase 1C, not Phase 1B**:
  - Phase 1B Week 4-8 already loaded with DailyMed (Week 4-5) + §5.1 Tier 1 6國 (Week 5-6) + Anonymous Trial Flow polish (Week 7) + integration test (Week 7-8). No buffer.
  - GTM priority: §5.1 in-locale differentiation is the moat (UpToDate / OpenEvidence don't have local data); WHO is a global baseline competitors can replicate.
  - Sequencing: implementing §5.1 first surfaces whether WHO ingestion is needed standalone or can be folded into §5.1 local-vs-global comparison logic.
- **Pre-implementation gates**:
  - §5.1 Tier 1 6國 shipped (informs WHO data shape requirements)
  - §2.1 Model Provider refactor shipped (clean retriever interface)
- **Distinct from existing [P1] WHO ICD-11 API integration entry above**: that item is about ICD-11 anchor codes (cross-language disease term alignment, Wedge 1). This item is about WHO content ingestion as RAG documents.
- **Estimated**: 2-3 days
- **Discovered**: 2026-05-06 — user-flagged BACKLOG gap during §4.5 UX polish closing review

### [P2] Guideline document ingestion pipeline (AAPD / NHS / SDCEP / EAPD / WHO 等)
- **Background**: 2026-05-08 顧問 dogfooding 回饋 揭示 international clinical practice guideline (AAPD / NHS / SDCEP / EAPD / WHO 等) 不在 PubMed 主索引 — 很多是 PDF / website / 機構出版物。即使 PRD §2.10.6 證據分層把 Tier 1 weight × 2.0,如果 retrieval 根本撈不到 Tier 1 文件,classifier 也沒用。
- **Scope**: Build ingestion pipeline for guideline documents from authoritative bodies:
  - **Pediatric**: AAPD (American Academy of Pediatric Dentistry), EAPD (European Academy of Paediatric Dentistry)
  - **Dental general**: ADA (American Dental Association)
  - **Public health**: NHS (UK), SDCEP (Scottish), WHO global guidelines (already P2 in BACKLOG)
  - 各 guideline document 拉進 RAG corpus,標 source_type='Guideline' + tier=1
- **Why Phase 1C, not Phase 1B**:
  - Each guideline source has different format (PDF / HTML / DOCX); 新 parsing pipeline
  - 授權狀況 varies (AAPD 商業授權 / NHS 公開 / WHO 公開) — 須 case-by-case review
  - Multi-week effort,Phase 1B 已滿載
- **Pre-implementation gates**:
  - PRD §2.10.6 evidence tier classification shipped (Phase 1B)
  - Tier 1 weight × 2.0 validated against Phase 1B Week 7-8 dogfooding eval
- **Distinct from existing [P2] WHO API integration entry**: that one ingests WHO global treatment guidelines + GHO statistics. This entry covers professional society guidelines (AAPD / ADA / EAPD / NHS / SDCEP) — different authorities, may share infrastructure but content scope distinct.
- **Estimated**: 4-6 days (depends on # of guideline sources targeted in MVP — recommend MVP = AAPD + NHS + 1 more, expand later)
- **Discovered**: 2026-05-08 — 顧問 dogfooding case revealed retrieval missing international guideline tier of evidence

---

## Phase 2 candidates (exploratory) — post Phase 1B / post Stage 3, not scheduled

### [P2] Generative UI — structured/interactive answer rendering

> **Reworked 2026-06-08 into two tiers:** a near-term **Tier 1 Verify PoC** pulled
> forward to the Phase 1B tail, feeding the go/no-go on the **Tier 2** full rollout
> (unchanged — still Phase 2, gated on prod data). Every original rationale line +
> design constraint below is PRESERVED and applies to BOTH tiers.

#### TIER 1 (NEW — near-term): [P2] Verify generative-UI PoC (rich structured rendering)
- **Scope**: render Verify's EXISTING validated structured output (interaction matrix
  + severity badge + per-drug info cards + source chips) as interactive components.
  This is OPTION (i) — rich rendering of already-structured data — NOT the full
  LLM-component-manifest / component-selection machinery (that stays Tier 2).
- **Goal**: cheapest path to an experiential signal on whether structured rendering
  feels better than plain text, before committing to the larger rollout.
- **Time-box**: ≈ 1-2d. Keep the PoC throwaway-tolerant.
- **Placement / sequencing gate — Phase 1B TAIL (≈ Week 6+)**: schedule AFTER
  (a) Verify 強制英文 + drug-name resolution AND DailyMed integration (Week 4-5), so it
  renders the FINAL stable + richer DailyMed-sourced data contract (don't build on a
  moving target — same "先量再動" lesson as PRD §2.10.5); AND (b) §5.1 在地差異 6國 moat
  ships (Week 5-6), so a learning PoC does not displace the PMF-critical path.
- **Gate-override note**: this PoC INTENTIONALLY overrides this entry's own "gate on
  prod data, not trend" rule (Tier 2 constraint #4 below). Defensible because Verify is
  the lowest over-trust-risk mode AND is this entry's own designated "suggested entry
  point" — a small, time-boxed, throwaway bet is worth an experiential signal before
  real-user data exists.
- **Over-trust guardrail (carried over from the constraints below, restated)**: render
  ONLY already-validated structured data; introduce NO new medical inference; do NOT
  wrap prose clinical judgment to look more authoritative — consistent with the
  citation-mandatory / anti-hallucination positioning.
- **Exit condition**: productionize the PoC AND consider Tier 2 (full generative UI)
  ONLY if the PoC result + prod data BOTH support it.

#### TIER 2 (UNCHANGED — full generative-UI rollout, Phase 2, gated on prod data)
> Cross-ref: Tier 1 above is the pulled-forward Verify PoC that feeds this decision.
- **Source**: Andrew product exploration 2026-06-02 (generative UI trend research + medical over-trust risk analysis)
- **Idea**: Render Vela answers as structured/interactive components (React/HTML) instead of plain text/markdown, for more intuitive comprehension. Trend is real (Gartner: ~30% of new apps to use AI-driven adaptive interfaces by 2026; Vercel AI SDK RSC / Google A2UI / CopilotKit AG-UI are mature patterns — LLM emits structured JSON selecting which component to render).
- **CRITICAL design constraints (the reason this is recorded, not just "do generative UI")**: medical context inverts the usual "rich UI = better" conclusion because of the OVER-TRUST risk (Stanford-Harvard State of Clinical AI 2026 + ECRI 2026 top patient-safety concern: users over-trust confident-looking systems lacking clinical context). Rich/authoritative UI can make a possibly-hallucinated answer LOOK more authoritative, directly undermining Vela's citation-mandatory / anti-hallucination positioning. Therefore:
  1. **Structured UI ONLY for: source/citation surfacing, numeric values vs ranges, verification paths.** NOT for wrapping prose clinical judgment to make it look more authoritative.
  2. **Per-mode suitability differs by data shape:**
     - **Verify (drug interactions)** — BEST fit, lowest over-trust risk. Data is already structured (drug pairs, severity, mechanism, source from FDA/DailyMed). Interaction matrix + severity badge visualizes already-validated structured data, not free-generated prose. The removed ProductShowcase Verify card ("⚠ Major Interaction" badge) was a proto-version.
     - **Explain (lab results)** — GOOD fit, BUT numeric-mapping correctness is safety-critical: a value→status mapping error (e.g. TSH 12.5 shown as "normal/green") is MORE dangerous than a prose error because visualization makes it look precise. Requires strict correctness validation of the value→status mapping. The removed Explain card ("↑ Above normal range") was a proto-version.
     - **Research (evidence Q&A)** — WORST fit for charts (prose reasoning forced into visuals = the over-trust trap). BUT citation can be structured (source cards, evidence-tier badges, PubMed links) — that part STRENGTHENS verification, so it's additive.
  3. **Numeric/status mappings (Explain) need rigorous correctness validation** — wrong mapping in a visual is more dangerous than in prose.
  4. **Gate on prod data, not trend** — only invest if PostHog shows users struggle with plain-text answers (e.g. high dwell/bounce on Explain lab interpretation). The problem (plain text is hard to comprehend) is unvalidated until there are real users.
- **Solo-founder cost note**: large effort — component manifest, LLM structured-output prompt engineering + validation, streaming render, per-component 16-locale i18n, a11y, AND medical content correctness validation (heavier than general-purpose apps). Competes with Stage 3 + Phase 1B for resources.
- **Suggested entry point IF pursued**: narrow PoC on Verify interaction matrix first (most structured data, lowest over-trust risk, existing ProductShowcase proto). NOT a full-app generative UI rewrite.
- **Estimated**: full rollout TBD; much larger than Tier 1. (The narrow Verify PoC estimate moved to Tier 1 = 1-2d; the ~3-5d originally noted here referred to that now-Tier-1 PoC.) Re-scope when prod data justifies.
- **Slot**: Phase 2 (post Phase 1B, post Stage 3). Not scheduled.

---

## ❌ Removed from roadmap (per ADR 004)

- **Prescription Parser MVP** (originally PRD § 4.4 Phase 1B 殺手功能) — permanently removed from active roadmap. No Phase 2 candidate spec. If revisited, redesign from scratch.
- **TFDA API integration** — tied to prescription parser. Not implementing in any phase.
- **LLM-based drug name resolution** (per ADR 003) — empirically shown unsafe (53-60% confident-wrong rate on GPT-4.1 series).
- **Prescription clipboard paste with OCR** (was tied to prescription parser) — removed.

If user behavior over time creates strong signal for prescription/Rx workflow (e.g. Verify monthly active users > 1,000 with > 50 user requests for prescription parsing), revisit will trigger fresh design — not 2026-05-04 advisor spec resurrection.

---

## Phase 0 deploy retrospective follow-ups

Captured 2026-05-19 from production deploy + retrospective. See docs/retrospectives/phase-0-2026-05.md § 5 for full context.

- [ ] **[P2 → Phase 1A entry, ADR candidate] OG image persistent storage decision — Fly volume vs R2/CDN**
      
      Current state: `/static/og/*` PNGs live on Fly's ephemeral filesystem; lost on every machine restart, redeploy, or auto-stop wake event. `.gitignore` comment promises "production OG images go to R2/CDN, not local filesystem" but R2/CDN integration was never built. Wiring fix (commit a63b304, 2026-05-19) addressed URL/path mismatch but not persistence.
      
      Soft launch impact: Low — bot fetches (LinkedIn / Twitter / Google crawler) typically happen within seconds-to-minutes of share creation while PNG still exists. Risk surfaces for shares re-fetched after machine restart (rare for short-lived viral shares, more likely for evergreen explore pages).
      
      Decision tradeoff:
      - **Fly volume**: ~5 LoC fly.toml `[mounts]` section. Single-region pinning. Simpler to ship. Compatible with current single-machine production. Migration to multi-region later requires volume-per-machine + share-affinity routing.
      - **R2 / Cloudflare CDN**: Larger scope (boto3 + R2 creds + upload-on-create + URL change from `/static/og/<id>.png` to `<r2-bucket>.r2.cloudflarestorage.com/og/<id>.png` or CDN-fronted URL). Survives multi-region / multi-machine. Matches .gitignore comment intent.
      
      Decision likely warrants ADR (007 or 008 — number TBD based on §3.1 PRD revision decisions). Should be made before Phase 1A §3.1 ship to avoid retrofitting OG paths twice.
      
      Same root cause affects landing page `/og-image.png` (currently served from build-time COPY into image, so survives machine restart but not editable without redeploy).

- [ ] **[P3 → Phase 1B post-soft-launch] Dodo test/live env separation audit**
      
      Discovered during pre-deploy 2026-05-19 audit: 1 production user_usage row had `dodo_customer_id = test_cust_c53dfaa8cd4b` from 2026-03-19. Safety scan `WHERE dodo_customer_id LIKE 'test_%' OR dodo_subscription_id LIKE 'test_%'` returned 1 row only; no broader sandbox bleed. Row cleaned.
      
      Hypothesis: Either Dodo webhook handler accepted a test customer in production, or production DATABASE_URL was used during sandbox dev work. Single occurrence in 2 months suggests latter (one-off dev pollution), but worth auditing webhook handler logic in `api/services/dodo_webhook.py` (or equivalent) to confirm:
      - Webhook verifies request signature against `DODO_WEBHOOK_SECRET` (live key, not test)
      - Handler rejects events where customer prefix is `test_*`
      - No code path allows `dodo_customer_id LIKE 'test_%'` to be written to production
      
      Schedule: After Phase 0 soft launch starts producing real Dodo subscriptions (Phase 1B opening). Monitor user_usage for any new `test_*` rows for 4 weeks post-deploy as canary.

- [ ] **[P3 → Phase 1B post-soft-launch] Dodo webhook real-subscription canary monitoring**
      
      Production currently has 2 Pro users, both self-comp (Andrew personal + TEST_MODE marker), neither flowed through Dodo checkout. So Dodo webhook real-subscription path (subscription.created → user_usage.plan_type='pro' with dodo_subscription_id + current_period_end populated) has never been exercised in production.
      
      First real Dodo subscription post-soft-launch is implicit canary. Monitor for:
      - Webhook signature verification passes
      - user_usage row created with plan_type='pro', non-null dodo_subscription_id, non-null current_period_end
      - PostHog `subscription_started` event fires with correct properties
      - Backend gates correctly recognize the new Pro user (Explain unlocks, quota changes)
      - Subsequent webhook events (renewal, cancellation) flow correctly
      
      Schedule: Active monitoring starts day-1 of soft launch. Alert on first paid user in PostHog + Dodo Dashboard cross-check.

- [ ] **[P3 → next opportunity] share_revoked PostHog event verification follow-up**
      
      During PART C.1.6 PostHog Live Events verification on 2026-05-19, `share_revoked` event was not visible in the 30-minute window after revoking a test share. Possible causes: (a) event was truncated outside 30-min window in PostHog default view, (b) revoke action's PostHog capture call has a wiring gap. PRD §4.5 PHASE B lists 6 share events; only 5 were directly verified.
      
      Resolution: Next dogfooding session, revoke a fresh share and immediately check PostHog Live Events panel filtered on user clerk_id. If absent, grep frontend `MySharesTab.tsx` (or wherever revoke action lives) for `posthog.capture('share_revoked'` to confirm wire-up.

---

## Stage 2 landing copy i18n alignment (captured during landing redesign)

Two i18n content drifts surfaced during Stage 2 landing redesign (Steps 2 / 4a / 4b, 2026-05-28 → 2026-05-29). Both are 16-locale content edits in the i18n bundle — same category as blog content authoring (Rule 16: i18n-first). Non-blocking; best done together as one "[i18n] landing copy alignment" pass alongside or before Stage 2 push.

**Redeploy note:** i18n strings are bundled into the Next.js build (not DB-backed like blog content), so this pass WILL trigger a redeploy. Lighter than blog authoring but heavier than a hot config / DB content change.

- [ ] **Verify hero chip translations — native medical review (th/ar/hi/bn/he/vi)**
      T2 (2026-06-05) re-authored `heroChip2` ("Can elderly patients take BP meds with
      calcium?") and `heroChip3` ("Is it safe to use antibiotics during pregnancy?") to
      all-Research natural-language questions across all 16 locales (`utils/i18n.ts`).
      The en/zh-TW (Andrew) + zh-CN/ja/ko/es/fr/de/it/pt cells are normal-confidence; the
      **6 low-confidence locales — th, ar, hi, bn, he, vi (12 cells: 2 chips × 6)** —
      shipped **best-effort** and need a native-medical-terminology review (same review
      gate as the Stage 5 i18n + the Verify severity-label dict). RTL (ar/he) stored in
      logical order; proper nouns (Warfarin/Aspirin/Metformin/DOACs) kept Latin. Cosmetic
      (sample-query chips), low priority, but flagged so they're not assumed reviewed.

- [ ] **Hero copy not aligned to STATE.md Stage 2 locked spec**
      STATE.md "Next Up" Stage 2 locked the hero as: title "Ask in your language." (short, period-terminated) + subtitle "Evidence-cited medical answers from PubMed and the FDA, answered in your language. No account needed to try." Stage 2 Step 2 reused the existing `landingContent.<locale>.tagline` / `.subtitle` values (to preserve 16-locale coverage per Rule 16) which resolve to different strings — observed in en: title "Ask in your language. Verified by official sources. Answered in yours." + subtitle "The AI medical search for healthcare professionals who work beyond English." Aligning to the locked spec means editing `landingContent.tagline` / `.subtitle` across all 16 locales.

- [ ] **ProductShowcase Research mockup query drift**
      STATE.md Stage 2 locked the Research card snippet as "Metformin + CKD eGFR≥30". Current `t.mockupResearchQuery` resolves to a different query (observed in en: "What are the side effects of Metformin?"). Verify (`t.mockupVerifyDrugs` / `t.mockupVerifyBadge` → "Warfarin + Aspirin Major interaction") and Explain (`t.mockupExplainValue` / `t.mockupExplainStatus` → "TSH 12.5 above-normal") cards ARE already aligned — only Research drifts. Fix means editing the Research mockup query key across all 16 locales.

- [ ] **Dead landing i18n keys cleanup (post-Stage-4) — PARTIALLY DONE (S5.2)**
      Stage 4 S4.1 removed multiple landing UI elements, leaving their i18n
      keys dead. Stage 5 S5.2 (commit 644e2e8) already cleaned the bulk: when
      the ProductShowcase cards array was deleted, it removed the three
      referenced-but-dead `cta:` keys (`tryResearch`, `tryVerify`,
      `tryExplain`) plus all 8 `mockup*` keys (`mockupResearchQuery`,
      `mockupResearchSource`, `mockupVerifyDrugs`, `mockupVerifyBadge`,
      `mockupVerifySource`, `mockupExplainValue`, `mockupExplainStatus`,
      `mockupExplainSource`) from the `Translations` interface + all 16 locales.
      - Still present AND dead (audited 2026-06-02 against `utils/i18n.ts` +
        all `pages/*` / `components/*` — no consumer anywhere): `seeHow`,
        `socialProof`, `privacyTitle`, `seePricing`, `ctaPrimary`,
        `valueProp.{language,sources,anonymous}.{label,body}` (6 sub-keys).
        Safe to delete from the interface + all 16 locales.
      - STRUCK from this list — NOT dead: `privacyPolicyLink`. It was listed
        as "fully unused" but became stale when commit dcf890a's
        `LandingSettingsDropdown` resumed using it for the Privacy-link row
        (`components/LandingSettingsDropdown.tsx:75`). Leave it.

---

- [ ] **Hero chip screen-reader action-context i18n key (`heroChipAriaPrefix`)**
      Currently the hero chips have no `aria-label` (their visible text is the
      accessible name). For richer SR context like "Fill search with: <chip text>",
      add a `heroChipAriaPrefix` translation key across all 16 locales and wrap
      chips with `aria-label={`${t.heroChipAriaPrefix}${chip}`}`. Deferred from
      Stage 4 S4.3 to avoid introducing an untranslated English SR string
      mid-stage. Low priority; chips are currently AA-readable and the chip text
      alone is meaningful.

---

## Stage 3 theme follow-ups (captured during light audits)

- [x] **Shared modals/overlays light-theme audit (before Stage 3 closes)**
      **RESOLVED 2026-06-05** (shared-modals pass). Per-component verdicts after recon:
      - **FLIPPED** to theme tokens (commit `99169f0`):
        - `components/UpgradeModal.tsx` — card `#0f1f3d`→`bg-2`, gray text→`text-text/α`.
        - `components/OnboardingOverlay.tsx` — card navy gradient→`bg-2`, title→`text-text`.
          (Was genuinely broken in light: hardcoded-dark card + token body text → text
          flipped dark → invisible. The card flip fixes it.)
        - `components/BugReportButton.tsx` — modal card/inputs/option bgs `#0f1f3d`/`text-white`
          → `bg-2`/`text-text`. FAB (`bg-slate-600`) kept (neutral, theme-independent).
      - **KEEP-DARK** (intentional, unchanged): `components/ProFeatureOverlay.tsx` — small
        Pro-lock popover (`#1e293b`/`#475569`/`#cbd5e1`), same category as the LoincBadge /
        evidence tooltips kept dark in 3.5/3.6; reads fine on a light page.
      - **Already token / theme-independent** (no change needed):
        - `components/Toast.tsx` — white text on `rgb(var(--color-{success,warning,danger}))` bg.
        - `components/AnonymousUpgradeCTA.tsx` — card already `bg-bg-2`; scrim + `#2563eb` CTA theme-independent.
        - `components/ShareButton.tsx` → renders `components/ShareModal.tsx`, which is already
          fully token-based (only its scrim is hardcoded). ShareButton itself has no colors.
      - **Scrims kept** on all modals (`rgba(0,0,0,0.7)` / `0.72` spotlight) — theme-independent
        page-dimming, not a dark leak.
      Discovered 2026-06-03 (3.4 Dashboard) + 2026-06-04 (3.5 Research recon); closed 2026-06-05.

- [ ] **Future-polish: re-unify saturated CTA colors to the brand token**
      The Pro/upgrade CTA buttons use a hardcoded saturated coral `#ff6b4a` (+ `#cc5533`
      pressed) and blues `#1e4a8a` / `#2563eb` — `#ff6b4a` ≠ `--color-brand` (255·142·110),
      a lighter/peachier coral. These are theme-independent colored buttons (white text,
      readable in both themes) so they were KEPT as-is during the shared-modals pass, not a
      theme bug. Future visual-consistency pass could unify them to `--color-brand` (+ a
      brand-pressed/secondary token). Same future-polish bucket as the decorative-accent
      light-contrast flags (3.5/3.6) and the History severity-pill (3.7). Cosmetic, low priority.

- [ ] **OPEN PRODUCT QUESTION: should the Blog (Jinja2) follow the app theme?**
      Blog is NOT a Next.js page — it's server-rendered by FastAPI/Jinja2
      (`api/templates/blog_list.jinja2` + `blog_post.jinja2`, `api/services/blog_renderer.py`,
      route `api/server.py:2211`). It has its OWN self-contained `<style>` block with
      its own CSS variables (`--vela-text-muted`, `--vela-card-bg`, `--vela-text-primary`,
      hardcoded `#0a1628` / `rgba(255,255,255,0.08)`) — it does **not** consume the
      Next.js `--color-*` token system or `.dark`/`.light`, and never participated in
      next-themes. So Stage 3's "tokenize colors" audit does not apply, and Blog was
      intentionally left untouched in 3.7. **Heads-up for 3.8 total acceptance:** a
      Light-theme app user who navigates to `/blog` will see the blog's fixed
      (currently dark-ish) Jinja2 design — it will NOT visually match app-light.
      **Decision needed:** make the Jinja2 blog theme-aware (replicate the FOUC head
      script + token CSS in the template layer — a separate server-side effort) OR
      keep it a deliberate fixed-design public/SEO surface (like the landing's
      forced-light stance, but server-rendered). Surfaced 2026-06-04 during 3.7 recon.

- [ ] **Future-polish: restore History severity-badge colored pill (alpha variant)**
      `pages/history.tsx` interaction badges previously used `` `${getSeverityAccent()}20` ``
      for a colored pill bg, but that appended `20` to an `rgb(var(--color-…))` string
      → invalid CSS, silently dropped (token-migration artifact). 3.7 removed the dead
      line; badges now render as colored-text-only (`color: accent`). To restore a
      proper colored pill, `getSeverityAccent` needs to expose an alpha variant (e.g.
      return the bare `var(--color-danger)` channels so callers can do
      `rgb(var(--color-danger) / 0.12)`). Same future-polish bucket as the 3.5/3.6
      decorative-accent light-contrast flags. Cosmetic, low priority.

---

## v172 batch follow-ups (captured 2026-06-05)

- [x] **Evidence edge-case: undetectable Research query → output-language falls back to `en` instead of UI locale** — **✅ RESOLVED v179 (`12e7f4a`, 2026-06-11).** Research's answer/disclaimer language is now UI-driven via `_resolve_response_language` (the exact pattern this item proposed) — it no longer uses `detect_language` for output, so the low-signal "undetectable → en" conflation is gone; output language is the UI locale with an `en` *final* fallback by design. (Diagnosis retained below.)
      Research derives the answer language from `detect_language(question)` (server.py),
      which conflates "user wrote in English" with "input is undetectable" (pure drug names /
      numeric values / too-short strings). A zh-TW user asking a Research question that is just
      a drug name (e.g. "Metformin 0.5g") can get an English answer instead of 繁中. Decide: the
      detector should return `None`/unknown for low-signal input, and the caller falls back to the
      **UI locale** (same `_resolve_response_language` pattern Verify/Explain already use) rather
      than defaulting to `en`. **Distinct from the v172 parsing fix** (`afe0bdf`), which made the
      🟢🟡🔴 section-header parsing language-agnostic — that fixed the *indicator* rendering; this is
      about the *answer language* selection upstream. Low priority; surfaced during the T1 output-
      language recon + the evidence-parsing work.

- [ ] **Bug 2/3 cross-account verification under real Clerk (TEST_MODE=false / prod)**
      The sign-out cleanup (`454fad6` — clears the global `vela_plan_cache`/`vela_status_cache` +
      the per-user `hasSeenOnboarding` flag on sign-out) was **only dev-verified under TEST_MODE**,
      where all auth collapses to a single `test_user`, so a true two-account switch was never
      exercised. Needs a real check: sign out account A → sign in account B and confirm (a) no
      plan-cache bleed (B doesn't inherit A's Pro/free badge), (b) onboarding re-shows for a fresh
      account. Do during the next prod dogfooding session post-v172. Verification follow-up, not a
      code change (unless it surfaces a gap).

- [ ] **Parsing fix — live-verify untested locales (ar / he / th)**
      The v172 `parseResearchSections` rewrite (`afe0bdf`) is Node-harness-verified language-agnostic
      (strips `[ ]`/`［］`/`【】` + emoji + `— Lang`, extracts evidence position-independently), but only
      **en / zh-TW / ja / ko** are on the dev acceptance checklist. Run a Research query in **ar, he
      (RTL), and th** post-v172 and confirm: clean section titles (no brackets/emoji in text) +
      correct colored borders. Small dev-verify; expected to pass (the regex is locale-blind) but
      RTL + Thai script weren't live-run.

---

## Tooling / repo hygiene (pre-existing, surfaced during audits)

- [ ] **dev/prod DB safety: never point local `.env` at the prod Neon branch**
      **Surfaced 2026-06-05** (v172 batch, dev-DB work). Local backend `.env` `DATABASE_URL` was
      found pointing at the **production** Neon branch (`neondb`) during a routine "set test_user →
      free" task — caught before any write because the endpoint resolved to a prod-associated host.
      Mitigation applied: created a dedicated dev branch (`ep-spring-voice-a127ye10`), repointed
      `.env` (gitignored), and did the `test_user` plan write **only** against the confirmed dev
      endpoint. **Lesson / guardrails to consider:** (a) a pre-write assertion or wrapper that
      refuses any local dev write when `DATABASE_URL` host matches the known prod endpoint; (b) a
      `.env.example` / doc note documenting the dev vs prod Neon hosts so the distinction is explicit;
      (c) optionally a `scripts/` guard that prints the resolved DB branch before any destructive op.
      **Same test/prod-bleed class** as the existing "Dodo test/live env separation audit" (Phase 0
      retro follow-up) — worth handling together when ops hardening is scheduled. Priority: Medium
      (near-miss, no prod write occurred).

- [ ] **ESLint flat-config migration (pre-existing tooling debt)**
      `npm run lint` fails: ESLint 9.37 requires a flat `eslint.config.js`,
      but the repo has neither `eslint.config.*` nor `.eslintrc*`. Build's
      own type-check + Next lint succeed, so this only affects the
      standalone `npm run lint` script. Options: (a) create `eslint.config.js`
      flat config, (b) pin ESLint to v8 in package.json, (c) change the
      `lint` script in package.json to `next lint`. Surfaced during Stage 4
      S4.4 audit. NOT a Stage 4 regression.

- [ ] **Decide fate of `docs/Blog_Implementation_Spec.md`**
      Untracked since the 2026-05-25 blog feature ship; persisted as
      untracked across every Stage 2 / Stage 4 commit. Needs a decision:
      (a) `git add` + commit if intended as repo doc; (b) add to
      `.gitignore` if intentionally local; (c) delete if obsolete. Currently
      shows up as `??` in every `git status` and clutters the working-tree
      check.

## §4.3 deferred sub-needs (from §3.1 PHASE E, 2026-06-08)

PHASE E built §4.3 需求1+2 (My-Context editor + save) + 需求5 Trigger A (sign-in restore banner). These two §4.3 sub-needs were explicitly deferred:

- [ ] **§4.3 需求3 — "再問一次" 10th-query role prompt** — after a user's 10th query, show a small banner beside the FeedbackBar; clicking opens a mini modal to pick `role` directly; dismissable, record `dismissed_prompts`. Spec: PRD §4.3 需求3. Not in PHASE E scope. Low priority (engagement nudge).
- [ ] **§4.3 需求4 — privacy controls (export / clear preferences)** — "Export my preferences" → download the `vela_user_context` blob as JSON; "Clear my preferences" → confirm → clear localStorage; (Pro) "Clear synced data" → DELETE the server hash. Spec: PRD §4.3 需求4. Not in PHASE E scope. Note: a server DELETE would need a new backend endpoint (no migration). Privacy-first nicety.
- [ ] **§4.3 需求5 Trigger B — Settings "restore from last sync" button** — manual counterpart to PHASE E's Trigger A sign-in banner (same GET + hash-compare, user-initiated from the Settings My-Context tab). Deferred from PHASE E (Trigger A only). Small add once 需求4's Settings section exists.

## §3.3 full (deferred from the §3.3 basic E-tail, 2026-06-08)

- [ ] **[P2] §3.3 full — rotating pool/shuffle + `example_query_clicked` event + mode-routing chips** — the §3.3 basic ship (commit `1671253`) does role-FILTERED STATIC examples only (3 per group, REPLACE the hero chips, event-free, all run as Research). Full version adds: (a) a rotating 5–8 example pool per role with per-load **shuffle**; (b) the **`example_query_clicked` { example_text, role, position }** PostHog event (1-line add in `handleChipClick`, would also cover heroChips); (c) **mode-routing chips** — examples carry a target mode so a Verify/Explain-flavored example (e.g. "這張處方有交互作用嗎?") routes to `/verify` / `/explain` instead of running as Research (D3: those examples were DROPPED from basic to avoid the affordance mismatch). **Gate on prod data** — only build if PostHog shows onboarding-completion volume + role-set users engaging with the Research-only examples. Spec: PRD §3.3 (L1123–1173).

## Deletion-feature C — account / data hard-delete (COMPLIANCE DEBT · HIGH)

> **✅ 🔴 COMPLIANCE BLOCKER CLEARED (v180, `61e25dc`–`0e03659`).** The live /privacy §4 30-day-deletion promise is now **keepable by hand**: the lawyer-confirmed **design-E manual SOP** (`docs/manual-deletion-sop.md`) is executable + **dev dry-run-verified 14/14**, and the **`user_usage.deleted_at` FREEZE** (PIECE 1) is **live on prod** (migration 008 applied dev+prod). What remains below is the **🟡 in-app self-service deletion feature + Clerk `user.deleted` webhook — post-launch, NOT a blocker** (the manual SOP covers the obligation today).

- [ ] **🟡 In-app self-service deletion (post-launch — NOT a blocker; the manual SOP + PIECE-1 freeze cover the obligation today)** — the per-table spec below is already realized by the manual SOP; the remaining work is the in-app UI + the Clerk webhook trigger. Per the lawyer's per-table spec:
  - **HARD-DELETE:** `chat_history`, `audit_logs`, `user_feedback`, `user_profile` (the PHASE-E Pro context hash), `bug_reports`.
    - (`bug_reports` option: instead of full delete, **SET NULL on the email field** and keep the anonymized technical fields — note for the implementer.)
  - **DE-IDENTIFY/RETAIN 5yr (statutory):** `api_cost_log` → **SET NULL `user_id`** (rows kept); `user_usage` → **✅ design E: FREEZE via `deleted_at`** (retained in ORIGINAL form, hidden from all product logic — supersedes the old "sever `clerk_user_id`" idea, which was impossible since `clerk_user_id` is the PK). Lawful basis GDPR Art. 6(1)(c) / TW Business Accounting Act Art. 38. (The former FLAG #1 pseudonymize question is resolved by the freeze.)
  - **`shared_query`:** **SET NULL on `created_by`, KEEP the public page** (locked decision 2026-06-09; stated in Policy §8). (`anonymous_usage` is anon-keyed, not account-linked — n/a.)
  - **Triggers (recommended = all three):** in-app **"Delete account & data"** button (`DELETE /api/user/account`, Clerk-JWT) + a **history-only** option + a **Clerk `user.deleted` webhook** (`/api/webhooks/clerk`, svix-verified — needs `CLERK_WEBHOOK_SECRET`; closes the orphaned-rows gap when a user deletes via Clerk's own portal).
  - **Shared helper** `_hard_delete_user(db, user_id)` reused by all triggers (one table list to maintain). No schema/migration needed; the webhook needs the new env var.
- [x] **✅ MANUAL deletion SOP — DONE (v180, `61e25dc`–`0e03659`).** Lawyer-confirmed design-E runbook (`docs/manual-deletion-sop.md`): cancel-Dodo → hard-delete 5 tables → `api_cost_log` SET NULL → `user_usage` FREEZE (`deleted_at`) → `shared_query.created_by` SET NULL → Clerk dashboard reconcile → zh-TW completion email. Proven executable via `scripts/deletion_dryrun.py` (allow-list dev-only, rollback-only) — **dev dry-run 14/14**. The 30-day promise is keepable by hand now.
- **Discovered:** 2026-06-09 legal review. Related: BACKLOG "§4.3 deferred sub-needs" 需求4 (export/clear prefs) is the lighter in-app preference-clear; C is the full account/data erasure.

## §3.4 Privacy Policy — i18n-refactor + 16-language translation

- [ ] **§3.4 — localize `/privacy` to 16 languages.** **NO LONGER BLOCKED on the English master** (legal-reviewed English stopgap approved + shipped 2026-06-09, `bebe20e`). Still pending two things:
  - **(i) i18n-refactor:** `pages/privacy.tsx` is hardcoded English JSX → refactor to an i18n-driven page (extract the ~10 sections into the i18n bundle + `useLang`) before any translation. This is **more than pure i18n** (a page restructure).
  - **(ii) translation-confidence decision:** the 15 non-English versions are **LEGAL + medical** text — decide machine-translated vs human-reviewed (do NOT auto-trust). Ship with the lawyer's **"English version shall prevail"** disclaimer (already in the English page header).
  - Note: keep the "24h backup / 6h PITR" wording in sync with TECH_DEBT (d) — revise on a Neon paid-plan upgrade.
