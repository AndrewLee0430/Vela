# ARCHIVE UI car — 2026-10-05

**State: BUILT LOCAL — `45204fa` committed, NOT pushed, NOT deployed. PUSH + DEPLOY HELD:** the full-suite pytest
gate did not complete — the run was stopped by Claude Code under system memory pressure (not a test failure; 55
tests had passed, 0 failed, when it was reaped; no orphan process survived). The car authorizes push + deploy only
if every Phase 2–3 gate is green, so it stopped here. Prod stays **fly 263** at `655f2d1`.
Repo asserted (Rule 24): toplevel `C:/Users/andre/projects/Vela`, start HEAD `2f09f83db019be33ad2b1fb1983a70482759744a`.

**Founder rulings 2026-10-05, verbatim:**

> U1 In the ARCHIVE build, Verify, Explain, Pricing and Refund disappear from the UI entirely: nav, mobile nav, footer, landing bands, CTAs, settings dropdown, any "Pro"/"credits"/"free account"/"upgrade" copy. Direct URLs (/verify, /explain, /pricing, refund page) render the existing ArchivedFeatureNotice. Feature code stays (flag-gated) — no deletion.
> U2 The landing Verify and Explain bands are REMOVED in the archive build (supersedes "keep as showcase, CTA → /about/").
> U3 The ArchiveBanner is REMOVED from all pages in the archive build. To keep /about/ reachable, add ONE footer link "About the project" (reuse the existing archiveShowcaseLink key) → /about/, archive build only.
> U4 FAQ gets an archive variant (below). Terms / Privacy / Refund legal TEXT is NOT edited — only listed.
> U5 Founder confirmed 2026-10-05 ~20:50 that prod IS the archive build (a hard refresh removed Verify/Explain/Pricing; the earlier view was browser cache).

## §0 Phase 0 — cache + readback method

**0a.** `GET https://vela.an-tho.com/` (and `/research`, `/faq`, the `_app` JS chunk) carries **no `Cache-Control`
header** — only `ETag` + `Last-Modified`; no `Age` (no shared cache in front). A browser therefore applies HEURISTIC
freshness (RFC 9111 §4.2.2, commonly 10% of the time since `Last-Modified`) and may reuse a cached page for hours
without revalidating — which is why the founder saw the pre-archive page until a hard refresh. No long `max-age` is
set, so nothing was changed. **Flag (founder):** `Cache-Control: no-cache` on HTML responses would make every visit
revalidate against the ETag. **Also found:** HEAD and GET disagree on Next.js page routes — `HEAD /research` and
`HEAD /faq` answer **404** while GET answers 200 (`/` and `/about/` agree). The catch-all route is GET-only and HEAD
falls through to the root StaticFiles mount. `curl -I` readbacks are therefore misleading here; every readback in
this car uses GET.

**0b. Premise check, then discriminating markers.** The closeout-v2 readback grepped the HTML **document**, not the
JS bundle, and `ArchiveBanner` returned `null` with the flag off — the first archive car measured banner = 0 in the
flag-off `out/index.html` and 1 in the archive one, so that readback could fail. The markers below are markup the
flag-gated components emit; proved on the two LOCAL builds of the GREEN run (pytest temp copies, unit = occurrences
in the prerendered HTML):

| page | marker | archive | unset | discriminates |
|---|---|---|---|---|
| index.html | `href="/verify"` | 0 | 2 | YES |
| index.html | `href="/explain"` | 0 | 2 | YES |
| index.html | `href="/pricing"` | 0 | 2 | YES |
| index.html | `href="/refund"` | 0 | 1 | YES |
| index.html | `data-band="verify"` | 0 | 1 | YES |
| index.html | `data-band="explain"` | 0 | 1 | YES |
| index.html | hero chip 2 text | 0 | 1 | YES |
| index.html | `data-archive-link="about"` | 1 | 0 | YES |
| index.html | `role="note"` (banner) | 0 | 0 | no — removed from both builds by design; kept as a prod "absent" check |
| research.html | `href="/verify"` | 0 | 2 | YES |
| research.html | `href="/faq"` | 2 | 0 | YES |
| faq.html | `data-archive-faq` | 1 | 0 | YES |
| faq.html | `href="/sign-up"` | 0 | 1 | YES |
| faq.html | `href="/refund"` | 0 | 1 | YES |
| refund.html | `data-archived-notice` | 1 | 0 | YES |
| verify.html | `data-archived-notice` | 1 | 0 | YES |

These are the Phase-3 prod readback markers (unused so far — Phase 3 did not run).

## §1 Phase 1 — inventory (unit: rendering sites; read at `2f09f83`, cited at HEAD `45204fa`)

| # | surface (key / component) | file:line | archive build before → after |
|---|---|---|---|
| 1 | landing nav Verify / Explain / Pricing | `pages/index.tsx:334-336` | hidden (archive car) → hidden |
| 2 | landing nav Sign In | `pages/index.tsx:354` | hidden → hidden |
| 3 | hero composer Verify / Explain modes | `components/HeroComposerModeSelector.tsx:38-39` | shown → selector hidden |
| 4 | Verify band (headline, sub, `tryVerify`, `verifyDemoAlt`) | `components/LandingSections.tsx:558`, `:567` | shown, CTA → /about/ → **removed** (U2) |
| 5 | Explain band (`explainSub`, `tryExplain`, demo alts) | `components/LandingSections.tsx:607-641` | shown → **removed** (U2) |
| 6 | landing footer Pricing | `pages/index.tsx:457` | hidden → hidden |
| 7 | landing footer Refund (`refundLabel`) | `pages/index.tsx:463` | shown → replaced by the About link |
| 8 | landing JSON-LD `offers` (Free / Pro, credits) | `pages/index.tsx:214-230` | present (structured data, not visible) → omitted |
| 9 | `PlanBadge` Try Vela / PRO | `components/PlanBadge.tsx:43`, `:82`, `:95` | Try Vela or PRO → Try Vela only |
| 10 | landing settings Sign In row | `components/LandingSettingsDropdown.tsx:67` | hidden → hidden |
| 11 | `ArchiveBanner` | `pages/_app.tsx` | every page → **removed** (U3) |
| 12 | app Navbar links | `components/Navbar.tsx:175` | Research + History → **Research + FAQ** |
| 13 | Navbar PRO badge | `components/Navbar.tsx:187` | Pro users → hidden |
| 14 | Navbar Upgrade (`upgrade`) | `components/Navbar.tsx:234` | hidden → hidden |
| 15 | Navbar Share ("Sign up to share", `buttonDisabledAnon`) | `components/Navbar.tsx:209`, `components/ShareButton.tsx:120` | shown → hidden |
| 16 | settings plan label (`proPlan` / `freePlan`) | `components/Navbar.tsx:284` | shown → hidden |
| 17 | settings credits (`todayCredits`, `creditsUsed`, literal "Research: 3 · Verify: 1 · Explain: 2") | `components/Navbar.tsx:291`, `:294` | shown → hidden |
| 18 | settings Manage Subscription | `components/Navbar.tsx:331` | Pro → hidden |
| 19 | settings Cancel / Upgrade to Pro / cancel dialog | `components/Navbar.tsx:338`, `:347`, `:383-409` | hidden → hidden |
| 20 | Navbar Sign In (row + pill) | `components/Navbar.tsx:273`, `:366` | hidden → hidden |
| 21 | MobileNav tabs | `components/MobileNav.tsx:78-79` | Research + History → **Research + FAQ** |
| 22 | Research export, Pro-locked (`proFeature`, `proFeatExport`) | `pages/research.tsx:625`, `components/ProFeatureOverlay.tsx:110` | shown → hidden |
| 23 | 3rd-query CTA (`thirdQueryBody` "Create a free account … unlock Explain") | `pages/research.tsx:640` | shown → off |
| 24 | quota-hit modal (`quotaHitBody`, "Sign up free", "Go Pro — $9.99 / mo") | `pages/research.tsx:742` | shown → existing `dailyCapToast` |
| 25 | `UpgradeModal` on `limit_reached` (Pro, credits, $9.99 / $89.99, Refund) | `pages/research.tsx:335`, `:393`, `:724` | possible → `dailyCapToast` |
| 26 | hardcoded "Sign up required to continue. Please create a free account." | `pages/research.tsx:337` | unreachable for Research (signup_required is Explain-only) → unchanged, listed |
| 27 | FAQ nav "Get Started" → /sign-up | `pages/faq.tsx:112` | shown → "Try Vela" → /research |
| 28 | FAQ content (Features, Pricing sections) | `utils/i18n-faq.ts` | normal FAQ → archive FAQ |
| 29 | FAQ footer Refund (`refundPolicy`) | `pages/faq.tsx:169` | shown → About link |
| 30 | Dashboard Verify / Explain cards | `pages/index.tsx:509`, `:515` | signed-in → hidden |
| 31 | Dashboard footer Refund | `pages/index.tsx:585` | signed-in → About link |
| 32 | Dashboard `UpgradeModal` (`?upgrade=true`) | `pages/index.tsx:486` | possible → off |
| 33 | `OnboardingOverlay` ("You have 15 free credits") | `components/OnboardingOverlay.tsx:95` | signed-in first visit → off |
| 34 | History free-plan line (`freeHistoryMsg`) | `pages/history.tsx:275` | shown → hidden |
| 35 | History Pro-locked search (`proFeatSearchHistory`) | `pages/history.tsx:281` | locked → unlocked (client-side filter over own rows) |
| 36 | History Share | `pages/history.tsx:568` | shown → hidden |
| 37 | History type labels for past Verify / Explain rows | `pages/history.tsx:42-43` | unchanged — they describe stored records; listed |
| 38 | `/privacy` and `/terms` footer Refund links | `pages/privacy.tsx:101`, `pages/terms.tsx:90` | shown → hidden (footer navigation; legal text untouched) |
| 39 | `/refund` | `pages/refund.tsx` | policy → `ArchivedFeatureNotice` (U1) |
| 40 | `/verify` `/explain` `/pricing` `/sign-in` `/sign-up` | — | notice (archive car) → notice |
| 41 | default meta description ("verify drug interactions … explain lab results") | `pages/_app.tsx:144` | not UI → unchanged, listed |
| 42 | FAQ meta description (mentions pricing) | `pages/faq.tsx:100` | not UI → unchanged, listed |
| 43 | inline `/refund` link inside Terms §5 legal text | `pages/terms.tsx:50` | unchanged (U4) → now lands on the notice |
| 44 | `ContextRestoreBanner` (Pro-only restore on sign-in) | `components/ContextRestoreBanner.tsx` | signed-in Pro only → unchanged, listed |

Generic uses of the verb "verify" (`CitationPanel.tsx:271` "Click View source to verify each reference", the
locale-hint lead) are not the feature and stay.

**1b — FAQ.** `pages/faq.tsx` + `utils/i18n-faq.ts`: 4 sections, **14 Q&A pairs** (en). False in archive mode
(7): Q1 (describes drug-interaction and report features), Q6 Verify, Q7 Explain, Q11–Q14 (all Pricing). Partly false
(2): Q2 and Q3 (LOINC / MedlinePlus are Explain-only sources). Adjacent: Q4 lists **Indonesian** among the 16
languages; the product's locale set has **Italian** and no Indonesian.

**1c — footers + refund route.** Refund links in the landing, Dashboard, FAQ, `/privacy` and `/terms` footers; the
route is `pages/refund.tsx` (`/refund`).

**1d — Terms / Privacy / Refund paragraphs on subscriptions, payments, refunds, accounts or Explain (LIST ONLY —
FOUNDER / COUNSEL DECISION; nothing edited):**

| file:line | first 12 words |
|---|---|
| `pages/terms.tsx:25` | Vela is an AI-powered clinical reference tool that provides evidence-based information from |
| `pages/terms.tsx:44` | 4. Subscription & Payment |
| `pages/terms.tsx:45` | Paid subscriptions are processed by Dodo Payments, our Merchant of Record. By |
| `pages/terms.tsx:49` | 5. Refund Policy |
| `pages/terms.tsx:50` | We offer a 7-day money-back guarantee from the date of your first |
| `pages/terms.tsx:54` | 6. Fair Use Policy |
| `pages/terms.tsx:55` | Pro subscribers enjoy unlimited access to all features subject to our fair |
| `pages/terms.tsx:59` | 7. Account Termination |
| `pages/terms.tsx:60` | We reserve the right to suspend or terminate accounts that violate these |
| `pages/privacy.tsx:26` | Account data: Name, email address (via Clerk authentication) |
| `pages/privacy.tsx:27` | Usage data: Feature usage counts, subscription status |
| `pages/privacy.tsx:28` | Payment data: Processed exclusively by Dodo Payments — we never store card |
| `pages/privacy.tsx:30` | Signed-out (Anonymous) Usage: Query content and AI-generated responses are processed in |
| `pages/privacy.tsx:31` | Signed-in Usage (Free & Pro): To provide chat history and ensure service |
| `pages/privacy.tsx:32` | Pro Subscription Preferences: For Pro subscribers, we synchronize a 16-character cryptographic hash |
| `pages/privacy.tsx:48` | You have the right to request the deletion of your account and |
| `pages/privacy.tsx:49` | Account deletion is handled by contacting support@an-tho.com . Once your request is |
| `pages/privacy.tsx:50` | Statutory Exception for Financial Records: Please note that pursuant to Article 38 |
| `pages/privacy.tsx:51` | When you delete your account or chat history, the eligible personal data |
| `pages/privacy.tsx:60` | Dodo Payments — Payment processing (Merchant of Record) |
| `pages/privacy.tsx:83` | If you delete your account, the link between you and any pages |
| `pages/refund.tsx:29` | If you are not satisfied with Vela Pro, you may request a |
| `pages/refund.tsx:33` | 2. How to Request a Refund |
| `pages/refund.tsx:36` | Your account email address |
| `pages/refund.tsx:37` | The date of purchase |
| `pages/refund.tsx:38` | Reason for refund (optional) |
| `pages/refund.tsx:44` | Refunds are processed within 5–10 business days and returned to your original |
| `pages/refund.tsx:49` | You may cancel your subscription at any time through the Dodo Payments |
| `pages/refund.tsx:54` | Refunds will not be issued for accounts terminated due to violations of |
| `pages/refund.tsx:59` | For refund requests or questions: support@an-tho.com |

`pages/privacy.tsx:30` is in this list for a second reason — see §3.

## §2 Phase 2 — `45204fa` feat(archive): strip retired surfaces, remove banner, archive FAQ

All 44 inventory rows handled as the table says, every change gated on `ARCHIVE_MODE` (`utils/archiveMode.ts`).
New: `utils/i18n-faq-archive.ts` (7 Q&A × 16 locales — en authored, zh-TW native, 14 MACHINE-TRANSLATED marked,
196 marked cells), `REPO_URL` beside `SHOWCASE_URL`, `tests/test_archive_ui_build.py`.

**Archive FAQ — en (verbatim):**

- **Vela is archived** (section title)
- **What is Vela now?** Vela was a multilingual medical search tool for healthcare professionals, built and run from February to October 2026. It is now an archived project: this site is a demo of Research only and is no longer maintained. *[link: About the project → /about/]*
- **Is it free?** Yes. There are no accounts and no payments. The demo runs on a small daily usage budget, so it may pause until the next day once the budget is used up.
- **What happened to Verify and Explain?** Both were retired when Vela was archived. How they worked is described on the project page. *[link: About the project → /about/]*
- **Is this medical advice?** Vela is a research tool, not a medical device. It does not provide medical advice. *(= `footerDisclaimer`, reused per locale)*
- **What happens to my questions?** Vela no longer has accounts, and questions asked in the demo are not saved to a database. To answer a question, Vela sends it to OpenAI's language model and sends search terms based on it to PubMed and openFDA. The server's logs do record the question text, and error reports can include it; those logs are kept by our hosting and error-monitoring providers. To enforce the daily budget, Vela keeps a usage count under a one-way hashed identifier made from your IP address and browser session. Usage analytics record events, such as how many sources were cited, not the text you type.
- **I had a subscription.** All subscriptions have ended. For questions about a past payment, write to support@an-tho.com.
- **Is the code available?** Yes. The source code is on GitHub. *[link: github.com/AndrewLee0430/Vela]*

**Archive FAQ — zh-TW (verbatim):**

- **Vela 已封存**（區塊標題）
- **Vela 現在是什麼？** Vela 是為醫療專業人員打造的多語言醫學搜尋工具，於 2026 年 2 月至 10 月間開發與營運。它現在是已封存的專案：這個網站只保留「研究」功能的展示，且已不再維護。*［連結：關於這個專案 → /about/］*
- **需要付費嗎？** 不需要。沒有帳號，也不收費。展示版有每日使用預算，預算用完後可能會暫停到隔天。
- **「驗證」和「解讀」到哪裡去了？** 這兩個功能已隨 Vela 封存而停用。它們的運作方式記錄在專案頁面上。*［連結：關於這個專案 → /about/］*
- **這是醫療建議嗎？** Vela 為研究工具，非醫療器材，不提供醫療建議。*（= `footerDisclaimer` zh-TW）*
- **我的提問會怎麼處理？** Vela 已不再提供帳號，在展示版中提出的問題不會存進資料庫。為了回答問題，Vela 會把問題傳送給 OpenAI 的語言模型，並把依據問題產生的搜尋詞傳送給 PubMed 與 openFDA。伺服器的記錄檔會記下問題的文字，錯誤回報也可能包含它；這些記錄由我們使用的主機與錯誤監控服務商保存。為了控管每日預算，Vela 會用一個由你的 IP 位址與瀏覽器工作階段經單向雜湊產生的識別碼來記錄使用次數。使用分析只記錄事件（例如引用了幾個來源），不記錄你輸入的文字。
- **我之前有訂閱。** 所有訂閱都已結束。如對過去的付款有疑問，請來信 support@an-tho.com。
- **可以取得原始碼嗎？** 可以，原始碼放在 GitHub 上。*［連結：github.com/AndrewLee0430/Vela］*

Q6's contact is the address already published at `pages/privacy.tsx:48` (none invented).

**Readbacks (Phase 2 gates):**

| gate | result |
|---|---|
| new build tests | RED 10 failed (each for the intended reason) → GREEN 10 passed (`tests/test_archive_ui_build.py`) |
| mutation | Verify band re-shown in the archive build → 2 failed; restored byte-identical (`cmp`) |
| `npm run build` | exit 0 with `NEXT_PUBLIC_ARCHIVE_MODE=true` and exit 0 with it unset (both inside the GREEN fixture) |
| `npx tsc --noEmit` | exit 0 |
| lint | problem set identical to the `2f09f83` baseline (22 = 22) |
| pytest, full suite | baseline 504 passed / 28 skipped at `2f09f83`; **after: NOT COMPLETED** — reaped by Claude Code under memory pressure at 55 passed / 0 failed; not re-run (the reap notice says to re-run only when asked) |

Cost note: the new build test adds two `next build` runs (~4.5 min) to every full-suite run — plausibly what tipped
the machine into memory pressure. Option for the founder: keep it in the suite, or gate it behind an env var and run
it as a separate step.

## §3 Q5 derivation — what the anonymous `/api/research` path stores or sends (lines at `45204fa`)

*2026-10-06: the 'server logs record the question TEXT' row describes `45204fa`; superseded by §7.2 (fix deployed fly 264).*

| store / flow | what | where |
|---|---|---|
| `chat_history` | **none** for anonymous users; none for anyone under ARCHIVE_MODE | `api/server.py:1061-1083` |
| `audit_logs` | **none** for anonymous users (signed-in only — stores the sanitized question; flagged in the archive-mode baton §2) | `api/server.py:1034-1043` |
| `anonymous_usage` row | `anon_id` = SHA-256 of salt + client IP + a per-tab random session UUID; daily credit counter; created / last-active timestamps — no text | `api/services/anonymous_identity.py:21-28`, `api/models/sql_models.py:89-96`, `utils/analytics.ts:53-61`, `api/server.py:1063` |
| `api_cost_log` row | `user_id` NULL, feature, model, token counts, cost, time — no text | `api/server.py:1067`, `api/models/sql_models.py:68-78` |
| application log (Fly) | first 8 chars of `anon_id` + question LENGTH (`api/server.py:873`); **the question TEXT** — `Query rewritten: '<question>'` at INFO on every request (`api/rag/retriever.py:178`), again on an empty relevance filter (`:247`) and a PubMed no-result warning (`api/data_sources/pubmed.py:349`); a PHI block logs PHI type, endpoint and client IP (`api/server.py:769`), not the text | as cited |
| Sentry | enabled on prod (secret NAME `SENTRY_DSN` present; value not read); `send_default_pii=False`; sentry-sdk's default logging integration attaches recent INFO log lines as breadcrumbs to an error event — so an error report can carry the question | `api/server.py:25-34` |
| PostHog | `anonymous_query_submitted` (session id), `research_completed` (counts, language, timings), `research_failed`, `anonymous_quota_hit` — no question text; posthog-js autocapture is on by default (input values masked by default); whether session recording is enabled is a PostHog project setting, NOT verifiable from the repo | `pages/research.tsx:322`, `:339`, `:394`, `:407`; `pages/_app.tsx:42-45` |
| browser storage | `sessionStorage` anon query counter + CTA flag | `pages/research.tsx:255-260` |
| third parties (processing) | OpenAI receives the question (guards, query rewrite, embeddings, generation); search terms derived from it go to PubMed (NCBI) and openFDA | `api/rag/retriever.py`, `api/data_sources/pubmed.py` |
| feedback | `/api/feedback` requires sign-in — anonymous thumbs are not stored | `api/server.py:1979` |

**⚠️ Contradiction — FOUNDER / COUNSEL DECISION, not changed here (U4):** `pages/privacy.tsx:29` says anonymous query
content "is processed in volatile memory and is not stored or logged on our servers". The code logs it (row above).
Already on record: `TECH_DEBT.md:1737` (2026-10-02 correction under the E5 `[HONESTY][P2]` entry, `TECH_DEBT.md:1715`) —
not re-filed (Rule 27). Q5 states what the code does, so the archive FAQ and the privacy page will disagree once this
deploys. Two ways to resolve: change `api/rag/retriever.py:178` / `:247` / `api/data_sources/pubmed.py:349` to log the
length only (a backend change, outside this UI car), or revise the policy text.

## §4 Flags (found, NOT changed)

1. **Dead code (U3):** `components/ArchiveBanner.tsx` and the `archiveBanner` i18n key (16 cells, `utils/i18n-ui.ts`) are
   unused in BOTH builds now — left in place per the ruling.
2. **FAQ Q6** states "All subscriptions have ended" — confirm the remaining Dodo cancellations before this deploys.
3. **FAQ Q7** links the repo, which is PRIVATE until the founder makes it public (R3) — the link 404s until then.
4. **History is off the nav** (U5 row 1: nav = Research + FAQ); signed-in users can still open /history by URL.
5. **Hardcoded English** strings on the Research page (`pages/research.tsx:335` sign-up text, the "Service temporarily
   at capacity" budget toast) — pre-existing, not i18n.
6. **HTML caching** (§0) — no `Cache-Control`; consider `no-cache` for HTML.
7. **HEAD 404 on Next routes** (§0).
8. **Normal FAQ Q4** names Indonesian instead of Italian (§1b).

## §5 PROD EYE (BLANK — after the deploy)

| # | row | founder result |
|---|---|---|
| 1 | no banner; nav = Research + FAQ only | |
| 2 | landing has no Verify / Explain bands | |
| 3 | footer has the About link, no Pricing / Refund | |
| 4 | the archive FAQ shows | |
| 5 | anonymous Research answers a question | |
| 6 | /about/ en + zh-TW open | |

## §6 Next

1. **Founder:** authorize a re-run of the full pytest suite (or rule that the targeted results suffice) → then the
   held push + `.\deploy.ps1` + the Phase-3 readbacks with the §0 markers.
2. Founder / counsel: §3 contradiction; §1d legal text; flags §4.
3. Then: PROD EYE §5 · make the repo public (R3) · delete the Dodo webhook endpoint · OpenAI monthly hard budget.


## §7 CONTINUATION — privacy log fix + gates + push (2026-10-06)

**State: PUSHED `2f09f83..83fdaf9` (9 commits), NOT DEPLOYED.** The `.\deploy.ps1` run was stopped by Claude Code under
system memory pressure during Step 1's build-context upload ("load build context") — no image was built, no release
was cut. Verified read-only afterwards: `fly releases` top = **v263**, both machines v263, image unchanged
(`deployment-01M45D8166J8M0CJFNNVXWXZY8`), `/health` revision = `655f2d13c66c79205014e88f3c1fb4e94a0d449f`; no `flyctl` /
`deploy.ps1` process survived. Per the reap notice the deploy was NOT restarted. The ONE authorized live Research
query (the log check) was NOT sent — it only means something against the new code.

**Founder rulings 2026-10-05, verbatim:**

> P1 Make /privacy TRUE in code rather than edit legal text: question text must not be written to server logs or sent to Sentry. Log length (and the existing 8-char hashed-id prefix) only. Applies to ALL users, not only anonymous.
> P2 FAQ Q5 (all 16 locales) is rewritten to match the code AFTER P1 — claim nothing the code does not guarantee.
> P3 The two production-build tests move out of the default pytest run (opt-in), so the full suite fits in memory.
> P4 Strategy-side correction recorded: the earlier claim "the banner readback could not fail" was WRONG (you measured 0/1 on HTML). Note it in the baton.

**P4 — recorded.** The closeout-v2 banner readback grepped the prerendered HTML document; `ArchiveBanner` returned
`null` with the flag off, so the readback could fail — measured banner = 0 in the flag-off `out/index.html` and 1 in the
archive build (§0 0b above). The strategy-side claim that it "could not fail" was wrong.

### §7.1 Commits

| commit | what |
|---|---|
| `4679ffb` | P3 — `tests/test_archive_ui_build.py` opt-in via `RUN_BUILD_TESTS=1` (module-level skipif) |
| `b23b729` | P1 — 40 log call sites + DB `hide_parameters` + Sentry options |
| `0cee36a` | P1 follow-up — reranker skip logs (2 sites) |
| `5b787c1` | P1 follow-up — generator (4) + guard (2) failure logs |
| `33266c5` | P2 — FAQ Q5 rewritten, 16 locales |
| `a62234a` | P1 follow-up — retrieval-refusal shadow `factor` (+ 3 background-task failure logs) |
| `83fdaf9` | end-to-end Research-route sentinel test (catch-all) |

### §7.2 P1 — derived log-site set vs the 3 cited (Rule 25; unit: logger / print call sites)

**Method.** An AST scan of every `logger.*` / `logging.*` / `print` call under `api/` whose arguments reference a
user-text-like name (47 candidates on the anchored name set, +6 on a substring set — all 6 prompt file paths), a
grep for log calls echoing an exception in the modules on the question path, and a read of each hit. **The 3 sites
cited by the previous car (`api/rag/retriever.py:178`, `:247`, `api/data_sources/pubmed.py:349`) are a SUBSET of the
derived set — they do NOT match it.** Changed: **52 call sites** + **2 non-log channels**:

| class | sites | where |
|---|---|---|
| A — question text (or text derived from it) interpolated directly | 24 | retriever 178 / 180 / 247 · pubmed 123 / 349 · fda 155 / 158 (`print`) · tfda_lookup 397 · server Verify drug lists ×3 · dailymed ×2 · explain_service ×6 · loinc / medlineplus / rxnorm ×4 · retrieval-refusal `factor` (server, `a62234a`) |
| B — exception text that can carry it (httpx `ConnectError` / `HTTPStatusError` text = the request URL with `term=` / `search=` — the openFDA URL also carries `api_key`; OpenAI error text; parser errors) | 28 | retriever ×10 · pubmed 142 / 154 / 356 / 376 · fda 183 / 263 · tfda_lookup 294 · reranker ×2 · generator ×4 · guards ×2 · background-task failures ×3 |
| non-log — DB error text | 1 | `api/database/sql_db.py`: `create_engine(hide_parameters=True)` — SQLAlchemy's error text carried the row values (an AuditLog's `query_content`) into `_safe_db_write`'s log and Sentry |
| non-log — Sentry | 1 | `api/server.py` `_sentry_init_kwargs()`: `include_local_variables=False`, `max_request_body_size="never"` (the `/api/research` body IS the question), `HttpxIntegration` disabled (it recorded outgoing URLs with their query strings as breadcrumbs and as span data on traced requests); `send_default_pii` stays `False` |

Every replaced site now logs a length, a count or `type(e).__name__`; levels and messages are otherwise unchanged.
Reachable in prod today: the Research-path sites; the Verify / Explain sites sit behind the 410 gate and were fixed so
the guarantee holds if ARCHIVE_MODE is ever lifted. **Cost, recorded:** the generator's 4 error logs lost their
traceback (`exc_info`) — a traceback's last line is the exception text. **Honest miss:** the first scan did not include
the name `factor`; the retrieval-refusal log was caught only by the Step-4 shadow-flag read — hence the end-to-end
catch-all test. Left as-is (not question text): `__main__` demo prints in `fda.py` / `pubmed.py` / `phi_handler.py`,
language codes, share ids, the Dodo cancel response body.

**Sentry logging integration:** left on — after P1 no log line on the question path carries question text, so its
INFO breadcrumbs carry none (proved by the end-to-end test, which runs with every shadow flag on).

**Tests** (`tests/test_no_question_text_in_logs.py`, 8): the retrieval path with the REAL PubMed + openFDA clients over
an httpx MockTransport whose errors carry the request URL; the filtered-out branch; a failing DB write; the Sentry
options; the reranker skip paths; generator + guard failures (guards still fail CLOSED); the retrieval-refusal shadow;
and the end-to-end `/api/research` route (signed-in + anonymous, ARCHIVE_MODE + all three shadow flags on, model
echoing the question) followed by the three background tasks. Each was seen RED first (4 failed → GREEN; then 1 failed
each for the reranker, generator/guard and refusal additions); mutation (old `retriever.py:178` restored) → 2 failed in
the retrieval tests and 1 in the catch-all; reverted byte-identical each time.

### §7.3 Client side (2d — read-only)

- **Sentry (client):** `sentry.client.config.ts:3-8` initialises with `dsn: process.env.NEXT_PUBLIC_SENTRY_DSN`; that
  value is `""` in `fly.toml:13` and the Dockerfile never passes it, so client Sentry has no DSN and sends nothing; no
  Replay integration is configured.
- **PostHog:** `pages/_app.tsx:41-44` sets only `capture_pageview: false` — posthog-js defaults apply: autocapture on
  (element metadata and text of clicks; input VALUES are not captured). `track()` events carry no question text.
  The Research `<input>` (`pages/research.tsx:658`) has no `ph-no-capture` class.
- **FOUNDER CHECK:** whether PostHog **session recording** is enabled is a PostHog project setting, not visible in the
  repo (its default masks inputs). Not guessed.

### §7.4 P2 — FAQ Q5 (`33266c5`), verbatim

- **en:** Questions asked in the demo are not saved to a database, and Vela no longer has accounts. To answer a question, Vela sends it to OpenAI's language model and sends search terms derived from it to PubMed and openFDA. Vela's server logs record a question's length, not its text. To enforce the daily budget, Vela keeps a usage count under a one-way hashed identifier made from your IP address and browser session; the count holds no question text. Usage analytics record events, such as how many sources were cited, not the text you type.
- **zh-TW:** 在展示版中提出的問題不會存進資料庫，Vela 也已不再提供帳號。為了回答問題，Vela 會把問題傳送給 OpenAI 的語言模型，並把依據問題產生的搜尋詞傳送給 PubMed 與 openFDA。Vela 的伺服器記錄檔只記下問題的長度，不記下問題的文字。為了控管每日預算，Vela 會用一個由你的 IP 位址與瀏覽器工作階段經單向雜湊產生的識別碼來記錄使用次數，這個計數不含任何問題文字。使用分析只記錄事件（例如引用了幾個來源），不記錄你輸入的文字。

The other 14 locales are MACHINE-TRANSLATED (marked). No claim about third-party retention or error reports.
**Not yet live** — it ships with the deploy that did not complete; until then prod still serves the pre-fix Q5 and
the pre-fix logging.

### §7.5 Step 4 — shadow flags (read-only report; both are Fly SECRETS — values not read)

| flag | when ON | extra calls per Research query | logs question text? |
|---|---|---|---|
| `SOURCE_WEIGHT_SHADOW` | `api/server.py` reads it per request; `retriever.retrieve()` captures the full reranked pool into a sink; after DONE, signed-in only, `_run_source_weight_shadow` (`api/server.py:721-756`) computes tier / composite would-be rankings locally (`api/services/source_weight_shadow.py`) and writes `AuditLog.extra_data['source_weight_shadow']` | **none** — local arithmetic, no LLM, no network | no — counts and tier distribution only |
| `RETRIEVAL_REFUSAL_SHADOW` | signed-in only: schedules `_run_retrieval_refusal_background` (`api/server.py:689-718`) → `retrieval_refusal.assess` (`api/services/retrieval_refusal.py:146-180`) on `gpt-4.1` (`:37`); writes the decision (incl. the question-derived factor / outcome) to `AuditLog.extra_data['retrieval_refusal']` | **N + 2 `gpt-4.1` calls** — 1 factor/outcome extraction, 1 per pool source (N ≥ 2), 1 counter-prior | it DID — `decision.factor` was logged verbatim; fixed in `a62234a` (length only) |

The anonymous demo runs neither observer (both sit in the signed-in branch); only `SOURCE_WEIGHT_SHADOW`'s pool capture
happens for everyone. **Recommendation (founder decides):** in an archived product neither shadow measures anything
that will be acted on, and `RETRIEVAL_REFUSAL_SHADOW` costs N + 2 `gpt-4.1` calls per signed-in query and stores
question-derived text in the AuditLog — unset both (`fly secrets unset RETRIEVAL_REFUSAL_SHADOW SOURCE_WEIGHT_SHADOW`,
which is itself a release). Their values were not read.

### §7.6 Gates and readbacks

| gate | result |
|---|---|
| full pytest (default) | Step 1: 504 passed / 38 skipped (baseline 504 / 28: +10 skipped = the opt-in module's 10 items, not +2 — all 10 share the build fixture). Step 5: **512 passed / 38 skipped** (+8 = the new privacy tests) |
| build tests (opt-in, `RUN_BUILD_TESTS=1`) | 10 passed (Step 1, 454 s); **10 passed** (Step 5, 609 s) — both `npm run build` variants exit 0 |
| `npx tsc --noEmit` | exit 0 |
| lint | problem set identical to the `2f09f83` baseline (22 = 22) |
| push | `2f09f83..83fdaf9`; `git ls-remote origin main` = `83fdaf9d44274731f7cd9f7806c4ad8a047a9544` = HEAD (40 chars) |
| deploy | attempt 1 reaped at the build-context upload — no release; prod unchanged (above) |
| prod readbacks + live log check | **NOT RUN** — they follow the deploy |

### §7.7 PROD EYE (BLANK — after the deploy)

| # | row | founder result |
|---|---|---|
| 1 | no banner; nav = Research + FAQ only | |
| 2 | landing has no Verify / Explain bands | |
| 3 | footer has the About link, no Pricing / Refund | |
| 4 | the archive FAQ shows | |
| 5 | anonymous Research answers a question | |
| 6 | /about/ en + zh-TW open | |
| 7 | FAQ Q5 reads correctly | |

### §7.8 Next

1. **Deploy** — `.\deploy.ps1` (run it from a terminal, or re-authorize a run here when the machine has memory headroom;
   background runs on this machine have now been reaped twice). Then the readbacks with the §0 markers + the ONE live
   Research query and the `fly logs` sentinel count ("side effects of metformin" → expected 0).
2. Founder: PROD EYE §7.7 · make the repo public (after the BSL-vs-MIT README decision) · delete the Dodo webhook ·
   OpenAI monthly hard budget · PostHog session-recording check (§7.3) · shadow-flag decision (§7.5).

### §7.9 CLOSEOUT — prod verified, fly 264 (2026-10-06)

The founder ran `.\deploy.ps1` in their own terminal (Claude Code background runs were being reaped under memory
pressure). Everything below was read by Claude Code, read-only and in the foreground, plus the ONE authorized
anonymous Research query.

| check | command | result |
|---|---|---|
| release | `fly releases -a vela-ai-medical` | **v264** complete (v263 before it) |
| machines | `fly status -a vela-ai-medical` | `2879720c66d478` + `683d447c2e5428` on v264, both started; image `deployment-01M47WM35VAADSEXFXZPWZD54Z` |
| /health | GET `/health` | revision `858d20ff2a51508b6fd2c731281f61e1900a1818` = the deployed HEAD (40 chars) |
| shadow secrets | `fly secrets list` (NAMES only, 19) | `RETRIEVAL_REFUSAL_SHADOW` **present**, `SOURCE_WEIGHT_SHADOW` **present** — not unset; `DIRECTION_CHECK_SHADOW` absent |
| retired API | unauth `POST /api/verify` | **410** `{"detail": "Vela is archived. This feature is no longer available."}` |

**Discriminating markers on prod (GET, prerendered HTML; unit = occurrences) — 23 / 23 as expected:**

| page | marker | expected | prod |
|---|---|---|---|
| / | `href="/verify"` · `href="/explain"` · `href="/pricing"` · `href="/refund"` | 0 · 0 · 0 · 0 | 0 · 0 · 0 · 0 |
| / | `data-band="verify"` · `data-band="explain"` · hero chip 2 text | 0 · 0 · 0 | 0 · 0 · 0 |
| / | `data-archive-link="about"` · `role="note"` | 1 · 0 | 1 · 0 |
| /research | `href="/verify"` · `href="/faq"` · `role="note"` | 0 · 2 · 0 | 0 · 2 · 0 |
| /faq | `data-archive-faq` · `href="/sign-up"` · `href="/refund"` · `data-archive-link="about"` | 1 · 0 · 0 · 1 | 1 · 0 · 0 · 1 |
| /faq | post-fix Q5 "length, not its text" (en) | 1 | 1 |
| /refund · /verify · /explain · /pricing | `data-archived-notice` | 1 each | 1 each |
| /about/ · /about/zh-TW.html | page title | 1 · 1 | 1 · 1 |

All nine pages answered 200.

**Live log check.** ONE anonymous query, "What are the common side effects of metformin?", sent with `curl -N` at
06:06:21Z: HTTP 200 in 17.2 s, a 2,209-character answer (471 answer events), 5 citations, a `done` event, no error
event. Then `fly logs -a vela-ai-medical --no-tail` (100 lines, 06:01:00Z → 06:06:36Z), ANSI-stripped and cut to the
window 06:06:21Z → 06:06:53Z (stream end + 15 s; 15 lines):

| term | window | whole output |
|---|---|---|
| "side effects of metformin" | **0** | 0 |
| "metformin" (any case) | **0** | 0 |
| Traceback | **0** | 0 |
| `api_key=` | **0** | 0 |

The fix is visible in the window: `vela INFO [Research] tier=L0 anon_id=6341dc58 query_length=46` (the question is 46
characters) and `api.rag.retriever INFO Query rewritten: len=46 -> 3 variants`. No line names the drug at all, so there
was no retrieval-term line to separate from question text.

E5 (`TECH_DEBT.md`, the 2026-10-06 bullet) stays OPEN — founder ratification pending to close.

### §7.10 LEDGER CORRECTIONS — E5 mislabel, shadow secrets unset, repo public (2026-10-06)

**The L2 mislabel.** The LICENSE FIX + E5 CLOSE car (2026-10-06, commit `75c34ee`) carried strategy-side ruling L2,
verbatim:

> L2 E5 (question text in logs) is RATIFIED CLOSED if step 2 returns YES: fix deployed fly 264, live sentinel log check = 0, regression guarded by tests/test_no_question_text_in_logs.py.

Step 2 returned YES, but E5 is not the logging issue. E5's heading and its Status bullet cover the SIGNED-IN wording
"de-identified (via PHI masking as a primary safeguard)" against the mask's actual coverage, which is waiting on
counsel. The logging problem was only E5's "Adjacent (a)" note. That car therefore held the close: nothing was
re-classed and E5 was left untouched. **Where the mislabel came from:** this car's own TECH_DEBT bullet
(2026-10-06, CODE FIX) ended "Founder ratification pending to close", and the last line of §7.9 above repeats it.
Both sentences meant Adjacent (a) only but read as if the log fix could close E5. They are kept verbatim
(mark-never-delete) and corrected here and in the E5 entry.

**Founder rulings 2026-10-06, verbatim:**

> R1 E5 stays OPEN (option B). Strategy-side ruling L2 mislabelled E5 as "question text in logs"; E5 is the privacy.tsx:30 signed-in "de-identified (via PHI masking)" wording vs the mask's coverage, awaiting counsel. Record the mislabel.
> R2 Shadow secrets RETRIEVAL_REFUSAL_SHADOW + SOURCE_WEIGHT_SHADOW were unset by the founder 2026-10-06 (fly v265, same code revision 858d20f).
> R3 The GitHub repo was made public by the founder 2026-10-06.

**Readbacks (read-only, 2026-10-06):**
- **R2:** `fly releases -a vela-ai-medical` top = **v265**, directly above v264. `/health` revision =
  `858d20ff2a51508b6fd2c731281f61e1900a1818`, unchanged, so v265 is a secrets-only release. `fly secrets list`, NAME
  column only (values and digests not read): neither `RETRIEVAL_REFUSAL_SHADOW` nor `SOURCE_WEIGHT_SHADOW` is present
  (0 of 2).
- **R3:** an unauthenticated request to GitHub's REST repo endpoint for this repository answered 200 with
  `"private": false` and `"visibility": "public"`.

**Line pin (Rule 25):** `45204fa` (2026-10-05) moved both privacy sentences down one line. At `2a5d98c`, where E5 was
measured, the anonymous claim was `pages/privacy.tsx:29` and the signed-in wording `:30`. At `75c34ee` they are `:30`
and `:31`. So E5's heading ":30" and the anonymous ":30" below are different sentences.

**The anonymous privacy claim at `75c34ee`** ("not stored or logged", `pages/privacy.tsx:30`): verified TRUE for
anonymous Research. This basis is copied from the previous car's reply; each line was re-read at HEAD `75c34ee`
before this commit. `git diff 858d20f 75c34ee -- api` is empty, so the API code is the fly 264 revision.
- **Database:**
  - the audit log is written only for signed-in users (`api/server.py:1051`, `if not is_anonymous:`);
  - chat history is written only on the signed-in branch and is skipped under ARCHIVE_MODE (`api/server.py:1092-1095`);
  - the anonymous DONE branch writes only a usage counter under the hashed id (`api/services/usage_service.py:213-218`)
    and a cost row of model and token counts (`api/services/cost_tracker.py:45-52`). Neither holds question or answer
    text.
- **Logs (lengths only):** `api/server.py:890`, `api/rag/retriever.py:178` and `:247`, `api/data_sources/pubmed.py:123`
  and `:349`.
- **Sentry and the database driver:** Sentry starts with `_sentry_init_kwargs` (`api/server.py:26`), and the database
  engine hides bound parameters (`hide_parameters=True`, `api/database/sql_db.py:25` and `:32`).
- **Regression guard:** `tests/test_no_question_text_in_logs.py` (8 tests). The live sentinel log check at fly 264
  returned 0 (§7.9).
- **Residuals (flagged, not fixed — no code change was authorized):**
  - `api/server.py:1029` logs an LLM exception's text, but only when `QUESTION_NEUTRALIZATION_SHADOW` is set. That
    name is in neither `fly.toml [env]` nor the Fly secret names, so the line cannot run in prod.
  - `api/server.py:865` and `:789` log exception text, but the code that raises there never puts the question into
    its errors: a regex check, a lookup that logs only the exception type (`api/services/tfda_lookup.py:294`), and
    the PHI regex detector.

**Status after this commit:**
- **E5:** OPEN. Its Adjacent (a) is resolved; the signed-in wording waits on counsel.
- **Founder checklist:** PROD EYE (§7.7, 7 rows) · delete the Dodo webhook and revoke the API key · OpenAI monthly hard
  budget · turn PostHog session recording off · E5 counsel wording.
