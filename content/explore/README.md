# Vela Explore Pages — Content Authoring

Markdown-based content workflow for the /explore/{slug} SEO pages (PRD § 4.6).

## File naming

```
content/explore/{slug}.{locale}.md
```

Example: `metformin-renal-dose-adjustment.en.md`

Slug + locale in the filename MUST match `slug` + `locale` in the frontmatter.

## Frontmatter schema

```yaml
---
slug: metformin-renal-dose-adjustment
locale: en
query: "How should metformin be dose-adjusted for renal impairment?"
meta_title: "Metformin Renal Dose Adjustment | Vela"
meta_description: "Evidence-based dose adjustment of metformin for renal impairment patients."
category: dose-adjustment
hreflang_group: metformin-renal
status: draft        # draft | published | archived (default: draft)
citations:
  - source_type: pubmed
    title: "Drug Interactions of Metformin Involving Drug Transporter Proteins"
    authors: "Pakkir Maideen NM et al"
    journal: "Advanced Pharmaceutical Bulletin"
    year: 2017
    url: "https://pubmed.ncbi.nlm.nih.gov/example"
    credibility: peer-reviewed
    snippet: "Metformin is the most widely used antidiabetic agent..."
---

## Overview 🟢 — English
Markdown body becomes the answer_text. Section headers with evidence
markers (🟢 / 🟡 / 🔴) are parsed by the renderer for evidence-strength
card UI.

## Dose Adjustment 🟡 — English
...
```

### Required fields
`slug`, `locale`, `query`, `meta_title`, `meta_description`, `status`

### Optional fields
`category`, `hreflang_group`, `citations`

## Workflow

### Generate a draft from Vela

```bash
python scripts/explore_cli.py from-vela "How should metformin be dose-adjusted for renal impairment?" --locale en --slug metformin-renal-dose-adjustment
```

Runs the Vela research pipeline and writes the draft to `content/explore/{slug}.{locale}.md` with `status: draft`. Never auto-publishes.

### Edit the draft

Open the generated file. Fill in:
- `meta_title` (60 chars max for SEO)
- `meta_description` (155 chars max)
- `category` (`dose-adjustment` / `drug-interaction` / `regulation` / ...)
- `hreflang_group` (used to link same-topic pages across locales)
- Refine the body for accuracy / clarity

### Sync to DB

```bash
python scripts/explore_cli.py sync
```

Scans `content/explore/*.md`, validates, UPSERTs to the `explore_page` table. Idempotent (md5-based change detection).

### Publish

```bash
python scripts/explore_cli.py publish metformin-renal-dose-adjustment --locale en
```

Flips status to `published` and stamps `published_at` if first time.

### List all entries

```bash
python scripts/explore_cli.py list
```

### Unpublish / archive

```bash
python scripts/explore_cli.py unpublish metformin-renal-dose-adjustment --locale en
python scripts/explore_cli.py archive metformin-renal-dose-adjustment --locale en
```

## Slug rules

- Lowercase ASCII alphanumeric + hyphens only
- Max 80 chars
- No double-hyphens
- Pattern: `^[a-z0-9]+(?:-[a-z0-9]+)*$`

Examples:
- ✅ `metformin-renal-dose-adjustment`
- ❌ `Metformin-Renal` (uppercase)
- ❌ `metformin--renal` (double hyphen)
- ❌ `metformin_renal` (underscore)

## hreflang_group

Same topic across multiple locales shares one `hreflang_group` value. Google uses this to connect language versions.

Example: both `metformin-renal-dose-adjustment.en.md` and `metformin-renal-dose-adjustment.zh-TW.md` use `hreflang_group: metformin-renal`.

Single-row groups (no siblings) emit no hreflang tags — saves SEO clutter.

## Status lifecycle

```
draft  →  published  →  archived
   ↑           ↓
   ←  unpublish
```

Only `published` rows appear at /explore/{slug} and in sitemap-explore.xml. `draft` and `archived` both return 404 from the public route (avoids leaking existence of unpublished pages).

## What the CLI does NOT delete

`sync` never deletes DB rows. If you remove a markdown file but the row still exists in DB, sync logs a warning and lists the orphans. Use `archive` to retire them, or restore the markdown file.

## See also

- PRD § 4.6 — full functional spec
- `scripts/explore_cli.py` — CLI source
- `scripts/seed_explore_dev.py` — dev seed (use this for one-off test rows, not editorial workflow)
