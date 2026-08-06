# The rewrite arm — the flagship wrong-drug case is a THRESHOLD defect, unanimously

**Date:** 2026-08-06 · **Budget:** 10 successful calls, hard cap, **10 spent** (9 rewrite LLM + 1
batched embedding) · **Scope:** one query. No pipeline run, no `api/`/`data/` change, no index write.

> ## ⚠️ THIS IS A FRESH SAMPLE, NOT A RECONSTRUCTION
> **The rewrite strings used in the historical 12/12 runs are PERMANENTLY UNRECOVERABLE.** They were
> never persisted, `_dailymed_union_queries` logs nothing, and `_rewrite_query` is a nondeterministic
> LLM call. Everything below is a **fresh draw of the same distribution**, justified only by the fact
> that the outcome it explains (ACECLOFENAC cited 12/12 across two index configurations) is itself
> stable. See the observability-gap entry in TECH_DEBT.

---

## 1. What was sampled, and what was not (Rule 21)

**Sampled:** three independent draws of `_dailymed_union_queries("aspirin contraindications and who
should not take it", k=3)` — production's own function, 9 LLM calls. Union of all emitted strings,
de-duplicated → **9 unique rewrite strings**. All 9 embedded in **one batched call** via production's
embedder (`text-embedding-3-small`). The raw string's vector was reused from the `d1ec8e0` cache —
not re-embedded.

**An abort guard was installed** on `_translate_to_medical_english`: any fallback would have raised
rather than spending a call. **It never fired** — all 9 rewrites succeeded on the primary path, so
no fallback strings contaminate the sample.

**NOT sampled:** any other query · the LLM relevance filter, the safety-section exemption, the
reranker, the composite reorder, the generator · what the *historical* runs drew. **One query only.
No generalisation.**

**Rule 23 — both keys enumerated at every lookup:** `ASPIRIN` → rows 277–278 (VAZALORE; no safety
sections) · `ACETYLSALICYLIC ACID` → rows 57–61 (DURLAZA). Row 57 identity was verified by `setid` +
`moiety` + section code in the prior baton and re-verified before this run.

**Consistency with `d1ec8e0`:** the raw arm reproduces exactly — DURLAZA 0.4031 / rank 500,
ACECLOFENAC 0.5787 / rank 0, 0 docs above floor. **No contradiction; no stop triggered.**

---

## 2. The distribution — 9 rewrite strings

Gates: cosine floor **0.6** (`server.py:450`) and in-store cutoff **`n_results=5`**
(`vector_store.py:120-121`).

| rewrite string | DURLAZA cos / rank | ≥0.6 | ACECLOFENAC cos / rank | ≥0.6 | docs ≥0.6 |
|---|---|---|---|---|---|
| *(raw, cached)* aspirin contraindications and who should not take it | 0.4031 / 500 | n | 0.5787 / 0 | n | 0 |
| aspirin contraindications mechanism adverse effects | 0.3906 / 849 | n | 0.5658 / 0 | n | 0 |
| aspirin use contraindications clinical management | 0.3915 / 999 | n | 0.5596 / 1 | n | 0 |
| **acetylsalicylic acid contraindications patient selection** | 0.3686 / 823 | n | **0.6787 / 0** | **Y** | 1 |
| aspirin contraindications mechanism | 0.3923 / 632 | n | 0.5860 / 0 | n | 0 |
| aspirin adverse effects treatment guidelines | 0.3506 / 1995 | n | 0.5114 / 4 | n | 0 |
| **acetylsalicylic acid contraindications MeSH** | 0.3777 / 798 | n | **0.6493 / 0** | **Y** | 1 |
| aspirin contraindications mechanism risks | 0.4051 / 648 | n | 0.5806 / 0 | n | 0 |
| aspirin adverse effects patient management | 0.3534 / 2151 | n | 0.5173 / 6 | n | 0 |
| **acetylsalicylic acid contraindications guidelines** | 0.3731 / 817 | n | **0.6681 / 0** | **Y** | 1 |

### Counts over the 9 unique rewrite strings

| | count |
|---|---|
| surfaces **ACECLOFENAC** (clears 0.6 **and** in top-5) | **3 / 9** |
| surfaces **DURLAZA** | **0 / 9** |
| surfaces **BOTH** — the only case where a filter helps | **0 / 9** |
| surfaces **NEITHER** — nothing clears the floor at all | **6 / 9** |
| ACECLOFENAC only | 3 / 9 |
| DURLAZA only | 0 / 9 |
| DURLAZA clears 0.6 *at any rank* | **0 / 9** |

### Cross-draw stability — high

**6 of the 9 strings appeared in all three draws; draws 2 and 3 were identical to each other.** Draw
1 contributed 3 extra strings. So `_rewrite_query` is far more stable on this query than the repo's
general "rewrite nondeterminism" caveat implies. ⚠️ One query, three draws — not a claim about the
rewriter in general.

**The picture did not differ across draws.** DURLAZA fails on every string from every draw.

---

## 3. Four-way split — no disagreement to report

| mechanism | DURLAZA, across all 9 strings |
|---|---|
| **coverage** (no owned doc exists) | ❌ NO — row 57 exists, embedded, row-aligned |
| **threshold** (<0.6) | ✅ **YES — 9 / 9, unanimous** |
| **in-store rank cutoff** (clears 0.6, outside top-5) | never reached — it fails the floor first |
| **downstream ranking** (enters pool, loses) | never reached — it never enters |

**The distribution does not disagree with itself. It is unanimous: THRESHOLD.** DURLAZA's best score
across every string sampled is **0.4051** against a **0.6** floor — a **0.195 shortfall**, not a near
miss. It ranks between **632 and 2151** of 4608. Nothing here is marginal.

⚠️ Note this also puts DURLAZA beyond reach of the **safety-section whitelist exemption**
(`retriever.py:38-48`), which re-adds sections the *relevance filter* dropped — it only applies to
documents that were **retrieved** in the first place. A document that never clears the store floor
cannot be rescued by it.

---

## 4. 🔴 THE NUMBER THIS BATON EXISTS TO PRODUCE — for open-item #2

**Denominators named explicitly.**

| question | fraction |
|---|---|
| Removing ACECLOFENAC yields a **CORRECT** citation (DURLAZA present) | **0 / 9** unique rewrite strings sampled |
| Removing ACECLOFENAC yields **ZERO** DailyMed citations | **3 / 3** of the strings where ACECLOFENAC is actually surfaced — i.e. **every string on which the filter would fire at all** |
| Strings where the filter would do **nothing** (ACECLOFENAC not surfaced anyway) | 6 / 9 |

**Stated plainly: on this query, in this sample, there is no string on which removing ACECLOFENAC
produces a correct citation, and every string on which the filter would act produces zero DailyMed
citations instead.**

**No recommendation for or against the filter is made here** — that is a founder decision, and this
is one query.

---

## 5. Why — verified offline, and it is not a ranking accident

`scripts/build_dailymed_label_corpus.py:528`: **`texts = [d["content"] for d in docs]`** — only the
section **content** is embedded. **The title, which is the only place the moiety appears, is NOT.**

| document | does its embedded content contain… | | |
|---|---|---|---|
| | `aspirin` | `acetylsalicylic` | brand |
| **DURLAZA — Contraindications** (the owned doc) | ❌ **no** | ❌ **no** | ✅ "DURLAZA" |
| **Clanza (Aceclofenac) — Contraindications** | ❌ no | ✅ **yes** | — |

DURLAZA's contraindications text reads *"DURLAZA is contraindicated: In patients with a
hypersensitivity to nonsteroidal anti-inflammatory drugs (NSAIDs)…"* — it names the **brand** and
never the substance. Aceclofenac's text reads *"…Like NSAIDS, **acetylsalicylic acid** and other
drugs which inhibit prostaglandin…"*.

**So aspirin's own safety document is semantically invisible to aspirin's own name**, while a
competitor's document is not.

### The sharpest consequence — the synonym key makes it worse, not better

The three strings containing **"acetylsalicylic acid"** — precisely the synonym key Rule 23 exists to
make us enumerate — are the **only** three that push anything above the floor, and what they push is
**ACECLOFENAC**, from 0.586 up to **0.679**. On those same strings **DURLAZA drops to its lowest
scores of the whole sample** (0.3686–0.3777).

**Enumerating the correct synonym strengthens the wrong document and weakens the right one.** That is
a property of what was embedded, not of the retrieval ranking, and it is why this is a threshold
defect rather than one a reranker or filter can address.

---

## 6. Rule 18 — skipped, unverified, out of scope

- **Historical strings: permanently unrecoverable.** This is a fresh sample; it cannot prove what the
  12/12 runs drew.
- **One query.** No claim about any other drug, query shape, or about `_rewrite_query` generally.
- **No pipeline run.** No claim about the relevance filter, exemption, reranker, composite, or
  generator — only about what enters the DailyMed store's output.
- **Not measured:** whether re-embedding content **with the title prefixed** would lift DURLAZA over
  the floor. That is the obvious next question and it needs a corpus re-embed — **out of scope, not
  attempted, and not recommended here.**
- Raw-arm numbers reproduce `d1ec8e0` exactly; no instrument contradiction.
- Vectors and per-string results cached to `tests/results/_rewrite_arm.json` (**gitignored scratch**).
