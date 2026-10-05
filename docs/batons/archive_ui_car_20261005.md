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
