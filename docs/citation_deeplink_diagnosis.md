# "View source" citation deep-link — ROOT-CAUSE DIAGNOSIS (2026-07-28)

**DIAGNOSE ONLY — no fix applied.** READ-ONLY on product code. No deploy, no flags.

## ⛔ ROOT CAUSE (proven, not inferred)

**`scripts/build_drug_vectordb.py` hard-codes `"url": ""` on every document it writes** (lines **78,
99, 117, 135, 153**). All **690/690** documents in `data/drug_vectordb/index.json` therefore carry an
empty URL, and the Research References panel renders `<a href="">` for them — which navigates the
browser to the **current** page. In a Next.js static-export SPA that remounts `/research` at its
initial empty state, discarding the answer and references. **That is precisely the reported symptom.**

## ⚠️ IT IS NOT A REGRESSION — the window analysis is negative

- **`components/CitationPanel.tsx` has not changed since fly 206.** `git log 53a5755..HEAD --
  components/CitationPanel.tsx` → **empty**.
- **The citation producer path has not changed either.** `git log 53a5755..HEAD -- api/rag/generator.py
  api/models/schemas.py api/server.py` → **empty**.
- The builder has emitted `"url": ""` since the store was created. **The FDA-chip deep-link has never
  worked.**

**Why it surfaced now, and why the fly-206 gate did not catch it:** that gate verified
*"DailyMed chip renders 'DailyMed' + section-in-title + **setid deep-link**"* — **DailyMed, which
works.** It never exercised the FDA/local chip. fly 209/211 then raised how often official-label
sections reach the cited pool, so local `fda-*` documents appear in more answers, making a
long-standing defect newly visible. **This is a gate-coverage gap, not a coding slip, and no commit in
the window should be treated as its cause.**

---

## Evidence chain (each link measured)

| # | Step | Evidence |
|---|---|---|
| 1 | Builder writes empty URLs | `scripts/build_drug_vectordb.py:78,99,117,135,153` — literal `"url": ""` |
| 2 | Store reflects it | `data/drug_vectordb/index.json`: **690 docs, 0 with a non-empty url** |
| 3 | Retrieval passes it through | `api/database/vector_store.py:112` `url=meta.get("url", "")` → `""` |
| 4 | Citation copies it | `api/models/schemas.py:139` `url=self.url` in `to_citation()` |
| 5 | SSE emits it | `api/rag/generator.py:179` → the `citations` event (`api/server.py:903`) |
| 6 | Panel renders it | `components/CitationPanel.tsx:142` `<a href={citation.url}>` → `href=""` |
| 7 | Browser navigates to self | `<a href="">` = current URL → static-export SPA remounts empty |

### Step 1 measurement — DATA, not RENDER

Raw `citations` SSE payload captured from a live local run. Field name is **`url`**; per source type:

| source_type | url present | sample |
|---|---|---|
| `pubmed` | ✅ | `https://pubmed.ncbi.nlm.nih.gov/12667121/` |
| `dailymed` | ✅ | `https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=1f8833f9-…` |
| `local` (renders as **"FDA"**) | ❌ **`""`** | — |

Corpus-wide url coverage:

| store | docs | with url | empty |
|---|---|---|---|
| **local drug store** | **690** | **0** | **690 ← the bug** |
| TFDA indication | 10,941 | 10,941 | 0 |
| DailyMed label | 4,608 | 4,608 | 0 |

**Verdict: DATA defect, isolated to the `local` source.**

### Step 2b — the named hypothesis is REFUTED

`CitationPanel.tsx:141-146` renders a **plain `<a>`**, not a Next.js `<Link>`:

```tsx
<a href={citation.url} target="_blank" rel="noopener noreferrer"
   onClick={handleSourceClick} onAuxClick={handleSourceClick} …>
```

`handleSourceClick` (`:67-78`) fires one `track()` call inside `try/catch` and returns nothing — **no
`preventDefault`, no `router.push`, no interception.** With a correct URL this anchor works. Client-side
routing is not involved.

### Why the founder saw it on an "FDA" citation

`utils/sourceLabels.ts:61` — `local: { label: 'FDA', tooltipKey: 'officialTip' }`, i.e. *"cached FDA
labeling → MERGES into FDA"*. Also `api/database/vector_store.py:103-104` relabels the stored
`source_type` `fda_label` → `local`. **So a chip the user reads as "FDA" is a `local` document with an
empty URL.** The report and the measurement agree once that mapping is applied.

### ⚠️ One part of the report I could NOT reproduce — stated, not papered over

The symptom was also reported on **DailyMed** citations. **I could not reproduce that.** DailyMed URLs
are populated 4,608/4,608 in the corpus and well-formed in the live SSE payload. Two possibilities,
undecided on this evidence: (a) the FDA-chip case was the one observed and DailyMed was conflated with
it, or (b) a second, distinct defect exists on prod that this local run does not exhibit. **Worth one
targeted prod check** — click a citation whose chip reads *DailyMed* specifically and note whether it
opens. I am not claiming DailyMed is fine on prod; I am reporting that it is fine here.

### Step 3 — cross-surface (Rule 19): there is no second surface to diff against

| surface | renders a citation deep-link? |
|---|---|
| Research React app | **YES** — `pages/research.tsx:727` → `CitationPanel` (the broken one) |
| History page | **NO** — `grep -c CitationPanel pages/history.tsx` = **0**; it re-renders answers without a citation panel |
| Shared public answer page | **NO external anchor** — `q_base.jinja2` styles `.vela-citation-card` but its only `<a href>`s are the logo and privacy/terms. `share_renderer.py:225` reads `citation["url"]` **only to classify host → source slug**, never to emit a link |

**Finding:** the deep-link exists on **exactly one surface**, so there was no redundancy and no
cross-check — a single-surface defect with no way to notice it by comparison. That is the inverse of
the usual Rule 19 shape (a mitigation that failed to travel); here **the feature itself never
travelled**, so nothing else could reveal its breakage.

---

## Proposed minimal fix (NOT applied)

**Change:** in `scripts/build_drug_vectordb.py`, populate `url` at the five construction sites with the
openFDA label URL the record already implies, then rebuild `data/drug_vectordb/index.json`
(`python scripts/build_drug_vectordb.py`). The `drug_name` field is already on every record, so a
stable per-drug openFDA search URL is derivable without new data.

**Defensive companion (recommended, one line):** in `CitationPanel.tsx`, do not render the anchor when
`citation.url` is empty — show the chip without a link. **Rationale:** a missing link is honest; a link
that silently destroys the user's answer is not. This also protects against any *future* source that
ships without a URL, which is the failure class that produced this bug.

**Blast radius and risk class**

- **Does NOT touch medical output.** No retrieval ranking, no generation, no prompt, no answer text,
  no citation *selection* — only the `url` attribute of an already-selected citation and whether an
  anchor renders. Answer bytes are unchanged.
- **Therefore §2.7 is NOT required.** A **human-eye gate is** — this is user-visible UI behaviour, and
  the whole point is that automated gates never saw it.
- The rebuild regenerates a gitignored data artifact; embeddings are unchanged in shape (690 docs), so
  no index/embedding row-count mismatch risk (`vector_store.py:231` guards that anyway).

## Regression test (fails now, passes after)

Two layers, both cheap and offline:

1. **Data guard** — assert **every** document in `data/drug_vectordb/index.json` has a non-empty,
   `https://`-prefixed `url`. **Fails today at 690/690.** Extend it to the TFDA and DailyMed corpora
   so the invariant is "no corpus ships a citable document without a URL" rather than a one-store
   patch.
2. **Render guard** — assert `CitationPanel` renders **no `<a>`** when `citation.url` is empty. Fails
   today (it renders `href=""`).

**Negative control required** (project standard): inject a `url: ""` document and confirm the guard
**fails**; a guard that has never failed on a real instance is not evidence.

## Sequencing recommendation: **(a) its own small baton — do NOT fold it in**

It shares a *file neighbourhood* with the pending wrong-drug-citation build, but not a code path:

- this bug is in the **corpus builder** + the **anchor render**; the wrong-drug work is in **retrieval
  ordering** (`retriever.py` between `_collapse_subchunks` and the `top_k` cut);
- **risk classes differ** — this is non-medical-output and needs no §2.7, while the wrong-drug build is
  🔴 and needs §2.7 20/20 + a danger-path re-gate. Bundling would drag a one-line UI fix behind a full
  medical gate, and would blur which change any gate result belongs to;
- this one is **shippable in a day** and is user-visible on every Research answer containing an
  FDA-chip citation.

## Standing gate item — recommended

Add to the prod human-eye gate checklist:

> **Citation deep-links resolve — one per source type present in the answer** (PubMed · FDA · DailyMed
> · TFDA), confirming each opens the external site in a new tab and the Research page **retains its
> answer**. The fly-206 gate checked the DailyMed deep-link only, and this defect lived in the
> unchecked FDA/local chip through three subsequent human-eye gates.

## Limits

- Live SSE capture was **one pool**; it contained `pubmed` and `dailymed` but no `tfda` doc, so TFDA's
  live URL is verified from the corpus (10,941/10,941) rather than from a rendered citation.
- The DailyMed part of the report is **unreproduced** (see above) — a targeted prod check is warranted
  before assuming a single root cause explains everything the founder saw.
- No fix, no rebuild, and no product-code edit was made in this baton.
