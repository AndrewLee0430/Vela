# c1 — local drug corpus DEPRECATION: build + gate record (2026-07-29)

**🔴 This IS a retrieval change** (a source is removed) → section-aware danger-path re-gate + prod
human-eye gate required. No flags, no secrets, no thresholds, no composite weights, no `top_k` touched.

> ## 🚀 DEPLOYED fly 215 — 2026-07-29 · founder human-eye gate **PENDING**
>
> Image `registry.fly.io/vela-ai-medical:deployment-01KYQ8N0FWA262D2C5DFTHDHGH` (333 MB), nrt.
> Scope vs the fly-214 commit (`b19d3a8`): **6 files** — `api/rag/retriever.py`, `api/server.py`,
> `api/services/share_renderer.py`, `scripts/build_drug_vectordb.py`, `tests/citation_url_guard.mjs`,
> `utils/sourceLabels.ts`. **`fly.toml`, `Dockerfile`, `requirements.txt` untouched. No migration.**
>
> ### Post-deploy verification
>
> | # | check | result |
> |---|---|---|
> | 1 | `/health` | **PASS** — 200, `{"status":"healthy","version":"2.2.0"}` |
> | 2 | both machines on the new version | **PASS** — `2879720c66d478` and `683d447c2e5428` both **215**, hand-parsed from the `│` rows (not `deploy.ps1`'s "All machines running", whose `^\S+` parser has a known [P3] defect). `2879720c66d478` `stopped` = the documented benign autostop |
> | 3 | `/api/status` new shape | ⚠️ **NOT COMPLETED — see below** |
> | 4 | levers unchanged by name | **PASS** — `RETRIEVAL_REFUSAL_SHADOW` · `SOURCE_WEIGHT_SHADOW` · `SOURCE_WEIGHT_ACTIVE` all **present, digest `d8c5ac2e11c8e492`, Deployed = ON**; `DIRECTION_CHECK_SHADOW` and `QUESTION_NEUTRALIZATION_SHADOW` **absent = unset = OFF**; **every secret reads `Deployed` — none staged** |
> | 5 | b1 locale panel + `?localeDebug=1` | **PASS** — chunk `research-757f6f067e7cc77a.js` carries hsa.gov.sg · npra.gov.my · moh.gov.my · fda.gov.tw · nhi.gov.tw · who.int · `Asia/Kuala_Lumpur` · `localeDebug` ×2 · `cat_labels` ×2 · `健保給付` ×1, and **0** `NHI` in i18n keys. ⚠️ **The chunk hash is IDENTICAL to fly 214** — expected: the only frontend change was a *comment* in `sourceLabels.ts`, stripped at build. **The frontend is byte-identical; this deploy is a backend-behaviour change only.** |
> | 6 | log-grep | **PASS** — and the decisive line: startup logs show **only** `TFDA indication corpus loaded: 10941` and `DailyMed label corpus loaded: 4608`, with **NO `Vector store loaded: 690 documents` line**. That is direct production confirmation the corpus is not loaded. No ERROR / CRITICAL / Traceback; the only non-2xx is my own probe's 403 |
> | 7 | a published share/explore page still renders | **PASS — and it exercised the exact legacy path.** `/explore/metformin-contraindications-renal?locale=en` → **HTTP 200**, 5 citation cards, **0** tracebacks, and it renders **`[2] Local`** — a pre-ship `local` citation still labelled correctly through the retained fallback. **Had the mapping been removed, this live SEO-indexed URL would have silently relabelled to "Source".** *(It also makes the recorded [P2] `sourceLabels`↔`share_renderer` drift visible: this page says "Local" where the app says "FDA". Pre-existing, unchanged by this ship.)* |
>
> ### ✅ FOUNDER PROD HUMAN-EYE GATE — **PASS, 8/8** (2026-08-03) → **SHIPPED**
>
> | row | query | result |
> |---|---|---|
> | 1 | metformin renal (EN) | DailyMed 2 + PubMed 2, **no FDA chip**, renal dosing + lactic acidosis covered — **PASS** |
> | 2 | `warfarin 和 aspirin 一起用 safe 嗎` | PubMed 3, **no FDA chip**, bleeding risk warned — **PASS** |
> | 3 | aspirin contraindications | 1 citation — **PASS on the written criterion**, ⚠️ **but the citation is the WRONG DRUG (Finding A)** |
> | 4 | ibuprofen warnings | DailyMed 2 + PubMed 2, GI/CV warned — **PASS**, ⚠️ **`[1]` is the wrong drug (Finding A)** |
> | 5 | **no "FDA" chip anywhere, all rows** | **PASS — the c1 objective, confirmed on prod** |
> | 6 | `冠脂妥台灣核准的適應症是什麼` | TFDA 核准適應症 **×4** — **PASS** (see Finding C) |
> | 7 | `metformin 腎臟不好的病人可以用嗎` | DailyMed 3 + PubMed 2 — **PASS** |
> | 8 | statins canary | PubMed 4 only, no safety intrusion, no FDA chip — **PASS** |
>
> **Both halves of the c1 objective hold on prod: the empty-stub "FDA" chip is gone, and no answer lost
> clinical content.**
>
> **⚠️ 3.3 REMAINS UNVERIFIED ON PROD — CODE-VERIFIED ONLY.** `/api/status` is `Depends(require_auth)` and prod
> runs real Clerk auth, so an unauthenticated request returns **403 `{"detail":"Missing token"}`** — I have
> no prod session. What that *does* prove: the route exists and the handler is reachable (a clean 403, not
> a 500). What it does **not** prove: that the payload is the new `{"status":"deprecated", …}` shape on
> prod.
>
> **⚠️ AND A BROWSER SESSION CANNOT CLOSE IT EITHER — confirmed by the founder.** `require_auth` reads a
> **Bearer token**, not a cookie, so a signed-in browser hitting `/api/status` still returns
> `{"detail":"Missing token"}`. **Status: CODE-VERIFIED ONLY, never prod-verified. Do not record it as
> verified.**
>
> **Cheapest ways to close it (proposed, NOT built):** **(a)** copy a live Clerk JWT from the browser
> devtools Network tab (any authenticated XHR carries `Authorization: Bearer …`) and replay it with one
> `curl -H`; **(b)** add `/api/status` to the unauthenticated allowlist — ⚠️ **NOT recommended**, it
> exposes corpus/feature internals publicly for a debug convenience; **(c)** fold the assertion into the
> next authenticated smoke test rather than checking it standalone. **(a) is a 30-second manual step and
> needs no code change** — that is the recommendation.

Basis: [`citation_gate_findings_20260729.md`](citation_gate_findings_20260729.md) Finding 1 ·
[`local_corpus_decision_20260729.md`](local_corpus_decision_20260729.md) (`3e32c03`).

**Rationale recorded as decided:** local's complementary coverage exists ONLY in `full_label`, which is
**not indexed**. The indexed content is ≤ 20 chars (max 5, median 1), so **the corpus delivers zero
value as shipped, regardless of repair**. Repair (option b) is rejected: it would import 22/190
combination-product records, repackager-first selection, and an unusable URL — and **c2 obtains the same
coverage from the real SPL instead**.

---

## Task 0 — `/api/status` bypassed `enable_local` (BLOCKER) → **report as deprecated**

`api/server.py:2418` called `get_vector_store().get_stats()` **directly**, so disabling the source would
**not** have stopped the 690 docs loading into memory — the deprecation would have been incomplete and
the endpoint would have kept reporting a corpus nobody queries.

**Decision: report it as deprecated, do not delete the key.** `/api/status` is ops/debug only — **no
frontend code reads it** (grep: referenced only in docs and one TECH_DEBT deploy-polling suggestion), so
the shape could have been dropped; keeping it is free and avoids breaking an unknown ops consumer, while
the payload now tells the truth:

```json
"vector_store": {"status": "deprecated",
                 "note": "local drug corpus removed from Research retrieval 2026-07-29 (c1)"}
```

## Task 1 — the ship

| change | file | why |
|---|---|---|
| `enable_local=False` + rationale comment | `api/server.py:449` | the **only** retrieval wiring point; `retriever.py:109` and `:180` both already guard on it, so this is a supported, test-covered path |
| **`enable_local` DEFAULT flipped `True → False`** | `api/rag/retriever.py:96` | ⚠️ **not cosmetic — see the incident below** |
| `/api/status` no longer loads the store | `api/server.py:2426` | Task 0 |
| deprecation header, ⛔ do-not-run + do-not-"fix" | `scripts/build_drug_vectordb.py` | re-running it rebuilds the same empty corpus; the defect is upstream in `collect_drug_data.py` |
| exemption retired → **deprecation invariant** | `tests/citation_url_guard.mjs` | the exemption's subject is gone |
| legacy-only annotations (**comments only, no string changes**) | `utils/sourceLabels.ts:61`, `api/services/share_renderer.py:195` | persisted-artifact safety — see Task 3.7 |

### ⚠️ INCIDENT — the first danger-path re-gate was INVALID, and it exposed a whole class

The first run of `scripts/dailymed_danger_path_verify.py` returned a clean 0/0 — and its log said
**`✅ Vector store loaded: 690 documents`**. The harness builds `HybridRetriever()` **with no arguments**
(`:181`), so it inherited the library default `enable_local=True` and **measured the pre-ship config**.
That result was discarded, not reported.

**It is not one script. Nine harnesses construct `HybridRetriever()` bare** —
`dailymed_danger_path_verify`, `direction_shadow_eval`, `pathb_recall_probe`, `pathb_scope_probe`,
`question_neutralization_eval`, `retrieval_recall_check`, `source_weight_activation_verify`,
`source_weight_local_tier_sweep`, `source_weight_shadow_eval`. While the server also passed `True` they
matched production **by accident**; the moment production stopped using local, every one of them would
have kept measuring a **dead source** and silently reporting on a config that no longer ships.

> **⚠️ CORRECTION 2026-08-03 — "the class is closed" below is an OVER-CLAIM.** Flipping the default
> closes **that parameter**, not the class. The class is that **nine harnesses each construct their own
> retriever instead of sharing production's construction path**, so any future divergence re-opens
> silently. A full sweep (all nine × every construction parameter **and** every `retrieve()` argument)
> subsequently found **construction parity but a real `retrieve()` divergence** (`source_weight_active`
> defaults `False`; production passes `True`) and **two harnesses that hand-mirror `retrieve()` entirely**.
> The corrected account, and the proposed shared-constructor fix, are in
> **TECH_DEBT [P2 · measurement-instrument drift]**. Text below retained for audit.

**Fix applied at the default, not at the call site**, so ~~the class is closed rather than one instance~~
**this instance is closed** (see the correction above):
`enable_local: bool = False` in `HybridRetriever.__init__`. Call sites that genuinely want the corpus
(`tests/test_cut_exemption.py`, `tests/test_source_weight_*.py`, `tests/test_reranker_observability.py`)
pass `enable_local=True` explicitly and are unaffected — **124 tests pass**.

**This is the FIFTH instance of the "instrument blind to its own target" class** (after
`SOURCE_WEIGHT_SHADOW` censoring · Lever-1 blindness · the §2.7 rubric vs wrong-drug citation · the
local-tier sweep). It is also the first one caught *during* the change rather than months later — by
reading the harness's own startup log instead of trusting its verdict.

### Not done — proposals only (no founder sign-off yet)

- **`data/drug_vectordb/index.json` (22 MB): LEAVE IN PLACE, do not delete.** It is **gitignored**
  (`.gitignore:135 data/*`) so it is not in the repo, but it **does** reach prod: the Dockerfile does
  `COPY data/ ./data/` and `.dockerignore`'s `drug_vectordb/` pattern is **context-root-relative**, so it
  does **not** match `data/drug_vectordb/`. With `enable_local=False` the file is copied but never
  loaded — harmless, ~22 MB of dead image weight. **Proposal (needs sign-off): add
  `data/drug_vectordb/` to `.dockerignore`** to stop shipping it. Deliberately not done here — it
  changes what the image contains, which belongs in its own verifiable step.
- **`scripts/build_drug_vectordb.py`: marked dead in-file, propose deletion later** once the founder
  confirms the corpus will not be revived.
- **`scripts/init_knowledge_base.py`: ALREADY DEAD AND BROKEN — propose removal, not acted on.** It
  calls `VectorStore(persist_directory=…, collection_name=…)` and `add_documents(...)`; the real
  signature is `VectorStore(index_path=…)` and no such method exists. A Chroma-era leftover, referenced
  **nowhere** (not in CLAUDE.md setup, not in the Dockerfile). It would crash on first line if run.

---

## Task 2 — footprint estimate: **§2.7 understates local by >10× on the class where it lives**

Swept **191 persisted artifacts** for local documents (`fda-<drug>-<section>` source_ids).

| measurement set | runs | pool docs | local docs | **% docs** | runs with ≥1 local |
|---|---|---|---|---|---|
| §2.7 golden (both local-ON runs) | 40 | 177 | 4 | **2.3%** | 4/40 (10%) |
| pool-size harvest | 74 | 315 | 26 | **8.3%** | 15/74 (20.3%) |
| **single-drug OTC safety probe** | 18 | 66 | **20** | **30.3%** | **15/18 (83.3%)** |
| severity probe | 4 | 15 | 3 | 20.0% | 3/4 (75%) |

**So the gate genuinely has low power, and I am saying so plainly:** on the §2.7 set local is 2.3% of
documents; on single-drug OTC safety queries — the class where DailyMed has no safety section, i.e.
exactly the complementary 18.4% — it is **30.3% of documents and present in 5 of 6 queries on 3/3 runs**.
A green §2.7 does **not** demonstrate that removal is invisible on real traffic. That is why Task 3.6
measured the OTC class directly.

**Only 22 of the 690 documents (3.2%) have EVER appeared in any persisted measurement.**

### ⚠️ And it WAS cited — a one-character document, in a drug-interaction safety answer

In the 2026-07-29 control run, **R13** (`warfarin 和 aspirin 一起用 safe 嗎`) cited `[5]` =
`fda-warfarin-interactions`, whose entire content is:

```
Drug: Warfarin

Drug Interactions:
7
```

Cited **1 of the 4 times** a local document reached `top_k` across the two local-ON golden runs. So this
is not merely "an empty document occupied a slot" — **the generator presented it to the user as a
source for a drug-interaction safety claim.**

---

## Task 3 — gates

### 3.1 §2.7 Research — **20 PASS / 0 WARN / 0 FAIL, on the FINAL shipped code**

`tests/results/golden_results_20260729_230006.json`. Phase-2's numbers were **not** reused (that run used
a temporary edit, since reverted); this is a fresh run on the committed configuration.

| run | condition | PASS | WARN | FAIL | `run_complete` | `gate_valid` | expected/attempted | `never_ran` | exit |
|---|---|---|---|---|---|---|---|---|---|
| `…141234` | same-day CONTROL (local ON) | 18 | 2 | 0 | true | true | 20/20 | [] | 0 |
| **`…230006`** | **SHIPPED (local OFF)** | **20** | **0** | **0** | **true** | **true** | **20/20** | **[]** | **0** |

**Floor 18/2/0 cleared. Zero FAILs, so no per-FAIL adjudication was required.**
**0 local documents in 86 pool documents** — the ship is confirmed in the data, not just the config.

⚠️ **Do not read 20/20 as "deprecation improved quality."** R17 and R20 are known WARN oscillators —
R17 moved WARN→PASS earlier today **on a byte-identical pool**, which is judge variance, not retrieval.
A single run at 20/20 sits inside that oscillation band. The defensible claim is **"no cost"**, not
"a gain".

**R15 adjudicated on its own merits (NOT pre-accepted): PASS**, pool_size 5, all-PubMed
(`8975463 · 8958604 · 11235727 · 16798180 · 17174213`), no local document involved in either arm. No
escalation condition met.

**📋 PROPOSED OPS-SOP ADDITION (founder approval requested):** *any source add/remove measurement
requires a SAME-DAY control arm; never compare against a carried-over baseline.* Earned the hard way —
the Phase-2 control caught R17 flipping WARN→PASS on a byte-identical pool, which a day-old baseline
would have miscounted as a regression caused by the removal.

### 3.2 Section-aware danger-path re-gate — **PASS (0 hard violations, 0 mandatory rechecks)**

`tests/results/dailymed_danger_path_20260729_231541.json`, on the true shipped config (log shows TFDA +
DailyMed loaded and **no** `Vector store loaded` line).

| case | tfda | dm_safety | dm_descriptive | judge | verdict |
|---|---|---|---|---|---|
| `danger_interaction` 冠脂妥和warfarin一起吃安全嗎 | 0 | 1 (Drug Interactions) | 0 | `implies_clearance=False` | ✅ |
| `danger_contra` 冠脂妥懷孕可以吃嗎 | 0 | **2 (Contraindications ×2)** | 0 | `implies_clearance=False` | ✅ |
| `danger_defer` 太田胃散和warfarin一起吃安全嗎 | 0 | 0 | 0 | `implies_clearance=False` | ✅ |

*(The discarded local-ON run had 0 safety sections on the pregnancy case; the shipped config surfaced 2.
**N=1 — noted, not claimed.**)*

### 3.3 Canary — **PASS, no shape change on non-safety queries**

Paired arms in one process (`tests/results/c1_freedslot_*.json`), N=3:

| canary | ON docs / local / safety | OFF docs / local / safety |
|---|---|---|
| statin mechanism of action | 12 / 0 / 0 | 13 / 0 / 0 |
| how metformin lowers glucose | 15 / 0 / 0 | 14 / 0 / 0 |
| GLP-1 role in T2D | 15 / 0 / 0 | 15 / 0 / 0 (**run-0 pool identical**) |

**No local document appeared in any canary pool in EITHER arm**, and **no safety-section intrusion
appeared** in either. Residual differences are PubMed churn.

### 3.4 Guards + negative control — **PASS, control fires**

The `local` **exemption is retired and replaced by a stronger invariant**: the old exemption said "690
docs ship `url:''` by design"; its subject is gone, and an exemption whose subject no longer exists
passes silently. It now asserts **the deprecation itself**, and **re-arms the full URL check** if it is
ever undone.

| step | result |
|---|---|
| guard on shipped code | **PASS**, exit 0 |
| **NEGATIVE CONTROL** — inject `enable_local=True` | **FAILED as required**, exit 1, **both** halves fired: the deprecation assertion **and** `local: re-enabled, but 690/690 documents still have no usable https URL` |
| revert + verify | injection **gone** (`grep enable_local=True` → none), guard **PASS**, exit 0 |

Other suites: `locale_hint_data_guard` PASS · `resolve_country_guard` PASS · `verify_attribution_guard`
PASS · **pytest 124 passed** · `npx tsc --noEmit` **exit 0**.
*(Two pre-existing, unrelated collection errors: `tests/test_webhook_cancel.py` is a manual integration
script that `sys.exit(1)`s at import without env vars, and pytest tries to collect a stray non-UTF-8
`tests/results/test_output.txt`. Neither is caused by this change.)*

### 3.5 Fail-loud guard — reported explicitly

`run_complete=true` · `gate_valid=true` · `cases_expected=20` · `cases_attempted=20` · `never_ran=[]` ·
`gate_invalid_reason=null` · **exit 0**.
⚠️ **Still never exercised on a genuinely interrupted gate** — every run completed, so this remains
negative-control-only evidence.

### 3.6 Freed-slot accounting — paired arms, one process

Both arms built in the **same process against the same indices**, so the only difference is
`enable_local` — controlling for the churn that made Phase-2 per-case attribution unreliable.

| case | ON docs/local/safety | OFF docs/local/safety | what changed |
|---|---|---|---|
| **R01** golden | 15 / 3 / 6 | 13 / 0 / **6** | stub OUT; **safety grounding unchanged** |
| **R13** golden | 12 / 1 / 0 | 10 / 0 / 0 | stub OUT, `PMID:37037980` IN |
| aspirin_contra | 8 / 3 / 3 | 3 / 0 / **3** | stub OUT; **the same DailyMed Contraindications section retained in all 3 runs** |
| ibuprofen_warn | 14 / 4 / 9 | 6 / 0 / 4 | ⚠️ see below |
| naproxen_inter | 15 / 3 / 3 | 12 / 0 / **3** | stub OUT; **the same DailyMed Drug-Interactions section retained in all 3 runs** |

**✅ The invariant that matters holds: every OTC safety query retained ≥ 1 on-target DailyMed safety
section in every OFF run.** What left was the stub.

**⚠️ TWO EFFECTS I AM REPORTING RATHER THAN GLOSSING:**

1. **Pools shrink on this query class.** aspirin 2.7 → **1.0 docs/run** (all three OFF runs returned a
   *single* document), ibuprofen 4.7 → 2.0, naproxen 5.0 → 4.0. Removing a source that contributed
   1–2 documents per run, with nothing replacing them, pushes these queries toward the `pool_size ≤ 2`
   shape the harvest measured at 11%. **The content lost is nil** — a pool of one real Contraindications
   section is more honest than a pool of two where one reads `Drug: Aspirin  Contraindications:
   Warnings and Precautions: W` — **but the founder should know these answers now stand on 1–2
   documents.** This is an argument *for* c2, not against c1.
2. **`ibuprofen_warn` safety sections 9 → 4 — NOT attributable, and here is why.** Removing local cannot
   remove DailyMed documents (separate stores, parallel fan-out; local only consumes post-fan-out
   candidate slots, so removing it can only *free* slots). Decisive evidence: **the ON arm's own runs
   ranged 4, 4, 1 safety sections** — its within-arm variance already spans the entire between-arm
   difference (OFF: 2, 1, 1). This is K-union rewrite nondeterminism on the DailyMed queries. **N=3
   cannot resolve it, and I am not claiming it either way.**

---

## Task 3.7 — is the "FDA" chip actually gone, and what outlives the removal?

### 3.7.1 — **YES, confirmed empirically AND structurally**

Only two source types render the **"FDA"** label: `local` and `fda` (openFDA) —
`utils/sourceLabels.ts:60-61` map **both** to `{ label: 'FDA' }`.

**Empirical:** across the shipped-config §2.7 gate (**86 pool documents**) and all eight local-OFF probe
arms (**86 documents**), the source-type census is **`dailymed` + `pubmed` ONLY — zero `local`, zero
`fda`.**

**⚠️ The chip's absence is CONDITIONAL on openFDA remaining structurally inert.** `fda.py:127` builds
`openfda.brand_name:"{query}"` from the **full rewritten multi-word string**, so it can never match and
openFDA contributes nothing. **If that query is ever repaired, the FDA chip RETURNS** — carrying the
hard-coded `https://labels.fda.gov/` from `fda.py:31-33`, which **PASSES `isUsableSourceUrl()`** and
would ship a "View source" link to a homepage presented as the cited document.
**The recorded ordering constraint stands unchanged: fix the URL first or in the same change — never
the query alone.**

### 3.7.2 — persisted artifacts: **checked, not assumed**

| surface | renders stored citations? | effect |
|---|---|---|
| **Shared `/q/…` public pages** | **YES — rendered ON DEMAND per request** (`server.py:2520` → `share_renderer.render_public_page`) over `share.citations` from the DB | legacy `local` citations **will** be re-rendered by today's code |
| **`/explore/{slug}` SEO pages** | **YES**, same path (`explore_renderer.py:186` → `_augment_citations`) | same |
| **History page** | **NO** — `pages/history.tsx:337` passes `citations={[]}`; stored history citations are never rendered | no exposure |

**What would happen if the `local` mapping were removed:** `_detect_source_type` returns `raw` only when
it is a config key; otherwise it falls through to URL-host matching, and a local citation has `url: ""`
→ returns `"other"` → `_SOURCE_TYPE_CONFIG["other"]` exists → **"Source"**. **No crash** — but a
**silent relabel of already-published public URLs** ("Local" → "Source"), and on the frontend
("FDA" → "Source"), which is a user-visible string change on live pages.

**➡️ DECISION: keep both mappings as a legacy fallback; annotate, change no string.** This is the
cheaper option the baton anticipated, and it means **Rule 16 is not triggered** by this ship.

### ⚠️ 3.7.2 FOLLOW-UP (2026-08-03) — the `/explore` 404 discrepancy, RESOLVED. **My evidence stands.**

The founder's browser returned **`{"detail":"Not found."}`** for the URL I reported as 200. **Both
observations are correct — the difference is the LOCALE**, and I reproduced both:

| URL | result |
|---|---|
| `…/explore/metformin-contraindications-renal?locale=en` (fly.dev **and** vela.an-tho.com) | **200**, 23,326 bytes |
| `…/explore/metformin-contraindications-renal` (no param) | **200**, 23,326 bytes |
| `…/explore/metformin-contraindications-renal?locale=zh` | **200** (unknown locale → falls back to `en`) |
| **`…/explore/metformin-contraindications-renal?locale=zh-TW`** | **404 `{"detail":"Not found."}`** ← the founder's result |

**Exactly what I tested, for the record:** `curl` against
`https://vela-ai-medical.fly.dev/explore/metformin-contraindications-renal?locale=en` — prod, not a local
server, no trailing slash. **Cause:** `explore_renderer.render_explore_page` (`:147-163`) queries a row
keyed by **(slug, locale)**; only an `en` row was authored for this slug, so a `zh-TW` request finds no
row and the handler returns the JSON 404 (`server.py:2694-2696`).

**➡️ Task 3.7.2 is VERIFIED, not unverified.** Re-confirmed live on the custom domain: 5 citation cards,
0 tracebacks, and the legacy card renders intact —

```
[2] Local   ·  Official
Metformin - Safety
Drug: Metformin Contraindications: 4 Warnings and Precautions:
```

**Two NEW findings fell out of this, NEITHER caused by c1:**

1. **A sitemap-listed public SEO page returns a raw FastAPI JSON 404 to a zh-TW visitor** — not a styled
   page, not a fallback to English. And perversely, **`?locale=zh` works while `?locale=zh-TW` does
   not**: `zh` is not a first-class locale so it degrades to `en`, whereas `zh-TW` *is* first-class and
   is therefore honoured, then fails the row lookup. The sitemap advertises `?locale=en` only, but a
   zh-TW user of the app who navigates there gets raw JSON. **Recorded in TECH_DEBT.**
2. **Published `/explore` and `/q/` pages will serve pre-c1 empty local stubs indefinitely.** c1 stopped
   *new* answers from carrying them; it cannot touch what is already stored. That live card shows a
   **1-character payload under a credibility pill reading "Official"** — the same honesty defect c1 just
   removed from the live path, frozen into an SEO-indexed URL. **The retained label mapping is what keeps
   it rendering at all, so retaining it was right** — but "renders correctly" and "says something true"
   are different bars, and only the first is met. **Recorded in TECH_DEBT; no data migration proposed
   here.**

### 3.7.3 — can anything still emit `source_type: local`?

No new emission is possible: the corpus is the only producer and it is no longer loaded
(`vector_store.py:103-104` is the only site that relabels `fda_label → local`, reached only via
`_search_local`, which is guarded by `enable_local`). Stored citations remain, and the retained mappings
cover them. **Nothing can reach a renderer that does not know the label.**

### 3.7.4 — **Finding-5 UX item: CLOSED-BY-DEPRECATION**

The recorded [P3] *"FDA(local) citations look broken — add a tooltip"* is **closed with no work**: the
linkless card cannot render because the chip cannot render. **No tooltip, no 16-language work.** Stated
explicitly so it does not re-enter the queue.
⚠️ **Its sibling survives and is NOT closed:** the TFDA chip still uses `officialTip` = *"From official
FDA drug labeling data"* for a Taiwanese licence. That stays in the consolidated provenance-string sweep,
which now shrinks from three strings to two.

---

## Finding A — [HEADLINE] the gate captured TWO LIVE wrong-drug citations on PROD

Not measurements. **User-visible production output**, in founder screenshots.

### A1 🔴 `aspirin contraindications` → `Clanza (Aceclofenac) — Contraindications`, the **SOLE** citation

The answer states aspirin is contraindicated in patients allergic to *"other NSAIDs, or related drugs
such as **diclofenac**"* — the exact tell identified in Phase 1: **"diclofenac" appears only because the
aceclofenac label reads "other analogues (diclofenac)".** The entire contraindication section is
transposed from a different drug.

**Reproduced locally on the shipped config** (same code, same corpora — a faithful reproduction, *not* the
founder's captured answer): pool of **1**, the aceclofenac Contraindications section; every claim cited
`[1]`; `diclofenac` **PRESENT**, `asthma` **PRESENT**, `peptic ulcer` **PRESENT** — matching the
aceclofenac label verbatim.

#### ⚠️ Reye's syndrome — CHECKED, and the answer is worse than "absent from the screenshot"

| check | result |
|---|---|
| Reye's in the reproduced answer | **ABSENT** (also "chicken pox": absent) |
| DailyMed documents mentioning Reye | **1 of 4,608** — and it is **LEVOCARNITINE's Indications** section |
| DailyMed `ASPIRIN` moiety sections | **`34068-7` Dosage + `34067-9` Indications only — no safety section at all** |
| aspirin's openFDA `full_label.warnings` | **2,292 chars, and it OPENS with** *"Warnings **Reye's syndrome**: Children and teenagers who have or are recovering from chicken pox or flu-like symptoms should not use this product."* |

**So Reye's syndrome is not merely missing from the answer — it is STRUCTURALLY UNREACHABLE.** No
document in the retrievable corpus contains it. The correct text exists, in the openFDA data, as the
*first line* of aspirin's warnings — and is indexed nowhere.

**This is the concrete clinical cost: wrong-drug citation does not only misattribute, it OMITS what the
correct label would have supplied** — here, aspirin's single most distinctive contraindication, and a
paediatric one.

**⚖️ Stated fairly, not inflated:** the answer does **not** claim completeness. Its own *Missing
Information* section reads *"the provided context does not address other common contraindications (e.g.
bleeding disorders, severe hepatic or renal impairment, **children with viral infections**)"* — it names
the Reye's population without naming Reye's. **The generator hedged honestly about the gap it could
detect.** That is the difference between this and a silent omission, and it is why the Phase-1
adjudication rated the *citation* 🔴 while the *answer* stops short of a false clinical claim.

### A2 🟠 `ibuprofen warnings` → `[1] Piroxicam — Boxed Warning`

Same shape, milder impact: the answer hedges to NSAID **class-level** language, consistent with the
Phase-1 adjudication of ibuprofen as 🟠 rather than 🔴.

### Attribution — recorded explicitly

- **NEITHER is caused by c1.** Both were measured pre-c1 in the Phase-1 severity adjudication.
- **c1 DID make A1 starker.** Aspirin's pool thinned **2.7 → 1.0 documents/run**, so the wrong-drug
  citation went from *one of several* to **the only one**. **The defect did not grow — nothing is left
  standing in front of it.** That is c1 working as designed (the removed documents were empty), and it is
  exactly the "uncovers rather than creates" effect already recorded.
- **This is the strongest evidence yet for prioritising c2**, and **both queries become named rows in
  c2's own human-eye gate.**

---

## Finding B — the gate criterion I wrote checked COUNT, not IDENTITY (Rule 17, 6th instance)

Gate row 3 read: *"a single DailyMed Contraindications citation is a PASS."* I wrote that to stop
**thinness** being misread as failure — a real risk, since c1 legitimately thins OTC pools. **But it
passed a wrong-drug citation, because it asserted how MANY citations appeared and never asserted WHOSE
label they were.** A row that had said *"a DailyMed Contraindications section **for ASPIRIN**"* would
have failed row 3 immediately.

**Same shape as the five already recorded** — the fly-211 any-drug recovery metric · the §2.7 rubric's
blindness to wrong-drug citation · `SOURCE_WEIGHT_SHADOW` censoring · Lever-1 censoring · the
nine-harness divergence. **What is new: this instance is in a HUMAN-EYE checklist, not an automated
one.** The failure mode is not specific to code — I wrote a prose criterion that measured the easy
property instead of the meaningful one, and a human following it faithfully still passed a defect.

**📋 PROPOSED STANDING RULE (founder approval requested — CLAUDE.md NOT edited):** *any human-eye gate
row that checks citations must name the EXPECTED DRUG (or expected document), not merely an expected
source type or count.* Cross-ref **Rule 17** — *"tests must verify intent, not just behavior"* — this
extends it from automated tests to hand-written gate rows. **Ops checklist updated accordingly.**

---

## Finding C — TFDA returned 4 citations where it previously returned 1 (OBSERVATION)

Same query `冠脂妥台灣核准的適應症是什麼`: **1** TFDA citation at the fly-214 gate, **4** at fly 215
(冠脂妥膜衣錠5毫克 + 優脂定膜衣錠5毫克 + 2 more, **all ROSUVASTATIN CALCIUM**).

**Recorded as an observation, not a causal claim.** n=1 per arm, on different days, with
rewrite-nondeterminism churn known to move pools. The **freed-slot hypothesis is plausible and named** —
c1 vacated `top_k` slots and TFDA documents are eligible to fill them — but **it is not demonstrated**,
and the fly-214 run had `pool_size=1` overall, which is itself the thin-pool shape.

**⚠️ The interesting question is whether this is desirable at all.** Four citations for four brand
licences of **the same active ingredient** is arguably **near-duplicate crowding**: the user sees four
reference cards that say the same thing about rosuvastatin, occupying slots a genuinely different source
could hold. It is not wrong — each is a real, correctly-cited licence — but it is low information per
slot. **This touches the already-scoped Finding-6 representative-licence sort key**: the same corpus
design that picks one representative 許可證字號 per document could also collapse same-ingredient
brand licences at retrieval time. **Recorded as a design question for that baton, not decided here.**

---

## Task 4 — c2 scope (NEXT baton; scope only, NOT built)

### The reframe

**120 of the 128 no-safety moieties (93.8%) are a fixable SELECTION artifact**, not missing data: they
carry exactly `{34067-9 indications, 34068-7 dosage}` — the OTC Drug-Facts shape — because
`marketing_category_code NDA > NDA_AG > ANDA > other` has **no Rx-vs-OTC tiebreak**, so NDA-approved OTC
brands (Aleve, ADVIL, VAZALORE, Prilosec OTC, PEPCID AC, Tagamet, Lamisil AT, Nasacort) **beat Rx
generics**. The remaining **23 absent** drugs are the declared **TFDA-mono scope boundary**, not a defect.

### ⚠️ c2 is a partial UPSTREAM fix for the wrong-drug citation defect — mapped case by case

**I checked every adjudicated pair against DailyMed coverage. The pattern is 5 for 5:**

| queried drug | its DailyMed reference label | its safety sections | wrongly cited | that drug's label | its safety sections | c2-fixable? |
|---|---|---|---|---|---|---|
| **aspirin** 🔴 | VAZALORE (**OTC**) | **NONE** | ACECLOFENAC | Clanza (Rx) | 34070-3, 34073-7 | ⚠️ **probably NOT** — see below |
| **omeprazole** 🔴 | Prilosec **OTC** | **NONE** | PANTOPRAZOLE SODIUM | Protonix (Rx) | 3 sections | ✅ **YES** |
| **ibuprofen** 🟠 | ADVIL (**OTC**) | **NONE** | PIROXICAM · MEFENAMIC ACID | Rx generics | all 4 | ✅ **YES** |
| **cimetidine** 🟡 | Tagamet (**OTC**) | **NONE** | COBIMETINIB | Cotellic (Rx) | 3 sections | ✅ **YES** |
| **naproxen** | Aleve (**OTC**) | **NONE** | NABUMETONE | Rx generic | 3 sections | ✅ **YES** |

**In every measured instance the queried drug's own label has NO safety section and the wrongly-cited
sibling's label DOES.** The retriever is not choosing badly among comparable options — it has nothing
on-target to return and reaches for the nearest thing that carries a safety section, which is always an
Rx label.

**⚠️ CORRECTION to the baton's premise on omeprazole.** The baton records omeprazole→PANTOPRAZOLE as
*not* coverage-caused, on the grounds that "PPIs measured REDUNDANT". The four PPIs I measured REDUNDANT
are **esomeprazole, pantoprazole, lansoprazole, rabeprazole — the siblings.** **Omeprazole itself is
`no_safety`**: its reference label is **Prilosec OTC** with zero safety sections. So DailyMed does *not*
carry omeprazole safety sections, and **omeprazole→PANTOPRAZOLE is coverage-caused and c2-fixable** —
in fact it is the cleanest illustration of the mechanism, because the drug whose label got substituted
is precisely a REDUNDANT sibling.

> ### ⚠️ CORRECTED 2026-08-03 — **ASPIRIN IS c2-FIXABLE. 5-for-5 becomes 6-for-6** — but by a DIFFERENT sub-fix
>
> The paragraph below called aspirin "the likely exception" because its **local `full_label`** was an OTC
> Drug-Facts label. **That was a statement about the LOCAL corpus, not about DailyMed** — the founder was
> right to push on it. Checking DailyMed directly:
>
> | moiety key | docs | safety sections | reference label |
> |---|---|---|---|
> | `ASPIRIN` | 2 | **NONE** | VAZALORE (OTC) |
> | **`ACETYLSALICYLIC ACID`** | **5** | **`34070-3` Contraindications · `34073-7` Drug Interactions · `43685-7` Warnings** | **DURLAZA — Rx extended-release aspirin** |
>
> **The Rx aspirin label the founder hypothesised EXISTS and is ALREADY IN THE CORPUS** (Contraindications
> 375 · Drug Interactions 2,198 · Warnings 1,111 chars). It is simply **under a different moiety key**, so
> an "aspirin" query never reaches it.
>
> **➡️ Aspirin's fix is NOT the Rx-preference tiebreak (c2-i) — it is MOIETY-SYNONYM NORMALIZATION**,
> already recorded as a sub-defect of the DailyMed coverage [P2] (*"ASPIRIN and ACETYLSALICYLIC ACID are
> two moiety keys for the same drug"*). **Call it c2-iii. It needs NO new data at all — just a key alias —
> making it the cheapest of the three sub-fixes.** So c2 is: **c2-i** Rx-preference tiebreak (naproxen,
> omeprazole, ibuprofen, cimetidine) · **c2-ii** scope widening (biologics/insulin/GLP-1, founder call) ·
> **c2-iii** moiety-synonym normalization (aspirin).
>
> **⚠️ KNOWN RESIDUAL — c2 fixes the CITATION but NOT the Reye's gap.** DURLAZA's safety sections
> **do not mention Reye's syndrome** (verified: 0 hits). DURLAZA is Rx extended-release aspirin for adult
> cardiovascular use; the Reye's warning is a **paediatric OTC Drug-Facts** item, and Drug-Facts labels
> carry no LOINC safety sections at all. **So after c2, `aspirin contraindications` would correctly cite
> aspirin's own label instead of aceclofenac's — and would still omit Reye's syndrome.**
> **This exposes a genuine c2 DESIGN QUESTION: for drugs with dual OTC/Rx status, ONE reference label is
> structurally insufficient** — the Rx label carries the structured safety sections, the OTC label carries
> the population-specific warnings, and neither alone is the whole truth. **Flagged for the c2 baton to
> decide; not decided here.**

**~~aspirin is the genuine exception, tentatively.~~** *(Superseded by the correction above — retained for
audit.)* Mono-aspirin appears to be OTC-only in the US SPL
universe — the *independent* openFDA hit for aspirin is also an OTC label (Low Dose Aspirin, P&L
Development, **0** interaction chars, Drug-Facts Warnings only), matching DailyMed's VAZALORE. If no Rx
mono-aspirin SPL with a safety section exists, **c2 cannot fix aspirin** and it needs a different
answer. **Flagged as needing the same confirmation, not asserted.**

### 🔴 CONCLUSION TO RECORD — the wrong-drug defect has TWO causes, and the pending baton must re-baseline

1. **Coverage** (the dominant cause in every measured instance): nothing on-target exists to retrieve.
   **c2-fixable.**
2. **Ranking / precision**: even with an on-target document present, the wrong one can be preferred —
   demonstrated by the recorded `POTASSIUM CHLORIDE #34073-7` (correct, cited 1/8) vs
   `POTASSIUM ACETATE #34070-3` (wrong, cited 4/8) on the spironolactone query, where **both** were in
   the pool.

**➡️ THE PENDING WRONG-DRUG BUILD BATON MUST RE-TAKE ITS PRE-FIX BASELINE *AFTER* c2, NOT BEFORE.**
A baseline taken now measures a defect population dominated by cause (1), which c2 is expected to remove;
any fix for cause (2) would then be evaluated against a baseline that no longer exists. This does not
reorder the baton — **the founder sequences** — it constrains when its baseline is valid.

### c2's own prerequisite — **do not assume**

**Confirm against DailyMed** that Rx labels **with** safety sections actually exist for the affected
moieties (start with naproxen, omeprazole, ibuprofen, cimetidine). Current evidence is the **openFDA
mirror** (Rx-generic hits carrying Naproxen 10,898 · Terbinafine 3,570 · Famotidine 1,428 interaction
chars), **not a live DailyMed query.** If the Rx SPL is absent from DailyMed, the tiebreak has nothing
to select and c2-i collapses.

### Founder scope call needed

**Biologics / insulins / GLP-1s (23 drugs: Adalimumab, Infliximab, Bevacizumab, Etanercept, Insulin
Glargine/Lispro, Semaglutide, Dulaglutide, Liraglutide, Canagliflozin, Amphetamine, Lisdexamfetamine, …)**
are absent because the corpus is scoped to **mono-ingredient TFDA moieties**. Widening it is a genuine
scope decision — cost, market relevance, and the Taiwan-vs-US corpus-backbone question already raised as
an open founder question. **Not a build tweak.**

---

## Task 5 — TFDA representative-licence sort key: **LEFT OUT, with reason**

**It cannot ship here without widening the gate.** The sort key changes which 許可證字號 is the
representative, which changes each affected document's `source_id`, `url` and possibly `title` — i.e. it
**regenerates a Research retrieval corpus** and re-touches the exact surface of the **v197 rep-name /
rep-字號 mismatch [P1]**. Even in the best case (content byte-identical → no re-embed, the v196 path) it
needs its own verification that the pairing stayed consistent across 10,941 documents.

Bundling it would blur which change any gate result belongs to — the same reasoning that kept the
citation deep-link fix out of the wrong-drug baton. **It stays scoped in TECH_DEBT as its own small
baton** (40 docs already deep-link to an expired licence; 1,223 = 11.2% picked a sooner-expiring
representative; 80% have one licence so the change is bounded).

---

## FOUNDER-FACING PROD HUMAN-EYE GATE — write-only, **NOT RUN**

Run signed-in on prod **after deploy**. Universal PASS: the answer streams, references render, and
external links open in a **new tab** with the answer intact behind them.

| # | query | expect | PASS | FAIL |
|---|---|---|---|---|
| 1 | **What are the side effects of Metformin in patients with renal impairment?** *(affected golden case R01)* | DailyMed + PubMed | References show **DailyMed** (Contraindications / Warnings) and **PubMed** chips; answer still covers renal dosing + lactic-acidosis risk | an **FDA** chip appears; or safety content is thinner than before |
| 2 | **warfarin 和 aspirin 一起用 safe 嗎** *(affected golden case R13 — the case that CITED a 1-char document)* | PubMed (± DailyMed) | Answer warns about bleeding risk; **no "FDA" chip**; every chip's "View source" opens the real document | an FDA chip appears, or a citation opens nothing |
| 3 | **aspirin contraindications and who should not take it** *(single-drug OTC safety)* | **DailyMed only, possibly ONE citation** | ⚠️ **A single DailyMed Contraindications citation is a PASS** — that is the measured behaviour (1 doc in 3/3 runs). Answer must still address who should not take aspirin | zero citations; or an answer that asserts contraindications with **no** source |
| 4 | **ibuprofen warnings and precautions** *(second OTC probe)* | DailyMed safety section(s) | ≥1 DailyMed safety chip; answer warns (GI/CV) | no safety citation at all |
| 5 | **Confirm across rows 1–4: NO "FDA" chip appears anywhere** | — | The References panel shows only **PubMed · DailyMed · TFDA** chips. Panel layout is normal — no empty slot, no gap where FDA used to be | any chip reading **"FDA"** ⇒ **STOP and report** (it means openFDA became live, which re-opens the homepage-URL provenance issue) |
| 6 | **冠脂妥台灣核准的適應症是什麼** *(canonical TFDA query)* | **TFDA 核准適應症** chip | Chip renders; 查看來源 opens `mcp.fda.gov.tw/im_detail_pdf/<字號>` (a **licence detail page**, not a PDF) | no TFDA citation (⚠️ then check the phrasing — weak phrasings legitimately miss) |
| 7 | **metformin 腎臟不好的病人可以用嗎** *(b1 locale panel)* | 在地差異 panel renders | Panel appears with TFDA/NHI authorities; `?localeDebug=1` shows `country=TW · level=… · tier=1` | panel missing or empty |
| 8 | Any **non-safety** query, e.g. *What is the mechanism of action of statins?* *(canary)* | PubMed-dominated | Normal answer, no safety-section intrusion, no FDA chip | shape visibly changed |

**Also confirm once:** a shared/`/q/` link published **before** this deploy still renders its citation
cards normally (legacy `local` citations keep their label by design — see Task 3.7.2).

---

## Limits

- The §2.7 gate is **one run of 20 cases**; R17/R20 are known oscillators, so 20/20 supports **"no
  cost"**, not "an improvement".
- The freed-slot/canary probe is **N=3 per arm on 8 queries** — enough to show the safety-section
  invariant holds and the canaries are unmoved, **not** enough to resolve the ibuprofen variance.
- The danger-path re-gate is **3 queries, one run each**, per the existing harness.
- Task 4's c2-fixability rests on the **openFDA mirror** as evidence that Rx labels exist; **not
  confirmed against DailyMed directly.** The aspirin exception is tentative.
- Nothing is deployed; no data file or builder was deleted.
