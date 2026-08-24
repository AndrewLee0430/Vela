<!-- ─────────────────────────────────────────────────────────────────────────
ADDENDUM — ADDED 2026-08-24, AFTER THE FACT. NOT PART OF THE ORIGINAL REPORT.
The original text begins below the horizontal rule and is PRESERVED UNALTERED.
───────────────────────────────────────────────────────────────────────── -->

> ## ⚠️ LATER ADDENDUM — read before the body
>
> **This report SUPERSEDES the Tier-3 finding of**
> [`recon_20260824_step8_and_pmid.md`](recon_20260824_step8_and_pmid.md) **(same day).**
> That report claimed the two `api/` sites run the `(\d{5,})` regex unguarded; this one
> traces the path in full and returns **(b) NOT REACHABLE** — both are guarded at
> `api/services/direction_checker.py:83-84` and `api/services/retrieval_refusal.py:73-74`.
> The superseded file is retained deliberately, as the record of how that false negative
> was produced.
>
> **🔴 THIS REPORT CARRIES ITS OWN UNCORRECTED ERROR — arithmetic, in Item 7.**
> The body splits its 10 `(\d{5,})` occurrences as **"5 guarded / 5 unguarded"**.
> Recounting **its own `file:line` list** gives **4 guarded / 6 unguarded**:
>
> - guarded — `direction_checker.py:86` (1) · `retrieval_refusal.py:76` (1) ·
>   `question_neutralization_eval.py:59-60` (2) = **4**, not 5
> - unguarded — `citation_truth_check.py:132` (1) · `direction_shadow_eval.py:98,141,143` (3) ·
>   `pathb_recall_probe.py:58` (1) · `retrieval_recall_check.py:46` (1) = **6**, not 5
>
> Both readings still total 10, which is why the miscount survived its own cross-check —
> **a sum that reconciles is not a count that is right.** The narrative conclusion
> (the guarded sites are the two `api/` ones plus the eval script; every unguarded
> occurrence is under `scripts/`) is unaffected; only the two digits are wrong.
>
> **The body is NOT corrected — the error is noted here only.** The authoritative
> count will be RE-DERIVED FROM THE REPO in the next car, not carried over from either
> figure above.

---

HEAD is `7a24c70233d51d14692f957ad45b2c8a099398fb` at `C:/Users/andre/projects/Vela`. Proceeding. No edits made.

---

## Answer: **(b) NOT REACHABLE**

**The filters, at named `file:line` — both are the line pair immediately preceding the regex, in the same function:**

```
api/services/direction_checker.py:83-84
    if getattr(d, "source_type", None) != SourceType.PUBMED:
        continue
api/services/direction_checker.py:86
    m = re.search(r"(\d{5,})", getattr(d, "source_id", "") or "")
```

```
api/services/retrieval_refusal.py:73-74
    if getattr(d, "source_type", None) != SourceType.PUBMED:
        continue
api/services/retrieval_refusal.py:76
    m = re.search(r"(\d{5,})", getattr(d, "source_id", "") or "")
```

**Correcting my previous report.** I wrote that "the other nine sites, including both `api/` sites, do not have [the source-type guard]." **That is false.** Both `api/` sites have it, two lines above the regex. My grep matched the regex line and looked for `SourceType.PUBMED` on the *same* line — which is how `scripts/question_neutralization_eval.py:59-60` spells it (inline in a comprehension) — so the preceding-line `continue` guard form was invisible to that search. The Tier-3 "product defect" concern in my last report does not exist. The repo's own ledger had already recorded the guard twice (`TECH_DEBT.md:809`, `TECH_DEBT.md:1079`, both citing `retrieval_refusal.py:73-74` as "skips every non-PubMed `source_type`"), and I contradicted it.

---

## 1–2. The functions and every caller; what builds their document list

Both functions are ~10-line builders that take the raw document pool and return a PubMed-only projection.

| | `direction_checker.cited_sources_from_documents` | `retrieval_refusal.pool_sources_from_documents` |
|---|---|---|
| Defined | `api/services/direction_checker.py:76-90` | `api/services/retrieval_refusal.py:69-79` |
| Guard | `:83-84` `!= SourceType.PUBMED → continue` | `:73-74` `!= SourceType.PUBMED → continue` |
| Regex | `:86` | `:76` |
| Returns | `list[CitedSource(pmid, abstract)]` | `list[tuple[pmid, abstract]]` |

**Callers — complete list (`git grep`):**

| Caller | Context |
|---|---|
| `api/server.py:551` | `_run_direction_check_background` — **the only prod caller of `direction_checker`** |
| `api/server.py:582` | `_run_retrieval_refusal_background` — **the only prod caller of `retrieval_refusal`** |
| `scripts/direction_shadow_eval.py:153` | offline eval harness, not prod |

Nothing else calls either builder. `scripts/direction_shadow_rescore.py:24`, `scripts/retrieval_refusal_eval.py:31`, `scripts/retrieval_refusal_prior_probe.py:15` import the modules for offline scoring.

**What builds the document list:** `api/server.py:860` — `documents, retrieval_status = await retrieve_task`, where `retrieve_task = asyncio.create_task(retriever.retrieve(...))` (`:828`). That is the **full mixed pool** — PubMed, FDA, LOCAL, TFDA, DAILYMED — the same object handed to the generator at `:890` (`documents=documents`) and to the LLM judge at `:516`. It is passed unmodified to both hooks:

```
api/server.py:951   _run_direction_check_background(audit_id, body.question, full_answer, documents)
api/server.py:959   _run_retrieval_refusal_background(audit_id, body.question, documents)
```

**So: is it filtered by `source_type` anywhere upstream? No — and deliberately not.** There is no upstream filter between `retriever.retrieve()` and the hook call. A DailyMed or TFDA `RetrievedDocument` **does enter both functions**. It is stopped inside, at `:83-84` / `:73-74`, on the iteration before the regex would run. **The guard is in-function, not upstream.**

**Guard robustness — checked, not assumed.** `getattr(d, "source_type", None)` fails closed three ways: a dict or a duck-typed object without the attribute yields `None ≠ PUBMED → continue`; `SourceType` is a `str, Enum` (`api/models/schemas.py:14-20`), so a raw string `"dailymed"` also `!= SourceType.PUBMED → continue`; and `RetrievedDocument.source_type` is a pydantic-validated `SourceType` field (`api/models/schemas.py:116`), constructed as `SourceType(raw_source_type)` on the vector-store path (`api/database/vector_store.py:107`). There is no spelling of a non-PubMed document that survives the guard.

## 3. `source_id` traced to the call site — the actual string

| Source | `source_id` built at | Actual string shape | What the regex would find *if it ran* | Reaches `:86` / `:76`? |
|---|---|---|---|---|
| **PubMed** | `api/data_sources/pubmed.py:36-37` → `f"PMID:{self.pmid}"` | `PMID:29421936` | `29421936` ✅ correct | **YES** |
| **DailyMed** (Research corpus) | `scripts/build_dailymed_label_corpus.py:291` → `f"DailyMed:{setid}#{loinc}~{idx}"` | `DailyMed:a1b2c3d4-…#34073-7~0` | first ≥5-digit run in the UUID, else `34073` from the LOINC | **NO** — stopped at `:84`/`:74` |
| **DailyMed** (Verify live client) | `api/data_sources/dailymed.py:68-70` → `f"DailyMed:{self.setid}"` | `DailyMed:a1b2c3d4-…` | first ≥5-digit run in the UUID | **NO** |
| **TFDA** | `scripts/build_tfda_indication_corpus.py:124` → `"source_id": rep_lic` | the 許可證字號, e.g. `057803` | the licence number itself | **NO** |
| **FDA** | `api/data_sources/fda.py:35-36` → `f"FDA:{self.brand_name}"` | `FDA:LIPITOR` | usually no match → `None` | **NO** |

**The string at the moment the regex runs is always `PMID:{digits}`, and nothing else.** The prior measurement (DailyMed → `84432`, TFDA → `057803`, recorded `TECH_DEBT.md:322`) is real, but it was measured through **`scripts/citation_truth_check.py:132`**, which is the site with **no** guard — the `or`-chained URL fallback there is the only PubMed-aware branch, and it is unreachable whenever `source_id` holds a 5-digit run. That script's defect stands exactly as filed. It does not extend to `api/`.

## 4. What the extracted number feeds

**`direction_checker`** — `CitedSource.pmid` (`:89`). It is used as a **label only**: interpolated into the counterintuitiveness prompt (`:137` `ABSTRACT (PMID {source.pmid})`), the structural catalog (`:187`), error messages (`:118`, `:121`), and carried out as `DirectionFlag.selected_anchor_pmid`. **The actual evidence judged is `d.content` — the full abstract already in hand.** No fetch, no lookup, no join. A wrong pmid would mislabel a log line; it could not cause the wrong text to be judged.

**`retrieval_refusal`** — same: `(pmid, abstract)` (`:78`), pmid interpolated into `_source_direction`'s prompt (`:109`) and used as the `dirs{}` dict key (`:159`), which feeds `_spread()` (`:160`).

**The decision** (`api/services/retrieval_refusal.py:165`):
```python
refuse = bool(spread["one_sided"] and counter)
```
`spread` is computed from the **stance strings**, not the pmids (`:137-141`); `counter` comes from `_counter_prior()`, which takes only `factor`/`outcome`. **The pmid does not enter the refusal decision.** Its only structural role is as a dict key — a collision (two docs yielding the same digits) would silently drop one source from `dirs` and could shift `one_sided`. That is a real hazard in principle, but it cannot arise here: PubMed `source_id` is `PMID:{pmid}` and PMIDs are unique.

**Does `retrieval_refusal` decide whether the product refuses to answer? No — not today.** The module docstring (`:14-15`) and the caller docstring (`api/server.py:573-578`) both state SHADOW/decision-only. `_run_retrieval_refusal_background` (`:581-598`) does exactly three things: `logger.info`, write `AuditLog.extra_data["retrieval_refusal"]`, `db.commit()`. **`decision.refuse` is never read by any request path.** It is fired as `asyncio.create_task` *after* the answer has already streamed, wrapped in `try/except` (`:597-598`), touching no SSE frame.

**Is it user-visible? No.** Nothing in the SSE stream, the answer, or the citations reflects it. It reaches the `AuditLog` row and the application log only. The name "REFUSAL" describes what the detector *would* recommend under a future enforcement mode; enforcement is explicitly out of scope ("A2 / route-gated", `:15`).

## 5. Path and flag

**Research only.** Both `asyncio.create_task` calls sit inside the Research SSE generator (`api/server.py:949-960`), in the same `if audit_id` block as the LLM judge and the source-weight shadow. `grep -n "_run_direction_check_background\|_run_retrieval_refusal_background" api/server.py` returns **exactly 4 lines — 2 defs, 2 calls.** No Verify path, no Explain path.

**Both are behind flags, both default OFF:**
```
api/server.py:949   os.getenv("DIRECTION_CHECK_SHADOW",   "").lower() == "true"
api/server.py:957   os.getenv("RETRIEVAL_REFUSAL_SHADOW", "").lower() == "true"
```
Neither appears in `fly.toml` (`[env]` holds only `SENTRY_DSN`) — they are Fly secrets.

**Prod state, per the most recent recorded check** — `docs/local_corpus_deprecation_c1_build.md:20`, last committed **2026-08-03** (`0b63caa`), 21 days ago:

> `RETRIEVAL_REFUSAL_SHADOW` · `SOURCE_WEIGHT_SHADOW` · `SOURCE_WEIGHT_ACTIVE` all **present, digest `d8c5ac2e11c8e492`, Deployed = ON**; `DIRECTION_CHECK_SHADOW` and `QUESTION_NEUTRALIZATION_SHADOW` **absent = unset = OFF**

So **`RETRIEVAL_REFUSAL_SHADOW` is ON in prod and `pool_sources_from_documents` runs on live Research traffic; `DIRECTION_CHECK_SHADOW` is OFF and `cited_sources_from_documents` does not run in prod at all.** ⚠️ This is a **committed-doc claim, not a live read** — confirming it needs `fly secrets list`, an external call outside read-only recon. It does not change the verdict either way: the guard makes the regex safe whether the flag is on or off.

## 6. Test coverage: **zero**

`git grep -rn "direction_checker\|retrieval_refusal\|cited_sources_from_documents\|pool_sources_from_documents" -- tests/` returns **no hits**. Neither function, neither module, and neither guard is exercised by any of the 342 tests. **The guards are correct today and nothing would fail if someone deleted them** — which is the actual live risk at these two sites, and it is a Rule 17 gap, not a reachability defect.

## 7. Duplicate count: **10 is the complete count for this bug**, not a floor

Re-searched every spelling you named, plus others:

| Spelling | Result |
|---|---|
| `\d{5,}` | **10 occurrences / 7 files** — the original count |
| `[0-9]{5,}` | **0 hits** repo-wide |
| any `\d{N,}` (`\d{4,}`, `\d{3,}`, `\d{6,}`…) | 10 more hits, **all unrelated**: `api/middleware/phi_handler.py:134,148,152,153,172,177,183` (PHI redaction on user text), `scripts/build_dailymed_label_corpus.py:142` (`_DEVCODE_RE`, a title-prefix stripper), `tests/probes/baton_check/check_baton.py:48` (`FIGURE`), `tests/run_golden_tests.py:327` (`_CITE_MARKER_RE`, matches `[n]` markers). **None touches `source_id`.** |
| bare `\d+` on `source_id` | **0** — the only bare `\d+` is `citation_truth_check.py:132`'s URL fallback, already counted |
| `int()` / `isdigit()` on `source_id` | **0**. `api/rag/retriever.py:550` is `year_str.isdigit()`; `tests/probes/wrongdrug/answer_layer_pack.py:81` is `c["id"][1:].isdigit()` on a case ID |
| `.split` / `.replace` / `.lstrip` / slicing on `source_id` | 8 hits, **a different and correct class** — see below |

**Verdict on the count: 10 is COMPLETE, not a lower bound**, for the digit-scraping bug. Of those 10, **the guarded ones are `api/services/direction_checker.py:86`, `api/services/retrieval_refusal.py:76`, and `scripts/question_neutralization_eval.py:59-60`** (5 occurrences). **The 5 genuinely unguarded ones are all in `scripts/`:**

```
scripts/citation_truth_check.py:132
scripts/direction_shadow_eval.py:98, 141, 143
scripts/pathb_recall_probe.py:58
scripts/retrieval_recall_check.py:46
```

**One adjacent class I checked rather than assumed, and it is NOT a duplicate.** `scripts/dailymed_danger_path_verify.py:133`, `tests/probes/wrongdrug/owner_assertion.py:156,162`, and `tests/probes/ownership_eval/seat_v2.py:378-380` extract `setid`/`loinc` by splitting on the `DailyMed:` and `#` **keys** — which is the *correct* pattern per Rule 21 ("where an exact key exists, use the key, not the text"). `_dm_section_class` guards properly (`:130` `if not source_id.startswith("DailyMed:") or "#" not in source_id: return None`). These are key-based, and their failure mode on a foreign id would be a loud `IndexError`, not silent mis-resolution. **Do not fold them into the count.**

---

### Bottom line

**(b) NOT REACHABLE.** A DailyMed or TFDA document does reach both *functions* — the pool is unfiltered upstream — but is discarded at `api/services/direction_checker.py:83-84` and `api/services/retrieval_refusal.py:73-74`, before the regex on the next-but-one line. The regex only ever sees `PMID:{digits}`. `retrieval_refusal` does run in prod (flag ON as of the 2026-08-03 record) and `direction_checker` does not (flag OFF), but neither is user-visible: both are post-stream, background, sink-only, and `decision.refuse` is never read by any request path.

**The blast radius from my previous report shrinks accordingly: the car is `scripts/`-only, 5 unguarded occurrences across 4 files, no product-code exposure.** The existing TECH_DEBT scoping ("not a gate, PubMed-only, flagged not fixed") was correct and needs no correction — my last report's suggestion that it was incomplete was the error. The one real gap that remains at the `api/` sites is **item 6: zero test coverage on either guard**, so nothing would catch their removal.
