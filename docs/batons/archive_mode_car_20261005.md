# ARCHIVE MODE car — 2026-10-05

**Founder decision 2026-10-05 (intent, as given):** stop iterating; Vela becomes an open, non-commercial archived
work. Build (A) a self-contained static showcase site and (B) a capped live demo serving anonymous Research only.
Payments are being shut down by the founder in the Dodo dashboard (manual, not this car). There is no user data
to retain, so archive mode STOPS collecting; no existing DB row is deleted.

**State:** LOCAL — committed, **NOT pushed, NOT deployed**. Start HEAD `4f5176f` (3 commits ahead of origin: the
route-mismatch probe + Segment 1 commits `3a6448b` · `48416bb` · `4f5176f`, which ride the same future push).
Car commits: **1** `68657f5` feat(archive) · **2** `73ea59d` feat(showcase) · **3** this docs commit.
Repo asserted (Rule 24): toplevel `C:/Users/andre/projects/Vela`, HEAD `4f5176f1ee4d9d0c83a0c3d6f26c74f8ff736812`.

## §0 Phase 0 — read-only probe (at start HEAD `4f5176f`)

0a. `git log --oneline -5` → `4f5176f` · `48416bb` · `3a6448b` · `69b4992` · `f2d6070`. `git status --short` → only the
allowlist (`.superpowers/`, three `public/media/*.png`). No STOP.

0b. Locations. Cited at the post-car HEAD so a reader lands on the right line; the Phase-0 reading at
`4f5176f` is kept as "was N" (the car shifted `api/server.py` by +27 from line 519 and by +33 below the
Research history edit, and the frontend files by a few lines).

| item | location now (was, at `4f5176f`) |
|---|---|
| anon daily budget $2/day | `api/services/cost_guard.py:31` (was 10), compared at `:51` (was 30); gate call `api/server.py:874` (was 847) |
| POST /api/research | `api/server.py:852` (was 825) |
| ChatHistory writes in /api/research | ONE site, `api/server.py:1078` (was 1045; signed-in DONE branch). The anonymous DONE branch from `api/server.py:1061` (was 1034) writes none (anon credit deduct + cost log only). AuditLog `api/server.py:1035` (was 1008) is signed-in only. |
| POST /api/verify | `api/server.py:1262` (was 1229) |
| POST /api/explain | `api/server.py:1769` (was 1736); L0 refused at `api/server.py:1786` (was 1752) |
| POST /api/explain/extract-image | `api/server.py:1903` (was 1870) |
| LemonSqueezy POST /api/checkout | `api/server.py:2221` (was 2188) |
| Dodo POST /api/checkout/dodo | `api/server.py:2243` (was 2210) |
| POST /api/webhooks/lemonsqueezy | `api/server.py:2318` (was 2285) |
| POST /api/webhook/dodo | `api/server.py:2398` (was 2365) |
| POST /api/webhooks/clerk | `api/server.py:2603` (was 2570) |
| Dodo cancel_subscription, POST /api/subscription/cancel | `api/server.py:2740` (was 2707) |
| POST /api/user/context/hash | `api/server.py:2819` (was 2786) |
| POST /api/share/create | `api/server.py:3414` (was 3381) |
| keep-list: /health · GET /api/history · DELETE /api/history | `api/server.py:2950` · `api/server.py:2128` · `api/server.py:2185` (were 2917 · 2095 · 2152) |
| pages/verify.tsx · pages/explain.tsx · pages/pricing.tsx | default exports `pages/verify.tsx:583` · `pages/explain.tsx:822` · `pages/pricing.tsx:21` (were 581 · 820 · 17) |
| pages/sign-in/* · pages/sign-up/* | one file each, `[[...index]].tsx`, default export (was line 3 in both) |
| Navbar links · Upgrade · sign-in · cancel UI | `components/Navbar.tsx:173` (link map) · `components/Navbar.tsx:219` (Upgrade) · `components/Navbar.tsx:263` + `components/Navbar.tsx:352` (sign-in) · `components/Navbar.tsx:137` handler, `components/Navbar.tsx:327` menu row, `components/Navbar.tsx:370` dialog (were 168 · 214 · 258 + 347 · 132, 322, 365) |
| MobileNav | `components/MobileNav.tsx:20` (verify tab) · `components/MobileNav.tsx:30` (explain tab) (were 19 · 29) |
| landing nav · sign-in · footer Pricing · composer mode jump | `pages/index.tsx:333-335` · `pages/index.tsx:346` · `pages/index.tsx:455` · `pages/index.tsx:140-141` (were 325-327 · 336 · 445 · 135-136) |
| hero chips | `utils/i18n.ts:44` (interface) · `utils/i18n.ts:88` (en heroChip2) — unchanged; consumed at `pages/index.tsx:121` (was 116) |
| Verify / Explain landing bands | `components/LandingSections.tsx:536` (CTA `components/LandingSections.tsx:555`) · `components/LandingSections.tsx:596` (CTA `components/LandingSections.tsx:604`) (were 535 / 552 · 593 / 601) |
| landing settings sign-in row | `components/LandingSettingsDropdown.tsx:60-69` (was 59-68) |
| fly.toml | `[build.args]` present — 6 keys: NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY, NEXT_PUBLIC_POSTHOG_KEY, NEXT_PUBLIC_POSTHOG_HOST, NEXT_PUBLIC_API_URL, NEXT_PUBLIC_LOCALE_HINT_ENABLED, NEXT_PUBLIC_SENTRY_DSN. `[env]` present — 1 key: SENTRY_DSN. |

Every listed route and the budget constant were found where expected. No STOP. *(Disclosure: Phase 0 printed the
whole fly.toml, so the committed public NEXT_PUBLIC_* values were displayed in the session; no `.env` or secret
was opened.)*

0d. **Rule 27** — `git grep -n -i -E "archive mode|ARCHIVE_MODE|archived|showcase" -- TECH_DEBT.md BACKLOG.md STATE.md`
→ **199 lines** (BACKLOG 8 · STATE 124 · TECH_DEBT 67), classified: 184 ledger-archive paths (`docs/archive/…`),
9 incidental "archived" prose, 6 "ProductShowcase" (a deleted landing component). Narrow grep
`ARCHIVE_MODE|archive[ _-]mode|archive car|archived work|archive site|showcase site|static showcase` → **0**.
**None found** — no existing entry covers archive mode.

## §1 0c — "Unable to cancel. Please contact" (diagnosis only; nothing changed)

*Line numbers in this section are at the post-car HEAD (the Phase-0 reading at `4f5176f` was 33 lines lower in `api/server.py` from the cancel route on, 5 lower in `components/Navbar.tsx`, 5 lower in `utils/i18n-ui.ts`).*

**Flow.** `components/Navbar.tsx:137-158` `handleCancelSubscription` → POST `/api/subscription/cancel` →
`api/server.py:2740-2776` → PATCH to host `live.dodopayments.com`, path subscriptions/{dodo_subscription_id}, body
status=cancelled. The message is `ui.cancelError` (`utils/i18n-ui.ts:517`), shown at `components/Navbar.tsx:382`
for ANY non-2xx response or a thrown fetch — the frontend cannot tell the branches apart.

**Every branch that produces it:**

1. **404** — no `user_usage` row, or `dodo_subscription_id` empty (`api/server.py:2751-2752`). **Logs nothing.**
2. **500** — `DODO_API_KEY` unset (`api/server.py:2754-2757`); logs "DODO_API_KEY not configured".
3. **500** — Dodo answered non-200/204 (`api/server.py:2768-2770`); logs "Dodo cancel failed: <status> <body>".
4. **500** — the httpx call raised (`api/server.py:2771-2773`); logs "Dodo cancel error: <type>".
5. **403** — `require_auth` (`api/server.py:441-470`) on a missing or undecodable token.
6. **429** — the rate limiter, 3 requests per 60 s on this path (`api/server.py:292`).
7. A thrown fetch (network / CORS) on the client (`components/Navbar.tsx:153-154`).

(A null Clerk token returns early with NO message, `components/Navbar.tsx:141-142` — not this symptom.)

**Most likely, from the code alone: branch 1 (no `dodo_subscription_id` on the founder's row), with branch 3 the
runner-up.** Why 1: the Cancel row only renders for `plan === 'pro'` (`components/Navbar.tsx:318`), and three code
paths yield `plan_type='pro'` WITHOUT a Dodo id — the Lemon Squeezy webhook (`api/server.py:2365-2367` stores
`lemon_subscription_id` only), any manual DB edit, or a Dodo payload carrying neither `data.subscription_id` nor
`data.id` (`api/server.py:2526`). Branch 1 is also the only branch that logs nothing. Why 3 stays close: the
PATCH shape has **no committed test or probe** against Dodo (`git grep` over tests/docs finds the shape only in
`docs/manual-deletion-sop.md:55-60` and the 2026-08-25 recon), and the `data.id` fallback at `api/server.py:2526` could store
an id that is not a subscription id, which Dodo would reject. Ruled out: `tests/run_golden_tests.py:396` sets
`plan_type='pro'` only for `clerk_user_id='test_user'`.
**Decisive evidence (founder-only, prod read):** `fly logs` around the attempt — a "Dodo cancel failed" /
"Dodo cancel error" line ⇒ branch 3/4; no such line ⇒ branch 1 (or 5/6). Or the founder's `user_usage` row:
`dodo_subscription_id` NULL ⇒ branch 1.
**Adjacent:** the copy itself is truncated — every locale ends at "Please contact" (en `utils/i18n-ui.ts:517`) and
`components/Navbar.tsx:382` appends nothing, so the user is never told whom to contact.
**Under archive mode** the route answers 410 and the cancel UI is hidden; cancellation now happens in the Dodo
dashboard (founder checklist §6), and the Dodo webhook stays ungated so the `subscription.cancelled` event still
lands and downgrades the row.

## §2 Segment B — `68657f5` feat(archive): ARCHIVE_MODE gate

**Design.** Backend env flag `ARCHIVE_MODE` (truthy = "true", read per request) + frontend build arg
`NEXT_PUBLIC_ARCHIVE_MODE` (`utils/archiveMode.ts`). Both default OFF in code; ON in `fly.toml`.

- **Gate:** `archive_gate` (`api/server.py:533-544`), attached as a route-level dependency
  (`dependencies=[Depends(archive_gate)]`) on **9 routes** — `git grep -c "dependencies=\[Depends(archive_gate)\]" -- api/server.py`
  = 9, matching the 9 the spec names (unit: route decorators). FastAPI runs route-level dependencies before the
  endpoint's own, so the 410 lands before auth, get_db, body validation, PHI, guards, LLM, credit and vendor work.
  Body: one generic detail string (Rule 5).
- **Kept:** /api/research, /api/webhook/dodo, /api/webhooks/clerk, /health, GET + DELETE /api/history, /q/*, /explore/*.
- **Research:** in archive mode, no ChatHistory write for any tier (`api/server.py:1069-1083`); deduct, cost log,
  AuditLog and the judge task are unchanged.
- **Budget:** `ANON_DAILY_BUDGET_USD` via `_budget_from_env` (`api/services/cost_guard.py:15-28`) — unset/blank ⇒
  2.00 (unchanged); malformed, negative or non-finite ⇒ raises at import (process does not start); 0 = kill switch.
- **Frontend:** `components/ArchiveBanner.tsx` in `pages/_app.tsx`; `components/ArchivedFeatureNotice.tsx` on
  /verify, /explain, /pricing, /sign-in, /sign-up; Navbar / MobileNav / landing hide Verify, Explain, Pricing,
  Upgrade, sign-in and the cancel UI; band CTAs → `SHOWCASE_URL`; hero chip 2 withheld.
- **fly.toml:** `[env]` ARCHIVE_MODE = "true", ANON_DAILY_BUDGET_USD = "0.5" (section existed — not created);
  `[build.args]` NEXT_PUBLIC_ARCHIVE_MODE = "true".

**Deviations from the spec, each flagged:**
1. **Dockerfile changed** (not in the car's file list): `ARG` + `ENV NEXT_PUBLIC_ARCHIVE_MODE` before
   `npm run build`. Without them the fly.toml build arg never reaches Next.js and the archive frontend silently
   does not ship (Rule 19). Pinned by `test_fly_toml_turns_archive_mode_on_and_dockerfile_carries_the_build_arg`.
2. **A third i18n key**, `archiveShowcaseLink` ("About the project"), for the link label the banner and the notice
   need — Rule 16 forbids an unkeyed visible string. So: 3 keys × 16 locales; 45 non-en cells MT-marked.
3. **`SHOWCASE_URL` is the literal placeholder `{{SHOWCASE_URL}}`** (`utils/archiveMode.ts:13`). Until filled,
   the banner / notice / band links are relative and broken (the export renders them as
   `/%7B%7BSHOWCASE_URL%7D%7D`). Fill BEFORE the closeout build.
4. **Chip 2 hiding supersedes, for the archive build only, the 2026-10-02 STATE Next Up wording "FIX FIRST, no
   chip hiding"** (route-mismatch block). With the flag OFF the chip is unchanged.

**AuditLog — reported, NOT changed (flag):** for signed-in Research, `AuditLog.query_content` stores
`PHIDetector.sanitize_for_log(body.question)` and `resource_ids` (the cited source ids) (`api/server.py:1035-1042`),
and `_run_judge_background` adds LLM-judge scores to the same row (an extra LLM call per signed-in query). Under
archive mode that is still collection of query content for any signed-in session. Founder decision whether to
skip it too.

**Readbacks.**

| check | result | command |
|---|---|---|
| RED | 15 failed / 9 passed — every failure for the intended reason; the 9 are keep-list, flag-off and control tests that assert existing behaviour | `SENTRY_DSN= python -m pytest tests/test_archive_mode.py -q` |
| GREEN | 24 passed | same |
| mutation | `/api/verify` gate removed ⇒ 2 failed (signed-in + anonymous verify); restored byte-identical (`cmp`) | scripted replace + same pytest |
| full suite | before 480 passed / 28 skipped (508 collected) ⇒ after 504 passed / 28 skipped; +24 = the new file | `SENTRY_DSN= python -m pytest tests -q` |
| tsc | exit 0, 0 lines, before and after | `npx tsc --noEmit` |
| lint | problem set identical, 22 = 22 (file, severity, rule, message; line numbers ignored); exit 1 before and after (pre-existing) | `npm run lint` + normalizer |
| build (archive) | exit 0; exported HTML: banner on every page checked, notice on /verify /explain /pricing, chip 2 absent, no /verify or /pricing link on the landing | `NEXT_PUBLIC_ARCHIVE_MODE=true npm run build` |
| build (default) | exit 0; banner 0, notice 0, chip 2 present, /verify + /pricing links present — the OFF path is unchanged | `npm run build` |

Harness safety: `api.server` runs `load_dotenv()`, so the local live vendor keys are in-process. The test file
blocks every non-loopback DNS lookup and connect and dummies the per-request vendor keys, so RED and the mutation
run could not reach Dodo, Clerk, Lemon Squeezy or OpenAI (the RED log shows `ConnectError` / "Connection error"
locally). The RED `share_create` run wrote two OG PNGs into the gitignored `static/og/`; both were deleted.

## §3 Segment A — `73ea59d` feat(showcase): static archive site

`showcase/index.html` (en) + `showcase/zh-TW.html` (zh-TW, written natively; reuses the product's zh-TW feature
names and disclaimer), `showcase/README.md`, `showcase/media/` (byte-identical copies, originals untouched).
Inline CSS, system font stacks, no JS, no external requests, no trackers; light + dark tokens with an explicit body
background. Media 2,506,788 bytes (2.39 MiB); showcase total 2,544,130 bytes (2.43 MiB).

**Checks.** `html.parser`: 0 errors in either file; every local src/href exists (8 per file); 0 control bytes;
no horizontal overflow at 360 px or 1280 px (measured in Chrome over a localhost static server:
scrollWidth == clientWidth, 0 elements past the viewport edge). **Every external URL in showcase/:** `{{DEMO_URL}}`,
`{{REPO_URL}}` (placeholders, one each per file) and `https://an-tho.com` (one per file). Nothing else.

**Findings and their sources** (each also carried as an HTML comment beside the figure):

| finding | figure | source at commit |
|---|---|---|
| cheaper model, different question | mini 2 of 8, gpt-4.1 0 of 8 | `tests/probes/bp_calcium/step10_0b_grades.json` @ `438a19c` |
| right label, wrong route | 42 of 149; 42 of the calcium question's 85; 0 of the other 64; 14 questions | `tests/probes/route_mismatch/step2_grades.json` @ `4f5176f` |
| one drug, two names | 3 safety sections vs none; "6 of 6"; five rounds | `CLAUDE.md:162` (rule 23) @ `c51f36e` |
| ranking test blind to its documents | 690 stubs; 11 of 13 | `CLAUDE.md:160` (rule 22) @ `c51f36e`; `api/rag/retriever.py:96-106` @ `cf6b78b`; `tests/probes/retrieval_attrition/poolsize_postc1_comparison_20260823.json` @ `f9c318d` |
| text heuristics overcount | 69 ⇒ 3 of 1,036; 22% ⇒ 13% | `CLAUDE.md:158` (rule 21) @ `c51f36e`; `tests/probes/c2/nonhuman_scope.json` @ `3d38d3e` |
| DailyMed corpus size (how it worked) | 4,608 sections, 1,038 labels | `tests/probes/route_mismatch/step1_corpus_route_census.json` @ `3a6448b` |

Honesty boundary: the 149 grades were assigned by reading (Claude Code, 2026-10-02), not by a clinician — the page
says so. The "69" and "22% ⇒ 13%" figures live only in CLAUDE.md prose; their original sweeps are not retained as
committed artifacts (the "3 of 1,036" half is).

**The FOUNDER REVIEW paragraph (en, verbatim as committed):**

> Vela answered medical questions with a language model. Offering that to the public runs into a regulatory gate
> for software that gives medical answers, and clearing it responsibly is not something one person can do on the
> side. Keeping the answers honest also took constant maintenance: every model change, data source and safety
> check had to be measured again by hand, as the findings above show. Meanwhile, well-resourced teams now offer
> capable medical search for free. Rather than let Vela decay while still charging for it, I stopped development,
> ended subscriptions, and left a small, cost-capped Research demo online as a record of what it did.

(The zh-TW page carries a native-written equivalent inside the same markers.)

## §4 Flags — found, NOT changed (founder's call)

1. **Still collecting under archive mode:** `/api/feedback`, `/api/explain/feedback` and `/api/bug-report` write
   rows; PostHog `track()` still runs; signed-in Research AuditLog (§2).
2. **Signed-out users cannot reach history deletion:** sign-in is retired, so GET/DELETE /api/history serve only
   sessions that already exist.
3. **Surfaces that still lead to retired pages** (they land on the archived notice, not an error): the landing
   composer's mode selector (`pages/index.tsx:140-141`), the signed-in Dashboard Verify/Explain cards,
   `components/AnonymousUpgradeCTA.tsx`, `components/ShareButton.tsx` sign-up push, the anon History link
   (redirects to /sign-in). `UpgradeModal` via `/?upgrade=true` would call the 410'd checkout.
4. **Banner coverage:** Next.js pages only — the Jinja-rendered /q/*, /explore/* and /blog pages carry no banner.
5. **Landing settings dropdown** is fixed at `top-[72px]`, sized for the nav alone; with the banner above the nav
   it opens ~29 px higher relative to the gear. Visual only — eyeball at closeout.
6. **`.dockerignore` does not exclude `showcase/`**, adding ~2.5 MB to the deploy build context (the image is
   unaffected — stage 2 copies only api/, scripts/, data/ and the export).
7. **Route-mismatch Segment 2 is paused by the archive decision;** the `[HONESTY][P1]` entry stays open, chip 2
   is hidden in the archive build only.
8. **ADR 001 named the env var `ANONYMOUS_DAILY_BUDGET_USD`** (`docs/decisions/001-anonymous-trial-flow.md:794`,
   never implemented); the car spec's `ANON_DAILY_BUDGET_USD` was used.
9. **The cancel error copy is truncated** in all 16 locales (§1).

## §5 Segment C — this commit (ledgers)

STATE.md: Last-updated line, a Next Up block at the top, a Recently Shipped entry. TECH_DEBT.md: the LEMON_SQUEEZY
`[sec]` entry annotated (class and P unchanged), a dated NAV block (pre-change derive at `73ea59d`, post-change
re-derive). BACKLOG.md untouched. Ledger text written by a file-staged Python script; 0 control bytes asserted in
all three ledgers before the commit.

## §6 FOUNDER CHECKLIST (manual — not Claude Code)

- [ ] **Dodo:** cancel every active subscription, including your own; archive the products; delete the webhook
      endpoint only AFTER the archive deploy (cancellation events must land first); the payout is below the $50
      threshold, so contact Dodo support about releasing it.
- [ ] **Clerk:** restrict sign-ups (the UI no longer offers them, but the Clerk instance still accepts them).
- [ ] **OpenAI:** set a monthly hard budget on the project key.
- [ ] **Showcase:** deploy `showcase/` to Cloudflare Pages (`showcase/README.md`: preset None, no build command,
      output directory `showcase`).
- [ ] **Placeholders:** fill `{{DEMO_URL}}` and `{{REPO_URL}}` in both showcase pages, and `{{SHOWCASE_URL}}` in
      `utils/archiveMode.ts` BEFORE the product build that ships archive mode
      (`git grep -n "{{" -- showcase utils/archiveMode.ts`).
- [ ] **Copy:** review the FOUNDER REVIEW paragraph in both pages (§3); remove the markers when accepted.
- [ ] **DNS:** decide which hostname carries the showcase and which the live demo.
- [ ] **Flags §4:** rule on AuditLog / feedback / PostHog collection and the history-deletion reachability.
- [ ] **Closeout prompt:** push (this car + the 3 route-mismatch commits) and `.\deploy.ps1`.

## §7 CLOSEOUT v2 — 2026-10-05 (/about page + publish prep + push + deploy)

**Founder rulings 2026-10-05, recorded verbatim** (they supersede the earlier closeout draft, which was NOT run):

> R1 No separate static host. The showcase becomes /about/ on vela.an-tho.com, served by the existing app. showcase/ is removed from the repo.
> R2 Live demo = vela.an-tho.com, Research only (already gated by ARCHIVE_MODE). Verify/Explain code is KEPT (gated), not deleted.
> R3 The GitHub repo WILL be made public — by the founder, manually, AFTER reviewing your scan report. You do NOT change repo visibility.
> R4 Fly cost: keep the current 1 GB machine (measured mem_used avg 595 MB of 962 MB, founder dashboard 2026-10-05) — no infra change this car.

R1 supersedes §3's Cloudflare Pages plan and the §6 items "Cloudflare Pages deploy", "fill {{DEMO_URL}} / {{REPO_URL}} / {{SHOWCASE_URL}}" and "DNS decision" (all three are now done or moot).

### §7.1 Phase 1 — secret scan + sensitive inventory (read-only; NO value printed or written)

**Tools.** gitleaks 8.30.1 (official Windows x64 release, SHA-256 verified against the release's published checksums,
binary kept outside the tree) run with `--redact=100` over `git log --all` (909 commits, 7 local refs; origin has `main`
only) and over a `git archive HEAD` export of the tracked tree (967 files — `.env`, untracked and ignored files are
never in it). Plus a custom sweep over every ADDED line of `git log -p --all` and over the same export, with the car's
pattern list + one added rule (`sk-proj-` / `sk-svcacct-` / `sk-admin-`, which `sk-[A-Za-z0-9]{20,}` cannot match) and a
count-only pass for Google client secrets, Google API keys, JWTs, literal Bearer tokens, Fly tokens, GitHub tokens and
Google OAuth client ids (**0 each**).

| class (unit: distinct values) | TREE (HEAD) | HISTORY (all refs) | reasoning |
|---|---|---|---|
| **REAL SECRET** | **0** | **0** | — no STOP |
| INFO — publishable | 2 | 3 | Clerk `pk_live_` + PostHog `phc_` in `fly.toml:8-9` (shipped in client JS by design); history adds the old Clerk `pk_test_` (`3e4471e`) |
| TEST FIXTURE | 4 | 4 | test-only literals in `tests/test_httpx_log_level.py`, `tests/test_payment_webhooks.py` (incl. a deliberately WRONG secret in a bad-signature test) and `scripts/smoke_webhook_cancel.py` |
| FALSE POSITIVE | 10 | 10 | `.env.example` placeholders; bare prefixes in code/docs (`whsec_` strip logic, `sk_live_` / `sk_test_` mentioned as text); a `user:password@ep-xxx` README URL; prose in a theme-token test |
| gitleaks findings (unit: findings) | 2 | 3 | all `generic-api-key` on `fly.toml:8-9` → the INFO row |

One FALSE POSITIVE is worth the founder's eye: `docs/archive/tech_debt_done.md:566` quotes the prod Clerk secret key as
`sk_live_` + **3 characters** + `...` — a truncated prefix (non-functional; a real key is ~40+ characters), present in
history since `a8877e9`. Not a secret; flagged because it is a real key's first characters.

**Sensitive-but-not-secret inventory (report only).**

| item | count | where |
|---|---|---|
| Clerk user ids | 2 distinct, 3 files | `docs/retrospectives/phase-0-2026-05.md` + `scripts/smoke_webhook_cancel.py` (labelled in-file as the founder's own account); `TECH_DEBT.md:2938` (a user deleted in Clerk) |
| Dodo customer / subscription ids | 0 / 0 | — |
| email addresses | 10 distinct domains, 41 files | public support address (an-tho.com), placeholders (example.com, acme.com, email.com, ep-xxx…neon, oxxx…sentry), drug-label manufacturer contacts in `data/drug_database/` (public label text), one vendor contact domain in `BACKLOG.md` (tradevan.com.tw), and 2 gmail.com addresses — NOT the founder's — a test-user email at `scripts/smoke_webhook_cancel.py:6` and a synthetic PHI test input at `tests/golden_dataset.json:1403` |
| prod DB hostnames | 0 prod | `README.md:162` is a placeholder; `tests/probes/research_error_path/result*.json` carry a real Neon host that the probe's README states is the **dev** DB |
| probe files carrying prod readings | 8 | `tests/probes/bp_calcium/step8_prod_smoke*` (prod Research answers to the hero-chip question, fly 262), `step6_spend.py`, two `.patch` files — no user data |
| legal-counsel references | 25 files match the term set; outside drug-label data the hits are references to "lawyer-confirmed" designs (`docs/manual-deletion-sop.md`, `BACKLOG.md:1555`, `:1593`, `scripts/deletion_dryrun.py`, `api/services/deletion_service.py:20`, `tests/test_phi_taiwan_phone.py:2`) and one medical-advisor gate (`STATE.md:330`); **no verbatim counsel opinion was found by this grep** — read before publishing |
| `docs/legal-versions/` | 19 files | 11 privacy + 7 terms versions + README (the published policy history) |
| License claim | 1 conflict | `README.md:17` badge says **Business Source License 1.1**; the car adds an MIT `LICENSE` (R3 prep). Left unchanged per "rest of README unchanged" — **founder decision before the repo goes public** |

**REPO_URL** (`git remote get-url origin`, no credential part): `https://github.com/AndrewLee0430/Vela` (`.git` dropped
for the link). The repo is still PRIVATE until the founder acts (R3) — the /about/ "Read the source code" link 404s
for visitors until then.

**Fly inventory (read-only, nothing changed — R4).**

| item | value |
|---|---|
| app | `vela-ai-medical`, owner personal, hostname `vela-ai-medical.fly.dev` |
| scale | group `app`: 2 machines, shared, 1 CPU, 1024 MB, region nrt(2) |
| machines (before deploy) | `683d447c2e5428` (young-river-7305) started · `2879720c66d478` (withered-field-6397) stopped — both v262, `shared-cpu-1x:1024MB`, nrt, no volume |
| IPs | v6 `2a09:8280:1::e5:e2f5:0` public ingress (dedicated) · v4 `66.241.125.32` public ingress (shared) |
| volumes | none |
| machines (after the deploy, read from `fly status`) | both v263, started — no scale / size / region / IP change (R4) |

### §7.2 Phase 2 — /about page (`655f2d1`)

`showcase/index.html` → `public/about/index.html`, `showcase/zh-TW.html` → `public/about/zh-TW.html` (`git mv`); media
point at the existing `/media/*`; duplicated media + `showcase/README.md` removed. `{{DEMO_URL}}` → `/research`,
`{{REPO_URL}}` → REPO_URL, `SHOWCASE_URL = "/about/"`; 0 `{{` left. Landing band CTAs become plain `<a>` in an archive
build (the static page is outside the Next.js router). MIT `LICENSE` (2026, AndrewLee0430). README: 8-line archived
status block prepended; rest unchanged.

**Serving check (Rule 18 — measured, not assumed).** Local backend from a scratch dir whose `static/` is the archive
export, `TEST_MODE`, `SENTRY_DSN` blank, **`DATABASE_URL=sqlite:///:memory:` — deliberately NOT the dev branch**: this
closeout does not authorize DB access, and the app's lifespan runs `create_all` and the retention cleanup pass (which
deletes) on startup — it logged "deleted 0 … older than 180 days" against the in-memory DB. Results:

| GET | status · bytes | page |
|---|---|---|
| `/about/` | 200 · 16793 | about (en title) |
| `/about` | 200 · 16793 | about (en title) |
| `/about/index.html` | 200 · 16793 | about (en title) |
| `/about/zh-TW.html` | 200 · 17222 | about (zh-TW title) |
| `/no-such-page-xyz` (control) | 200 · 21781 | SPA index — the fallback is distinct |

No serving change was needed: the catch-all's directory-index branch (`api/server.py:3727-3729`) already serves it.
html.parser 0 errors on both pages, every link resolves, 0 control bytes; no horizontal scroll at 360 px (Chrome) on
`/about/`, `/about/zh-TW.html`, `/` and `/verify`; the three images decode at native size. Aside: `.webp` is served as
`text/plain` on the local Windows run (mimetypes) — images still render (no `nosniff`).

Readbacks: pytest 504 passed / 28 skipped; tsc 0; lint problem set identical (22 = 22, baseline regenerated at
`90f5b6d`); `npm run build` exit 0 with `NEXT_PUBLIC_ARCHIVE_MODE=true`.

### §7.3 Phase 3 — push + deploy

**Push.** `git push origin main` → `69b4992..655f2d1`, **7 commits** (`git rev-list --count origin/main..HEAD` before the
push; unit: commits) = 3 route-mismatch (`3a6448b` · `48416bb` · `4f5176f`) + 3 archive car (`68657f5` · `73ea59d` ·
`90f5b6d`) + `655f2d1`. `git ls-remote origin main` = `655f2d13c66c79205014e88f3c1fb4e94a0d449f` = HEAD (40 chars).

**Deploy.** `.\deploy.ps1` run plain (no redirect), **attempt 1 of max 3, exit 0**. Build context 152 MB uploaded on
the first try; image `deployment-01M45D8166J8M0CJFNNVXWXZY8`. **Release READ from `fly releases`: v263 complete**
(top was v262 before the deploy) → **fly 263**. The script's Step 3 found `2879720c66d478` stopped and Step 4 started
it; final `fly status`: both machines **v263, started**. Transcript copied verbatim to
`tests/probes/deploy_parser/fly263_deploy_transcript.txt` (903 lines; 0 hits for sk- / sk_live_ / whsec_ /
credentialed postgres URLs / api_key= / Bearer tokens; 12 ESC bytes, same as the fly262 precedent).

| readback (prod, 2026-10-05) | result |
|---|---|
| `/health` revision | `655f2d13c66c79205014e88f3c1fb4e94a0d449f` — 40-char MATCH with the pushed SHA |
| unauth POST /api/verify | **410** `{"detail": "Vela is archived. This feature is no longer available."}` |
| unauth POST /api/checkout/dodo | **410**, same body |
| unauth POST /api/checkout · /api/webhooks/lemonsqueezy (extra, for the TECH_DEBT LEMON status) | **410** · **410** |
| GET / | 200 · the en `archiveBanner` string present |
| GET /research | 200 · banner present |
| GET /about/ · /about · /about/zh-TW.html | 200 · about en title · about en title · about zh-TW title |
| GET /verify | 200 · archived notice present |
| `fly logs --no-tail` | 100 lines: 53 backfill (05:28:16Z → before the boundary) + **47 post-boundary** (06:52:54Z → 06:54:12Z, 78 s); post: Traceback 0 · httpx 0 · api_key= 0; every level-tagged line INFO (39) |

No live Research query was sent. Aside (pre-existing, not changed): prod serves `/media/*.webp` as `text/plain`
(the image's mimetypes table lacks `.webp`); images still render (no `nosniff` header).

### §7.4 PROD EYE — founder (BLANK)

| # | row | founder result |
|---|---|---|
| 1 | landing shows the archive banner | |
| 2 | nav shows no Verify / Explain / Pricing / sign-in | |
| 3 | /verify and /explain show the archived notice | |
| 4 | anonymous Research answers a question | |
| 5 | the banner link opens /about/ (en + zh-TW) | |
| 6 | /about/ demo + repo links work | |

### §7.5 FOUNDER CHECKLIST (updated — supersedes §6 where they differ)

- [ ] Review §7.1 → resolve the README BSL-vs-MIT license conflict → then make the GitHub repo public (R3).
- [ ] Delete the Dodo webhook endpoint (the archive deploy is live).
- [ ] OpenAI: set a monthly hard budget.
- [ ] Dodo payout: reply pending (an account can be archived only after 180 days without payment activity).
- [ ] Still open from §6: cancel remaining Dodo subscriptions (incl. own) + archive products; Clerk sign-up restriction; review the FOUNDER REVIEW paragraph on /about/ (both languages) and remove the markers; rule on the §4 flags.
- [ ] PROD EYE §7.4.
