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
