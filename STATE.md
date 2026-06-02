# STATE.md — Vela Current Development Focus

**Last updated**: 2026-06-02 (Stage 2 + Stage 4 + Step 5 + Stage 5 **DEPLOYED to prod as fly v170** at 2026-06-02 04:16 UTC; Andrew verified Stage 4+5 on prod. Git push to origin/main still pending — batched with Stage 3 or separate (Andrew's call). Next: Stage 3.)

## Phase

Phase 0 — production shipped 2026-05-19 (started 2026-04-17, deploy commit a63b304, v164)

## Current Focus

Phase 0 production deployed 2026-05-19 (v164, commit a63b304). All 🔴 CRITICAL ship gates passed: server health, vector store (690 docs), Clerk auth, anon share 403, §2.7 Explain canonical (K=6.8 case), §2.8 anon trial quota (6/8 modal), §2.9 multilingual response, §2.0 PostHog events. One 🟡 HIGH fix-forward landed: OG image URL/path mismatch in StaticFiles mount (commit a63b304).

Next focus: **Stage 3** (full-site dark/light theme switching). The landing/composer redesign is now **DEPLOYED to prod (fly v170, 2026-06-02)** — **Stage 2** (light theme token block + warm light hero + `?q=` auto-run + full light-zone), **Stage 4** (single-fold radial-gradient hero + chips + 3 cards), **Step 5** (Navbar gear dropdown redesign), and **Stage 5** (Vela Composer: cards removed, in-input mode selector, cross-page `?prefill=` protocol, dead i18n cleanup) all landed on branch `main` (range `e8d0cfe..6976ec6`) and **deployed as fly v170 (2026-06-02 04:16 UTC)**, superseding the Stage-1 landing at v169 (2026-05-27, commits cc6eec6..0e5464d). Andrew verified Stage 4+5 on prod (5 scenarios + 4 spot checks); the Theme toggle is cosmetic-only as designed (Stage 3 wires it to next-themes). Git push to origin/main is pending (Andrew's call). Total acceptance done, so **Stage 3** starts immediately — no metrics waiting period (Andrew confirmed). Then resume §3.1 PHASE C (frontend) → PHASE D (OnboardingWizard) → PHASE E (Settings) per the user's priority sequence. §3.1 PHASE B backend is DEPLOYED (2026-05-22 v167; migration 006 applied; endpoints live but dormant until PHASE C wires the frontend caller). §4.6 PHASE E 4-week GSC indexing window running in background.

Last shipped: Landing/composer redesign Stage 2 + Stage 4 + Step 5 + Stage 5 — **DEPLOYED to prod 2026-06-02 (fly v170)**, 24 commits (`e8d0cfe..6976ec6`). Prior deploys: Landing/theme Stage 1 (2026-05-27 v169) + Blog feature (2026-05-25) + §3.1 PHASE B backend (2026-05-22 v167) + Phase 0 production deploy (2026-05-19).

## Next Up (push + deploy → Stage 3 full-site theming → §3.1 frontend resumption)

1. **Landing/theme redesign Stage 3 — full-site dark/light theme switching** — **starts immediately after push + deploy + total acceptance** (no metrics waiting period; Andrew confirmed). Sub-stages:
   - **3.1** — Install `next-themes` (decided over self-built `ThemeContext`: theme-flash handling + static-export compatible + system-preference detection) and remove the hardcoded `className="dark"` on `<Html>` in `pages/_document.tsx` (C1 hardcoded it; `next-themes` will own the class).
   - **3.2** — Wire the Step 5 theme toggle (currently COSMETIC) to `next-themes` `useTheme()` so it actually switches the theme.
   - **3.3** — Dashboard light-theme audit.
   - **3.4** — Research / Verify / Explain / Blog / History light-theme audit (user chose full-site theming, not just landing).
   - **3.5** — Theme default decision (light / dark / system).
   - Infra already in place: Tailwind `darkMode:'class'`; token CSS vars split `.dark` vs `:root`/`.light` (Stage 2 filled the light block) — `next-themes` swaps the `<html>` class and both resolve automatically.
2. **Long-tail color cleanup** (parallel, non-blocking) — `CitationPanel` source chips + Explain code-system chips intentionally NOT tokenized in Stage 1; future small commit to finish the migration.
3. **Blog content authoring follow-up** (parallel, non-blocking) — prod `blog_post` table ships EMPTY; only the `content/blog/asian-medical-ai-playbook.en.md` sample exists (PHASE B). Content authoring task (not code): edit `content/blog/*.md` → `DATABASE_URL=<neon-prod-url> python scripts/blog_cli.py sync`. NO redeploy needed.
4. **§4.6 PHASE E 4-week GSC indexing window** — passive, monitored weekly. Started 2026-05-19 with production deploy. `/explore` index page follow-up can land during this window.
5. **§3.1 PHASE C — frontend hook + LangContext write-through + analytics.ts writer** — wire the writer for `user_context_hash` localStorage (resolves §2.0 silent-loss Finding A from retrospective.md § 2), the §3.2-Step-3 dual-write to `vela_lang` + `vela_user_context.work_language` (G3 decision), and the POST call to `/api/user/context/hash` for Pro users on context change. Spec: PRD §3.1 v1.5+v1.6 (bf446e3 + 603917f). Estimated ~1d. **Queued AFTER Stage 3 lands.**
6. **§3.1 PHASE D — `OnboardingWizard.tsx` (§3.2 three-step flow)** — distinct from existing `OnboardingOverlay.tsx`. Spec: PRD §3.2. Estimated ~1.5d.
7. **§3.1 PHASE E — Settings §4.3 tab** — including 需求 5 dual-trigger restore (sign-in passive + Settings button), `role_category` derivation in PostHog identify, §3.3 basic examples. Spec: PRD §4.3 v1.5. Estimated ~1d. Note: Stage 2 already redesigns the Settings panel chrome; §3.1 PHASE E adds the §4.3 tab content inside the new chrome.
8. **Deploy batch for §3.1 C/D/E** — single prod deploy after PHASE E lands. PHASE B already deployed (v167, 2026-05-22, migration 006 applied); future §3.1 migrations (007 was taken by `blog_post`; `schema_versions` per TECH_DEBT + any `user_profile` schema extension would claim 008+) still need manual `psql -f` before their deploy — no auto-migrate runner.
9. **Phase 0 Retrospective integration into Phase 1A planning** — retrospective.md complete (de4e7d4); surface findings (Clerk publicMetadata dormant, user.deleted webhook gap, OG image ephemeral fs, 5 dogfooding nuance issues) during #6–#8 implementation. No standalone deliverable, embedded in PHASE C/D/E work.

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

- **2026-06-02** [landing/theme] **Stage 2 + Stage 4 + Step 5 + Stage 5 — landing/composer redesign** — **DEPLOYED to prod 2026-06-02 04:16 UTC (fly v170)**. 24 commits (`e8d0cfe..6976ec6`). Transforms the landing from the Stage-1 dark-blue design into a warm light single-fold composer. Migration: NONE (pure frontend); `npm run build` clean at each step. Andrew verified Stage 4+5 on prod (5 scenarios + 4 spot checks all passed); the Theme toggle is cosmetic-only as designed (Stage 3 wires it to next-themes). Supersedes the Stage-1 landing (v169) in production. (Git push to origin/main pending — Andrew's call.)
  - **Stage 2 — visual redesign + light theme:** added the light-theme token block to `globals.css` (the `:root`/`.light` half of the 12-token system Stage 1 only filled for `.dark`); warm light hero with a real typeable input; hero input wired to `/research?q=` AUTO-RUN (net-new router/query infra in `research.tsx`: `useRouter` + `executeQuery` extraction + `isReady`-guarded `useEffect` + `router.replace` one-shot URL clean); neutral typewriter overlay (`pointer-events-none` so the input stays typeable); below-fold converted to the continuous light zone (no dark seam).
  - **Stage 4 — single-fold hero:** Perplexity-style single-viewport hero on a radial warm gradient centered on the input; 3 suggestion chips (polished states + a11y); 3 feature cards. *(Cards were REPLACED in Stage 5 — see below.)*
  - **Step 5 — Navbar settings redesign:** gear dropdown with a Theme 3-card control (light/dark/system, DEFAULT light — **COSMETIC this batch**, wired to `next-themes` in Stage 3) + a Language dropdown replacing the cramped 2-col `LanguageSwitcher`; Pro/credits/shares/subscription rows kept. Shared `SettingsControls` extracted; an anon-trimmed top-right settings gear added to the landing (+ mobile-overflow hotfix: absolute → fixed positioning).
  - **Stage 5 — Vela Composer redesign:** the 3 feature cards REMOVED; a Claude-style in-input **mode selector** (Research/Verify/Explain with C-short descriptions + Pro badge on Explain) added at the input's bottom-right next to the send button; submit routes by mode — Research → `/research?q=` (auto-run), Verify → `/verify?prefill=`, Explain → `/explain?prefill=`. Cross-page **`?prefill=` receiver protocol** added to `verify.tsx` + `explain.tsx` (mirrors Research's one-shot consume, no auto-run; anon Explain still hits the lock screen). Redundant footer `LanguageSwitcher` removed (language now lives in the gear).
  - **Dead i18n cleanup (PARTIAL):** S5.2 removed the referenced-but-dead `tryResearch/tryVerify/tryExplain` cta keys + the 8 `mockup*` keys across all 16 locales (interface + locales) and added 3 `composerModeDesc{Research,Verify,Explain}` keys × 16 locales (48 cells). The BACKLOG "Dead landing i18n keys cleanup" item (98ad3ea) is now **partially resolved** — the `try*`/`mockup*` portion is DONE; the remaining "fully unused" candidates (`seeHow`, `socialProof`, `seePricing`, `ctaPrimary`, `valueProp.*`, `privacyTitle`) still need a dedicated verification + cleanup pass. ⚠️ That item also needs re-scoping: `privacyPolicyLink` is NOT dead — `LandingSettingsDropdown` actively uses it.
- **2026-05-27** [theme] Landing/theme redesign **Stage 1** — design-token refactor — **DEPLOYED to prod 2026-05-27 (fly v169)**. Groundwork for Stage 2 (landing visual redesign) + Stage 3 (full-site dark/light switching). 6 commits (cc6eec6..0e5464d): C1 `bfb6295` scaffold dark-theme token system (`tailwind.config` `darkMode:'class'` + CSS vars under `.dark` + `backgroundImage.app-bg` + `fontFamily.sans`); C2a `7f5ec4d` migrate `bg-gradient` consumers to `bg-app-bg` token (+ 3 `#0f2040` modals → `bg-bg-2`); C2b `b5c7771` migrate white-base alpha consumers to text / card tokens (+ opacity steps 4/6/7/8/12); C3 `fe11e97` collapse feature accents (verify-blue, explain-green) to neutral — brand orange kept as SOLE accent (logo / CTA / links / spinner / active-nav); features now distinguished by icon + label, not color; C4 `e0a6ca2` swap body font Arial → Noto Sans via `next/font/google` (latin subset; CJK via system "Noto Sans CJK TC" fallback matching Jinja2); closes TECH_DEBT P3 Arial entry; C5 `0e5464d` tokenize severity / semantic colors → `success` / `warning` / `danger` + 2 NEW tokens `info` (`#60a5fa`, Minor severity) + `danger-soft` (`#fca5a5`, dark-bg error text); amber fully tokenized to `warning` (no amber residual). Net result: a **12-token CSS-var system** (10 from C1 + 2 from C5), all 58 scattered hex/rgba semantic consumers migrated, feature 3-colors collapsed to neutral, Noto Sans body font, severity colors canonicalized. Migration: NONE (pure frontend; no DB change). Verified on prod + dev: feature accents neutral, brand orange preserved, CJK unchanged. **NOTE (prod-true as of fly v169 2026-05-27; partially obsolete on local `main` as of 2026-05-29):** the landing in PRODUCTION is still the OLD dark-blue design — the warm-orange gradient redesign is Stage 2 (locked plan in Next Up #1). The token architecture was built so flipping the light-theme `:root` token block in Stage 2 enables light mode with no per-component edits. **Update 2026-06-02:** Stage 2 has since fully shipped locally, along with Stage 4 + Step 5 + Stage 5 (24 commits ahead of origin/main, not pushed; production still serves this Stage-1 state until the batch deploys). See the 2026-06-02 Recently Shipped entry above.
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
