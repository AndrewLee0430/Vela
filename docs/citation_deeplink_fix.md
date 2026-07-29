# Citation deep-link fix — BUILD record (2026-07-29)

**Not a 🔴 baton** — no retrieval, generation, or citation-*selection* change. **§2.7 not required; a
human-eye gate IS.** Not deployed. Diagnosis: `docs/citation_deeplink_diagnosis.md` (`1cfaa58`).

**Closed question applied:** the founder confirmed on prod that a DailyMed deep-link opens correctly
(GLUMETZA, `setid=fb832474-…`). There is **no second prod-only defect**; the original "FDA and
DailyMed" report was inaccurate — only the FDA chip was clicked. Single root cause.

---

## Task 1 — provenance: **BRANCH (3). No stable identifier exists. No URL invented.**

Inspected the builder's input (`data/drug_database/*.json`, 190 records — the source
`scripts/build_drug_vectordb.py` reads at `:40`, default dir `:181`):

| field | value | usable as a document id? |
|---|---|---|
| `full_label.url` | **`https://labels.fda.gov/`** on **190/190** records — one shared host | ❌ identifies nothing |
| `full_label.source_id` | `FDA:<brand name>` e.g. `FDA:Pain Reliever Extra Strength` | ❌ a name, not an id |
| `spl_set_id` / `set_id` / `application_number` / NDC | **absent** — no hit anywhere in `scripts/` or `api/data_sources/fda.py` | ❌ |

**Therefore: the corpus keeps empty URLs BY DESIGN.** A URL synthesized from a drug name is a
**search**, not the source document; presenting it under "View source" would claim provenance the link
does not have — the same defect family as the "FDA Label Analysis" honesty [P1] fixed in v199/v201.
**The fix is Task 2 only.** This is recorded as a documented exemption in the guard, with an explicit
⛔ *do not "fix" this by generating search URLs*.

## Task 1b — openFDA (live) : **two findings, both worse than expected**

**1. Its URL is a hard-coded homepage.** `api/data_sources/fda.py:31-33`:

```python
@property
def url(self) -> str:
    return "https://labels.fda.gov/"
```

A **compile-time constant** — every openFDA citation, for every drug, gets the same generic homepage.
It is not empty (so it does not destroy the answer) but it is **not the cited document**: a false
provenance claim of exactly the kind Task 1 forbids. **Recorded, deliberately NOT silently changed** —
altering it is a behaviour change on a different source and belongs to the founder to sequence.

**2. openFDA and local are INDISTINGUISHABLE in the UI.** `utils/sourceLabels.ts:60-61`:

```
fda:   { label: 'FDA', tooltipKey: 'officialTip' },
local: { label: 'FDA', tooltipKey: 'officialTip' },   // cached FDA labeling → MERGES into FDA
```

So a chip reading **"FDA"** is either a `local` doc (`url:""` → after this fix, **no link**) or an
openFDA doc (`labels.fda.gov/` → a **homepage**). **Two sources, two different wrong URL behaviours,
one chip.** That is a provenance problem independent of the empty-URL bug.

**3. Forcing an openFDA citation: UNOBSERVED — and now explained.** Two attempts with
`source_filter=[SourceType.FDA]` returned **`status=no_results`, 0 docs**. Root cause found at
`api/data_sources/fda.py:127`:

```python
search_query = f'openfda.brand_name:"{query}" OR openfda.generic_name:"{query}"'
```

In the Research path `query` is the **full rewritten multi-word string** (e.g.
`"metformin pharmacokinetics renal impairment"`), which can never equal a brand or generic name →
openFDA 404s. **openFDA is structurally inert in Research** — it is fanned out to on every query
(`retriever.py:185`) and can essentially never contribute a document. **This independently explains
Phase 1's openFDA 0/18.** Its URL value is nonetheless *proven by inspection* (a constant), even
though no rendered instance could be produced. **Recorded, not fixed — out of scope.**

## Task 1c — resolve tests (populated ≠ resolves)

| source | HTTP | verdict |
|---|---|---|
| pubmed `…/12667121/` | **200** | ✅ resolves to the document |
| dailymed `drugInfo.cfm?setid=ca73b519-…` | **200** | ✅ resolves to the document |
| tfda `mcp.fda.gov.tw/im_detail_pdf/%E8%A1%9B…` | **200** | ✅ the percent-encoded Chinese PDF path **does** resolve |
| openFDA `https://labels.fda.gov/` | **200** | ⚠️ resolves, but to a **HOMEPAGE**, not the cited document |
| local | — | **no URL** — nothing to resolve (branch 3) |

No 404s, no redirects to search pages, **no bot-blocks** — so no browser-confirmation is needed here
(the `moh.gov.my` precedent did not have to be invoked).

## Task 2 — render guard (shipped)

`components/CitationPanel.tsx` — the only code change:

- New exported pure helper **`isUsableSourceUrl(url)`**: requires an absolute `http(s)://` URL;
  rejects empty/whitespace, relative (`/research`), scheme-less (`labels.fda.gov`), and
  `javascript:` / `data:`.
- The anchor is now gated: `{isUsableSourceUrl(citation.url) && ( <a …> )}`.
- **No new user-visible string** → Rule 16 not triggered, no 16-language work. When there is no URL,
  nothing renders.

## Task 3 — rebuild: **NOT PERFORMED, and therefore trivially neutral**

Branch (3) means the corpus keeps empty URLs, so **`data/drug_vectordb/index.json` was not rebuilt and
not modified**. No embeddings, no content, no ordering, no file changed.

**Sequencing dependency is satisfied by construction:** the next baton's pre-fix retrieval baseline is
**unaffected** — there is no rebuild to prove neutral, and the ≥5-query old-vs-new comparison is moot
because old and new are the same bytes. *(Had branch (2) applied, the builder re-embeds — `create_documents`
feeds the embedding call — so a rebuild would have required the full neutrality proof.)*

## Task 4 — tests (`tests/citation_url_guard.mjs`)

Two layers, both **negative-controlled**:

| layer | assertion | negative control | result |
|---|---|---|---|
| DATA | every DailyMed + TFDA doc has a usable `https://` URL; `local` **exempt with documented reasoning** | injected an empty-url doc into the DailyMed corpus | **FAILED as required** (`1/4609 …`), then restored (4608, injection gone) |
| DATA | the `local` exemption must still describe reality — fails loudly if local ever *gains* URLs, so a stale exemption cannot pass silently | — | passes |
| RENDER | `isUsableSourceUrl` rejects `''`, whitespace, `null`, `/research`, `#`, `javascript:`, `data:`, `labels.fda.gov`; accepts the four real citation URLs | — | passes |
| RENDER | `CitationPanel.tsx` must actually **gate the anchor** on the helper, not merely export it | reverted the gate to `{true && (` | **FAILED as required**, then restored |

The guard header records **which source types are resolve-verified and when**, so "non-empty https" is
never mistaken for "this link works".

`npx tsc --noEmit` → **exit 0**.

---

## Task 5 — recorded, NOT built

### 1. PRODUCT QUESTION — users cannot verify sources on past or shared answers

`pages/history.tsx` renders **`CitationPanel` 0 times**; the shared public page
(`api/templates/q_base.jinja2`) styles `.vela-citation-card` but its only anchors are the logo and
privacy/terms, and `share_renderer.py:225` reads `citation["url"]` **only** to classify host→source
slug. **The citation deep-link exists on exactly one surface.**

**The inverse Rule 19 shape:** not a mitigation that failed to travel, but **a feature that never
travelled** — which is precisely why no second surface could reveal the breakage by comparison. For
the founder: should History and the shared page offer source links at all? (Shared pages are public
and SEO-facing, so outbound official-source links may be desirable there for reasons beyond
verification.) **Not scoped.**

### 2. OPEN QUESTION — is the 690-doc `local` corpus still warranted?

It is relabeled `fda_label` → `local` (`vector_store.py:103-104`), displayed as **"FDA"**
(`sourceLabels.ts:61`), and **cannot carry a document URL at all** (Task 1). `sourceLabels.ts:13`
already records a prior honesty note about unproven FDA provenance for `localauthority`.

**Reasoning to weigh — deprecation may beat fixing:** the 4,608-doc **per-section DailyMed corpus is
live** and carries real setid deep-links; `local` is 690 whole-drug blobs with no provenance, whose
main distinguishing feature is now that it is the only source that cannot be cited to a document.
Against: it may still contribute recall the section-level corpus misses, and Phase-1 measurement
showed `local` docs *do* reach top_k regularly (unlike openFDA). **Deciding needs a recall
measurement, not an opinion. Not scoped, not acted on.**

### 3. Gate checklist — added to the `[ops]` entry in BACKLOG (third SOP line).

---

## Human-eye gate checklist (founder-facing — WRITE ONLY, not run)

Run on prod after deploy, signed-in. For each query, click **every** "View source" present.

**Universal PASS:** the external site opens in a **new tab** and the Research page **still shows its
answer and references** behind it.
**Universal FAIL:** the tab lands back on `vela.an-tho.com/research`, or the answer/references vanish.

| # | Query | Expect | PASS | FAIL |
|---|---|---|---|---|
| 1 | **"What are the common side effects of Metformin?"** *(the founder's original report)* | FDA(local) chip present | **No "View source" link on the FDA chip** — correct and honest; the card still shows source name, title and snippet | A link appears and clicking it empties the page |
| 2 | `warfarin aspirin bleeding risk interaction` | PubMed + DailyMed | PubMed → `pubmed.ncbi.nlm.nih.gov/<PMID>`; DailyMed → `drugInfo.cfm?setid=…` showing the **named drug's label** | lands on /research, 404, or a DailyMed **search** page |
| 3 | `metformin 腎臟不好的病人可以用嗎` *(zh-TW)* | TFDA and/or DailyMed | TFDA → `mcp.fda.gov.tw/im_detail_pdf/…` opens the **PDF** (Chinese filename is expected) | blank tab, 404, or download error |
| 4 | `冠脂妥適應症查詢` | TFDA 核准適應症 chip | TFDA PDF opens | as above |
| 5 | Any query returning an **openFDA** chip *(rare — see Task 1b: structurally inert)* | FDA(openFDA) | `labels.fda.gov/` opens — ⚠️ **a homepage, not the document. Record it, do not fail the gate**; it is the recorded provenance finding | page fails to load |

**Also confirm once:** a citation card with **no** link still renders its source name, title and
snippet normally — i.e. suppressing the anchor did not visually break the card.

## Limits

- **openFDA was never observed in a rendered citation** (0 docs on two forced attempts); its URL is
  proven by code inspection as a constant, not by observation.
- The resolve tests are **one representative URL per source type**, not the whole corpus.
- The render guard is asserted by **source-pattern check plus helper unit tests**, not by a DOM
  render — the repo has no React test harness, and adding one was out of scope.
