# 在地差異提示 — b1 (locale-detection waterfall + Tier-2 + SG/MY) + b1-fix — BUILD RECORD

**Shipped:** b1 = **fly 212** (2026-07-26, commits `65ac21f` → `ab8a35c` → `e0ef382`) ·
b1-fix = **fly 213** (2026-07-27, commit `24ec545`).
**Classification:** FRONTEND-ONLY both ships — **zero `api/`**, zero `.py`, zero `fly.toml`/`Dockerfile`/`requirements`.
**Flag:** `NEXT_PUBLIC_LOCALE_HINT_ENABLED` was ALREADY `"true"` (`fly.toml:12`, since fly 210) — there was **no flag-OFF
staging step**; each deploy went live for all users on landing.

> **Why this file exists (kunion baton-A convention).** The working build report lived at
> `tests/results/locale_waterfall_b1_step0_report.md`, which is **gitignored** (`.gitignore:113`) — so b1's build context
> survived nowhere in the repo. This is the promoted, durable version.

---

## 1. What shipped

**b1** extends the fly-210 Taiwan-only panel into a country-resolving system:

- **`utils/country.ts` (new)** — `CountryCode {TW,JP,KR,SG,MY,TH}` + an `OTHER` sentinel, and a **pure**
  `resolveCountry()` waterfall (zero network, zero localStorage, zero imports → unit-testable standalone).
- **Waterfall:** **L1** Settings locale > **L2** `work_language` (zh-TW→TW · ja→JP · ko→KR · th→TH) > **L3** timezone
  (Asia/Taipei→TW · Tokyo→JP · Seoul→KR · Singapore→SG · Kuala_Lumpur→MY · Bangkok→TH) > **L4** UI language (same 4 as L2).
  **L3 MUST stay above L4** — SG/MY are English-speaking, so timezone is their ONLY implicit path.
  L1 `OTHER` is **terminal** (the user has said "use international sources"), it does NOT fall through.
- **No IP geolocation** — frontend-only by decision (see §7 drift D).
- **RULE 1 — two independent axes:** the **answer language** picks the keyword list (*does it fire?*); the **resolved
  country** picks the authorities (*what does it point to?*). Resolving a country never changes the panel language.
- **RULE 2 —** a resolved country with **no Tier-1 data** (JP/KR/TH in b1) falls to **Tier-2**, never an empty/broken panel.
  So b2 is pure data work: no resolver change needed.
- **Tier-1 data:** TW (TFDA + NHI, byte-identical to fly-210) · SG (HSA + MOH) · MY (NPRA + MOH).
  **Tier-2:** WHO · NICE · EMA · Cochrane.
- **Settings** gained a Country/region selector (`MyContextTab.tsx` → `setLocale` → `vela_user_context.locale`).

**b1-fix** repairs the one gate defect and adds gate instrumentation — see §5 and §6.

---

## 2. English keyword list — FINAL 29 terms

The zh-TW list is **byte-identical to fly-210** and was not touched. The EN list is new in b1.

| Category | Count | Terms |
|---|---|---|
| **dosing** | **6** | `starting dose` · `initial dose` · `maximum dose` · `dose adjustment` · `dose titration` · `dosing regimen` |
| **reimbursement** | **12** | `reimburse` · `formulary` · `insurance coverage` · `out-of-pocket` · `out of pocket` · `copay` · `co-pay` · `prior authorization` · `prior authorisation` · `subsidy` · `subsidized` · `subsidised` |
| **indication** | **8** | `approved indication` · `licensed indication` · `off-label` · `off label` · `approved use` · `marketing authorization` · `marketing authorisation` · `label indication` |
| **contraindication** | **3** | `black box warning` · `black-box warning` · `boxed warning` |

### 2.1 Calibration intent — deliberately TIGHTER than zh-TW (29 vs 34)

zh-TW fires only on zh-TW answers and was validated in one country. **English fires on English answers globally, and
English is many users' default UI language** — so the same false-positive *rate* is a far larger absolute volume. A panel
that becomes wallpaper cannot be un-rung. Widen later **from PostHog data**; do not widen on intuition.

### 2.2 Precision cuts (behavior-changing) — rationale per cut

- **`prescribing information`, `package insert` — CUT from `indication`.** These are the **official label documents' own
  names**. DailyMed has been the **5th Research retrieval source since fly 206**, and **fly 209 + fly 211 both deliberately
  raised the rate** at which official label safety sections reach the cited pool. These two terms would therefore fire on a
  large share of ordinary drug answers that have **no local-regulatory-difference angle** — the panel would follow DailyMed
  around rather than track local difference.
- **bare `titrate`, bare `titration` — CUT from `dosing`.** Generic clinical prose verbs — the English equivalent of the
  bare dosage terms **v188 already stripped from zh-TW** (劑量/用量/dose/dosage/mg/劑型). The compound decision term
  **`dose titration` is KEPT**.

### 2.3 Substring de-dup (zero behavior change)

Matching is **SUBSTRING**, case-insensitive (`lower.includes(kw.toLowerCase())` in `detectLocaleCategories`), **not
word-boundary**. Each term below is a strict subset of a retained term, so removing it changes nothing:

| Dropped | Covered by |
|---|---|
| `renal dose adjustment`, `hepatic dose adjustment` | `dose adjustment` |
| `reimbursement` | `reimburse` |
| `co-payment` | `co-pay` |

Verified programmatically: **0 substring redundancies remain, 0 duplicates.**

### 2.4 KNOWN LIMITATION — `contraindication` is boxed-warning-only

The category contains **only boxed-warning phrasings — one concept, and a US-FDA-specific construct**. In b1 it
effectively detects *"this answer mentions a US boxed warning"*, **not contraindications generally**. Deliberately NOT
widened: doing so now would be guessing. **Revisit once PostHog shows the real category distribution.**

### 2.5 PARKED — `subsidy` / `subsidies` recall gap

Under substring matching `subsidy` does **not** cover `subsidies` (different stem). The obvious stem `subsidi` would
false-match `subsidiary`, and adding bare `subsidies` alone over-fits one plural. **Parked for the PostHog tuning round —
resolve with data, not a guess.**

---

## 3. Authority data + link status

| Country | Authority | name_native | name_en | url_native | HTTP | covers |
|---|---|---|---|---|---|---|
| TW | TFDA | 衛生福利部食品藥物管理署 | Taiwan Food and Drug Administration | fda.gov.tw | 200 ✓ | dosing, indication, contraindication |
| TW | NHI | 衛生福利部中央健康保險署 | National Health Insurance Administration | nhi.gov.tw | 200 ✓ | reimbursement |
| SG | HSA | Health Sciences Authority | *(same)* | hsa.gov.sg | 200 ✓ | dosing, indication, contraindication |
| SG | MOH | Ministry of Health | *(same)* | moh.gov.sg | 200 ✓ | reimbursement |
| MY | NPRA | **Bahagian Regulatori Farmasi Negara** | National Pharmaceutical Regulatory Agency | npra.gov.my | 200 ✓ | dosing, indication, contraindication |
| MY | MOH | Kementerian Kesihatan Malaysia | Ministry of Health Malaysia | moh.gov.my | **403 ⚠️** | reimbursement |
| Tier-2 | WHO / NICE / EMA / Cochrane | — | — | who.int / nice.org.uk / ema.europa.eu / cochrane.org | 200 ✓ | see code |

- **NPRA's Malay name** was confirmed from official domains (`npra.gov.my/index.php/my/`, `pharmacy.moh.gov.my`) as
  **"Bahagian Regulatori Farmasi Negara"** — NOT the WebFetch model's first guess "Agensi Farmaseutikal Kebangsaan",
  which the model itself flagged as unconfirmed. Per the no-machine-translation rule, the confirmed official name was used.
- **`moh.gov.my` = TOOL-UNCONFIRMED (403 to automated checks) / BROWSER-CONFIRMED at the gate.** Both `curl` (browser UA)
  and WebFetch got 403 — a **WAF bot-block, not a dead site**. It is the official Malaysia MOH domain and the structural
  sibling of the HTTP-200-confirmed `moh.gov.sg`. Founder browser-confirmed it live at gate row 2.
  ⚠️ **The PRD §5.1.1 monthly `url_native` HEAD-check cron will 403 on this URL forever** — it needs an allowlist
  exception when that cron is built, or the one permanently-crying URL erodes the whole link-health layer.
  Recorded in **TECH_DEBT [P2 · link-health cron]** and as an inline comment at the `MY_MOH` entry.
- **Tier-2 `covers` mapping (judgment call):** WHO/EMA/Cochrane → dosing + indication + contraindication;
  **NICE → reimbursement** + indication + contraindication (NICE does HTA/cost *and* clinical guidance). So a
  reimbursement-only Tier-2 query shows **NICE only**.
- **MOH → reimbursement (judgment call):** SG/MY mirror TW (regulator → dosing/indication/contraindication; ministry →
  reimbursement), since in SG/MY the Ministry of Health runs drug subsidy / the national formulary.

---

## 4. i18n approach — APPROVED DEVIATION from "7 strings × 16 locales"

Country options use **native endonyms + a Latin name in parentheses** — 台灣 (Taiwan) · 日本 (Japan) · 대한민국 (South Korea) ·
Singapore · Malaysia · ประเทศไทย (Thailand) — so the 6 options need **no per-locale i18n keys**. SG/MY carry no
parenthetical because their endonyms already *are* the Latin names.

This **deliberately differs** from the sibling answer-language selector's pure-endonym style: that list is chosen **by
someone who reads the target language**; this one is not, so a reader who cannot parse the script still needs an anchor.

Only **2** new keys were added (`myContextCountry` heading + `myContextCountryOther`), as **optional**, with en + zh-TW
real and an **en-fallback** in the component for the other 14 UI locales. Net cost: 2 English strings visible in 14
non-en/zh-TW Settings UIs — versus the **7 × 14 = 98 placeholder cells** the literal spec would have added to a codebase
where **14 of 16 locales are already English placeholders**.

Panel strings: `localeHintTitle`/`Lead` templated with `{country}`; `localeHintTitleTier2`/`LeadTier2` added. en + zh-TW
real, 14 EN placeholders — invisible, because the panel renders only in en / zh-TW in b1.

---

## 5. FIX 1 — TW-specific category label leaked to every country (found at the b1 prod gate)

**Symptom.** Timezone `Asia/Kuala_Lumpur` + an English reimbursement query resolved to **Malaysia** correctly and
rendered NPRA + MOH with `name_en` correctly — but the category chip read **"NHI reimbursement"**. NHI is *Taiwan's*
National Health Insurance. A Malaysian pharmacist must never see it.

**Root cause.** The TW term was baked into the **shared i18n string itself**: `localeHintCatReimbursement` was authored as
`'NHI reimbursement'` (en, and all 14 EN-placeholder locales) / `'健保給付'` (zh-TW) back when the panel was **Taiwan-only**
(fly-210). The b1 restructure made the **authority data** country-keyed but never revisited the **label strings**, which
stayed flat and country-independent — so every country rendered Taiwan's insurer.

> ### ⚠️ CLASS OF BUG — what b2 must check when adding JP/KR/TH
> **b1 country-keyed the DATA but not the STRINGS.** Any user-visible string authored during the Taiwan-only era is
> **suspect until proven country-neutral**. The country-keying refactor moved the authority data and stopped there.
> Do not assume a string is generic because the data around it is.

**Audit of the other three categories + Tier-2 (performed at fix time).** `dosing` (Dosing / 劑量), `indication`
(Indication / 適應症), `contraindication` (Contraindication / warnings / 禁忌／警語), `localeHintTitle`/`Lead`
({country}-templated), `localeHintNote`, and both Tier-2 strings are **all country-neutral — NO other leak found**.
Two `健保` hits elsewhere are correct and were left alone: `i18n-share.ts` (健保號 in a PHI-consent string — a field name)
and the zh-TW **detection keyword** `'健保'` in `localeHint.ts` (a trigger term, not a label; fires only on zh-TW answers).

**Fix.** Country-neutral default in i18n (`'Reimbursement'` / `'給付'`, all 16 locales) + an **optional per-country
`cat_labels` override** on the country data entry. TW opts back into `NHI reimbursement` / `健保給付` — genuinely better
*for Taiwanese users*. Every other country and Tier-2 gets the neutral default with **zero extra data**. Resolution is a
generic data lookup — `getCategoryLabelOverride(tier1, cat, lang) ?? ui[CAT_LABEL_KEY[cat]]` — **not** a TW special case
in render logic, so b2's JP/KR/TH inherit the neutral label purely by having no override.

**Guard (`tests/locale_hint_data_guard.mjs`).** For every non-TW country entry and for Tier-2, assert no category label
contains `NHI` or `健保`; assert **TW keeps** its override; assert TW has no override on the other three; and
**source-scan `utils/i18n-ui.ts`** so the neutral defaults stay neutral across all 16 locales (≥64 `localeHintCat*` lines).
**Both halves were negative-controlled**: re-introducing the i18n leak fails the guard (1 failure); giving MY a
TW-flavoured override fails it (18 failures). A guard that has never failed on a real instance of the bug is not evidence.

---

## 6. FIX 2 — `?localeDebug=1` opt-in resolution display

When the URL carries `?localeDebug=1` the panel renders a muted `country · level · tier` line. Without the param it
renders **nothing** — no element, no layout shift, no console output. Read in a `useEffect`, not during render, because the
app is a **static export** and touching `window` during render would desync hydration; it is a runtime URL read, so **it
works on PROD**, which is where the human-eye gate runs. The values are already computed for the PostHog payload — this
surfaces existing state, it adds no logic.

**Why it earns its place (do NOT re-derive this at the b2 gate).** Verifying b1 on prod **burned several paid queries on
failures that were pure measurement artifacts, not code defects**:

- DevTools timezone overrides **silently reset between queries**;
- the page **navigated back to Research mid-run**, dropping the override;
- DevTools' own **"Locale" field looks like it sets the app's locale but only overrides `navigator.language`** — which
  this waterfall never reads.

There was no way to see which waterfall level actually fired short of reading `localStorage` in the console before **every
single query**. b2 adds five more countries, so this gets strictly worse.

**It paid for itself immediately.** At the mini-gate the debug line showed `level=work_language` where the founder
expected `ui_lang` — **correct behavior that would otherwise have been misread as a defect**. So the value is not only
saved queries: it **prevents false FAIL calls at the gate**. **Start the b2 gate with `?localeDebug=1` on.**

**Known scope boundary (accepted).** The line renders only when the **panel itself renders**. On a no-fire query the
country is never resolved (`research.tsx` resolves only after a keyword matches), so there is nothing truthful to display —
showing `level=none` there would mislead rather than help.

---

## 7. Gate results

### 7.1 b1 prod human-eye gate — fly 212, 2026-07-26 — **PASS with one defect**

**PASSED:** SG via timezone (L3) · MY via timezone (L3) · TW via ui_lang (L4) · US → Tier 2 · JP → Tier 2 (resolves but
has no Tier-1 data → correctly falls back, **not** a broken panel — RULE 2 holds) · **L1 > L3 precedence** (Settings=SG
with a real `Asia/Taipei` timezone → Singapore panel) · no-fire on a mechanism-of-action query (English keyword precision
holds) · zh-TW regression sample: dosing fires, dosing+indication fires with **both** labels shown, per-query dismiss still
re-shows on the next query · **`moh.gov.my` BROWSER-CONFIRMED**.

**FAILED:** the `reimbursement` category chip → **FIX 1** (§5).

### 7.2 b1-fix mini-gate — fly 213, 2026-07-27 — **PASS**

| Row | Setup | Result |
|---|---|---|
| **F1** | TZ `Asia/Kuala_Lumpur`, English, reimbursement query | **Malaysia** panel; chip reads neutral **"Reimbursement"**; **zero NHI anywhere**; MOH rendered with `name_en`. Debug: `country=MY · level=timezone · tier=1`. **The leak is fixed.** |
| **F2** | zh-TW answer language, no TZ override, 「metformin 的起始劑量與健保給付規定?」 | **Taiwan** panel, **two** chips: 劑量 and **健保給付** — the TW override **survived**, the fix did not over-correct. TFDA + NHI both rendered. Debug: `country=TW · level=work_language · tier=1`. |

### 7.3 ✅ FOUR-LEVEL COVERAGE IS COMPLETE

Across the b1 and b1-fix gates, **every waterfall level was exercised on prod with a real user session** — stronger
evidence than the row list alone conveys:

| Level | Exercised by | Evidence |
|---|---|---|
| **L1** settings | Settings = SG with a **real** `Asia/Taipei` timezone | SG panel → L1 beats L3 |
| **L2** work_language | mini-gate **F2** | debug line read `level=work_language` — the zh-TW **answer language** matched at L2, so L4 was never reached |
| **L3** timezone | SG, MY, and JP→Tier-2 rows | debug `level=timezone` |
| **L4** ui_lang | TW panels while `work_language` was `"en"` | TW resolved with no L2/L3 hit |

### 7.4 ✅ ORIGINAL ROW 5 (isFallback suppression) — VERIFIED post-restructure, no longer "N/A"

The first F2 attempt asked 「metformin 有健保給付嗎?」 — a **pure policy question that PubMed and FDA cannot answer** — so it
returned the 「未找到與此查詢相關的文獻／基於一般醫學知識」 fallback, and **the panel correctly did NOT render**. That confirms the
`!isFallback` gate **survived the b1 restructure**. Previously recorded as "N/A — covered by fly-210"; now **VERIFIED**.

An ungrounded answer must never receive false local-authority credibility — this gate is the reason.

### 7.5 Rows not run (with reason)

Row 6 (ja UI — **no `ja` keyword list in b1 by design**, so no-fire is the spec, not a gap) · Row 9 (`locale="Other"` —
same selector code path as row 10, which passed).

---

## 8. PRD reconcile — canonical A–G drift table

This is **the canonical numbering**. Earlier STATE wording referred to "drifts 1/3/4", a numbering that existed nowhere in
the repo; STATE now points here.

| # | Drift | Resolution (applied in the same commit as this file) |
|---|---|---|
| **A** | §5.1 acceptance said Tier 1 covers **"12 國"** | → **6** (TW/JP/KR/SG/MY/TH). The +6 expansion (VN/PH/ID/HK/SA/AE) is tracked separately as its own BACKLOG item. |
| **B** | §5.1 acceptance required **"LLM 正確識別"** | → the **deterministic-keyword** bar, per the 2026-06-25 revision that already superseded the LLM-in-generator-prompt trigger design. The acceptance line had not been updated to match. |
| **C** | §5.1.1 `config/locale_authorities/` YAML · `global_fallback.yaml` · `get_authorities(locale)` | → marked **(e)-SCOPED**. **b1 shipping must NOT be read as §5.1.1 acceptance met** — the **behavioral half is done** (waterfall, Tier-2 fallback, 6-country resolution, `locale=US → Tier 2`), the **structural half is not** (data is still a frontend TS constant, not backend YAML). |
| **D** | §5.1 detection logic listed **IP geolocation** as a signal | → **struck**. b1 is **frontend-only, no IP** by decision: no server round-trip, no new PII surface, and the panel must work without a backend call. The waterfall is L1 settings > L2 work_language > L3 timezone > L4 ui_lang. |
| **E** | §4.3 said **"Locale(Phase 1C 啟用 UI)"** | → **Phase 1B**; the selector **shipped and was gate-verified** in b1 (Settings → My Context → Country/region writes `locale`, and L1 > L3 was proven on prod). |
| **F** | §5.1 / §5.1.1 headers carried inconsistent Phase markers | → normalized to **Phase 1B**. |
| **G** | PRD PostHog payload spec listed `{ query_id, locale, tier, authorities_count }` | → reconciled with the **actual** fields, which now include **`resolved_country`**, **`resolution_level`**, and **`tier`**. The misleading hardcoded `locale:'TW'` was removed from all three events in b1. |

### 8.1 `url_search_pattern` — DELIBERATE DEVIATION (PRD amended to match code)

PRD §5.1.1 specifies a `url_search_pattern` field per authority (e.g.
`https://www.fda.gov.tw/TC/siteListContent.aspx?sid=1619&q={query}`). **b1 omits it, and that stays.**

A **pointer panel does not need query-injection URLs** — it names the dimension that may differ locally and links the
authority's front door for the user's own verification. Injecting the user's query into a foreign site's search
parameters is fragile (every one of those URL shapes is a private contract that breaks silently on a site redesign) and
**unused fields rot** — a field nothing reads is a field nobody maintains, and a stale one is worse than an absent one.
**The PRD is amended to match the code**, not the other way round.

---

## 9. Verification record

| Check | b1 (fly 212) | b1-fix (fly 213) |
|---|---|---|
| `tests/resolve_country_guard.mjs` | PASS | PASS |
| `tests/locale_hint_data_guard.mjs` | PASS | PASS (+ anti-leak assertions, negative-controlled) |
| `tests/verify_attribution_guard.mjs` | PASS | PASS |
| `npx tsc --noEmit` | exit 0 | exit 0 |
| `npm run build` | exit 0, 15 pages | exit 0, 15 pages |
| Lint | skipped — 7 pre-existing errors in files b1 never touched; the deploy build itself skips linting | same |

**Post-deploy bundle verification (fetched from live chunks, not inferred from the build log):** all 10 authority URLs
present · all 6 timezone keys + `work_language`/`ui_lang`/`OTHER` present · keyword arrays byte-exact to the approved 29 ·
`name_en` strings present · country labels present · neutral `Reimbursement` ×15 + `給付` ×1 with **0** `NHI` in i18n keys ·
`cat_labels` present exactly twice (the TW data entry + the inlined `override ?? default` lookup) · `localeDebug` present.

**Lever state — UNCHANGED across both ships** (frontend code only, no flag changes), enumerated **BY NAME** because the
three ON flags share Fly digest `d8c5ac2e11c8e492` (Fly hashes the *value* `'true'`, so a shared digest proves nothing
about which flag it is):

`RETRIEVAL_REFUSAL_SHADOW` ON · `SOURCE_WEIGHT_SHADOW` ON · `SOURCE_WEIGHT_ACTIVE` ON ·
`DIRECTION_CHECK_SHADOW` OFF · `QUESTION_NEUTRALIZATION_SHADOW` OFF (both **absent** from secrets; all five read
`os.getenv(NAME, "").lower() == "true"`, so absent = OFF) ·
**locale-hint ON via `fly.toml [build.args]`** — a build-arg, **never visible in `fly secrets list`**; auditable only in
committed `fly.toml`, verified unchanged by both ships.

**Log-grep:** clean on both deploys — zero ERROR/WARNING/CRITICAL/Traceback/Exception/`RERANK_SKIP`/`SOURCE_WEIGHT_INERT`,
zero 4xx/5xx. *(Scope: the log window covers the deploy and HTTP probes; Research **query** traffic is exercised by the
founder's gate runs, which require auth and credits.)*

---

## 10. What b2 inherits

1. **Pure data work.** `resolveCountry` already returns JP/KR/TH; they fall to Tier-2 by RULE 2. Adding their Tier-1
   authority entries is the whole job — **no resolver change**.
2. **Check the STRINGS, not just the data** — see the class-of-bug box in §5.
3. **Run the gate with `?localeDebug=1` from the first query** — see §6.
4. **The anti-leak guard already covers JP/KR/TH**: they get the neutral label by having no override, and the guard
   asserts exactly that.
5. **Blocked on native review** for the label/authority strings — see BACKLOG 在地差異 Tier 1 (b2).
6. **Open items carried forward:** the `contraindication` boxed-warning-only limitation (§2.4), the `subsidy`/`subsidies`
   recall gap (§2.5), L1 discoverability (BACKLOG sub-item (f)), and the `moh.gov.my` link-health cron exception
   (TECH_DEBT [P2]).
