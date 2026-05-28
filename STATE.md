# STATE.md — Vela Current Development Focus

**Last updated**: 2026-05-29 (Stage 2 in-progress, local — see Next Up #1. Last prod deploy is still Stage 1 at fly v169 from 2026-05-27.)

## Phase

Phase 0 — production shipped 2026-05-19 (started 2026-04-17, deploy commit a63b304, v164)

## Current Focus

Phase 0 production deployed 2026-05-19 (v164, commit a63b304). All 🔴 CRITICAL ship gates passed: server health, vector store (690 docs), Clerk auth, anon share 403, §2.7 Explain canonical (K=6.8 case), §2.8 anon trial quota (6/8 modal), §2.9 multilingual response, §2.0 PostHog events. One 🟡 HIGH fix-forward landed: OG image URL/path mismatch in StaticFiles mount (commit a63b304).

Next focus: **landing/theme redesign Stage 2** — IN PROGRESS, local only (Steps 1–4b landed on branch `main`, 7 commits ahead of origin/main, NOT pushed, NOT deployed; production landing is still the Stage-1 dark-blue-ish design at fly v169). Step 5 (Settings panel redesign) is the only remaining Stage 2 code step before push + deploy. Full mid-progress snapshot in Next Up #1. Stage 1 (design-token groundwork: 12-token CSS-var system, feature 3-color collapse → brand-orange-only, Noto Sans body font, severity tokens) shipped to prod 2026-05-27 (fly v169, commits cc6eec6..0e5464d). After Stage 2 lands, **Stage 3** wires next-themes for full-site dark/light switching (Research/Verify/Explain/Dashboard all switchable). Then resume §3.1 PHASE C (frontend) → PHASE D (OnboardingWizard) → PHASE E (Settings) per the user's priority sequence. §3.1 PHASE B backend is DEPLOYED (2026-05-22 v167; migration 006 applied; endpoints live but dormant until PHASE C wires the frontend caller). §4.6 PHASE E 4-week GSC indexing window running in background.

Last shipped: Landing/theme redesign Stage 1 (2026-05-27 v169) + Blog feature (2026-05-25) + §3.1 PHASE B backend (2026-05-22 v167) + Phase 0 production deploy (2026-05-19).

## Next Up (landing/theme redesign Stage 2 → Stage 3 → §3.1 frontend resumption)

1. **Landing/theme redesign Stage 2 — landing visual redesign + light theme** — IN PROGRESS, local only.

   > ⚠️ **MID-PROGRESS SNAPSHOT (2026-05-29) — Steps 1–4b are LOCAL ONLY, NOT pushed, NOT deployed.** Branch `main` is **7 commits ahead of origin/main**. Production still serves the Stage-1 dark-blue-ish landing at fly v169 (2026-05-27). Step 5 (Settings panel redesign) is the only remaining Stage 2 code step. After Step 5: `git push` + `.\deploy.ps1` + the proper Stage 2 close STATE update (with new fly version + full commit range moved into Recently Shipped) happens then, NOT now.
   >
   > **Local commits, in order:**
   > 1. `e8d0cfe` [theme] add light theme token block to globals.css (dormant) — Step 1
   > 2. `78540e3` [landing] Stage 2 Step 2 — light hero + real input (no-op) + neutral typewriter
   > 3. `ea87672` [landing] Stage 2 Step 3 — wire hero input → /research ?q= auto-run
   > 4. `0b0e1fe` [landing] Stage 2 Step 3 hotfix — typewriter overlay pointer-events-none (make input typeable)
   > 5. `ff58d09` [landing] Stage 2 Step 4a — move CTA + value-props into light zone
   > 6. `ca6dede` [landing] Stage 2 Step 4b — convert below-fold to light, eliminate seam, enlarge ProductShowcase
   > 7. `7c2f113` [docs] BACKLOG — landing copy i18n alignment follow-ups (hero + Research mockup)
   >
   > **State of the landing now (local working tree):** continuous warm-orange light surface from hero top to footer bottom, no dark seam anywhere. Real typeable hero input wired to `/research?q=` auto-run, verified end-to-end (single POST per submission, correct anon-quota accounting, URL cleans via `router.replace` so refresh doesn't re-trigger). ProductShowcase enlarged (max-width 780 → 960px, p-4 → p-5, rounded-xl → rounded-2xl) with semi-white cards `rgba(255,255,255,0.55)` matching the value-prop card family. Gradient: `linear-gradient(180deg, #ffffff 0%, #fff3ec 30%, #ffd9c4 60%, #ffd9c4 100%)` — warm peaks ~60% and plateaus through showcase/privacy/footer. Andrew visually verified Steps 2 / 3 / 3-hotfix / 4a / 4b in `npm run dev`.
   >
   > **Remaining Stage 2 code work:** Step 5 — Settings panel redesign (Navbar gear dropdown). Theme toggle as 3-card light/dark/system control (DEFAULT light) — **COSMETIC ONLY this stage**, will be wired to `next-themes` in Stage 3. Language dropdown replacing the cramped `LanguageSwitcher` 2-col grid. Keep Pro plan / credits bar / Manage shares / subscription rows.
   >
   > **Two deferred i18n follow-ups recorded in BACKLOG.md** (commit `7c2f113`): hero copy not aligned to STATE.md locked spec (current `landingContent.tagline` / `.subtitle` resolve to different strings than the locked title "Ask in your language." + locked subtitle); ProductShowcase Research mockup query drift (current `t.mockupResearchQuery` doesn't match locked "Metformin + CKD eGFR≥30"; Verify and Explain cards already aligned). Both are 16-locale content edits in the i18n bundle (Rule 16), non-blocking. Best done together as one "[i18n] landing copy alignment" pass alongside or before Stage 2 push (note: i18n strings are bundled into the build, so the pass WILL trigger a redeploy — unlike blog content authoring).

   Locked plan + design decisions (recorded so a fresh session can resume without re-deriving):
   - **First viewport — lovable.dev-style minimal**: small top-left logo (use real `coral_logo.png`, NOT floating/animated) + "Vela" wordmark; short title "Ask in your language."; subtitle "Evidence-cited medical answers from PubMed and the FDA, answered in your language. No account needed to try."; a REAL typeable input box (convert the current display-only `TypewriterPrompt` at `pages/index.tsx:26-69` into a real input) with circular orange up-arrow send button; "See how Vela works" scroll hint. Everything else below the fold.
   - **Background**: LINEAR gradient white → warm-orange (`#ffffff → #fff3ec → #ffd9c4`), calm/restrained (medical credibility) — NOT a saturated radial (user rejected that). This is the LIGHT theme.
   - **Hero input behavior**: Enter → navigate to `/research?q=<query>` and AUTO-RUN it (anonymous trial, 8/day). Fixed to Research mode on landing (mode-switch happens inside app). The `?q=` auto-run needs adding to `pages/research.tsx` (~30-50 lines: `useRouter` + extract `executeQuery` from `handleSubmit` + `useEffect` on `router.query.q` guarded by `isReady` + `router.replace` to clean URL). `research.tsx` currently has ZERO router/query infra — this is net-new but small.
   - **Below the fold**: enlarged `ProductShowcase` cards showing REAL answer snippets (Research: Metformin+CKD eGFR≥30; Verify: Warfarin+Aspirin Major interaction; Explain: TSH 12.5 above-normal) + value props (Multilingual / Verified sources / No account) + privacy 3-checks. Blog section DEFERRED until real articles exist (prod `blog_post` table is empty).
   - **Settings panel redesign** (Navbar gear dropdown): theme toggle (light / dark / system, DEFAULT light) as 3-card control + language as a clean dropdown (replacing the cramped 2-col grid `LanguageSwitcher`) + keep Pro plan / credits bar / Manage shares / subscription rows.
   - **Light theme implementation**: add a `:root` (or `.light`) block to `styles/globals.css` with light values for the 12 tokens (Stage 1 only filled `.dark`). Flipping the token block enables light mode — no per-component edits needed (the token architecture was built for this).
2. **Landing/theme redesign Stage 3 — full-site dark/light theme switching** — after Stage 2. Locked decisions:
   - Install `next-themes` (decided over self-built `ThemeContext`: theme-flash handling + static-export compatible + system-preference detection).
   - Remove the hardcoded `className="dark"` on `<Html>` in `pages/_document.tsx` (C1 hardcoded it; `next-themes` will own the class). Wire the theme toggle in Settings to `next-themes` `useTheme()`. App pages (Research / Verify / Explain / Dashboard) ALSO switchable (user chose full-site theming, not just landing).
   - Tailwind already `darkMode:'class'`; token CSS vars already split `.dark` — `next-themes` swaps the class on `<html>`, both `.dark` and `:root`/`.light` values resolve automatically.
3. **Long-tail color cleanup** (parallel, non-blocking) — `CitationPanel` source chips + Explain code-system chips intentionally NOT tokenized in Stage 1; future small commit to finish the migration.
4. **Blog content authoring follow-up** (parallel, non-blocking) — prod `blog_post` table ships EMPTY; only the `content/blog/asian-medical-ai-playbook.en.md` sample exists (PHASE B). Content authoring task (not code): edit `content/blog/*.md` → `DATABASE_URL=<neon-prod-url> python scripts/blog_cli.py sync`. NO redeploy needed.
5. **§4.6 PHASE E 4-week GSC indexing window** — passive, monitored weekly. Started 2026-05-19 with production deploy. `/explore` index page follow-up can land during this window.
6. **§3.1 PHASE C — frontend hook + LangContext write-through + analytics.ts writer** — wire the writer for `user_context_hash` localStorage (resolves §2.0 silent-loss Finding A from retrospective.md § 2), the §3.2-Step-3 dual-write to `vela_lang` + `vela_user_context.work_language` (G3 decision), and the POST call to `/api/user/context/hash` for Pro users on context change. Spec: PRD §3.1 v1.5+v1.6 (bf446e3 + 603917f). Estimated ~1d. **Queued AFTER Stage 2/3 land.**
7. **§3.1 PHASE D — `OnboardingWizard.tsx` (§3.2 three-step flow)** — distinct from existing `OnboardingOverlay.tsx`. Spec: PRD §3.2. Estimated ~1.5d.
8. **§3.1 PHASE E — Settings §4.3 tab** — including 需求 5 dual-trigger restore (sign-in passive + Settings button), `role_category` derivation in PostHog identify, §3.3 basic examples. Spec: PRD §4.3 v1.5. Estimated ~1d. Note: Stage 2 already redesigns the Settings panel chrome; §3.1 PHASE E adds the §4.3 tab content inside the new chrome.
9. **Deploy batch for §3.1 C/D/E** — single prod deploy after PHASE E lands. PHASE B already deployed (v167, 2026-05-22, migration 006 applied); future §3.1 migrations (007 was taken by `blog_post`; `schema_versions` per TECH_DEBT + any `user_profile` schema extension would claim 008+) still need manual `psql -f` before their deploy — no auto-migrate runner.
10. **Phase 0 Retrospective integration into Phase 1A planning** — retrospective.md complete (de4e7d4); surface findings (Clerk publicMetadata dormant, user.deleted webhook gap, OG image ephemeral fs, 5 dogfooding nuance issues) during #6–#8 implementation. No standalone deliverable, embedded in PHASE C/D/E work.

## Completed: §2.1 Model Provider Refactor (2026-05-13)

✅ **COMPLETE** — 7 commits, 1 day, 4-5d v1.4 estimate hit.

- 9/9 backend files migrated through Provider abstraction
- 21/21 unit tests green (tests/providers/test_factory_swap.py)
- Live smoke verified all 3 production surfaces in PHASE D
  (Research SSE 519 chunks 23s / Verify 7.9s / Explain 20.6s)
- Phase 0 ship state: 100% OpenAI defaults preserved
- Groq framework-ready; activation procedure in ADR 006
- §2.7 acceptance baseline (gpt-4.1 ExplainJudge) preserved

See ARCHIVE.md 2026-05-13 entry for full commit list + acceptance.

## Phase 1B preview (per advisor discussion + ADR 003+004)

Week 4-8 work queue (post Phase 0 Retrospective):

- **Week 4**: Verify 強制英文 (ADR 003) + system prompt polish — 2-2.5 days
- **Week 4-5**: DailyMed API — 2-3 days
- **Week 5-6**: 在地差異提示 Tier 1 6國 — 6-7 days
- **Week 7**: Anonymous Trial Flow polish — 2 days
- **Week 7-8**: Phase 1B integration test + polish + citation retrieval ranking evaluation — 2-3 days

Detail: see BACKLOG.md Phase 1B section.

## Active Acceptance Protocols

None active. § 2.7 Step 8 acceptance protocol completed 2026-04-30 (commits c5b3a09, 64c72f2, fa80ff9, a52bf9f, dffd015).

## Blockers

None known.

## Recently Shipped (last 7 days)

- **2026-05-27** [theme] Landing/theme redesign **Stage 1** — design-token refactor — **DEPLOYED to prod 2026-05-27 (fly v169)**. Groundwork for Stage 2 (landing visual redesign) + Stage 3 (full-site dark/light switching). 6 commits (cc6eec6..0e5464d): C1 `bfb6295` scaffold dark-theme token system (`tailwind.config` `darkMode:'class'` + CSS vars under `.dark` + `backgroundImage.app-bg` + `fontFamily.sans`); C2a `7f5ec4d` migrate `bg-gradient` consumers to `bg-app-bg` token (+ 3 `#0f2040` modals → `bg-bg-2`); C2b `b5c7771` migrate white-base alpha consumers to text / card tokens (+ opacity steps 4/6/7/8/12); C3 `fe11e97` collapse feature accents (verify-blue, explain-green) to neutral — brand orange kept as SOLE accent (logo / CTA / links / spinner / active-nav); features now distinguished by icon + label, not color; C4 `e0a6ca2` swap body font Arial → Noto Sans via `next/font/google` (latin subset; CJK via system "Noto Sans CJK TC" fallback matching Jinja2); closes TECH_DEBT P3 Arial entry; C5 `0e5464d` tokenize severity / semantic colors → `success` / `warning` / `danger` + 2 NEW tokens `info` (`#60a5fa`, Minor severity) + `danger-soft` (`#fca5a5`, dark-bg error text); amber fully tokenized to `warning` (no amber residual). Net result: a **12-token CSS-var system** (10 from C1 + 2 from C5), all 58 scattered hex/rgba semantic consumers migrated, feature 3-colors collapsed to neutral, Noto Sans body font, severity colors canonicalized. Migration: NONE (pure frontend; no DB change). Verified on prod + dev: feature accents neutral, brand orange preserved, CJK unchanged. **NOTE (prod-true as of fly v169 2026-05-27; partially obsolete on local `main` as of 2026-05-29):** the landing in PRODUCTION is still the OLD dark-blue design — the warm-orange gradient redesign is Stage 2 (locked plan in Next Up #1). The token architecture was built so flipping the light-theme `:root` token block in Stage 2 enables light mode with no per-component edits. **Update 2026-05-29:** Stage 2 Steps 1–4b have since landed LOCALLY (7 commits ahead of origin/main, not pushed); production still serves this Stage-1 state. Step 5 is the remaining Stage 2 code step before push + deploy. See Next Up #1 mid-progress snapshot.
- **2026-05-25** [blog] Feature shipped to prod — DB-backed Jinja2 blog at `/blog` (list) + `/blog/{slug}` (post, BlogPosting+FAQPage JSON-LD), content CLI (`scripts/blog_cli.py` sync/list against DATABASE_URL), theme-color Pillow auto-cover-images at `static/og/blog/`, `/sitemap-blog.xml`, and site-wide `/llms.txt` for GEO. Migration 007 (`blog_post` table, 13 columns, composite PK slug+locale) applied to Neon prod (neondb production branch via Neon SQL Editor). Fly deploy verified clean: GET /blog 200, GET /llms.txt 200, GET /sitemap-blog.xml 200, GET /blog/{slug} 404 for un-synced content (correct — no rows yet). 4 commits + 1 docs reconciliation: PHASE A 12328e5 (table + renderer + single-post route + BlogPosting+FAQPage JSON-LD), PHASE B 177c719 (blog_cli sync/list + content/blog + sample post), PHASE C 23cc704 (list page + theme-color covers + sitemap), PHASE D 2e5eb34 (site-wide /llms.txt), plus 9326a83 (chat-history privacy reconciliation: PRD §6.4/§2.8 vs shipped behavior; public privacy.tsx was already honest, internal docs were stale + contradictory — now aligned). **NOTE**: prod `blog_post` table is currently empty — content authoring pending (edit `content/blog/*.md` → `blog_cli.py sync` against prod Neon; no redeploy needed for new posts).
- **2026-05-22** [PRD 3.1] PHASE B — **DEPLOYED to production v167 2026-05-22** (migration 006 applied to Neon prod via Neon SQL Editor; 21645dd + 2d714fd; endpoints live, dormant until PHASE C wires the frontend). Two commits: migration 006 + UserProfile model (21645dd), and POST/GET /api/user/context/hash endpoints + tests (2d714fd). Pro-gated via user_usage.plan_type (G4); atomic UPSERT via pg_insert.on_conflict_do_update with explicit server-side func.now() at both INSERT and on-conflict paths (E3 "last verified"). Rate-limited 10/hour/IP (POST + GET share the bucket per review decision). 31/31 unit tests green (4 new model tests + 27 existing). Endpoint-level TestClient tests deferred per the cp950 import-crash workaround documented in `tests/models/test_user_profile.py`. Schema verified post-deploy: 5 columns, user_id PK, hash NOT NULL, locale nullable, both timestamptz default now(). Server startup clean in fly logs.
- **2026-05-20** [docs] PRD §3.1 v1.5 → v1.6 — POST 403 pro_required (overrides E1) + POST body hash-only (raw never leaves device). Ahead of §3.1 PHASE B. (603917f)
- **2026-05-20** [docs] PRD §3.1 v1.5 — User Context Schema audit integration (bf446e3). Integrates 8 audit decisions (E1–E4, F1, G3, G4, G7) + 5 findings (A, F1, G2, G3, G6) + self-repair derivation rule into §3.1 spec. Cross-section additions: §2.0.2 reciprocity pointer, §3.2 Step 3 dual-write spec, §4.3 需求 5 dual-trigger restore. +100/-13 lines, scope-tight to §3.1 ecosystem.
- **2026-05-19** [docs] CLAUDE.md Rule 17 (test intent) + Rule 18 (fail loud) appended (27572c8)
- **2026-05-19** [docs] TECH_DEBT — Research WARN pattern from 2026-05-19 golden eval (69e2cd0)
- **2026-05-19** [docs] STATE.md drift fix — Next Up #1 removed, #2-5 renumbered (bd7b22f)
- **2026-05-19** [docs] TECH_DEBT + BACKLOG — Phase 0 deploy retrospective follow-ups (a155c4a)
- **2026-05-19** [docs] PRD §4.5 + §4.6 status → ✅ SHIPPED (3c48433)
- **2026-05-19** [docs] docs/retrospectives/phase-0-2026-05.md — 346 lines (de4e7d4)
- **2026-05-19** [docs] ARCHIVE.md Phase 0 entries + 2026-05-14 audit-planning (07b2c0a)
- **2026-05-19** [docs] STATE.md Phase 0 production shipped marker (49309eb)
- **2026-05-19** [deploy] Phase 0 production deploy completed — v164 from a63b304 ✅ SHIPPED
- **2026-05-19** [fix 4.5] OG image URL/path mismatch in StaticFiles mount (a63b304)

For older work see ARCHIVE.md.

## Pointer to Other Docs

- **Active rules + workflow**: CLAUDE.md
- **Open future tasks**: BACKLOG.md
- **Completed work log**: ARCHIVE.md
- **Tech debt entries**: TECH_DEBT.md
- **Spec**: docs/PRD.md (v1.3)
- **Architecture**: docs/architecture.md
- **ADRs**: docs/decisions/
