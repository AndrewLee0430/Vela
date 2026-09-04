# HISTORY HONESTY car — opened 2026-09-03 (Segment 1 ✅ SHIPPED fly 245 · Segment 2 🔧 BUILT LOCAL 2026-09-04, §4 gate BLANK · Segment 2b FILED)

> **STATUS — Segment 1 (created_at timezone): ✅ SHIPPED as fly 245 (2026-09-03).** Readbacks: push `6f98db6..8a57dc9` → `git ls-remote origin main` = `8a57dc9665480ec1d7b923e77f44b2fe035ccf3f`, exact 40-char match to local HEAD → `.\deploy.ps1` → **fly v245**, image `deployment-01M1KBCA3Q37CJKARC9EFDC1DN`, `/health` = `{"status":"healthy","version":"2.2.0","revision":"8a57dc9665480ec1d7b923e77f44b2fe035ccf3f"}` **full-string, FIRST poll**; `fly status` both machines **245 `started`** (`2879720c66d478` 10:03:04Z · `683d447c2e5428` 10:02:26Z); deploy.ps1 parser Step 3 detected `2879720c66d478` `stopped` → Step 4 started it, no manual start (transcript `tests/probes/deploy_parser/fly245_deploy_transcript.txt`); unauth `GET /api/history` → 403 `{"detail":"Missing token"}` (unchanged). §1 gate founder-PASS 6/6. **✅ PROD EYE 2026-09-04 — 2/2 founder-PASS (prod, own account):** (1) /history row reads wall-clock time · (2) My Shares "shared … ago" sane. Provenance: founder statements 「1. 通過 2. 通過」 in the 2026-09-04 conversation, transcribed under the segment-2 probe authorization. **SEGMENT 1 CLOSED.** Segment 2: recon in §3 (2026-09-04, read-only); build gated on founder rulings D1–D3 (§3-D).
> *(build-time status, kept as the record)* ~~**STATUS — Segment 1 (created_at timezone): BUILT, LOCAL, NOT pushed, NOT deployed. Prod is still fly 244 = `b718a3d616a8ecee3b8e47aa00ecdc89b683f8d3`.**~~ Code commits `88ddde592dbf309356bd9ef69cbc92b7e9d68edf` + fixup `ed181eded26653e9601d950288237a9981c9091e` (OpenAPI keeps `format: date-time`; the /history wire designator is `Z`) + fixup 2 (`_utc_isoformat` emits `Z`, so share/list matches) on `main`, ahead of origin. **Gate §1 is BLANK — the founder fills it; no AI observation is a gate result.** Push and deploy are founder-only.

**Authority:** `TECH_DEBT.md` → `[HONESTY][P2] timestamps shown in the wrong timezone` (filed 2026-09-03, the entry of record) · `STATE.md` "NEXT-CAR CANDIDATE — history honesty car" line · founder sequencing 2026-09-03 (timezone is Segment 1). CLAUDE.md Rules 7 / 19 / 20 / 24 / 25 apply.

**Workflow Step 0 note:** no `docs/batons/` baton was the input to this segment (the inputs were the TECH_DEBT entry and the founder's prompt), so `check_baton.py` had nothing to check. This file is the car's baton from here on.

---

## Segments — founder-sequenced 2026-09-03

| # | segment | scope in one line | status |
|---|---|---|---|
| 1 | **created_at timezone** | serialize `created_at` WITH a UTC offset on `GET /api/history` (`ChatHistoryEntry` field serializer) and `GET /api/share/list`; no frontend change; storage untouched | **✅ SHIPPED as fly 245** (`8a57dc9`; gate §1 6/6 founder-PASS) |
| 2 | **event_stream flags** | the fallback flag → `research_v1` optional field or `research_v2`, so /history can know a fallback happened (`[HONESTY][P2]` fallback-flag entry) | **🔧 BUILT LOCAL 2026-09-04** — `84df9e0` (server: `errored` / `is_fallback` top-bound, ERROR→DONE = no write / no charge + ONE INFO line, `research_v1` + optional `fallback`) · `d647199` (parser keeps the key, absence = UNKNOWN, not rendered); rulings D1 (i) · D2 (i) · D3 Research-only; **§4 gate BLANK**; NOT pushed, prod still fly 246 |
| 2b | **Verify site 3 (false `ok` + charge on LLM double-failure)** | a third `verification_status` value at `server.py:1548-1568`, no deduct, rendered on /verify + /history (`TECH_DEBT` `[HONESTY][P2]` filed 2026-09-04 — §3.2 Probe B, founder ruling D3) | filed, not started |
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

## §1 Segment 1 — eye gate (TRANSCRIBED 2026-09-03 — founder 6/6 PASS)

**Environment:** local dev server (`uvicorn api.server:app` at `ed181ed` or later, with `PYTHONUTF8=1` on a cp950 console) + `npm run dev`; browser in **Asia/Taipei (UTC+8)**. Row 1's Expected column states the DB value and the expected wall-clock. **Observed / PASS-FAIL / Notes transcribed from the founder's closeout statements (see sign-off).**

| # | Surface / step | Expected | Observed | PASS / FAIL | Notes |
|---|---|---|---|---|---|
| 1 | `/history`, any row, Asia/Taipei | Displayed time = the DB `created_at` **+ 8 h**. Known row: dev id **2334**, DB `created_at` = `2026-09-03 03:21:37.726010` → **"Sep 3, 2026, 11:21 AM"** (fly 244 showed "03:21 AM"). Any other row: `SELECT id, created_at FROM chat_history ORDER BY id DESC LIMIT 3;` → each displayed time = that value + 8 h | wire `/api/history` `created_at` = `2026-09-03T03:43:33.406144Z` (id 2337) → rendered **"Sep 3, 2026, 11:43 AM"**; ids 2336 / 2335 / 2334 = `03:40:16Z` / `03:23:01Z` / `03:21:37Z` → 11:40 / 11:23 / 11:21 AM | **PASS** | Cross-check: id 2334 read "03:21 AM" in the §10 screenshot (recon_20260901) and "11:21 AM" now — the same row, +8 h |
| 2 | Same row after a full page refresh | Unchanged — identical string to row 1 | refresh: unchanged | **PASS** | — |
| 3 | `/history` row order | Still newest-first (top row = the latest `created_at`) | 2337 → 2334 → 2332, newest-first | **PASS** | — |
| 4 | Settings → **My Shares**: a share created moments ago | Reads **"just now" / "N minutes ago"**, not "~8 hours ago"; `days_since_created` in the PostHog event for a fresh share = 0 | a just-created share shows as recent, not ~8 h old | **PASS** | founder statement; display string not transcribed |
| 5 | `/verify` and `/explain` live pages | **No timestamp appears; nothing changed** (parity — these pages never rendered `created_at`) | /verify (warfarin + aspirin) and /explain rendered with no timestamp, unchanged | **PASS** | — |
| 6 | Delete flow on ONE disposable `/history` row | Confirm → row gone, survives refresh (regression on the shared `tests/test_history_delete.py` harness) | one disposable row deleted, gone after refresh | **PASS** | founder statement; suggested row was id 2336 — id per founder |

**Founder sign-off line (name · date · overall verdict):** Andrew Lee (founder) · 2026-09-03 · **6/6 PASS** — provenance: founder statements + screenshots in the closeout conversation, transcribed by Claude Code under the closeout authorization, per the 2026-09-01 zh-TW transcription precedent. Observed on localhost at HEAD `b1c42b5` (backend :8000 TEST_MODE, dev DB `ep-spring-voice-a127ye10`, viewer tz Asia/Taipei).

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

---

## §3 Segment 2 recon (2026-09-04) — read-only probe at HEAD `bc0430170075f8238995f94fde852461242af6a3` (= prod fly 246)

> **Purpose:** give the founder the facts for rulings D1–D3 (§3-D) BEFORE segment 2 is built. **No code was changed; nothing pushed; nothing deployed.** Every line number below was RE-DERIVED at HEAD (Rule 25); where a cited figure differs, §3.5 carries both readings. Repo asserted (Rule 24): toplevel `C:/Users/andre/projects/Vela`, HEAD `bc04301…af6a3`, status clean except the 4 founder-held untracked entries. Workflow Step 0: `PYTHONUTF8=1 python tests/probes/baton_check/check_baton.py docs/batons/history_honesty_car_20260903.md` → 30 verified · 2 "drifted" (both are non-unique-anchor warnings on lines that legitimately repeat across ledgers, not drift) · 6 advisory. *(Without `PYTHONUTF8=1` the checker itself dies on a cp950 console — `UnicodeEncodeError` on `⚠` at `check_baton.py:438` — flagged in §3.6, not fixed.)*

**Authority for this recon:** `TECH_DEBT.md` → `[HONESTY][P2] Research DONE-branch on error` (filed 2026-09-03) · `[HONESTY][P2] /history fallback indication` (filed 2026-09-02) · `docs/batons/recon_20260901_history_car.md` §4 addendum (the `citations_data` binding) · CLAUDE.md Rules 7 / 12 / 16 / 19 / 20 / 24 / 25.

### §3.1 Probe A — the Research error→DONE mechanism at HEAD

**A1 — every `StreamEventType.ERROR` yield in `api/rag/generator.py`** (derived: `grep -n "StreamEventType.ERROR" api/rag/generator.py` → 3 hits; cited 3 — MATCH). The enum (`api/models/schemas.py:90-96`) is exactly `ANSWER / CITATIONS / ERROR / DONE / FALLBACK` — no "errored-done", "partial" or "aborted" type exists.

| # | path | derived lines | cited | what follows the ERROR | reachable at HEAD? |
|---|---|---|---|---|---|
| 1 | `retrieval_status == "error"` | `if` :162 · ERROR :163 · DONE :164 · `return` :165 | :162-165 | DONE, then return — no ANSWER, no CITATIONS, no FALLBACK | **DEAD.** `has_api_error` (`api/rag/retriever.py:211`) is set only when a gathered task returns an `Exception` (`gather(..., return_exceptions=True)` :202); all five `_search_*` wrappers catch `Exception` and return `[]` — `_search_local` :600-602 · `_search_tfda` :616-618 · `_search_dailymed` :633-635 · `_search_pubmed` :663-665 · `_search_fda` :687-689 (derived = cited, 5/5). No wrapper re-raises. |
| 2 | main-path `except Exception` | `except` :206 · ERROR :209 · `logger.error("Generation error: %s", e, exc_info=True)` :210 · DONE :211 | :206-211 | zero or more ANSWER chunks may already have streamed (`full_answer` holds the partial text); **CITATIONS is never emitted** on this path (it sits at :203 after the loop) | **LIVE** — provider error, bad model name (`GENERATOR_MODEL='gpt-does-not-exist'`, recon_20260901 §10 row 10), timeout after retries |
| 3 | fallback-path `except Exception` (`_generate_fallback_stream`) | `except` :315 · ERROR :316 · `logger.error("Fallback generation error: %s", …)` :317 · DONE :318 | :315-318 | **FALLBACK (:289, `content="no_literature"`) has ALREADY been yielded** before the provider call, so the client's `isFallback` is TRUE when this ERROR arrives; CITATIONS (:312) never emitted | **LIVE** — same provider failures, on a no-literature query |

Also derived, outside the three: `generate_non_stream` (:215-273) returns `ERROR_MESSAGES["error"]` on the same three conditions but **has zero callers under `api/`** (`git grep -n "generate_non_stream" -- api/` → only its `def`) — dead code, flagged in §3.6. The fallback stream is entered at :169-172 **iff `not documents`**; the main path at :174+ otherwise.

**A2 — `api/server.py` `/api/research` `event_stream()` (:786-981), in order.**

Locals bound at the TOP of `event_stream()` today (:787-793): `full_answer = ""` (:787) · `citations_data: list = []` (:792, with the call-site comment naming the NameError reason — recon §4 addendum, `62682f5`) · `audit_id` (:793). **Bound LATER, inside the try:** `research_question` (:806) · `stage_q` (:818) · `_sw_shadow_sink` (:838) · `documents, retrieval_status` (:866, after the retrieve task) · `lang` (:872) · `gen_question` (:881) · `usage_out = []` (:894) · `elapsed_ms` (:924, DONE branch only). **No `errored`, `is_fallback` or similar local exists.** `is_anonymous`, `user_id`, `anon_id`, `model_override`, `start_time` are closure captures from the handler (:749-784).

| step | lines | what it does | condition | writes / charges? |
|---|---|---|---|---|
| guard fail | :797-801 | yields SSE `error` (guard text) then `done`, `return` | `run_guards` false | NO write, NO charge — a SECOND error shape, server-emitted before the generator |
| FALLBACK branch | :906-907 | yields SSE `{type:'fallback', content:'no_literature'}` | generator FALLBACK | sets NOTHING server-side; the flag lives only on the wire |
| CITATIONS branch | :908-920 | rebinds `citations_data`; **non-anon: writes `AuditLog`** (:911-919, `action="research"`, `resource_ids` = bare source_ids); yields `citations` | generator CITATIONS | AuditLog only here → **error paths never write an AuditLog row** (no CITATIONS event on them) |
| ERROR branch | :921-922 | yields SSE `{type:'error', content}` | generator ERROR | sets NOTHING, logs NOTHING |
| **DONE branch** | :923-977 | `elapsed_ms` :924 → **anon:** `deduct_anonymous_credits(db, anon_id, "research")` :927, cost log :928-931 if `usage_out` → **user:** `ChatHistory` write :936-941 (label "History Save", `answer=_research_history_payload(full_answer, citations_data)`) → `deduct_credits(db, user_id, "research")` :943 → cost log :945-948 if `usage_out` → judge :950-953 if `audit_id and full_answer` → direction-check shadow :956-961 → retrieval-refusal shadow :965-969 → source-weight shadow :975-976 → yields SSE `done` :977 | **only `event.type == DONE`** — no check that an ERROR preceded it | **YES write, YES charge** on every generator path incl. A1 #2/#3 — the defect. Cost log is skipped there in practice (`usage_out` is empty: the provider reports usage at stream END, never before an exception) |
| outer `except` | :978-981 | `logger.error("Research stream error: %s", type(e).__name__)`; yields `error` ("An error occurred. Please try again.") then `done` | any RAISED exception (retrieve_task re-raise :864-866, a NameError, …) | NO write, NO charge, NO AuditLog — a THIRD error shape, already "(i)" by construction |

**Client side today** (`pages/research.tsx`): `error` → `setError(...)` + `research_failed` telemetry (:436-450); `done` → `setLoading(false)` + **`research_completed` telemetry fires regardless of a preceding error** (:452-467, with `used_fallback: localIsFallback`) — observed, flagged §3.6.

**A3 — `api/services/usage_service.py`.** `CREDIT_COSTS` :19-23 = research 3 · explain 2 · verify 1. `async def deduct_credits(db, user_id, feature) -> None` :137-148: `get_or_create_usage` → `credits_used_today += cost` (free plan also `credits_used += cost`) → `updated_at` → `db.commit()`. **No TEST_MODE branch — the deduction is unconditional**; TEST_MODE only skips the pre-stream `check_credits` (`server.py:777`, and :1146 / :1632 for Verify / Explain). `async def deduct_anonymous_credits(db, anon_id, feature) -> None` :209-218: `credits_used_today += cost`, `last_active_at`, commit. **Refund / reversal helper: NONE** — the module's full def list (`grep -n "^async def \|^def "`) is `_resolve_usage · get_or_create_usage · get_active_usage · reset_daily_if_needed · check_and_deduct_credits · check_credits · deduct_credits · _get_or_create_anonymous_usage · _reset_anonymous_daily_if_needed · check_anonymous_credits · deduct_anonymous_credits`; nothing decrements. Consequence for D1: "no charge" can only mean **not calling** the deduct — there is nothing to reverse after the fact. (Also observed: `deduct_credits` does not call `reset_daily_if_needed`; `check_credits` does — untouched, noted.)

### §3.2 Probe B — Rule 19: do Explain and Verify share the DONE-after-ERROR convention? **(decision driver for D3)**

Derived INSERT sites: `grep -n 'session_type="…"' api/server.py` → research **1** (:938) · verify **3** (:1385, :1436, :1552 — cited 3, MATCH) · explain **1** (:1665). No app-level exception handler is registered anywhere (`git grep -n "exception_handler" -- api/` → 0 hits), so an UNCAUGHT raise in any handler yields Starlette's default HTTP 500 with no INSERT and no deduct.

| mode · path | (a) how the error reaches the client | (b) history row written on it? | (c) credits deducted on it? | (d) anon variant |
|---|---|---|---|---|
| **Research** · generator ERROR (A1 #2, #3) | SSE `error` (`server.py:921-922`) **followed by** SSE `done` (:977); client shows the error banner (`research.tsx:436-450`) | **YES** — `research_v1` shell, `answer` = `""` or the partial text, `citations` `[]` (:936-941); no AuditLog | **YES** — 3 credits (:943); cost log skipped (no usage) | **charged** 3 of 8 (:927); never writes a row (by design, anon has no history) |
| Research · guard fail / outer except | SSE `error` then `done` (:797-801 / :978-981) | no | no | no charge |
| **Explain** · every pipeline error (7 yield sites: `explain_service.py` :485-491 empty_input · :495-501 input_too_long · :514-520 Stage-1 `VelaError` · :538-544 zero entities · :549-555 no values · :628-634 Stage-3 `VelaError` · :643-654 `ValueError` truncated/schema) | SSE `{type:'error', code, message}` **then `return` — NO `done` ever follows an error** | **NO** — the write (`server.py:1657-1668`, AuditLog + ChatHistory) is gated on `event.get("type") == "done"` (:1656), which never arrives | **NO** — `deduct_credits` (:1670) is inside the same `done` block | **N/A** — `raise FeatureNotAvailable("explain")` (:1618) before the stream; L0 never reaches the pipeline |
| Explain · outer except | SSE `{type:'error', code:'generic'}` (:1686-1691), no `done` | no | no | n/a |
| **Verify** · site 1 — no-label fallback SUCCESS (:1384-1395) | HTTP 200, `verification_status="ok"`, summary prefixed `"⚠️ No FDA label data found. "` (:1382) — a degraded success, not an error | YES (`ok`) | YES — :1398 anon / :1409 user (1 credit) + cost log | no row; **charged** |
| **Verify** · site 2 — no-label fallback FAILURE (`except` :1432-1460) | HTTP 200 with **`verification_status="failed_no_data"`** (:1459), summary "No FDA label data found. Please use specific drug names.", interactions `[]` — rendered as a warning badge + `ui.verifyFailedMsg` on /verify (`pages/verify.tsx:459`) and /history (`pages/history.tsx:423`) | **YES, WITH the explicit failure marker** (:1435-1446; the call-site comment: *"a total failure must never read as a clean result on /history either"*) | **NO** — the branch returns at :1447-1460 before either deduct; no cost log | no row; **no charge** |
| **Verify** · site 3 — main path, both LLM attempts fail (`for attempt in range(2)` :1493-1520, `analysis_success` stays False) | HTTP 200, **`verification_status="ok"`** (:1561, :1593), `summary=""`, `risk_level="Unknown"`, `interactions=[]` — **no error signal at all**; only `logger.error("LLM attempt %d failed")` :1520 | **YES, labelled `ok`** (:1548-1562, AuditLog + ChatHistory in one `_safe_db_write`) | **YES** — :1566 anon / :1568 user; cost log skipped (:1573 requires `analysis_success`) | no row; **charged** |
| Verify · uncaught raise | HTTP 500 (Starlette default) | no | no | no |

**Reading of the table (facts, not a ruling):** Explain is D1-option-(i) by construction. Verify's fallback-failure path is D1-option-(ii) by construction — a marker in the stored payload, no charge, rendered on both pages. Verify's main path shares the Research defect (write + charge on LLM failure) and adds a false `ok` on top; it is **not filed** in TECH_DEBT today. Research is the only mode whose error convention is ERROR-then-DONE.

### §3.3 Probe C — the fallback flag

**C1 — where the flag lives today.** `StreamEventType.FALLBACK` is yielded at `generator.py:289` (derived = cited) inside `_generate_fallback_stream` (:276-318), entered at :169-172 iff `not documents`; `server.py:906-907` (derived = cited) turns it into SSE `type:'fallback'`; `research.tsx:430` sets `isFallback`. **Other signals of "no literature" available in `event_stream()` scope at DONE time:**

| signal | in scope at DONE? | equals "fallback entered"? |
|---|---|---|
| `documents` (bound :866) | yes | `not documents` is the SAME predicate the generator uses (:169) — exact, except on the dead `retrieval_status == "error"` leg (also `[]`, no FALLBACK) |
| `retrieval_status` (bound :866) | yes | values at HEAD are **four**, not two: `"ok"` · `"no_results"` (`retriever.py:214`, no source returned anything) · **`"irrelevant"`** (:248 — sources returned docs, the relevance filter dropped ALL of them) · `"error"` (dead). Fallback ≡ `retrieval_status in ("no_results", "irrelevant")` |
| `citations_data == []` | yes | NO — also `[]` on the two live error paths (TECH_DEBT entry, confirmed) |
| `usage_out[0]["model"] == generator._fallback_model` | yes, if usage arrived | NO — the anon main path also runs on `_fallback_model` (`server.py:772`) |
| the SSE `fallback` event itself | only if captured into a new local in the :906 branch | exact — the TECH_DEBT fix path |

Also: the flag already leaves the process once — as `used_fallback` in the PostHog `research_completed` event (`research.tsx:462`) — but never reaches the DB.

**C2 — `_research_history_payload(full_answer: str, citations: list) -> str`** — `def` at `server.py:1059`, docstring :1060-1071, `return json.dumps({...})` :1072-1076 (cited :1072-1076 = the return statement — MATCH). Exactly one call site: :940 (`git grep -n "_research_history_payload"` → 2 hits: def + call). Emits `{"kind":"research_v1","answer":<markdown>,"citations":[…]}`, `ensure_ascii=False`.

**C3 — every consumer of the `research_v1` payload** (`git grep -n "research_v1" -- api/ pages/ components/ utils/ tests/` + the `.mjs`; 0 hits in `api/services/share_renderer.py`, `utils/exportPdf.ts`, `components/` — `pages/history.tsx` does not import `exportPdf`; the share flow receives MARKDOWN from the client, never the payload):

| consumer | file:line | role | ADDED optional `fallback: bool` | `kind: research_v2` |
|---|---|---|---|---|
| writer | `api/server.py:1072-1076` (+ call :940) | emits the JSON | **needs a change** (new key; `_research_history_payload` gains a parameter or the DONE branch passes it) | changes the literal |
| `GET /api/history` → `ChatHistoryEntry.answer` | `api/server.py` (response model) | passes `answer` through as an opaque string | ignored | ignored |
| `parseResearchAnswer` | `pages/history.tsx:81-97` | the ONLY reader | **ignored** — reads `kind` / `answer` / `citations` only; the returned object literal (:90-94) DROPS every other key, so the renderer cannot see the flag until it is taught to (segment 3) | **BREAKS** — `p.kind === 'research_v1'` (:89) → `null` → the row takes the half-A raw-text path and renders the **raw JSON** in the pre-wrap box for every v2 row until this file changes in the same deploy |
| `ShareButton answerText={… researchParsed?.answer ?? item.answer}` | `pages/history.tsx:485` | reader via the parser | ignored | via the parser: `null` → `item.answer` = the raw JSON is what a share created from a v2 row would PUBLISH (exactly the regression `tests/test_history_render_fallback.py:100` was written against) |
| `tests/history_render_fallback_guard.mjs` | :117-155 | pins the parser behaviourally | **passes** — no assertion on extra keys; the `noCit` case (:146-147) shows missing/extra keys are tolerated | **BREAKS by design** — :124 asserts `research_v2 → null` (*"a future schema must not be half-rendered by this branch"*); must be rewritten |
| `tests/test_history_render_fallback.py` | :58-72, :100 | source-pattern guard | ignored | ignored (patterns do not name the kind) |
| `tests/test_research_history_payload.py` | :191, :203, :213, :230 | pins the stored JSON | **BREAKS at :203** — `assert set(parsed) == {"kind", "answer", "citations"}` (written deliberately: *"no audit/request id in the payload"*); one-line update | **BREAKS at :191 / :213 / :230** (`== "research_v1"`) |
| docs prose (`recon_20260901`, `TECH_DEBT`, this baton) | — | narrative | n/a | n/a |

Old-row rendering: under (i) an old row has no `fallback` key → the ruled semantics say UNKNOWN → renders exactly as today (the `noCit` guard already proves the parser tolerates a missing key). Under (ii) old rows stay `research_v1` and keep the v1 branch; the renderer must hold BOTH branches (v1 + v2) forever, since no backfill exists (recon §7-D2).

**C4 — the two frontend components** (`pages/research.tsx`, both page-local functions):

| | `FallbackBanner` (:102-117) | `ProvenanceLine` (:77-100) |
|---|---|---|
| props / state | none; rendered when `!loading && isFallback` (:616-617); `isFallback` state :134, set :430 | `{ citations: Citation[] }`; rendered when `!isFallback && citations.length > 0` (:618) |
| hooks | `useLang()` → `getUI(lang)` | same |
| i18n keys | `ui.noLiteratureFound` · `ui.fallbackBasis` | `ui.provenanceSourced` (`{count}`) · `ui.sourceCountTip` (via `sourceCountTooltip`) · `ui.tfdaSourceLabel` (via `resolvedSourceLabel`) |
| helpers | — | `sourceLabelFor` · `resolvedSourceLabel` · `sourceCountTooltip` from `utils/sourceLabels.ts` (:133 / :54 / :141); `SourceLike` = `{source_type?, url?}` (:37-40) |
| theme tokens | `--color-warning` (bg /0.12, border /0.3, text, text /0.8) | `--color-text` (/0.45, /0.08); **the hover tooltip hard-codes `bg-white … text-gray-600`** (:92) — light-only classes, a theme-eye item if carried to /history's two schemes |
| data /history does NOT store | **the fallback flag itself** — its only input | **nothing** — counts are derived from the stored citation dicts, which carry `source_type` and `url`; no retrieval mode or source-count field is needed |

i18n confirmation (derived): the keys live in **`utils/i18n-ui.ts`** (0 hits in `utils/i18n.ts`); `grep -c "  <key>:"` = **17 each** for `noLiteratureFound`, `fallbackBasis`, `provenanceSourced`, `sourceCountTip` = 1 interface declaration + **16 locale blocks** (`en` :317; `zh-TW` :587 · `zh-CN` :845 · `ja` :1104 · `ko` :1361 · `es` :1618 · `fr` :1877 · `de` :2136 · `it` :2395 · `pt` :2654 · `th` :2913 · `ar` :3172 · `hi` :3431 · `bn` :3690 · `he` :3949 · `vi` :4208). → **0 new i18n keys** for the carry-across holds. Extraction to `components/`: precedent `VerifyInteractionCard.tsx` takes `lang: LangCode` as a prop and calls `getUI` (no hook inside); `CitationPanel` is the other shared piece. Moving both means: new file(s) under `components/`, imports for `getUI` (+ `useLang` or a `lang` prop), the `Citation` type from `components/CitationPanel`, the three `sourceLabels` helpers; `pages/research.tsx` re-imports them; no state moves.

### §3.4 Probe D — tests + observability

**D1 — `tests/test_research_history_payload.py`.** Pins **3 tests** (derived: `grep -c "^def test_"` = 3; `pytest --co` collected 3 — the prompt's "4 tests claimed" is a discrepancy, §3.5): `test_stored_row_carries_marker_markdown_and_streamed_citations` (:173 — marker, byte-identical markdown, same citation dicts, **key set exactly `{kind, answer, citations}`** :203) · `test_fallback_shape_stores_empty_citations` (:206 — CITATIONS `[]` → row with `[]`) · `test_no_citations_event_still_writes_row_with_empty_citations` (:218 — **ANSWER then DONE with NO CITATIONS event → asserts a row IS written and NO error event** — this test encodes today's write-on-error behaviour; under D1 (i) or (ii) its assertions change: it currently scripts the exception path WITHOUT the ERROR event, so it is really a "citations_data bound" test, not an error-path test). **The seam:** `monkeypatch.setattr(server, "generator", _FakeGenerator(events))` (:142) with `_script(chunks, citations_event, citations)` (:163-170) building the `StreamEvent` list — adding `StreamEvent(type=StreamEventType.ERROR, content=…)` before DONE, or `StreamEvent(type=StreamEventType.FALLBACK, content="no_literature")` first, is a one-line script change; guards/retriever/judge are already stubbed (:139-143), DB is an in-memory StaticPool (:77-96). **Anon seam:** `require_auth_or_anonymous` (`server.py:399-441`) treats an `X-Anon-Fingerprint` header as L0 even in TEST_MODE (:412-414) → the anon DONE branch is drivable from the same harness with one header; credits are readable from `UserUsage` / `AnonymousUsage` in the same session. Sibling harness: `tests/test_verify_history_payload.py` (3 tests) if D3 goes three-mode.

**D2 — audit / log line on the error path.** Today: `generator.py:210` `"Generation error: %s"` and `:317` `"Fallback generation error: %s"` (both `exc_info=True`, Fly logs only, no user id); `server.py:774` `"[Research] user=%s query_length=%d"` at handler entry; the ERROR branch (:921) logs nothing; `_safe_db_write` logs only on failure (:175); `deduct_credits` logs nothing; the outer except logs the exception TYPE only (:979). **There is NO line that states "row written / not written" or "charged / not charged"** — a future "no write / no charge" could be verified in prod logs only by a NEW log line in the DONE branch (or by the absence of a row + an unchanged `credits_used_today`, which is a DB read, not a log). AuditLog is written only in the CITATIONS branch, so error-path streams leave no AuditLog row today either.

### §3.5 Discrepancies — derived ≠ cited (both readings, 2026-08-24 precedent)

| claim (where cited) | cited reading | derived at HEAD `bc04301` | verdict |
|---|---|---|---|
| `tests/test_research_history_payload.py` test count (segment-2 probe prompt) | 4 tests | **3** (`grep -c "^def test_"` = 3; `pytest --co` = 3 collected) | **≠** — the 4th does not exist; the prompt's figure was inherited, not measured |
| "Explain (its `"done"` after an error event)" (TECH_DEBT DONE-on-error entry, fix-path bullet) | presumes Explain emits `done` after `error` | Explain **never** emits `done` after `error` — all 7 pipeline error yields `return` (§3.2); the server writes/charges only on `done` | **≠** — premise corrected; the Rule 19 audit outcome is "Explain already does (i)" |
| i18n: "strings already exist in all 16 locales (`noLiteratureFound`, `provenanceSourced`) → 0 new keys" (TECH_DEBT fallback entry) | 2 keys | **5 keys consumed** by the two components (`noLiteratureFound`, `fallbackBasis`, `provenanceSourced`, `sourceCountTip`, `tfdaSourceLabel`), all 16/16, in `utils/i18n-ui.ts` (not `utils/i18n.ts`, 0 hits) | count ≠, **conclusion holds** (still 0 new keys) |
| `retrieval_status` vocabulary (TECH_DEBT + recon treat "no_results" vs "error") | two non-ok values | **three**: `no_results`, `irrelevant` (`retriever.py:248`; the four values are already listed in the `retrieve()` docstring at :167), `error` (dead) | addition — matters for any `retrieval_status`-based fallback proxy (§3.3 C1) |
| `generator.py:162-165` (retrieval-error leg) | :162-165 | `if` :162 · ERROR :163 · DONE :164 · `return` :165 | MATCH |
| `generator.py:206-211` / `:315-318` / `:289` | as cited | :206-211 / :315-318 / :289 | MATCH |
| `retriever.py:211` + five wrappers `:600-602 :616-618 :633-635 :663-665 :687-689` | as cited | identical | MATCH (5/5) |
| `server.py:906-907` / `:923` / `:927` / `:936-941` / `:943` / `:1072-1076` | as cited | identical | MATCH |
| Verify INSERT sites | 3 | 3 (:1385, :1436, :1552) | MATCH |
| `research.tsx:102` / `:616-617` | as cited | `FallbackBanner` :102; the ternary spans :616-618 | MATCH (±1 line) |

### §3-D Founder decisions — options + facts. **NO recommendation is made here; NO decision is taken.**

> **✅ RULED 2026-09-04 (founder, from this section's options):** **D1 = (i)** no write / no charge · **D2 = (i)** optional `fallback` on `research_v1` (absence = UNKNOWN) · **D3 = Research-only**; Verify site 3 **FILED** as `TECH_DEBT` `[HONESTY][P2]` and sequenced as **segment 2b**, not fixed. Build record: §4 (gate, BLANK) and the STATE Next Up line. The option tables below are kept verbatim as the decision record.
>
> **Rule 25 at build time (2026-09-04):** every §3 `server.py` line number was re-derived at HEAD `b1ca296` before editing and MATCHED (`:792 :906 :921 :923 :927 :940-941 :943 :1059 :1073`); two drifts recorded — `parseResearchAnswer` spans `pages/history.tsx:86-97` (§3 wrote :81-97, which included the interface at :80-84), and the TECH_DEBT NAV was already 167, not §3's 166 (the fly-246 closeout had added one `[OTHER]`). **After `84df9e0` the §3 numbers are a dated record, not live pointers:** the flags sit at `server.py:798-799`, the DONE branch at `:932` with the `if errored:` skip at `:934`, `_research_history_payload` at `:1080` and its `"fallback"` key at `:1104` — the baton fact-checker will report `server.py:1059` as a blank line from here on; that is the shift, not an error in §3.

**D1 — the Research error path (generator ERROR → DONE).**

| option | precedent in this repo (Probe B) | what the user sees on /history | what the audit trail loses / keeps |
|---|---|---|---|
| **(i) no write / no charge** | **Explain**, by construction (write + deduct gated on `done`, which never follows `error`); also Research's own guard-fail and outer-except shapes | **nothing** — the errored session leaves no row; /research showed the error banner live; the Navbar credits meter is unchanged | **loses** the only per-user DB trace an errored Research call has today (the empty `research_v1` row; AuditLog is never written on error paths, cost log is skipped) — what remains is the Fly log line `Generation error: …` (generator.py:210/317, traceback, no user id). **Keeps** nothing new |
| **(ii) write with an explicit error marker / no charge** | **Verify** fallback-failure path: `verification_status="failed_no_data"` stored, no deduct, rendered as a warning badge on /verify (:459) and /history (:423) | a row under the Research tag; **until the renderer is taught the marker** (`parseResearchAnswer` drops unknown keys, :90-94) it renders as today's empty shell — Share disabled (`ShareButton.tsx:91`, empty `answerText`), Delete present; with a renderer change (segment 3) it can show a marker the way Verify's `failed_no_data` does | **keeps** a per-user record of the failure in `chat_history` (and, if chosen, the partial `full_answer` text that streamed before the exception — today stored unmarked); still no AuditLog; no charge |
| **(iii) other, found in code** | Verify's main path on LLM double-failure: write labelled `ok` + charge — the same defect in a second mode, listed for completeness, not as an option | as today | as today |

Facts that apply to both (i) and (ii): the anon DONE branch (:925-931) charges but never writes, so for L0 the only lever is the deduct; no refund helper exists, so "no charge" = not calling `deduct_anonymous_credits` / `deduct_credits`; the detection mechanism in either case is an `event_stream()` local set in the ERROR branch (:921) and bound at the top (:787-793) for the same reason `citations_data` is; on the fallback-path exception (A1 #3) FALLBACK precedes ERROR, so a row can be both "fallback" and "errored" — D1 and D2 interact on that path; `test_no_citations_event_still_writes_row_with_empty_citations` (:218) changes meaning under either option.

**D2 — fallback persistence.**

| option | consumer changes (Probe C3) | old-row rendering | semantics |
|---|---|---|---|
| **(i) optional `fallback: bool` on `research_v1`** (absence = UNKNOWN) | writer (:1072-1076 + :940) · 1 test assertion (`test_research_history_payload.py:203`) · the parser (:90-94) must be taught to KEEP the key before segment 3 can render it — the `.mjs` guard passes unchanged | unchanged — no key → UNKNOWN → today's render (the parser already tolerates missing keys, `.mjs:146-147`) | absence is a legal third state (old rows); the renderer must handle `true` / `false` / absent |
| **(ii) `kind: research_v2`** | writer · 3 payload-test assertions (:191/:213/:230) · the `.mjs` guard line :124 (written to make v2 a deliberate change) · **`parseResearchAnswer` :89 in the SAME deploy** — otherwise every v2 row renders its raw JSON in the pre-wrap box and a share from it publishes the raw JSON (`test_history_render_fallback.py:100`'s guarded regression) | v1 rows keep the v1 branch; the renderer carries v1 + v2 forever (no backfill, recon §7-D2) | v2 can make `fallback` REQUIRED (absence impossible for new rows) — the trade the two options differ on |

Facts that apply to both: the flag's source can be the :906 FALLBACK branch captured into a top-bound local, or `not documents` / `retrieval_status in ("no_results", "irrelevant")` at DONE (§3.3 C1) — all in scope; the flag already reaches PostHog (`used_fallback`) but not the DB; segment 3 (banner carry-across) reads whatever this ruling writes.

**D3 — scope: Research-only vs three-mode** (driven by §3.2).

| fact | Research-only | three-mode |
|---|---|---|
| Explain | no change under either D1 option (already (i)) | same — nothing to do |
| Verify fallback-failure (site 2) | no change (already (ii)) | same |
| Verify main path, LLM double-failure (site 3) | left as is: writes `ok` + charges; **not filed in TECH_DEBT** — a founder call whether to file | touches `server.py:1493-1568` (loop + write + deducts), the `verification_status` vocabulary (a third failure value beside `failed_no_data` / `deferred_ambiguous_brand`), `/verify` (:458-460) and `/history` (:423) renderers, `tests/test_verify_history_payload.py` (3 tests) |
| anon | Research anon branch (:925-931) | + Verify anon deducts (:1398 / :1566) |
| gate size | ~10 rows (§3.7) | + ~3 Verify rows (both pages, two tiers) |

### §3.6 Flagged, NOT fixed (collaboration principle #4 — founder chooses)

1. `AnswerGenerator.generate_non_stream` (`generator.py:215-273`) has **zero callers under `api/`** — dead code carrying its own copy of the three error conditions.
2. Verify main path writes `verification_status="ok"` with `summary=""` and charges 1 credit when both LLM attempts fail (:1520 → :1548-1568) — the Research defect's Verify sibling; not filed.
3. `pages/research.tsx:452-467` fires `research_completed` on `done` even after an `error` event (and `research_failed` also fired) — analytics honesty; not in the car's scope.
4. `ProvenanceLine`'s tooltip uses `bg-white … text-gray-600` (:92), light-only — a theme-eye row if carried to /history (segment 3).
5. `tests/probes/baton_check/check_baton.py:438` dies with `UnicodeEncodeError` on a cp950 console unless `PYTHONUTF8=1` is set (the same cp950 P3 seam the batons already record).
6. `deduct_credits` does not call `reset_daily_if_needed` (only `check_credits` does) — untouched, noted for the credits car.
7. This baton's title line still reads *"(Segment 1 BUILT, LOCAL ONLY)"* — stale since fly 245; left for the founder (a header edit, not a probe result).

**Status of this list after the segment-2 build (2026-09-04):** item 2 → **FILED** (`TECH_DEBT` `[HONESTY][P2]`, segment 2b, founder ruling D3) · item 3 → **still open, declined this segment** — the brief asked to skip `research_completed` on the error path, but the call site derives to `pages/research.tsx:459` (client-side, fired on the SSE `done` the server still forwards) and that file was required diff-empty; the smallest fix is a client-local `errored` flag set on the `error` event, two lines, for segment 3 or a fixup on ruling · item 7 → **fixed** (title) · items 1, 4, 5, 6 → untouched.

### §3.7 Expected segment-2 gate rows (blank FORM comes at build time — this is the row LIST only)

1. **Error row, user tier, main path** — backend restarted with `GENERATOR_MODEL='gpt-does-not-exist'`, a literature-hitting query: /research shows the error banner; /history shows [no row under D1 (i) | a marked row under D1 (ii)]; `credits_used_today` read before/after is **unchanged**.
2. **Error row, anon tier** (`X-Anon-Fingerprint`): `anonymous_usage.credits_used_today` unchanged; no row (as always).
3. **Fallback-then-error row** (a no-literature query under the bad model): FallbackBanner then the error banner on /research; the D1×D2 interaction — what is stored, what /history shows.
4. **Fallback row, good model** (a no-literature query): FallbackBanner on /research; the stored `answer` JSON carries the flag (DB read); /history renders as today (segment 3 adds the banner) — NOT raw JSON, no crash, no references block.
5. **Grounded row**: flag false / absent-per-ruling; references block present; render unchanged vs fly 246.
6. **Old v1 row** (e.g. dev id 2337) and **old plain-markdown row** (pre-segment-3): render byte-for-byte as before.
7. **Malformed-JSON row** (dev id 2333): still the pre-wrap raw text, no crash.
8. **Share from a new row** → `/q/…` shows markdown, never JSON (mandatory under D2 (ii); regression under (i)).
9. **Under D3 three-mode only**: Verify LLM double-failure → the new status marker on /verify and /history; `credits_used_today` unchanged.
10. **Delete flow** on one disposable row (regression on `tests/test_history_delete.py`'s surface).
11. **Prod eye after deploy**: one errored Research on prod, own account — meter before/after unchanged; /history per the D1 ruling.

---

## §4 Segment 2 — eye gate (TRANSCRIBED 2026-09-04 — founder 6/6 PASS)

**Founder-observed 2026-09-04 on localhost at HEAD `8638c50`** (backend :8000 TEST_MODE, dev DB `ep-spring-voice-a127ye10`, viewer tz Asia/Taipei); rows 1–4 machine facts from `tests/probes/research_error_path/result.json` (run 2, 25/25). Observed / PASS-FAIL transcribed from the founder's closeout statement (see sign-off). **Recipe correction, recorded here and in the row-3/row-4 text:** the error-path recipe must set BOTH `GENERATOR_MODEL` and `GENERATOR_FALLBACK_MODEL` — the anon path runs on the fallback binding (`api/server.py` `model_override = generator._fallback_model`), so recon_20260901 §10 row 10's single-variable form cannot error row 4 (probe README).

**Environment:** local dev server at the segment-2 HEAD (see the segments table for the two code SHAs) — `PYTHONUTF8=1` then `uvicorn api.server:app --reload --port 8000` with `TEST_MODE=true`, plus `npm run dev`; browser in Asia/Taipei. **Prod is still fly 246 — nothing here is a prod observation.** Credit readings are DB reads on the dev DB: authed → `SELECT credits_used_today FROM user_usage WHERE clerk_user_id = 'test_user';` · anonymous → `SELECT anon_id, credits_used_today, last_active_at FROM anonymous_usage ORDER BY last_active_at DESC LIMIT 3;` (the anon id is derived from IP + the browser fingerprint, so the row to watch is the most recently active one; note its `anon_id` prefix BEFORE the error run). The stored flag is read with `SELECT id, answer FROM chat_history WHERE session_type = 'research' ORDER BY id DESC LIMIT 1;` — look for `"fallback": true|false` at the end of the JSON.

| # | Surface / step | Expected | Observed | PASS / FAIL | Notes |
|---|---|---|---|---|---|
| 1 | `/research`, a normal literature-hitting query (e.g. *metformin renal dosing*) → `/history` | The new row renders exactly as under fly 246 (section cards + references block); the DB `answer` JSON ends with `"fallback": false` | id 2342 rendered section cards + references block (5), parity with fly 244 | **PASS** | parity row — the flag is stored, NOT rendered (segment 3). **Probe 2026-09-04 run 2 (`tests/probes/research_error_path/result.json`, :8010, TEST_MODE, dev DB):** dev row **id 2342** "metformin renal dosing" 03:21:51Z — `kind research_v1` · `fallback false` · 5 citations · keys {answer, citations, fallback, kind}; SSE = 678 answer chunks + citations(5) + done, NO `fallback` event; `credits_used_today` 6 → **9** (+3). The render itself is founder-only. |
| 2 | `/research`, a no-literature query (a nonsense drug name, e.g. *zorblaxitide 40 mg dosing*) → `/history` | FallbackBanner on `/research` as today; the new `/history` row renders exactly as under fly 246 (no banner yet, no references block); the DB `answer` JSON ends with `"fallback": true` | id 2343 rendered section cards, no references block, no banner (segment 3), not blank | **PASS** | **Probe run 2:** "zorblaxin 500mg dosing" produced the SSE `fallback` event on the FIRST candidate (no other string was needed); dev row **id 2343** 03:22:19Z — `kind research_v1` · `fallback true` · 0 citations; credits 9 → **12** (+3). The banner / render is founder-only. |
| 3 | Error path, authed — recon_20260901 §10 row 10 recipe, CORRECTED to set BOTH bindings: stop uvicorn, `$env:GENERATOR_MODEL='gpt-does-not-exist'; $env:GENERATOR_FALLBACK_MODEL='gpt-does-not-exist'`, restart; read `credits_used_today` BEFORE; run a literature-hitting query | `/research` shows the error banner and leaves its loading state; AFTER = BEFORE (**+0**, was +3 under fly 246); `/history` has **NO new row**; the backend log shows ONE line `[Research] generator ERROR before DONE — no history write, no charge (audit_id=res_…, anon=False, fallback=False)` | founder saw the error banner on `/research` (screenshot in the closeout conversation); probe: c2 = c3 = **12**, rows **2137 → 2137**, log line `audit_id=res_d6e806e403004e7d, anon=False` | **PASS** | restore: remove BOTH env vars, restart uvicorn. **Probe run 2 — NOTE the recipe extension:** the probe set BOTH `GENERATOR_MODEL` and `GENERATOR_FALLBACK_MODEL` to `gpt-does-not-exist` (the anon path runs on `_fallback_model`, so `GENERATOR_MODEL` alone cannot error row 4). Authed "warfarin bleeding risk": SSE `query_id · status ×3 · language · error · done` (error text *"Unable to retrieve information at this time due to a service issue. Please try again in a moment."*, 18.3 s); credits **12 → 12** (+0; run 1 read 6 → 6); rows **2137 → 2137** (research 1114 → 1114), newest id **2343** before AND after; server log: `2026-09-04 11:23:04,834 vela INFO [Research] generator ERROR before DONE — no history write, no charge (audit_id=res_d6e806e403004e7d, anon=False, fallback=False)`, preceded by `api.rag.generator ERROR Generation error: [LLM_MODEL_NOT_FOUND] … 404`. The error banner itself is founder-only. |
| 4 | Same recipe (BOTH env vars — the anon path runs on `_fallback_model`), anonymous (logged out, same browser) | error banner; the watched `anonymous_usage` row's `credits_used_today` unchanged (was +3); no history row (as always for L0); the log line reads `anon=True` | probe: anon row **0 → 0**, `last_active_at` unchanged, log line `anon=True` (`audit_id=res_f10d1e5fd59a4467`) | **PASS** | **Probe run 2 (anon = `X-Anon-Fingerprint` header, derived anon_id `412437c58e3756f1…`):** SSE error then done (21.1 s); `anonymous_usage` row credits **0 → 0** and `last_active_at` **unchanged** at 03:19:20Z (`deduct_anonymous_credits` writes it, so an unchanged value proves the deduct never ran); 25 anon rows before and after, none changed; history rows 2137 → 2137; authed credits untouched (12); server log: `2026-09-04 11:23:28,321 vela INFO [Research] generator ERROR before DONE — no history write, no charge (audit_id=res_f10d1e5fd59a4467, anon=True, fallback=False)`. Run 1 (`result_run1_20260904.json`) had no anon row beforehand — the pre-stream quota check created it at 0, which the probe's first "no row changed" check mis-read as a change (probe-side false positive, fixed for run 2). The banner is founder-only. |
| 5 | `/verify` (warfarin + aspirin) and `/explain` (any short report), one query each | Unchanged vs fly 246 — rows written and rendered as before (ruling D3: Research-only) | `/verify` + `/explain` unchanged | **PASS** | — |
| 6 | Pre-segment-2 rows: any fly-244-era `research_v1` row (e.g. dev id 2337) and any plain-markdown row | Render unchanged; browser console shows no error (the absent `fallback` key is tolerated as UNKNOWN) | id 2334 renders, console clean | **PASS** | — |

**Founder sign-off line (name · date · overall verdict):** Andrew Lee (founder) · 2026-09-04 · **6/6 PASS** — provenance: founder statement 「驗證完都通過」 + screenshot in the closeout conversation for the visual rows, probe `tests/probes/research_error_path/result.json` (run 2, 25/25) for the machine facts; transcribed by Claude Code under the closeout authorization, per the 2026-09-01 zh-TW transcription precedent. Observed on localhost at HEAD `8638c50` (backend :8000 TEST_MODE, dev DB `ep-spring-voice-a127ye10`, viewer tz Asia/Taipei).
