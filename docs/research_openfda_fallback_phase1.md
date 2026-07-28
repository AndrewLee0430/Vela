# Research openFDA fallback — PHASE 1 MEASUREMENT (read-only) — 2026-07-28

**Status: MEASUREMENT COMPLETE. Phase 2 NOT started — no fallback written.**

## ⛔ RECOMMENDATION: DO NOT BUILD THE FALLBACK. CLOSE the [P2] entry as INADEQUATE, and redirect to a defect the measurement exposed as far larger.

Two independent, each-sufficient reasons:

1. **The fallback would not fire where it is needed.** Research already queries openFDA on **every**
   query as a parallel retrieval source — and **openFDA documents were cited 0 / 18 runs** across six
   single-drug OTC safety queries. openFDA content is retrieved and then loses the ranking
   competition. Adding a *fallback* to a source that is already retrieved and already discarded
   changes nothing.
2. **The real defect is different and worse: Research cites ANOTHER DRUG's safety section** on
   single-drug OTC safety queries — measured on 5 of 6 test queries.

---

## 1. Verify's mitigation, mapped precisely (Task 1)

| Aspect | Detail |
|---|---|
| **Trigger** | `api/server.py:1211-1217` — for each drug, DailyMed is Tier 1, and a label "counts" ONLY if `drug_interactions` (LOINC 34073-7) is present. Absent → index appended to `openfda_indices`. The comment at `:1202-1204` names **aspirin** explicitly as the OTC Drug-Facts case. |
| **What it fetches** | `api/server.py:1219-1225` — `fda_client.search_drug_labels(drug, limit=1)` for the miss indices only. |
| **What it returns** | `:1240-1243` — the openFDA label is appended to `drug_labels`, with `label_provenance` recording `{"drug", "label", "setid": None, "tier": "openfda"}`. **`setid` is deliberately `None`** for openFDA-tier entries. |
| **Tier 3** | `:1256-1266` — spell-correction retry (Levenshtein ≤3 vs `KNOWN_DRUGS`) re-queries openFDA; also records `tier: "openfda"`. |
| **Attribution to the user** | `_resolve_interaction_source` (`:1002-1035`) maps provenance → `(source_str, source_url, attribution_kind)`. DailyMed-grounded → `"Interaction text cited from DailyMed label; severity is Vela's AI interpretation"` + a **specific SPL deep-link** (`drugInfo.cfm?setid=…`) + `ATTR_DAILYMED_GROUNDED`. Otherwise → `"AI analysis of FDA label"` + a **generic search link** + `ATTR_OPENFDA_ANALYSIS`. |
| **Citation-integrity rule** | `:1013-1020` — a specific setid is attached **only on a confident drug match**; on CJK→INN substitution, LLM rename or multi-word mismatch it **fails honest** and never invents a setid. |
| **Frontend chip** | `attribution_kind` (`schemas.py:235`, default `"openfda_analysis"`) is the **stable key** the frontend renders honesty markers from — deliberately decoupled from the display string. |

---

## 2. Rule 19 checklist — everything Verify does around DailyMed data (Task 2)

**This is Rule 19's first real use.** The openFDA fallback is one row; the others were found by
working the list rather than by looking for the known item.

| # | Verify does… | ref | Research has it? | Carry across / decline |
|---|---|---|---|---|
| 1 | **openFDA fall-through** when the DailyMed label lacks 34073-7 | `server.py:1218-1225` | **N/A — different retrieval shape.** Research queries openFDA **in parallel every query** (`retriever.py:185`, `_search_fda` `:657`), so there is no "miss" to fall through from | **DECLINE — the premise does not transfer.** See §3: openFDA is already retrieved and cited 0/18 |
| 2 | **Per-label provenance tier** (`dailymed` vs `openfda`) | `server.py:1234/1243` | **NO** — Research citations carry `source_type` but no tier/provenance concept | **DECLINE for now.** `source_type` already distinguishes the source; a tier adds nothing Research renders |
| 3 | **`attribution_kind` honesty key** (3 stable values) | `schemas.py:235` | **NO** — `Citation` (`schemas.py:69-81`) has no attribution field | **⚠️ GENUINE GAP — but belongs to the Verify [P1] honesty family, not here.** Research asserts less (it cites documents rather than generating an interaction verdict), so the exposure is lower; record, do not bundle |
| 4 | **Severity-is-Vela's-AI disclaimer** in the source string | `server.py:992` | **N/A** — Research emits no severity | Not applicable |
| 5 | **Citation-integrity: never invent a setid on a non-confident match** | `server.py:1013-1020` | **PARTIAL / ⚠️** — Research cites whatever the vector search returns, with **no drug-identity check at all**. §4 shows this misfires | **⚠️ THIS IS THE REAL GAP — see §4.** Research needs the *equivalent* guarantee, not the same mechanism |
| 6 | **Spell-correction + user-visible notice** | `server.py:1246-1254` | **NO** — Research relies on `_rewrite_query` (LLM), no deterministic correction, no notice | **DECLINE** — Research's free-text rewrite covers most of it; a notice would be noise on a research query |
| 7 | **LLM fallback when NO label found, labelled honestly** | `server.py:1267+` | **YES (equivalent)** — Research has the no-retrieval `isFallback` path with its own honest banner | Already carried across |
| 8 | **Snippet truncation** | `schemas.py:133` `content[:500]` | **YES** — same `to_citation()` path | Shared code; no gap |

**Rule 19 verdict:** of 8 mitigations, **1 is a genuine gap that matters (#5)**, **1 is a gap owned by
another entry (#3)**, 4 are explicitly declined with reasons, 2 are already present. **The item the
[P2] entry was opened for (#1) is a decline, not a gap.**

---

## 3. Exposure sizing (Task 3)

**Corpus-side (offline):** 128 / 1038 moieties (**12.3%**) have **no safety section**. Of these,
**23 are clinically significant** (the rest are topical/antiseptic/excipient — aluminium salts,
benzalkonium, carbomer, charcoal…):

> ASPIRIN · IBUPROFEN · NAPROXEN · CIMETIDINE · OMEPRAZOLE · ESOMEPRAZOLE (×2 salts) · FAMOTIDINE ·
> CETIRIZINE · LEVOCETIRIZINE · CHLORPHENIRAMINE · LOPERAMIDE · MELATONIN · NICOTINE ·
> PSEUDOEPHEDRINE · DEXTROMETHORPHAN (×2) · BISACODYL · CHLORAL HYDRATE · MAGNESIUM HYDROXIDE ·
> MAGNESIUM OXIDE · POTASSIUM GLUCONATE · POTASSIUM IODIDE

**openFDA availability (live, 15 sampled): 15/15 hit, 14/15 carry safety text.** So the data a
fallback would fetch does exist.

**But that is not the binding constraint.** §4 shows openFDA documents already reach Research's
retrieval and are **never cited**.

---

## 4. ⛔ The scope nuance does NOT hold as hoped — and the real defect is wrong-drug citation (Task 4)

Six single-drug OTC safety queries, N=3 each (18 runs), on drugs whose moiety has no DailyMed safety
section. Applying the pair-aware probe's content-audit discipline — *which drug does the cited section
actually belong to?* — rather than counting "a safety section was cited":

| Query | DailyMed safety cited | openFDA cited | Cited section actually belongs to |
|---|---|---|---|
| aspirin contraindications | 3/3 | **0/3** | **ACECLOFENAC** — a different NSAID |
| ibuprofen warnings | 3/3 | **0/3** | IBUPROFEN LYSINE ✅ **+ KETOPROFEN, MEFENAMIC ACID, PIROXICAM** |
| naproxen interactions | 3/3 | **0/3** | **NABUMETONE** — a different NSAID |
| **cimetidine interactions** | 3/3 | **0/3** | **COBIMETINIB HEMIFUMARATE** — a melanoma kinase inhibitor. Name similarity only. |
| omeprazole contraindications | 3/3 | **0/3** | **PANTOPRAZOLE** (+ ESOMEPRAZOLE ✅) |
| loperamide warnings | **0/3** | **0/3** | — nothing retrieved |

**Two findings:**

- **openFDA is cited 0 / 18 runs.** It is queried every time (`retriever.py:185`) and consistently
  loses to PubMed/local/DailyMed in the composite. **A fallback cannot help a source that is already
  present and already discarded.**
- **5 of 6 queries cite another drug's safety section.** `cimetidine → COBIMETINIB` is the clearest:
  an OTC H2-blocker query surfacing an oncology drug's interaction section on name similarity.

**Relation to the bilateral finding:** on *pair* queries, citing the counterpart drug's label is
**correct** — that label documents the interaction. On *single-drug* queries there is no counterpart,
so an adjacent drug's section is simply **wrong**, and the same retrieval behaviour flips from
strength to defect. The [P2] entry's scope nuance ("pair queries largely unaffected; exposure is
single-drug") is **directionally right but understates it** — the single-drug exposure is not a
missing fallback, it is misattributed citation.

**This is re-scoped surface (3)** — *danger-path wrong-object citation intrusion* — and it is
**substantially more prevalent than the spironolactone case suggested**: 5/6 queries here vs 4/8 runs
on one query there.

---

## 5. Verdict vs pool_size (Task 5 — free data, no re-run)

From today's §2.7 gate (`golden_results_20260728_114818.json`), all 20 cases carrying `pool_identity`:

| status | n | pool_size mean | min | max |
|---|---|---|---|---|
| PASS | 19 | 4.47 | **1** | 5 |
| WARN | 1 | 5.00 | 5 | 5 |

**No relationship visible.** R15 **PASSED on a 1-document pool**; the single WARN (R20) had a **full
5-document pool**. Combined with the 75-run harvest (`pool_size ≤ 2` on 11% of runs), small pools are
**not** obviously associated with worse verdicts.

**⚠️ Suggestive only — no causal claim.** n=1 per case, exactly one WARN, and one session. This
neither supports nor refutes a pool_size→verdict link; it removes the assumption that small pools are
self-evidently bad.

---

## 6. Plan-back

### Recommended: CLOSE the "Research has no openFDA fallback" [P2] as INADEQUATE

**Record in BACKLOG:** the entry rests on a premise that does not transfer between the two surfaces.
Verify needs a fallback because it queries DailyMed *by name* and has nothing else; Research fans out
to openFDA *in parallel every query*. Measured: **openFDA cited 0/18** on exactly the queries the
fallback was meant to serve. Building it would add a code path that cannot change an outcome.

### Redirect to re-scoped surface (3) — wrong-object citation, now the dominant failure mode

The measurement's real product. Recommended framing for that entry:

- **What:** on single-drug safety queries, Research cites a safety section belonging to a *different
  drug* — 5/6 measured queries, including a cross-therapeutic-class error
  (`cimetidine → COBIMETINIB`).
- **Why it is not the same as the pair case:** bilateral coverage makes counterpart citation correct
  for pairs and wrong for single-drug queries. Any fix must **not** break the pair behaviour, which is
  load-bearing (it is why pair-aware retrieval was refuted).
- **Why it is invisible today:** every current gate metric counts "a whitelisted LOINC was cited" as
  success. Rule 17 applies — assert the cited section *concerns the queried drug*.
- **Cheapest first step (measure, do not build):** add the content-audit assertion
  (`tests/results/_pairaware_m1_content_audit.py` already implements it) to the recall gate, and size
  the defect across the full research golden set before touching retrieval.

### If Phase 2 is nevertheless authorized, the gate list stands

Additive-only; no threshold/composite/`top_k` change · guard tests with a **negative control**
(injected bug must FAIL the guard) · **§2.7 20/20** · section-aware danger-path re-gate · prod
human-eye gate · no flag/secret changes.

**Gate-machinery note (carried from the baton):** the fail-loud guard (`61200cd`) has been
negative-controlled by injection but **never exercised on a real gate**. Whenever the next §2.7 runs,
report `run_complete`, `gate_valid` and the **exit code** explicitly — not just the pass count.
*(Today's 20/20 gate predates the guard in the same commit series; its JSON does not carry the fields.)*

---

## 7. Assumptions and limits

1. **n=6 single-drug queries, N=3.** Enough to show the defect exists and is not rare; **not** enough
   to estimate its rate across the corpus.
2. **"Clinically significant" (23 of 128) is my judgement**, from a keyword list over moiety names —
   disputable, and listed in full above so it can be challenged.
3. **openFDA availability sampled at 15 of 23**, not exhaustive.
4. **Verdict-vs-pool_size is n=1 per case with a single WARN** — suggestive only.
5. **`loperamide` retrieved no safety section from any source** — a recall miss distinct from
   misattribution; not investigated here.
6. Phase 2 was **not** started; no product code was modified in this phase.
