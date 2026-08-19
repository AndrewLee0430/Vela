# Legal version archive — Terms of Service & Privacy Policy

**Created 2026-08-11 (fly 226) to satisfy a written legal counsel requirement of the same date.**

> **Counsel's requirement, in substance:** the frontend need not publish historical versions, but
> the team **must retain, internally, the full text of every superseded version together with its
> effective date range** — so that a future dispute can establish *"what text bound this user in
> July 2026"*. Git history technically holds this, but **a commit log is technical evidence, not a
> legal record**: answering that question must not require archaeology.

---

## 🔴 THE RULE — any edit to either legal page MUST add a snapshot here, in the same commit

Editing `pages/terms.tsx` or `pages/privacy.tsx` **supersedes** the text that was live. Before the
edit lands:

1. Snapshot the **outgoing** text into this directory (see *Naming* below).
2. Close its row in the table: set its **effective TO** date.
3. Add a row for the new version with its **effective FROM** date.
4. Update the page's own **"Last updated"** line to the same date. Counsel: *the date must be
   updated whenever content materially changes, because it establishes which contract version binds
   a user at a given time.*

A commit that changes either page and does not touch this directory is incomplete.

*This rule is recorded here rather than in `CLAUDE.md` because this repo's `Important Rules` list
holds invariants about code behaviour ("never use `print()`", "never fail open"), not
edit-one-file-then-another workflow coupling. `CLAUDE.md`'s "Ship cleanup ritual" is the nearest
equivalent surface, and it is about STATE/BACKLOG/PRD bookkeeping. Kept here, next to the artefact
it governs.*

---

## How to read the table

**A version here is a DISTINCT TEXT, not a distinct "Last updated" label.** That distinction is
load-bearing, because the two have never matched:

🔴 **A "Last updated" label does NOT uniquely identify a text.** Reconstructing the history exposed
this — for example **`Last updated: 2026-06-12` labelled FOUR different Privacy Policy texts**, and
**`Last updated: 2026-05-08` labelled two different Terms texts**. Content changed repeatedly
without the declared date being bumped. **That is exactly the defect counsel's ruling closes**, and
it is why the archive is keyed on the text rather than on the label. The label the page displayed
during each period is recorded in its own column so the two can be reconciled.

**Effective dates are COMMIT dates.** This repo has no retained deploy log reaching back to March
2026, so commit date is the best available proxy for "when this text became live". Deploys follow
commits closely (usually same-day), but a boundary could be off by up to a day. **Stated as a
limitation rather than presented as precision we do not have.**

**Markup-only commits do not create a version.** Three theme-migration commits (`7f5ec4d`,
`b5c7771`, `fe11e97`, all 2026-05-27) touched both pages without changing a word of prose; they are
listed in the *also* column of the version they fall inside.

**Zero-length ranges are real, not errors.** Several 2026-08-11 rows show `2026-08-11 → 2026-08-11`:
fly 222, 223, 224 and 226 all shipped on the same day, so some texts were live for hours. They are
retained because each was genuinely published.

---

## Terms of Service — 7 superseded texts

| # | effective FROM | effective TO | commit | page displayed | what changed | snapshot |
|---|---|---|---|---|---|---|
| v01 | **UNDETERMINED**, ≤ 2026-03-19 | 2026-03-24 | `8d1c10e` | `March 2026` | Initial Terms page (Phase 6) | [terms_v01](terms_v01_2026-03-19_to_2026-03-24.md) |
| v02 | 2026-03-24 | 2026-03-27 | `5b2562b` | `March 2026` | Unlimited\* fair-use policy; ToS consent in UpgradeModal | [terms_v02](terms_v02_2026-03-24_to_2026-03-27.md) |
| v03 | 2026-03-27 | 2026-03-31 | `41b5a83` | `March 2026` | Credits and monthly price updated | [terms_v03](terms_v03_2026-03-27_to_2026-03-31.md) |
| v04 | 2026-03-31 | 2026-04-01 | `b3143ab` | `March 2026` | Subscription cancel / daily reset / portal | [terms_v04](terms_v04_2026-03-31_to_2026-04-01.md) |
| v05 | 2026-04-01 | 2026-05-08 | `c6d4f17` | `March 2026` ⚠️ | Business-logic consistency: cancel text, pricing, credit transparency, refund ToS | [terms_v05](terms_v05_2026-04-01_to_2026-05-08.md) |
| v06 | 2026-05-08 | 2026-08-11 | `ad506db` | `2026-05-08` | §8 Public Sharing added (PRD 4.5 PHASE D). *Also `7f5ec4d`, `b5c7771`, `fe11e97` — markup only.* | [terms_v06](terms_v06_2026-05-08_to_2026-08-11.md) |
| v07 | 2026-08-11 | 2026-08-11 | `d0ace1e` | `2026-05-08` ⚠️ | §11 Language and Governing Translation added (counsel, fly 222) | [terms_v07](terms_v07_2026-08-11_to_2026-08-11.md) |
| **current** | **2026-08-11** | — | *this commit* | **`2026-08-11`** | "Last updated" corrected; prior-versions contact note added (fly 226) | `pages/terms.tsx` |

⚠️ **v05** changed on 2026-04-01 while still displaying `March 2026`. ⚠️ **v07** added a whole
section while still displaying `2026-05-08`.

---

## Privacy Policy — 10 superseded texts

| # | effective FROM | effective TO | commit | page displayed | what changed | snapshot |
|---|---|---|---|---|---|---|
| v01 | **UNDETERMINED**, ≤ 2026-03-19 | 2026-03-31 | `8d1c10e` | `March 2026` | Initial Privacy page (Phase 6) | [privacy_v01](privacy_v01_2026-03-19_to_2026-03-31.md) |
| v02 | 2026-03-31 | 2026-04-01 | `b3143ab` | `March 2026` | Subscription/usage data wording | [privacy_v02](privacy_v02_2026-03-31_to_2026-04-01.md) |
| v03 | 2026-04-01 | 2026-05-08 | `c6d4f17` | `March 2026` ⚠️ | Business-logic consistency: privacy claims, data cleanup | [privacy_v03](privacy_v03_2026-04-01_to_2026-05-08.md) |
| v04 | 2026-05-08 | 2026-06-09 | `ad506db` | `2026-05-08` | §8 Public Sharing added (PRD 4.5 PHASE D). *Also `7f5ec4d`, `b5c7771`, `fe11e97` — markup only.* | [privacy_v04](privacy_v04_2026-05-08_to_2026-06-09.md) |
| v05 | 2026-06-09 | 2026-06-09 | `bebe20e` | `2026-06-09` | De-identified/pseudonymous framing, cross-border transfer, 5-yr billing retention, 30-day email deletion, **English-prevails disclaimer added (legal-reviewed stopgap)** | [privacy_v05](privacy_v05_2026-06-09_to_2026-06-09.md) |
| v06 | 2026-06-09 | 2026-06-12 | `7502d08` | `2026-06-09` | Stale §9 Data Deletion folded into §4 (removed a contradiction) | [privacy_v06](privacy_v06_2026-06-09_to_2026-06-12.md) |
| v07 | 2026-06-12 | 2026-08-11 | `b713d74` | `2026-06-12` | §4 erasure clause → design E (statutory retention in original form) | [privacy_v07](privacy_v07_2026-06-12_to_2026-08-11.md) |
| v08 | 2026-08-11 | 2026-08-11 | `105fade` | `2026-06-12` ⚠️ | Third-party (Clerk) deletion notice added to §4 — counsel interim mitigation (fly 222) | [privacy_v08](privacy_v08_2026-08-11_to_2026-08-11.md) |
| v09 | 2026-08-11 | 2026-08-11 | `493df70` | `2026-06-12` ⚠️ | Supremacy clause promoted from header note to titled §10 (fly 223) | [privacy_v09](privacy_v09_2026-08-11_to_2026-08-11.md) |
| v10 | 2026-08-11 | 2026-08-11 | `64cca4e` | `2026-06-12` ⚠️ | Supremacy clause text standardised on counsel's 2026-08-11 wording (fly 224) | [privacy_v10](privacy_v10_2026-08-11_to_2026-08-11.md) |
| v11 | 2026-08-11 | 2026-08-19 | `8a9fc1e` | `2026-08-11` | "Last updated" corrected; prior-versions contact note added (fly 226) | [privacy_v11](privacy_v11_2026-08-11_to_2026-08-19.md) |
| **current** | **2026-08-19** | — | `4f50c57` | **`2026-08-18`** ⚠️ | §4 third-party-deletion clause replaced (counsel-approved 2026-08-19); label bumped at edit time (2026-08-18), text effective at deploy (2026-08-19) | `pages/privacy.tsx` |

⚠️ Four texts (v07–v10) all displayed `2026-06-12`.

---

## No user notification was required for the 2026-08-11 changes

Counsel ruled the fly 222/223/224/226 changes are **「更有利或中性的補充」** — beneficial or neutral
additions — and therefore carry **no notice duty**. **No banner, modal or email was built.** Counsel
offered an optional non-blocking banner as best practice; it was **not authorised** and is not
implemented.

**The reusable test — a duty WOULD arise for a materially adverse change**, counsel's examples
being: **a price rise · new third-party data sharing · narrowed user rights.** Apply that test
before assuming a future edit is notice-free.

---

## Naming and extraction

**Naming:** `<page>_v<NN>_<from>_to_<to>.md`. `NN` orders the versions unambiguously even when
several share a date.

**Extraction:** prose is taken verbatim from the JSX at the named commit — headings, paragraphs and
list items in document order, inline `<strong>`/`<em>` stripped, HTML entities decoded
(`&rsquo;` → `’`), and link targets preserved as `label <url>` so a `mailto:` or `/refund`
destination is not lost. Each snapshot carries an HTML comment header with its source commit,
effective range, and the "Last updated" value the page displayed at the time.

**Two things deliberately excluded**, so their absence is not read as a loss:

- **Footer navigation links** (*Privacy Policy · Refund Policy · Back to Vela*) — site chrome, not
  legal text.
- **Nothing else.** The extractor asserts that no unconsumed markup or JSX brace survives into a
  snapshot, and the build fails rather than emitting a partially-stripped record.

**One formatting annotation:** in `privacy_v05` through `privacy_v08`, the English-supremacy clause
appears as a `>` blockquote line. That marks it as **header small-print rather than a numbered
section** — which is what it was on the page during that period, before fly 223 promoted it to §10.
The words are verbatim; the `>` records its position.
