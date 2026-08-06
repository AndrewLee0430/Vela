# Title-prefix hypothesis — DEAD as a fix, but it reveals what the binding constraint actually is

**Date:** 2026-08-06 · **Budget:** 2 batched embedding calls authorized, **1 used** · **Scope:** 11
documents, 2 drug cases, offline. **No corpus re-embed, no index write, no builder change, no `data/`
change, no pipeline run.**

> ## 🛑 VERDICT: the hypothesis is DEAD. Report-and-stop condition #1 was met.
> **`DURLAZA — Contraindications` clears the 0.6 floor on 0 of 9 rewrite strings *with* the title
> prefix — exactly as it does without it.** Best titled score **0.5614** against a **0.6** floor.
> A 🔴 corpus re-embed is off the table on this evidence. **This is a good outcome, not a failure:
> two batched calls bought the answer that a gate cycle would have bought expensively.**

---

## 1. What was sampled, and two corrections to the baton's premises (Rule 21)

**⚠️ The 9 rewrite-query embeddings were NOT cached.** `_rewrite_arm.json` stored the *strings* and
their cosines, not the vectors. Only the raw-query vector was cached. So the 9 strings were
**re-embedded** — which is *not* the thing the baton warned against: the strings are recorded
verbatim and embedding is near-deterministic for identical input, whereas re-drawing rewrites via the
LLM would not be comparable. **Fidelity was checked, not assumed:** recomputed cosines vs the
recorded ones deviate by at most **0.0049** — embedding-service jitter, comfortably inside the ±0.02
ambiguity band and ~40× smaller than the margin that decides this verdict.

**⚠️ There is no precedent title+content format to match.** The baton asked me to match the builder's
concatenation shape. **All three builders embed content only** — `build_dailymed_label_corpus.py:528`,
`build_tfda_indication_corpus.py:148`, `build_drug_vectordb.py:190`. So no shape exists to match and I
had to **choose** one, stated explicitly:

```
f"{title}\n\n{content}"      title = f"{brand} ({generic}) — {display}"   (builder:293)
```

Example: `'DURLAZA (Acetylsalicylic Acid) — Contraindications\n\n4 CONTRAINDICATIONS DURLAZA is…'`
**A different format could give different numbers.** Not tested — one format, stated.

**Sampled:** 11 documents (identity verified by `setid` + `moiety` + section code before embedding),
against the raw aspirin query + 9 recorded rewrite strings + the raw ibuprofen query.

**NOT sampled:** ibuprofen *rewrite* strings — never captured, and unrecoverable for the same
observability reason as the aspirin ones, so the ibuprofen case is **raw-arm only**. No other drug,
no other query, no pipeline stage beyond the store.

**Rule 23 — both keys on both sides:** aspirin = `ASPIRIN` (VAZALORE, rows 277–278) + `ACETYLSALICYLIC
ACID` (DURLAZA, row 57); ibuprofen = `IBUPROFEN` (ADVIL, rows 2126–2127) + `IBUPROFEN LYSINE`
(NEOPROFEN, rows 2128/2131/2132).

---

## 2. Aspirin — the target and its negative control

| rewrite string | DURLAZA now → titled | Δ | ACECLOFENAC now → titled | Δ |
|---|---|---|---|---|
| *(raw)* aspirin contraindications and who should not take it | 0.4031 → 0.4869 | **+0.084** | 0.5787 → 0.4979 | **−0.081** |
| aspirin contraindications mechanism adverse effects | 0.3906 → 0.4626 | +0.072 | 0.5658 → 0.4777 | −0.088 |
| aspirin use contraindications clinical management | 0.3915 → 0.4570 | +0.066 | 0.5595 → 0.4854 | −0.074 |
| **acetylsalicylic acid contraindications patient selection** | 0.3637 → 0.5448 | **+0.181** | **0.6756 → 0.5337** | **−0.142 (Y→n)** |
| aspirin contraindications mechanism | 0.3923 → 0.4761 | +0.084 | 0.5859 → 0.4943 | −0.092 |
| aspirin adverse effects treatment guidelines | 0.3506 → 0.4306 | +0.080 | 0.5114 → 0.4199 | −0.092 |
| **acetylsalicylic acid contraindications MeSH** | 0.3777 → 0.5584 | **+0.181** | **0.6494 → 0.5160** | **−0.133 (Y→n)** |
| aspirin contraindications mechanism risks | 0.4051 → 0.4849 | +0.080 | 0.5806 → 0.4939 | −0.087 |
| aspirin adverse effects patient management | 0.3534 → 0.4226 | +0.069 | 0.5172 → 0.4188 | −0.098 |
| **acetylsalicylic acid contraindications guidelines** | 0.3731 → 0.5614 | **+0.188** | **0.6681 → 0.5433** | **−0.125 (Y→n)** |

### Deciding counts (9 rewrite strings)

| | now | with title |
|---|---|---|
| **DURLAZA clears 0.6** | 0 / 9 | **0 / 9** |
| **ACECLOFENAC clears 0.6** | 3 / 9 | **0 / 9** |
| DURLAZA outranks ACECLOFENAC | 0 / 9 | **5 / 9** |
| mean Δ | DURLAZA **+0.111** · ACECLOFENAC **−0.103** | **differential +0.215** |

**Best DURLAZA titled score: 0.5614 — a 0.039 shortfall.** Outside the ±0.02 band, so an unambiguous
fail, though closer than the 0.195 shortfall without the title.

---

## 3. 🔴 The finding that matters more than the verdict

**The title prefix has strong discriminating power — in exactly the right direction — and it still
does not help.**

- It **raises** the owned document by **+0.111** on average and **lowers** the wrong one by **−0.103**
  — a **0.215** swing that reverses the ordering on **5 of 9** strings.
- Its largest gains (**+0.18**) land precisely on the three `acetylsalicylic acid` strings, which is
  the synonym failure `4c35654` identified. It **directly counteracts that mechanism.**
- **And yet nothing crosses the floor.** Worse: it drops ACECLOFENAC below 0.6 on the only 3 strings
  where anything cleared at all.

**Net effect on this query: the DailyMed store would return NOTHING on all 9 strings.** Title-
prefixing converts a wrong citation into **zero citations** — the same failure mode already
identified for the wrong-drug filter, arriving via the corpus instead of via a filter.

**So the binding constraint is the 0.6 floor, not the embedded text.** Every document in this
sample — right and wrong, titled and untitled — sits between 0.42 and 0.68. Fixing what is embedded
reorders that band; it does not lift anything through the threshold. ⚠️ **This is an observation
about one query, and it is NOT a recommendation to change the threshold** — `local_threshold` is
shared with the local and TFDA stores (`server.py:450`) and changing it is a far larger 🔴 change than
the one this baton was testing.

---

## 4. Ibuprofen — the second case, raw arm only

| document | now → titled | Δ | clears 0.6 |
|---|---|---|---|
| **NEOPROFEN — Warnings and Precautions** (owned, salt-inclusive) | 0.5754 → 0.5789 | +0.004 | n → **n** ⚠️ *−0.021, at the band edge* |
| NEOPROFEN — Drug Interactions | 0.5329 → 0.5307 | −0.002 | n → n |
| NEOPROFEN — Contraindications | 0.4005 → 0.4517 | +0.051 | n → n |
| Piroxicam — Boxed Warning *(wrong drug, cited in control)* | 0.5466 → 0.5186 | −0.028 | n → n |
| Mefenamic acid — Contraindications *(wrong drug)* | 0.5017 → 0.4700 | −0.032 | n → n |

**Same picture, weaker effect.** Nothing crosses in either direction. The owned NEOPROFEN Warnings
section already outranked Piroxicam before the change (0.575 vs 0.547) and still does — so on this
arm ibuprofen was **never** a ranking problem either. NEOPROFEN Warnings sits **0.021 below the
floor**, just outside the band — **flagged as borderline, not rounded into a verdict.**

**Rule 23 note:** `ADVIL — Indications and Usage` gains the most of any document measured
(**+0.144** on the ibuprofen query) because its title carries the moiety — and still reaches only
0.5072. Both `ASPIRIN`-key VAZALORE sections stay below 0.45.

---

## 5. What a corpus-wide change would still cost, and still not tell us

Recorded because the numbers above are **two drug cases, not a corpus measurement**:

- **It is 🔴.** It changes which documents are retrievable on **every Research query**, so it needs its
  own **§2.7**, **section-aware danger-path re-gate**, **canary**, and **prod human-eye gate**.
- **Blast radius is unbounded by row count.** Unlike E-B's *"45/1038 labels change"*, this changes the
  embedding of **all 4608 documents** — every Research retrieval, not a countable subset.
- **The embedding is not the cost.** A full re-embed of the corpus is **$0.063**. The cost is gate
  cycles and blast radius. *(Same correction already recorded for the c2 line.)*
- **Still unknown even after this baton:** the corpus-wide effect. This measured 11 documents on 2
  drugs. It cannot say how many *other* queries would gain or lose documents — and §3 shows the
  change **removes** documents as readily as it adds them.

**On this evidence a corpus-wide title-prefix change buys no retrieval of the owned document on the
one case it was proposed for, and would remove the only DailyMed citations that query currently
gets.** No further work is recommended or implied.

---

## 6. Rule 18 — skipped, unverified, out of scope

- **Query vectors were re-embedded, not reused** — the baton assumed a cache that did not exist.
  Fidelity max deviation **0.0049**, disclosed above.
- **One concatenation format tested.** No precedent existed; a different format is untested.
- **Ibuprofen: raw arm only** — its rewrite strings were never captured and are unrecoverable.
- **Two drug cases. Not a corpus measurement. Explicitly not extrapolated.**
- **Builder untouched** — not one line, not a comment. No `data/` write, no index write, no pipeline
  run, no filter work, c2 still parked.
- Per-document results cached to `tests/results/_titleprefix.json` (**gitignored scratch**).
