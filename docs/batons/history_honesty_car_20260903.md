# HISTORY HONESTY car — opened 2026-09-03 (Segment 1 BUILT, LOCAL ONLY)

> **STATUS — Segment 1 (created_at timezone): BUILT, LOCAL, NOT pushed, NOT deployed. Prod is still fly 244 = `b718a3d616a8ecee3b8e47aa00ecdc89b683f8d3`.** Code commits `88ddde592dbf309356bd9ef69cbc92b7e9d68edf` + fixup `ed181eded26653e9601d950288237a9981c9091e` (OpenAPI keeps `format: date-time`; the /history wire designator is `Z`) + fixup 2 (`_utc_isoformat` emits `Z`, so share/list matches) on `main`, ahead of origin. **Gate §1 is BLANK — the founder fills it; no AI observation is a gate result.** Push and deploy are founder-only.

**Authority:** `TECH_DEBT.md` → `[HONESTY][P2] timestamps shown in the wrong timezone` (filed 2026-09-03, the entry of record) · `STATE.md` "NEXT-CAR CANDIDATE — history honesty car" line · founder sequencing 2026-09-03 (timezone is Segment 1). CLAUDE.md Rules 7 / 19 / 20 / 24 / 25 apply.

**Workflow Step 0 note:** no `docs/batons/` baton was the input to this segment (the inputs were the TECH_DEBT entry and the founder's prompt), so `check_baton.py` had nothing to check. This file is the car's baton from here on.

---

## Segments — founder-sequenced 2026-09-03

| # | segment | scope in one line | status |
|---|---|---|---|
| 1 | **created_at timezone** | serialize `created_at` WITH a UTC offset on `GET /api/history` (`ChatHistoryEntry` field serializer) and `GET /api/share/list`; no frontend change; storage untouched | **BUILT LOCAL `88ddde5` + fixup `ed181ed` — gate §1 pending** |
| 2 | **event_stream flags** | the fallback flag → `research_v1` optional field or `research_v2`, so /history can know a fallback happened (`[HONESTY][P2]` fallback-flag entry) | not started |
| 3 | **frontend banner carry-across (+ badge i18n)** | `FallbackBanner` / `ProvenanceLine` carried into /history (Rule 19); the English Research/Verify/Explain badge under zh-TW on /history (nav keys exist, unused) | not started |
| 4 | **prose narrow fix / deferred** | `@tailwindcss/typography` registration for the `prose` no-op on /research + /history, WITH a two-page, two-scheme eye gate — or deferred by founder ruling | not started |

---

## §0 Repo assertion (Rule 24) — Segment 1 build session, 2026-09-03

| check | expected | derived | verdict |
|---|---|---|---|
| `git rev-parse --show-toplevel` | C:/Users/andre/projects/Vela | `C:/Users/andre/projects/Vela` | ✅ |
| `git rev-parse HEAD` (at start) | `6f98db63ebef85447c78d03cf4c7349fb081d628` | `6f98db63ebef85447c78d03cf4c7349fb081d628` | ✅ exact |
| `git status` | clean except `.superpowers/` + 3 landing PNGs (founder: stay untracked) | exactly those 4 untracked | ✅ |
| Prod | fly 244 = `b718a3d616a8ecee3b8e47aa00ecdc89b683f8d3` | not re-polled this session (no deploy in scope) | — |

---

## §1 Segment 1 — eye gate (BLANK FORM — founder fills)

**Environment:** local dev server (`uvicorn api.server:app` at `ed181ed` or later, with `PYTHONUTF8=1` on a cp950 console) + `npm run dev`; browser in **Asia/Taipei (UTC+8)**. Row 1's Expected column states the DB value and the expected wall-clock; the founder fills Observed. **PASS/FAIL and Notes are empty by design.**

| # | Surface / step | Expected | Observed | PASS / FAIL | Notes |
|---|---|---|---|---|---|
| 1 | `/history`, any row, Asia/Taipei | Displayed time = the DB `created_at` **+ 8 h**. Known row: dev id **2334**, DB `created_at` = `2026-09-03 03:21:37.726010` → **"Sep 3, 2026, 11:21 AM"** (fly 244 showed "03:21 AM"). Any other row: `SELECT id, created_at FROM chat_history ORDER BY id DESC LIMIT 3;` → each displayed time = that value + 8 h | | | |
| 2 | Same row after a full page refresh | Unchanged — identical string to row 1 | | | |
| 3 | `/history` row order | Still newest-first (top row = the latest `created_at`) | | | |
| 4 | Settings → **My Shares**: a share created moments ago | Reads **"just now" / "N minutes ago"**, not "~8 hours ago"; `days_since_created` in the PostHog event for a fresh share = 0 | | | |
| 5 | `/verify` and `/explain` live pages | **No timestamp appears; nothing changed** (parity — these pages never rendered `created_at`) | | | |
| 6 | Delete flow on ONE disposable `/history` row | Confirm → row gone, survives refresh (regression on the shared `tests/test_history_delete.py` harness) | | | |

---

## §2 Segment 1 build record (AI-written, facts and pointers only)

### 2a. Rule 25 — claimed surfaces vs derived surfaces (unit: **endpoints / render sites**, not lines)

Commands: `git grep -n "created_at" -- api/server.py api/models api/services` · `git grep -n "isoformat\|model_dump_json\|jsonable_encoder" -- api/` · `git grep -n "response_model" -- api/server.py` · `git grep -n "created_at\|Date.parse\|new Date(" -- pages components utils` · plus `git grep -nE '"[a-z_]+_at"\s*:' -- api/server.py` and `git grep -n "published_at\|updated_at\|created_at" -- '*.jinja2'`.

| surface | claimed by the entry | derived | rendered to a user today? | verdict |
|---|---|---|---|---|
| `GET /api/history` → `ChatHistoryEntry.created_at` (plain `datetime`, `api/server.py`) → `pages/history.tsx:285` `new Date(item.created_at)` | ✅ | ✅ | yes — every /history row | **MATCH · FIXED** |
| `GET /api/share/list` → `r.created_at.isoformat()` → `components/MySharesTab.tsx:45` / `:67` `Date.parse(iso)` | ✅ | ✅ | yes — "shared N ago" + `days_since_created` | **MATCH · FIXED** |
| `GET /api/user/context/hash` → `row.updated_at.isoformat()` (`UserProfile.updated_at`, naive utcnow) | — | found | **no** — `utils/contextSync.ts:84-91` reads only `user_context_hash` + `locale`; `updated_at` is never read or shown | third surface, **NOT fixed — founder's call** |
| Blog: `BlogPost.published_at` / `updated_at` (naive) → `blog_post.jinja2:14-15` JSON-LD `datePublished` / `dateModified` (naive ISO) and `:54` `<time>` shows `published_at_iso[:10]` (date only); `blog_list.jinja2:22/58-59` same | — | found | **yes, date-only** to humans; naive ISO to crawlers via JSON-LD (schema.org accepts a date-time without offset; wrong by the UTC date only within 8 h of midnight UTC) | third surface, **NOT fixed — founder's call** |
| Explore: `ExplorePage.last_updated_at` → `explore_renderer.py:372` `strftime("%Y-%m-%d")` → `category_listing.jinja2:20` | — | found | yes, date-only (same midnight-window caveat) | third surface, **NOT fixed — founder's call** |
| The other `created_at` columns (`sql_models.py:64/78/95/111/151/179`) | "not rendered today" | confirmed — no API exit, no template reference | no | MATCH |
| `_cleanup_old_records` (`api/server.py:183-195`) naive-to-naive server-side compare | "untouched" | untouched | n/a | MATCH |

**Derived set = the claimed set of two user-facing TIME surfaces (match), plus three date/ISO exits the entry did not list (none renders a wall-clock TIME to a user today).** Also observed, untouched, outside scope: the `/api/history` 7-/365-day cutoffs compare an AWARE `datetime.now(timezone.utc)` against the naive column (`api/server.py`, the two `cutoff =` lines in `get_user_history`) — works on Postgres via the session-timezone cast and on SQLite by string compare, but it is the same naive/aware seam; noted for the timestamptz car.

### 2b. BEFORE / AFTER — `ChatHistoryEntry(id=1, created_at=datetime(2026,9,3,3,21,37)).model_dump_json()`

| | wire string |
|---|---|
| BEFORE (HEAD `6f98db6`, = fly 244) | `{"id":1,"session_type":null,"question":null,"answer":null,"created_at":"2026-09-03T03:21:37"}` |
| AFTER (`88ddde5`, str serializer) | `{"id":1,"session_type":null,"question":null,"answer":null,"created_at":"2026-09-03T03:21:37+00:00"}` |
| AFTER (`ed181ed`, aware-datetime serializer — CURRENT) | `{"id":1,"session_type":null,"question":null,"answer":null,"created_at":"2026-09-03T03:21:37Z"}` |

Rendered under Asia/Taipei through the `pages/history.tsx:285` formatter (committed: `tests/probes/history_timezone/result.json`): BEFORE → **"Sep 3, 2026, 03:21 AM"**, AFTER → **"Sep 3, 2026, 11:21 AM"**; `Date.parse(naive) - Date.parse(+00:00)` = **-8 h** (the My Shares skew). The `Z` designator (current /history wire) renders identically to `+00:00` — both probed, ± microseconds. V8 accepts Python's 6-digit microseconds in every shape.

### 2c. The fix (`api/server.py`, three sites, one helper — Rule 19)

- `_utc_isoformat(v)`: naive → `v.replace(tzinfo=timezone.utc).isoformat()` (`…+00:00`); aware → `v.isoformat()` unchanged (no double shift).
- `ChatHistoryEntry`: `@field_serializer("created_at")` — at `88ddde5` it returned `_utc_isoformat(v)` (a `str`), which downgraded `/openapi.json` to `{"type": "string"}`. **Fixup `ed181ed`:** it returns an AWARE datetime (naive → `tzinfo=UTC`, aware untouched) and Pydantic serializes it, restoring `{"type": "string", "format": "date-time"}`; stated consequence: Pydantic 2.8 writes UTC as `Z`, so the /history wire is `…Z` while share/list (still `_utc_isoformat`) is `…+00:00` — same instant, both RFC 3339. **Fixup 2 (same day):** both endpoints emit `Z`; `+00:00` remains accepted by the parse test. No `when_used='json'`: `git grep -n "model_dump()" -- api/` has 7 hits, none on `ChatHistoryEntry`.
- `share_list`: `_utc_isoformat(r.created_at)` in place of `r.created_at.isoformat()`.
- **No frontend change.** `pages/history.tsx:285` `new Date(item.created_at)` and `components/MySharesTab.tsx:45` + `:67` `Date.parse(iso)` both honour an explicit offset — verified by the probe. Client-side `'Z'` appending explicitly NOT done (double-shifts once the server emits an offset).
- Column types / defaults untouched (`sql_models.py:25`, `:129` still `DateTime` + `datetime.utcnow`); `_cleanup_old_records` untouched. 0 new i18n keys.

### 2d. Tests (TDD — all four written first and watched fail)

`tests/test_history_delete.py` (+4 at `88ddde5`, +1 at `ed181ed`): `test_get_history_created_at_carries_utc_offset` (endpoint; wire ends `+00:00`/`Z`, parses to the DB instant read back, storage stays naive) · `test_history_entry_naive_created_at_serializes_as_utc` (pins the exact AFTER string) · `test_history_entry_aware_created_at_is_not_shifted` (pass-through guard — passed before the fix by design, must keep passing) · `test_share_list_created_at_carries_utc_offset` (no share/list harness existed; smallest one on this file's pattern). RED: 3 failed for "no UTC offset", 1 guard passing. GREEN: 8/8. Fixup: `test_openapi_keeps_date_time_format_on_created_at` (RED against the `str` serializer: `{'anyOf': [{'type': 'string'}, {'type': 'null'}]}`; GREEN 9/9), and the exact-string test re-pinned from `+00:00` to `Z`.

| check | baseline | after | delta |
|---|---|---|---|
| `python -m pytest -q` | 414 passed / 28 skipped | 418 / 28 at `88ddde5` → **419 / 28 at `ed181ed`** | +5 passed (exactly the 5 new tests), skips unchanged |
| `npx tsc --noEmit` | 0 errors | 0 errors | 0 |
| `npm run lint` | 22 (7 errors / 15 warnings) | 22 (7 errors / 15 warnings) | 0 (no frontend file changed) |

### 2e. Declined / left for the founder

1. The three third surfaces in §2a (`/api/user/context/hash` `updated_at`; blog `published_at`/`updated_at`; explore `last_updated_at`) — not fixed, per the segment brief ("DO NOT fix silently"). **Founder ruled 2026-09-03: NOT this car, note only** → filed as `TECH_DEBT.md` `[OTHER][P3] naive datetimes on three DATE-ONLY exits`, cross-referenced to the timezone entry.
2. The aware-vs-naive cutoff compare in `get_user_history` — observed, untouched.
3. `STATE.md`: one terse line added to the car line (CLAUDE.md solo-founder STATE discipline: STATE must not lag reality at a segment end) — beyond the three docs named in the brief; stated here so it is not silent.
