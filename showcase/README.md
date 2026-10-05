# showcase/ — the static archive site for Vela

A self-contained, two-page site describing Vela after it was archived (archive car, 2026-10-05).
Plain HTML with inline CSS. No build step, no JavaScript, no external requests, no trackers,
no user data, no stored share pages, no database content.

| File | What it is |
|---|---|
| `index.html` | English page |
| `zh-TW.html` | Traditional Chinese page (each page links to the other) |
| `media/` | Byte-identical copies of `public/media/research-demo.mp4`, `Verify_Landing_Demo.webp`, `Explain_Landing_Demo_1.webp`, `Explain_Landing_Demo_2.webp` |

## Before publishing

1. **Review the draft paragraph.** In both HTML files, the "Why it is archived" / 「為什麼封存」 paragraph sits
   between `<!-- FOUNDER REVIEW ... -->` and `<!-- /FOUNDER REVIEW -->`. It is a draft for the founder to edit or
   replace. Delete the two marker comments once it is approved.
2. **Fill the placeholders.** Each HTML file carries `{{DEMO_URL}}` (the live Research demo) and `{{REPO_URL}}`
   (the source repository) once each. Replace them with absolute `https://` URLs. Find every occurrence with:

   ```
   git grep -n "{{" -- showcase utils/archiveMode.ts
   ```

   The product side has one more placeholder, `SHOWCASE_URL` in `utils/archiveMode.ts`, which is where the archive
   banner and the retired pages link to. Set it to this site's final URL **before** the product is rebuilt and
   deployed, or those links stay relative and broken.
3. **Figures.** Every number on the page has an HTML comment beside it naming the committed file and commit SHA it
   came from, and a visible bracketed citation that points to the sources list. If a figure is edited, update both.

## Deploy to Cloudflare Pages

**Option A — connect the Git repository** (redeploys on every push that touches the repo):

1. Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**, and pick the Vela repository.
2. Build settings:
   - **Framework preset:** None
   - **Build command:** *(leave empty)*
   - **Build output directory:** `showcase`
   - **Root directory:** *(leave empty — the repository root)*
3. Optional: under **Build watch paths**, include `showcase/*` so product-only commits do not trigger a Pages build.
4. **Save and Deploy.** The site is served at `<project>.pages.dev`; add a custom domain under **Custom domains**.

**Option B — direct upload** (no Git connection): **Workers & Pages** → **Create** → **Pages** → **Upload assets**,
and drag the `showcase` folder in. Or from a terminal: `npx wrangler pages deploy showcase --project-name <name>`.

Note: with `showcase` as the output directory, this README is published too (at `/README.md`). It contains nothing
private; delete it from the upload, or move it, if that matters.

## Hostnames

Which hostname carries the showcase and which carries the live demo (for example the showcase at the apex or a new
subdomain, the demo staying on the current Fly.io hostname) is a founder decision — see the founder checklist in
`docs/batons/archive_mode_car_20261005.md`.

## Re-checking the pages

The archive car ran these checks (readbacks in the baton): both files parse with Python's `html.parser`; every
local `src` / `href` resolves to a file under `showcase/`; the only external URLs are the two placeholders and
`https://an-tho.com`.
