# DURLAZA `min_score` — one embedding, one number, and a reframing

**Date:** 2026-08-06 · **Scope:** ONE authorized network call (a query embedding). No pipeline run, no
`api/` or `data/` change, no index write, no rewritten-arm embeddings, no gate cycle.

**🔴 HEADLINE, STATED FIRST: the measurement did NOT close the UNKNOWN — it reframed it, and
refuted my own prior framing in the process.** `DURLAZA — Contraindications` fails the floor on the
raw arm — but **so does every other document in the store, including the one that is actually
cited**. The raw arm therefore contributes **zero** DailyMed documents to this query, and the
production citation must originate from a **rewritten** arm this baton was not authorized to embed.

---

## 1. Method, and what was sampled (Rule 21)

**Sampled:** exactly one query string — `aspirin contraindications and who should not take it` —
embedded once via `DailyMedCorpusStore._get_embedding()`, i.e. production's own embedder and model,
not a re-implementation. Cosine computed against **all 4608** shipped rows using the same expression
as `vector_store.py:87` (`emb @ q / (norms · |q|)`).

**Verified before computing** — row 57 identity by all three of `setid` /`moiety` / section code, not
by row number:

| field | value |
|---|---|
| `setid` | `4c2a1403-3862-1efd-0a91-444989222b37` |
| `moiety` | `ACETYLSALICYLIC ACID` |
| section | `34070-3` (Contraindications) |
| title | DURLAZA (Acetylsalicylic Acid) — Contraindications |

**Rule 23 — both keys enumerated** (7 docs for this substance, not 5):

| key | rows | sections |
|---|---|---|
| `ASPIRIN` → VAZALORE | 277, 278 | `34068-7`, `34067-9` — **no safety sections; no `34071-1` in the shipped index at all** |
| `ACETYLSALICYLIC ACID` → DURLAZA | 57–61 | `34070-3`, `34068-7`, `34067-9`, `34073-7`, `43685-7` |

**The query string is the raw one, verified not assumed:** production and the c2 probe both pass
`_annotate_research_question(q)` (`api/server.py:803`, `_c2_ab_retrieval.py:78`). For this English
fixture it returns the input **byte-identical** — the function short-circuits on `has_cjk()` false
(`api/server.py:718-719`). Asserted in the measurement script.

**NOT sampled, and therefore not claimed:** the ~9 **rewritten** queries that `_dailymed_union_queries`
(`retriever.py:395-413`) also embeds. Those are LLM-generated and nondeterministic; measuring them is
a distribution, not one number, and was outside the authorization. **Every statement below is scoped
to the raw arm.**

**Thresholds in force** — two gates in one call (`retriever.py:628-632`):

| gate | value | source |
|---|---|---|
| cosine floor `min_score` | **0.6** | `local_threshold`, `api/server.py:450`; default `retriever.py:95` |
| in-store top-N `n_results` | **5** (= `max_results`) | `vector_store.py:120-121` — `if len(results) >= n_results: break` |

---

## 2. The numbers

| document | key | cosine | vs 0.6 | in-store rank / 4608 | inside `n_results=5`? |
|---|---|---|---|---|---|
| **DURLAZA — Contraindications** (the owned doc) | `ACETYLSALICYLIC ACID` | **0.4031** | **FAILS** (−0.1969) | **500** | NO |
| **Clanza (Aceclofenac) — Contraindications** *(cited 12/12)* | ACECLOFENAC | **0.5787** | **FAILS** (−0.0213) | **0** | YES |
| Mefenamic acid — Contraindications *(cited, treatment arm)* | MEFENAMIC ACID | 0.5493 | FAILS (−0.0507) | 3 | YES |
| VAZALORE — Indications and Usage | `ASPIRIN` | 0.4733 | FAILS (−0.1267) | 65 | NO |
| VAZALORE — Dosage and Administration | `ASPIRIN` | 0.3109 | FAILS (−0.2891) | 2165 | NO |

**Documents clearing the 0.6 floor across the whole store on the raw query: `0 / 4608`.**

Top of the store on this query — every one of them below the floor:

```
#0  0.5787  ACECLOFENAC      34070-3   Clanza (Aceclofenac) — Contraindications
#1  0.5705  CARBACHOL        34070-3   MIOSTAT (carbachol) — Contraindications
#2  0.5555  SALSALATE        34070-3   Salsalate — Contraindications
#3  0.5493  MEFENAMIC ACID   34070-3   Mefenamic acid — Contraindications
#4  0.5481  KETOPROFEN       34070-3   Ketoprofen — Contraindications      <= n_results=5 cut
#5  0.5443  PIROXICAM        34070-3   Piroxicam — Contraindications
```

**Ambiguity rule applied:** DURLAZA's margin is **−0.1969** — far outside the ±0.02 band, so its
FAIL is unambiguous. ⚠️ **ACECLOFENAC's margin is −0.0213**, which is *just* outside the band
(0.0213 vs 0.02). It is reported as a fail **at the band edge**, not as a clean one; a different
embedding snapshot could move it across. Do not build on ACECLOFENAC's raw-arm score.

---

## 3. Verdict — **PARTIAL**, on the four-way split

| mechanism | raw arm |
|---|---|
| **threshold** (<0.6) | ✅ **YES for DURLAZA — and for all 4608 docs** |
| **in-store rank cutoff** (clears 0.6, outside store top-5) | n/a — nothing clears 0.6, so this gate is never reached |
| **downstream ranking** (enters pool, loses later) | ❌ not on this arm — nothing enters |
| **coverage** (no owned doc exists) | ❌ **NO** — the owned doc exists and is embedded (row 57, norm 0.9995) |

**Scoped verdict:** on the deterministic raw arm the mechanism is **threshold**, decisively — and
**vacuously**, because the arm returns an empty set.

**Unscoped verdict: UNRESOLVED.** The measurement's own internal check refutes any extrapolation:
**ACECLOFENAC is cited 12/12 in production yet scores 0.5787 on the raw arm, below the floor.** A
document that cannot enter the pool via this arm is nonetheless cited every single time — therefore
**the DailyMed pool on this query is produced entirely by rewritten queries**, and the raw arm
explains none of it. **Whether DURLAZA clears on a rewritten arm is still UNKNOWN.** Not extrapolated.

### What this does establish, and it is not nothing

1. **Coverage is definitively eliminated** as the mechanism for the flagship case — the owned document
   exists, is embedded, is row-aligned. The remaining candidates are threshold and ranking, both
   **on the rewritten arms**.
2. **Lever 1's raw augment contributes zero documents on this query.** `_dailymed_union_queries`
   appends the raw query as *"a deterministic augment"* to recover straddling safety sections
   (`retriever.py:398-399`, shipped `1217d66`). On the flagship wrong-drug query it recovers nothing —
   0/4608 above floor. ⚠️ **One query. Not a claim about Lever 1 in general.**
3. **The semantic gap is large, not marginal.** DURLAZA sits at rank **500** while ACECLOFENAC sits at
   rank **0** — a 500-place gap on the raw embedding. This is *suggestive* that the ordering may
   survive rewriting, but rank order under one embedding does **not** predict order under another.
   **Explicitly not a prediction.**

### The cheapest next measurement, if you want the UNKNOWN closed

Embed the **rewritten** arms — but they are nondeterministic, so it is N calls for a distribution.
A cheaper deterministic proxy: embed one or two *fixed, hand-written* rewrites of the form
`_rewrite_query` produces and report DURLAZA vs ACECLOFENAC on those. **Not authorized here, not done.**

---

## 4. Consequence for the wrong-drug filter (open-item #2)

Unchanged from the T1 report, and now sharper: **if the mechanism on the rewritten arms is also
threshold, a filter that removes ACECLOFENAC turns this query into ZERO DailyMed citations rather
than a correct one.** The raw-arm measurement cannot distinguish that case, so **the filter's premise
is still unverified**. Measure the rewritten arms before building it.

---

## 5. Rule 18 — what was skipped or is unverified

- **Rewritten arms: NOT measured.** One call, raw arm only. The UNKNOWN is narrowed, not closed.
- **ACECLOFENAC's raw-arm score sits at the ambiguity band edge** (−0.0213) — flagged, not rounded.
- **No pipeline run.** No claim about what the LLM relevance filter, the safety-section exemption,
  the reranker, or the composite reorder do to any of these documents.
- **One query only.** No generalisation to other drugs or other query shapes.
- The query embedding was cached to `tests/results/_durlaza_qemb.npy` (**gitignored scratch, not the
  index**) so re-analysis never needs a second call.
