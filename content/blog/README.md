# Vela Blog — Content Authoring

Markdown-based content workflow for the `/blog/{slug}` pages. Mirrors
the §4.6 Explore pattern; narrower MVP scope (no archive, no
from-vela, en + zh-TW only).

## File naming

```
content/blog/{slug}.{locale}.md
```

Example: `asian-medical-ai-playbook.en.md`

Slug + locale in the filename MUST match `slug` + `locale` in the frontmatter.

## Frontmatter schema

```yaml
---
slug: asian-medical-ai-playbook
locale: en
title: "Why Asian Medical AI Needs a Different Playbook"
summary: "Three structural factors — regulation, language, workflow — that don't translate."
theme: asia
status: published          # draft | published
published_at: 2026-05-25
tags: ["medical-ai", "asia", "positioning"]
cover_image: null          # optional; absolute URL or /static/... path
faqs:
  - q: "Why can't US medical AI tools just be translated?"
    a: "..."
  - q: "..."
    a: "..."
---

{markdown body becomes body_markdown — supports GFM, fenced code, tables}
```

### Required fields

`slug`, `locale`, `title`, `status`, plus a non-empty markdown body.

### Optional fields

`summary`, `theme` (default `strategy`), `cover_image`, `faqs`, `tags`, `published_at`.

## Valid theme keys

Drive the cover image background + card badge color. Pick the one
closest to the post's topic; fallback is `strategy` (neutral gray).

| theme | typical use |
|---|---|
| `research` | warm orange — research-feature topics |
| `verify` | light blue — drug-interaction / verify-feature topics |
| `explain` | bright green — explain-feature / lab-result topics |
| `asia` | coral — positioning / regional-strategy topics (aliases research color) |
| `privacy` | lavender — privacy / data-handling / consent topics |
| `allied-health` | sage green — pharmacist / nurse / therapist topics |
| `strategy` | neutral light gray — meta / business / default |

Unknown themes log a warning at sync time and render as `strategy`.

## Workflow

### Edit a post

Open or create `content/blog/{slug}.{locale}.md`. Fill the
frontmatter + body. Save.

### Sync to DB

```bash
python scripts/blog_cli.py sync
```

Scans `content/blog/*.md`, validates each, UPSERTs into the
`blog_post` table. Idempotent — re-running with no changes reports
`Unchanged=N`. Any meaningful edit (body, faqs, tags, theme,
cover_image, summary, title, status, published_at) bumps `updated_at`
and re-renders on next request.

**Update is live without redeploy** — the FastAPI Jinja2 renderer
reads from the DB on every request. This is the core promise of the
DB-backed pattern.

### List posts

```bash
python scripts/blog_cli.py list
```

Prints SLUG / LOCALE / STATUS / TITLE / UPDATED for every row in
`blog_post`. Useful for diagnosing orphans (DB rows without a
matching `.md` file).

## Slug rules

- Lowercase ASCII alphanumeric + hyphens only
- Max 80 chars
- No double-hyphens
- Pattern: `^[a-z0-9]+(?:-[a-z0-9]+)*$`

Examples:
- ✅ `asian-medical-ai-playbook`
- ❌ `Asian-Medical-AI` (uppercase)
- ❌ `asian--medical` (double hyphen)
- ❌ `asian_medical` (underscore)

## Locale

Blog MVP ships **only** `en` and `zh-TW`. Other locales are rejected
at sync time. To add a translation, write a second file
`{slug}.zh-TW.md` with translated `title`, `summary`, body, and FAQ
— the slug stays the same so future hreflang linking works.

## Status lifecycle

```
draft  →  published
```

No `archived` (use DELETE from `blog_post` if a post needs to be
fully retired, or flip back to `draft` to hide).

Only `published` rows are returned by `GET /blog/{slug}`. `draft`
rows return 404 from the public route (avoids leaking the existence
of unpublished posts).

## `faqs` shape — strict validation

`faqs` is what gets emitted as the FAQPage JSON-LD schema (per GEO
best practice, both BlogPosting and FAQPage are emitted on every
post — see `api/templates/blog_post.jinja2`).

Each entry **must** be a mapping with string `q` and `a` keys:

```yaml
faqs:
  - q: "Question text?"
    a: "Answer text."
```

Malformed shapes (missing keys, non-string values, list-of-lists)
are rejected at sync time, not at render time — a bad FAQ shape
emits broken schema.org JSON which is worse than no schema at all.

## `tags` shape — strict validation

`tags` is a flat list of strings. Used for editorial filtering /
future search. Not rendered into JSON-LD.

```yaml
tags: ["medical-ai", "asia", "positioning"]
```

## `published_at` semantics

- Frontmatter can specify an explicit ISO date (`YYYY-MM-DD`) or
  datetime (`YYYY-MM-DD HH:MM:SS`). The CLI honors it verbatim,
  letting you backdate or schedule posts.
- If frontmatter omits `published_at` AND status is `published`,
  the CLI auto-stamps `published_at = now()` on first publish.
- Re-syncs respect an explicit frontmatter value — change the date
  in frontmatter to change the column.

## What the CLI does NOT do

- **Does NOT delete DB rows.** If you remove a markdown file but
  the row still exists, sync logs a warning and lists the orphan.
  Delete via SQL or recreate the file.
- **No publish / unpublish / archive subcommands.** Edit the
  `status:` field in the frontmatter and re-sync.
- **No from-vela generation.** Blog posts are editorial content
  written by hand (not Vela-generated). Add new posts by hand under
  `content/blog/`.

## Cover images

PHASE C generates a Pillow cover at `static/og/blog/{slug}-{locale}.png`
on render (idempotent — second request skips). If `cover_image` is set
in frontmatter, that path/URL overrides the auto-generated one.

**Ephemeral on Fly.io** — `static/og/` is gitignored and lives on the
machine's writable layer, so covers are re-generated after machine
restarts or redeploys. Same inherited limitation as the `/q/*` (share)
and `/explore/*` OG images; persistent storage (Fly volume vs R2/CDN)
is a shared infra task covered by the existing BACKLOG entry under §4.5
"OG image persistent storage decision". Best-effort behavior is
acceptable for the soft-launch phase.

## See also

- `docs/Blog_Implementation_Spec.md` — full functional spec
- `scripts/blog_cli.py` — CLI source
- `api/services/blog_renderer.py` — runtime renderer
- `api/templates/blog_post.jinja2` — output template
- `content/explore/README.md` — sister feature, mostly-similar
  workflow with extra commands (publish / archive / from-vela)
