# ARCHIVE.md — Vela Completed Work Log

Chronological log of shipped work. Newest first.

**Format**: `YYYY-MM-DD [TAG] Title — one-line summary (commit SHA)`

**Tags**:
- `[PRD §X.Y]` — feature work tied to PRD section
- `[bug]` — production bug fix
- `[tech-debt]` — pre-existing gap closure
- `[refactor]` — code health
- `[docs]` — documentation
- `[Phase 1A polish]` — pre-shipped Phase 1A items
- `[acceptance]` — acceptance protocol completion

When new entries are added: keep one-liner format, no detail. For full context, consult the commit message.

---

## 2026-05-27

- 2026-05-27 [theme C4] Body font Arial→Noto Sans (latin) via next/font/google; CJK unchanged; closes TECH_DEBT P3 (Arial override, discovered 2026-05-05)

---

## 2026-05-20

- `[docs]` PRD §3.1 v1.5 → v1.6 — §3.1 API endpoints contract: POST 403 error type upgrade_required → pro_required (unify existing extract-image free-user→Pro convention, overrides v1.5 E1); POST body slimmed to { user_context_hash, locale } (raw context never leaves device, aligns §0.3, server-recompute redundant with v1.5 self-repair). Ahead of §3.1 PHASE B. +4/-2 docs/PRD.md only. (603917f)

- `[docs]` PRD §3.1 v1.4 → v1.5 — User Context Schema audit integration. Integrates 2026-05-14 §3.1 audit decisions + findings (retrospective.md § 2) into PRD spec. 8 decisions resolved: E1 (POST free user → 403 upgrade_required, backend gate explicit), E2 (dual-trigger restore — sign-in passive + Settings manual), E3 (UPSERT idempotent + updated_at bump as 'last verified' semantic), E4 (10/hour rate limit via existing §6.3 RATE_LIMITED_USER), F1 (Option α — user_context_hash as 7th derived localStorage field), G3 (§3.2 Step 3 dual-write to vela_lang + vela_user_context.work_language), G4 (user_usage.plan_type authoritative, TECH_DEBT P2 tracked, no PRD change), G7 (role_category 4-bucket mapping clinical/research/student/other). 5 findings addressed: A (§2.0 analytics.ts silent loss — resolves on §3.1 PHASE C ship), F1 (§2.0.2 vs §3.1 inconsistency — single-line reciprocity pointer), G2 ('specialty dropdown' straw-man — reframed not deleted at 3 locations: §3.2 line 1002 + §A.2 line 2230 + degrade-gracefully principle line 97), G3 (§2.9 LangContext drift — dual-write spec added to §3.2 Step 3), G6 (migration 006_add_user_profile — schema anchored to filename in §3.1). Additional self-repair derivation rule (read-time hash mismatch → recompute + writeback, prevents §2.0 silent-loss anti-pattern repetition). Hash spec locked: SHA-256(filter_non_null([workplace, role, work_language]).join('|'))[:16], locale excluded. Sections touched: §3.1 (5 sub-blocks + revision header), §2.0.2 (1 line), §3.2 Step 3 + opening framing, §4.3 (new 需求 5), §A.2 (1 row reframe), line ~97 (1 parenthetical). Net +100/-13 lines. Spec reference for Phase 1A §3.1 implementation PHASE B/C/D. (bf446e3)

---

## 2026-05-19

- `[deploy]` Phase 0 production deploy completed — v164 from commit a63b304. First Vela production push covering Phase 0 §2.0-§2.9 + §4.5 PHASE A-D + §4.6 PHASE A-D. Two-cycle deploy: initial v163 from 0950157 → 🟡 HIGH OG image 404 discovered in PART C verification → fix-forward a63b304 → second deploy v164. All 🔴 CRITICAL ship gates verified PASS on v164: server health (/health 200, version 2.2.0), vector store loaded (690 docs), Clerk JWT auth (anon 403 on /api/share/create with "Missing token"), TEST_MODE inactive, landing page real content (16KB HTML), sitemap structure (index + main + explore + robots.txt with Allow: /), §2.7 Explain canonical case (K=6.8 mEq/L + Furosemide 40mg BID + eGFR 32 → 3 items with 🔴 Potassium high risk + 🟡 Furosemide/eGFR moderate + 2 clinical correlations Potassium↔eGFR + Potassium↔Furosemide + disclaimer + LOINC/RxNorm source chips), §2.8 Anonymous Trial Flow (6/8 quota modal with 3 CTAs Sign up free / Continue tomorrow / Go Pro $9.99), §2.9 multilingual response (ja query 高齢者の骨粗しょう症 → ja response with 5 PubMed citations, zh-TW UI complete throughout), §2.0 PostHog events firing (share_modal_opened / share_link_generated / share_link_copied / share_link_visited / share_revoked / research_completed / clicked button autocapture, identify alias from anon to clerk user_id correct). Pre-deploy: SHARE_CREATED_BY_SALT + VELA_PUBLIC_BASE_URL secrets added (triggered v162 reload); 1 orphan user_usage row cleaned (user_3B939OrkarbJWpfTT8nCi9kDJ1B with test_cust_c53dfaa8cd4b Dodo sandbox leftover from 2026-03-19, safety scan confirmed no broader pollution). Known remaining (deferred): /static/og ephemeral filesystem on machine restart (Phase 1A entry ADR — Fly volume vs R2/CDN decision), /explore index page 404 breadcrumb dead-link (Phase 0 post-deploy 1 week), Clerk publicMetadata.plan dormant dual-source vs user_usage.plan_type (Phase 1A §3.1 scope), Clerk user.deleted webhook gap (Phase 1A §3.1 scope). Deploy + verification ~2.5h hands-on; LinkedIn Post Inspector preview confirmed working post-OG-fix on share /q/-1C8ZqfFOqg. Full retrospective: see docs/retrospectives/phase-0-2026-05.md.

- `[fix 4.5]` OG image URL/path mismatch in StaticFiles mount — root cause: catch-all `app.mount("/", StaticFiles(directory="static"))` double-prefixes "static/" so URL /static/og/<id>.png resolved to filesystem static/static/og/<id>.png which doesn't exist. Discovered during PART C deploy verification when LinkedIn Post Inspector showed missing preview image. Fix: dedicated `app.mount("/static/og", StaticFiles(directory="static/og"))` registered ABOVE catch-all (~5 LoC); also plugged re-share idempotency hole by calling _generate_og_png() in existing-SharedQuery early-return branch (~4 LoC, inside try/except so a Pillow failure won't break API). Affects both share OG images (PHASE B render path) and landing /og-image.png. Unit tests: tests/services/test_og_image.py (3 cases — generate writes file, generate idempotent via mtime unchanged, /static/og/<id>.png 200 image/png via TestClient); 24/24 tests green (3 new + 21 existing providers). Verified post-deploy v164: curl /og-image.png 200 + image/png (55KB), curl /static/og/-1C8ZqfFOqg.png 200 + image/png (20KB freshly-generated), LinkedIn Post Inspector shows preview card with title + image. Ephemeral filesystem issue (production PNGs lost on machine restart / redeploy) acknowledged in commit message + deferred to Phase 1A entry. (a63b304)

- `[docs]` STATE.md — Phase 0 production shipped 2026-05-19. Phase line: "code-complete, awaiting production deploy" → "production shipped 2026-05-19 (v164, a63b304)". Current Focus rewrite for post-deploy state referencing all 🔴 CRITICAL ship gate verifications + OG image fix-forward. Next Up rewrite to 5-item queue: post-deploy [docs] batch (4 follow-up commits — ARCHIVE/retrospective/PRD status/TECH_DEBT+BACKLOG) / §4.6 PHASE E 4-week GSC indexing window (passive, started 2026-05-19) / §3.1 PRD revision v1.4→v1.5 (can parallel) / §3.1 implementation + §3.2 Onboarding Wizard (Phase 1A start, ~4d) / retrospective integration. (49309eb)

---

## 2026-05-14

- `[docs]` STATE.md Next Up reorder — §3.1 audit promoted to active, §4.6 PHASE E marked deferred-parallel. Drove same-day §3.1 User Context Schema audit (Phase 0 closeout → Phase 1A bridge framing at the time). Audit produced 7 sections of findings (A-J) including 3 critical surprises: analytics.ts silently lossy ~1 month (PostHog wrapper since §2.0 ship 2026-04-18 reads from empty localStorage, every event ships user_context_hash/work_language/locale = null), §2.9 LangContext drift G3 (implementation reads vela_lang directly instead of user_context.work_language per PRD spec — latent bug surfacing on §3.2 ship), G2 specialty dropdown straw-man (no migration needed, single-specialty UI never existed in codebase). Plus F1 PRD internal hash storage inconsistency (§2.0.2 says localStorage hash, §3.1 schema omits it), G4 plan_type dual-source (Clerk publicMetadata vs user_usage), G6 migration 006_add_user_profile not yet created. 10 PRD §3.1 revisions queued for v1.5 (audit Section H). 8 decisions taken on Open Questions: E1 (POST free user → 403 upgrade_required), E2 (GET endpoint sign-in transition + Settings restore button), E3 (UPSERT idempotent + updated_at bump), E4 (10/hour rate limit via existing mechanism), F1 (Option α — cache hash as 7th derived localStorage field), G3 (§3.2 Step 3 dual-write to vela_lang + vela_user_context.work_language), G4 (user_usage.plan_type authoritative, Clerk drift to TECH_DEBT P2), G7 (4-bucket role_category: clinical/research/student/other). All decisions fold into PRD v1.5; ADR 007 not opened (decision tradeoffs insufficient depth, ADR 007 reserved). Audit report preserved in chat verbatim (no repo artifact, precedent: §2.1 audit). Full findings + decisions: see docs/retrospectives/phase-0-2026-05.md. (03dcafd)

- `[docs]` STATE.md Next Up retighten — Phase 0 production deploy promoted to #1 per PRD v1.3 §二 NOTE ship gate sequence; §3.1 moved to Phase 1A entry. Corrected prior reorder (03dcafd) which placed §3.1 at #1 — but PRD v1.3 explicitly specifies ship gate sequence §2.7 → §4.5 → §4.6 → Phase 0 Retrospective with §3.1 as Phase 1A entry, not Phase 0 closeout. Drift introduced by ad-hoc "Phase 0 closeout + Phase 1A bridge" framing; corrected back to canonical PRD v1.3 sequence. Retrospective moved post-verification (vs pre-deploy default) so it can cover deploy + post-deploy verification lessons. Sets up the actual Phase 0 production deploy 5 days later. (0950157)

---

## 2026-05-13

- `[PRD §2.1]` Model Provider Refactor — all 5 sub-phases shipped (7 commits, 1 day, hit 4-5d v1.4 estimate). 9 backend files migrated from direct openai SDK instantiation + hardcoded model strings to Provider abstraction layer with 19 env-var-driven task-layer bindings. OpenAIProvider (all 9 capabilities) + GroqProvider (text-only, 7 capabilities) shipped; Phase 0 ship state remains 100% OpenAI defaults; Groq framework-ready, activation deferred to Phase 1B per ADR 006. Commit chain: 8f6c988 (doc sync v1.4 + ADR 005) → ddc2121 (PHASE A scaffolding + 21 unit tests) → 47248a5 (PHASE B 3 Low files: vector_store/entity_extractor/explain_service) → c5b61f6 (PHASE C 4 Medium files: guards/reranker/llm_judge/retriever) → b158aeb (PHASE D 2 High files: generator/server.py + live smoke 3/3 PASS) → d153126 ([chore] gitignore dev artifacts) → [SHA] (PHASE E 收口 + ADR 006 Phase 1B activation checklist). Acceptance: 21/21 unit tests pass, live smoke 3/3 PASS in PHASE D (Research SSE 519 chunks 23s / Verify 7.9s / Explain 20.6s), golden --smoke 41+/42 PASS (1 unrelated quality WARN E22), CLAUDE.md Rule 15 fully complied, §2.7 acceptance baseline (gpt-4.1 ExplainJudge) preserved. Behavioral side-effects: anon path now reads GENERATOR_FALLBACK_MODEL env var (value unchanged at gpt-4.1-mini); guards.py CLAUDE.md Rule 3 violation (sync OpenAI in async) fixed incidentally. Pre-Phase 1B blocker: cost_tracker.py model-price table needs Groq entries before any *_PROVIDER=groq flip (see ADR 006 Step 2). (8f6c988..[SHA])

---

## 2026-05-12

- `[PRD §4.6]` PHASE D — Breadcrumb + Category listing + Related queries + 3 PostHog events. Breadcrumb (Vela › Explore › {category} › {query}) inserted at top of /explore/{slug}; category segment links to new /explore/category/{category} listing route (registered BEFORE /explore/{slug} for path priority). render_category_listing() lists all published rows in a category (ORDER BY last_updated_at DESC), 404 when empty, 400 for invalid category slug. get_related_queries() picks up to 8 siblings with 3-tier priority: Tier 1 same hreflang_group (different locale, link_type='hreflang' + locale badge), Tier 2 same category + current locale (link_type='category'), Tier 3 same category + any locale (fallback). Section hidden when 0 related. New category_listing.jinja2 extends explore_base.jinja2; q_explore.jinja2 grows breadcrumb + related-queries section + inline PostHog event script. Three events fire via window.posthog.capture() with existence guard (no-op until init exposed to public templates — PHASE E candidate): explore_page_visited {slug, locale, referrer_domain, is_first_view via vela_visited_explores localStorage flag} on DOMContentLoaded; explore_to_query_clicked {slug, time_on_page_sec, scroll_depth} on .vela-cta-button click; explore_related_clicked {from_slug, to_slug, link_type} on .vela-related-card click via data-* attributes. explore_strings.py +3 new keys (category_listing_title / category_listing_empty / related_queries_locale_badge_fmt) × 16 locales. scripts/smoke_explore_phase_d.py — 20 assertions PASS. Known gap: /explore index page (breadcrumb 'Explore' link) returns 404 until PHASE E follow-up. (SHA pending)

---

## 2026-05-11

- `[PRD §4.6]` PHASE C — Content import CLI. New scripts/explore_cli.py with 6 subcommands (sync / list / publish / unpublish / archive / from-vela). Markdown frontmatter (YAML) → ExplorePage DB UPSERT, idempotent via md5 content hash. `from-vela` calls the Vela research pipeline in-process via TestClient (no uvicorn dep) and writes a draft markdown stub with status='draft' hardcoded (editorial gate, never auto-publishes). content/explore/.gitkeep + README.md scaffold the authoring directory. scripts/smoke_explore_phase_c.py — 27 assertions PASS covering sync INSERT/UPDATE/Unchanged/Errored, list, status transitions, validation errors (missing field / invalid slug / filename mismatch). Verified `list` against live Neon DB (2 dev-seed rows visible).
- `[PRD §4.6]` PHASE B — sitemap-explore.xml + hreflang missing-locale skip rule. New api/services/sitemap_explore.py (sitemaps.org-compliant XML generator with xhtml hreflang alternates per published sibling, draft/archived skipped). /sitemap-explore.xml FastAPI route registered (no rate limit, crawler-friendly). public/sitemap.xml converted from flat urlset to sitemapindex referencing public/sitemap-main.xml (original 6 static routes) + sitemap-explore.xml (dynamic). next.config.ts dev rewrites add /sitemap-explore.xml → backend. Sitemap <loc> uses ?locale={locale} uniformly so each <url> has unique loc aligned with xhtml:link href. scripts/smoke_explore_phase_b.py — 23 assertions PASS covering well-formed XML, namespaces, hreflang published-pair vs draft-sibling, HTML hreflang regression. robots.txt confirmed healthy (no /explore disallow, Sitemap directive intact).
- `[bug]` Dev seed script for §4.6 PHASE A — scripts/seed_explore_dev.py connects to DATABASE_URL (Neon Postgres) and idempotently UPSERTs 2 sample rows (en + zh-TW in hreflang_group='metformin-renal'). Required because the PHASE A smoke test seeded only its own temp SQLite, so live dev environment had no data. (ce2225a)
- `[bug]` Next.js dev rewrites — add /explore/:slug + /static/og/explore/ proxies for §4.6 PHASE A live testing. (d324389)
- `[PRD §4.6]` PHASE A — ExplorePage schema + /explore/{slug} routing (reuses §4.5 renderer). New migrations/005_add_explore_page.sql + ExplorePage SQLAlchemy model with composite PK (slug, locale) + api/services/explore_renderer.py reusing share_renderer helpers (parse_research_sections / _augment_citations / _markdown_to_html / _MARKER_BORDER_COLORS) + api/templates/explore_base.jinja2 + q_explore.jinja2 (team-content semantics: no "shared by" framing, breadcrumb + related-queries slots for PHASE D, hreflang siblings in <head>) + api/i18n/explore_strings.py (16 locales, en + zh-TW first-class) + /explore/{slug} route registered before Next.js catch-all with in-handler rate limit (60/min). 23 smoke assertions PASS. (bc171a1)

## 2026-05-08

- `[docs]` PRD §2.10.6 evidence tier classification (within-source 5-tier model — international guideline / systematic review / RCT / observational / survey) + BACKLOG dogfooding follow-ups (DailyMed entry sub-task / Citation ranking 5th test / Phase 1C Guideline ingestion entry) + TECH_DEBT [P3] components/Untitled stale backup file (9834d85)
- `[bug]` CitationPanel — remove credibility 5-star UI per external advisor dogfooding feedback (2026-05-08). 5-star + "Credibility:" label removed from frontend CitationPanel + server-side share_renderer.py / q_public.jinja2 / q_base.jinja2. Backend Citation.credibility field preserved for Phase 1B evidence-tier classification repurpose. (211d9f7)
- `[PRD §4.5]` PHASE E.1 — Documentation closeout (pre-production-deploy): PRD §4.5 status marker bumped to 🟡 IMPLEMENTATION COMPLETE — DEPLOY PENDING (2026-05-08); new "Production Deploy Checklist (PHASE E.2)" subsection (14 checkboxes across 3 groups); STATE.md / BACKLOG.md sync. PHASE E.2 deferred to post-production-deploy. (f495a41)
- `[PRD §4.5]` PHASE D — Share clauses (en-only) added to /terms § 8 Public Sharing + /privacy § 7 Public Sharing per 需求 9 spec. Navbar gear-dropdown menu item label "Settings / 設定" → "Manage shares / 管理分享" (16-locale rename in `utils/i18n-share.ts`: `settingsNavLink` → `navbarManageSharesMenuItem`). PRD §4.5 (2026-05-08 修訂) inline note documenting the menu label decision. New P2 TECH_DEBT entry: /terms + /privacy en-only — 16-locale i18n retrofit pending before non-en GTM expansion. "Last updated" bumped to 2026-05-08 in both legal pages.
- `[PRD §4.5]` PHASE C — Settings 「我的分享」 tab — new `pages/settings.tsx` + tab nav scaffolding (extensible) + `components/MySharesTab.tsx` (list / copy / revoke with optimistic UI / PostHog events) + Navbar gear-dropdown Settings entry + 7 new i18n keys × 16 locales. Pure frontend; consumes existing PHASE B endpoints. Intl.RelativeTimeFormat for time-ago (no custom i18n). (6f7a154)

---

## 2026-05-07

- `[PRD §4.5]` UX polish 3/3 — PRD §4.5 inline (2026-05-06 修訂) notes + TECH_DEBT entries (Arial body font / native-speaker review / cost_report_7d / dotenv loader); priority-tier ladder extended with P3 (768dc0b)
- `[PRD §4.5]` UX polish 2.5 — Navbar ShareButton color tone-down (coral → neutral) + i18n full 16-locale rollout (b378659)
- `[PRD §4.5]` UX polish 2/3 — ShareButton to Navbar via new ShareContext + ShareModal QR removal + qrcode.react dep dropped + toast color brand-aligned (ca571ce)
- `[PRD §4.5]` UX polish 1/3 — public page visual alignment to main site (dark gradient, evidence cards, hand-rolled CitationPanel HTML, coral CTA, dual disclaimer); parseResearchSections() Python port; markdown==3.6 dep added (a5da1c5)
- `[bug]` Verify short disclaimer missing i18n — backend `get_verify_disclaimer()` helper + 16-locale dict + handler wires localized string into all 3 VerifyResponse return points (30bd0b5)
- `[PRD §4.5]` Dev quality-of-life — Next.js rewrites for /q/* and /api/share/* (e042efc)
- `[docs]` BACKLOG WHO API integration entry → Phase 1C (4fe0d7b)
- `[docs]` PRD §2.10 source strategy + BACKLOG dogfooding/source-weight sub-tasks (92dbe9b)

---

## 2026-05-06

- `[PRD §4.5]` PHASE B Share API + Modal + sensitive detection + history button — 3 endpoints (create/revoke/list) + track-visit, PHIDetector mode='share' (NHI + name+age combos for zh-TW/en/ja), ShareButton/ShareModal mounted on research/verify/explain/history, /?from_share handler in pages/index.tsx, qrcode.react dep added, SHARE_CREATED_BY_SALT env var introduced

---

## 2026-04-30

- `[docs]` Doc reorganization Stage 2 structural — STATE.md / BACKLOG.md / ARCHIVE.md / TECH_DEBT.md split out from CLAUDE.md (this commit)
- `[docs]` Architecture extract from CLAUDE.md → docs/architecture.md (59002d1)
- `[docs]` Drift sync post § 2.7 結案 — PRD v1.2→v1.3, Phase 0 remaining (3fdeddc)
- `[docs]` § 2.7 結案 + M06 in Phase 0 status (dffd015)
- `[bug]` M06 ja schema_validation_failed — null value coercion via Layer 4 cleaner (a52bf9f)
- `[PRD §2.7 Step 8]` ExplainJudge integration into golden_dataset (Plan B-Modified) + 5 acceptance fixes + E29-E33 — 95.3% pass, hard floor 100% (fa80ff9)
- `[tech-debt]` TEST_MODE bypass for rate limit middleware — closes pre-existing infra gap surfaced during § 2.7 Step 8 (64c72f2)
- `[PRD §2.7 Step 7]` ExplainJudge class + explain_judge.md prompt — 7-dim structured evaluator, gpt-4.1, acceptance-only (c5b3a09)
- `[PRD §2.7 Step 4 follow-up]` Body language vs disclaimer language drift — resolved via Bug C fix (explain_system.md v3→v4 body_language_correct dim, integrated in Step 8 acceptance)
- `[PRD §2.7 Step 4 follow-up]` Risk tier conservative skew evaluation — Step 8 acceptance found no systematic bias (yellow >70% trigger condition not met)

## 2026-04-29

- `[PRD §2.7 Path 1 phase 2]` Banner + tooltip Bug 2 fix for limited-evidence sources (daaf4be)
- `[bug]` Path 1 RAG citation hallucination — 3-layer defense + Bug X1/X2/X3 fixes (bebf099)
- `[PRD §2.7 Step 4 follow-up]` Generic error UX — 6 error codes (empty_input, no_values_in_input, input_too_long, openai_api_error, schema_validation_failed, generic) (a8eb6e8)

## 2026-04-28

- `[PRD]` Bump v1.2 → v1.3 — added § 4.5 Share Answer + § 4.6 SEO Explore (06a9605)

## 2026-04-27

- `[PRD §2.7 Steps 1-6]` Explain 臨床推理強化 — 19 commits cd697d1..dd128e2 (production deploy)
- `[Phase 1A polish]` Verify completion-event telemetry — verify_completed/verify_failed events with severity_distribution + interaction_count (dd128e2)
- `[Phase 1A polish]` Research completion-event telemetry — research_completed/research_failed events with citation_count + evidence_distribution + used_fallback (6a53dfc)
- `[PRD §2.7 Step 6]` Explain completion-event telemetry — explain_completed/explain_failed events (e63c231)

## 2026-04-25

- `[docs]` CLAUDE.md align with FEATURE_AUDIT.md 2026-04-25 reality (05aa2bb)
- `[docs]` Refresh FEATURE_AUDIT.md to 2026-04-25 reality (389c05c)

## 2026-04-22

- `[PRD §2.8]` Anonymous Trial Flow Round 3 — AnonymousUpgradeCTA + tier super-property + alias on first signIn (24b1d79)
- `[PRD §2.8]` Round 2B — frontend anonymous dispatch for Research + Verify (a8877e9)
- `[PRD §2.8]` Round 2A — Clerk localhost sign-in pages + Navbar refactor (cc1e1c7)
- `[PRD §2.8]` Round 1 — backend infrastructure + integration (7a8c5a8)
- **Discovered Gap G1 resolved**: Anonymous Trial Flow gap (Landing Page promised "No account required to try" but Try-it-free redirected to Clerk sign-in). Decision Record `docs/decisions/001-anonymous-trial-flow.md`.

## 2026-04-21

- `[PRD §2.5 polish]` Landing Page i18n 16-language expansion (a22ce9f)
- `[docs]` Record Landing Page polish tech debt — placeholder i18n + Privacy simplification (1101dcc)

## 2026-04-20

- `[PRD §2.4]` Bug 回報浮動按鈕 — BugReportButton FAB + /api/bug-report + PHI cleaning + rate limit 5/hour, production verified user_id=user_3BQM... (380d11f, dfdef25, 11270a9)
- `[PRD §2.9]` Verify 輸出語言對齊 user locale — response_language variable + verify_system.md v2.1 + 7 languages i18n + UX polish + Chinese variant handling spread (b2250ca, ee055d4, f2533f4, c621e3b, e718ec8)

## 2026-04-19

- `[PRD §2.2 + §2.3]` Wire query_id to analytics + citation/feedback tracking (04aae40)
- `[PRD §2.2]` Emit query_id as first SSE event across research/verify/explain (1737683)

## 2026-04-18

- `[docs]` ADR 001 — Anonymous Trial Flow decision record (f7fd8aa, 1e22f0a)
- `[docs]` Convert PRD v1.2 to markdown (539586d)
- `[PRD §2.0]` PostHog analytics wrapper — utils/analytics.ts + AnalyticsAuthBridge, sign-out reset (dd210b9, 3876239)

## 2026-04-17

- `[PRD §2.5]` Landing Page SEO fix — isLoaded gate removed, JSON-LD in place, og-image v1.1 (e00d8ac)
- **Phase 0 started.**

---

For pre-2026-04-17 work (Phase pre-0 / project init / Pre-PRD-v1.2 era), consult `git log --before=2026-04-17` and the original commit messages.
