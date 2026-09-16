# RETENTION EXECUTION CAR — opened 2026-09-14

> **🏁 SEGMENT 1 CLOSED 2026-09-15 (founder ruling R1; written 2026-09-16).** Gate §6 **6/6 founder-PASS** — row 6 on the `fly logs` line of `2026-09-15T03:58:26Z` (`683d447c2e5428`: **deleted 3 audit logs, 4 chat history records**, `cutoff=2026-03-19T03:58:24.808924 UTC`, 86,403 s after the boot pass) plus the founder's three prod `SELECT`s (`chat_history` count **1394 → 1390**, `min` **02:43:19 → 04:02:30**, overdue **1** = daily lag; `audit_logs` `min` **04:02:30.35**). Prod UNCHANGED at **fly 257 = `e12d3f0bb4bb37006834e8eaa19fe77537000944`**; `2879720c66d478` has been `stopped` since 2026-09-14T04:06Z (auto-stop; the floor machine ticks — residual (1) MEASURED, not a coverage gap). Ledger: the TECH_DEBT E1 entry stays **OPEN**, re-rated **P1 → P2**; the 2026-08-17 `[COMPLIANCE][P2] retention automation` duplicate is **MERGED** into it as a stub (NAV 189, delta 0). Segment 2 (E5) **NOT started** — order per `STATE.md` Next Up. Closeout detail: **§8**. Docs-only, NOT deployed by design.

**Segment 1 (E1) ✅ SHIPPED as fly 257 — 2026-09-14.** Prod = **fly v257 = `e12d3f0bb4bb37006834e8eaa19fe77537000944`**, image `deployment-01M2F0WV3X3A0R5XQ2R85KVGD2`, both machines
`started` in nrt. Previous prod was fly 254 = `93d704c286c752cb56edcef80cc0131c9720be19`.
⚠️ **The release number was READ from `fly releases`, not computed** — “254+1” would have given v255, and
**v255 / v256 (Sep 11, 04:54 / 04:55) were the `LEMON_SQUEEZY` secrets-unset rolling releases**, not rebuilds.
⚠️ **Post-deploy docs commits are NOT deployed by design** — `/health` reads the CODE SHA, so a newer docs
SHA on `origin/main` is not drift.

*(The BUILT-LOCAL line this replaced: “Prod is unchanged at fly 254 … machine version 256” — true when
written, superseded by the deploy below.)*

| segment | item | status |
|---|---|---|
| **1** | **E1** — `[sec][COMPLIANCE][P1]` *(→ `[P2]` 2026-09-15)* the 180-day retention task cannot be shown to have ever run | **✅ SHIPPED as fly 257, 2026-09-14** — run-then-sleep + unconditional log + `_cleanup_pass()` extraction. Gate §6 **rows 1–5 PASS**, **row 6 founder-pending** *(→ **PASS 2026-09-15**; **🏁 SEGMENT 1 CLOSED** — §8)*. ⚠️ The TECH_DEBT entry stays **OPEN, not `[DONE]`** *(re-rated P1 → P2 2026-09-15; the 2026-08-17 duplicate MERGED into it)*: no persisted last-run marker, and the daily-sweep-vs-「6 months」 question is unresolved |
| 2 | **E5** — `pages/privacy.tsx:30` claims query **and answer** content are "de-identified (via PHI masking as a primary safeguard)", which is false for `answer` in every mode and for `question` at the three Verify sites | **NOT STARTED** — recorded inside the E2 entry 2026-09-14; not yet filed as its own entry |

---

## §0 — REPO ASSERTION (Rule 24)

```
git rev-parse --show-toplevel  ->  C:/Users/andre/projects/Vela
git rev-parse HEAD             ->  e64d1572e5c081d082423fb68e10c555b27f4ced   (the [sec] ledger commit)
git status --short             ->  4 known untracked (.superpowers/ + 3 public/media/*.png)
git stash list                 ->  stash@{0}: On main: PHASE D partial work before crash   (PRE-EXISTING, untouched)
git status -sb                 ->  ## main...origin/main [ahead 2]
```

All five matched expectation. Every "before" line number below is **at `e64d157`**.

---

## §1 — RULE 25: DERIVED vs CITED, BEFORE EDITING

Commands: `awk` over `api/server.py` lines 188-220 for the verbatim block with indentation, plus one
`git grep -n` per symbol.

| cited by the task brief | derived at `e64d157` | verdict |
|---|---|---|
| `_cleanup_old_records()` `:190-208` | `:190-208` | **MATCH** |
| `await asyncio.sleep(86400)` at `:194`, BEFORE the delete | `:194`, first statement of the loop body | **MATCH** |
| cutoff `datetime.utcnow() - timedelta(days=180)` at **`:195`** | **`:196`** (`git grep -n "timedelta(days=180)"`) | **🔴 DRIFT — off by one** |
| `AuditLog` delete `:199` | `:199` | **MATCH** |
| `ChatHistory` delete `:200` | `:200` | **MATCH** |
| success log `:202-204`, guarded by `if deleted_audit or deleted_chat:` | guard `:202`, log `:203-204` | **MATCH** |
| `except Exception as e: logger.error("Data cleanup error: %s", e)` ~`:207-208` | `:207-208` | **MATCH** |
| lifespan `asyncio.create_task(...)` `:214`, cancelled `:216` | `:214` / `:216` | **MATCH** |
| in-code stale citation at **`api/server.py:271`** | **`:272`** (`git grep -n "Production guard at module init"`) | **🔴 DRIFT — off by one** |
| `pages/privacy.tsx:46` carries the retention promise | `:46` — *"Data is automatically deleted after 6 months."* | **MATCH** |
| prod `min` + 180 days = **2026-09-15 02:43 UTC** | `2026-03-19 02:43:19.292984 + 180d` = **2026-09-15 02:43:19** | **MATCH** |
| "TODAY IS 2026-09-14. Under 24 hours." | **26.7 h** from 2026-09-14 **00:00** UTC. "Under 24 h" holds only after **02:43 UTC on 2026-09-14** | **DRIFT (minor) — restated precisely** |
| entry currently carries expiry **2026-09-18** | confirmed present in the E1 entry; measured value is **2026-09-15 02:43 UTC**, i.e. **~2 d 21 h EARLIER** | **STALE — corrected in place** |
| retention is described in **PRD §6.4** | `docs/PRD.md:2215` — 「chat_history(所有已登入使用者 L1 + L2,180 天保留,到期自動刪除)」, with `:726` confirming §6.4 is the aligned section | **MATCH — `[PRD 6.4]` tag justified** |

🔑 **BOTH DRIFTS ARE MY OWN, INHERITED.** `:195` and `:271` were written by the 2026-09-14 probe into the E1
entry and the NAV block, and this task's brief inherited them from there. Neither was ever re-derived between
being written and being re-used — which is the exact chain Rule 25 exists to break. Corrected in the entry, and
recorded here rather than silently fixed.

### §1(a) — ⚠️ THE STOP CONDITION: is the `try/except` inside the loop, or around it?

**INSIDE the loop body. The STOP condition does NOT fire; the entry's severity as filed is correct.**

Derived by indentation, not by eye:

```
193| indent= 4 | while True:
194| indent= 8 | await asyncio.sleep(86400)
195| indent= 8 | try:          <- loop body, same level as the sleep
198| indent=12 | try:          <- inner: session lifecycle
205| indent=12 | finally:
207| indent= 8 | except Exception as e:   <- loop body
```

`while True:` is at indent 4; both `try:` and `except` are at indent 8, i.e. **statements of the loop body**.
A failed pass is therefore logged and the loop retries the next cycle. Had the `try` wrapped the loop, one
transient DB error would have ended retention for the life of the process — strictly worse than the filed
defect, and the brief correctly required a stop for that case. It is not that case.

**This property is now guarded** by `test_t5_pass_exception_does_not_kill_the_loop`, so the extraction cannot
silently move it.

### §1(b) — is the session closed in a `finally`?

**Yes, correctly. No leak; nothing to fix.** `db = SessionLocal()` at `:197` sits inside the outer `try` but
**before** the inner `try:` `:198` / `finally:` `:205` / `db.close()` `:206`. If `SessionLocal()` itself raises,
`db` is never bound and there is nothing to close — the outer `except` handles it. If it succeeds, the inner
`finally` always closes. The extraction carries this shape across verbatim (see §4, Rule 19).

---

## §2 — THE CHANGE (`api/server.py` only)

**2a. RUN-THEN-SLEEP.** `await asyncio.sleep(86400)` moved from the **first** statement of the loop body to the
**last**. A pass now runs immediately at process start and every 24 h after. **No startup grace period added** —
a delay before the first pass is what created this defect, and any grace period is a founder call, not a
default.

**2b. UNCONDITIONAL LOG.** The `if deleted_audit or deleted_chat:` guard is removed. The INFO line now emits on
**every** pass, zero-delete included, and carries **both counts and the cutoff timestamp it used**:

```
Data cleanup pass: deleted %d audit logs, %d chat history records older than 180 days (cutoff=%s UTC)
```

The cutoff is in the line on purpose: a wrong cutoff is then visible from logs alone, without a redeploy.

**2c. EXTRACTION.** `_cleanup_pass()` — open session → cutoff → two deletes → commit → log → close — called by
`_cleanup_old_records()`, which is now just the loop (call pass, catch, sleep). Required so §3 can be
behavioural rather than source-grep assertions (Rule 17).

⚠️ **Judgment recorded, not slipped in: `_cleanup_pass()` is SYNC, not `async`.** The DB work was already
synchronous inside the async function, so a sync extraction changes no threading behaviour at all, and it keeps
T2/T3/T4 free of an event loop. The loop stays `async` because it awaits the sleep.

**Rule 7 CHECK, at the site being edited.** Derived: the two bulk deletes at `:199-200` carried **no call-site
comment** naming their `_safe_db_write` exemption — `awk` over the block shows no comment between the inner
`try:` and `db.commit()`. **Case (a)**: a bulk `query().filter().delete()` is DML the helper cannot express (it
is `add()` + `commit()` only, and returns no row count — and the counts are exactly what this pass reports). The
comment is **ADDED in this commit**, as the rule's CHECK requires. This is the one commit that will ever have
this function open.

**Also fixed here, because the ledger commit deferred it explicitly to "the next commit that touches
server.py":** the stale in-code citation. It read `Production guard at module init (server.py:305-308)`.
⚠️ It is at **`:272`**, not `:271` as briefed, and the first repair I wrote said "the raise is at
server.py:327" — **which my own edit immediately invalidated**, moving the raise to `:371`. The comment is
therefore rewritten **symbol-first and line-free**: it names the guard by its literal message string so a reader
can `grep` for it, and says why no number is given. A bare line number in a comment ~50 lines from its referent
drifts on every edit above it, which is how it got stale twice in one session.

### DECLINED IN THIS SEGMENT — each stated, none built

| declined | why |
|---|---|
| a **persisted last-run marker** | the larger fix; a design decision (where the marker lives, what reads it), not a two-line change |
| any change to the **180-day constant** | out of scope; the constant is correct per PRD §6.4 |
| **E4** `_check_phi` fail-open · **E2** Verify masking · **E3** `patient_context` · **E5** the privacy.tsx de-identification claim | separate entries, separate ratings, separate segments |
| moving the sync DB work off the event loop (`run_in_threadpool`) | ⚠️ **behaviour delta worth naming**: the blocking DB pass now happens at BOOT rather than 24 h in. With 0 rows currently over 180 days the DELETE is trivial, and the table is 1,394 rows total, so this is not a startup risk today. Gate row 2 checks it empirically. Out of segment scope; recorded, not assumed away |

---

## §3 — TESTS AND MUTATIONS

New file `tests/test_cleanup_retention.py`. **The business rule, stated once and referenced by every docstring:**
*the deployed `/privacy` §4 promise that user data is deleted after 6 months is both EXECUTED and OBSERVABLE.*

| test | asserts | why it is not dead weight (Rule 17) |
|---|---|---|
| **T1** ORDER | monkeypatches `_cleanup_pass` and `asyncio.sleep`, runs the real loop, asserts the pass ran **before** the first sleep | catches the exact defect being fixed, behaviourally — not a source grep |
| **T2** zero-delete log | a session whose deletes return 0; asserts via `caplog` that the INFO line fires and carries both counts **and** the cutoff | a zero-delete pass is **correct** before 2026-09-15 02:43 UTC; if it is silent, correct and dead are indistinguishable |
| **T3** POSITIVE CONTROL | real in-memory rows at 181 d and 179 d, **both tables**; old deleted, new kept, read back through a fresh session | without it T1 and T2 both pass against a `_cleanup_pass` that logs and does no work |
| **T4** commit | recording session; asserts exactly 2 deletes, 1 commit, 1 close | `Session.close()` rolls back — a commit-less pass logs plausible non-zero counts while deleting nothing, the worst shape available |
| **T5** carry-across | a pass that raises; asserts the loop survives and runs again | guards §1(a) so the extraction cannot silently move the `try` around the loop |

⚠️ **DIALECT CAVEAT, stated in the harness docstring:** T3 runs on in-memory **SQLite**, not the Neon Postgres
of prod. What it exercises is the cutoff comparison and the commit, which SQLAlchemy emits identically for both
(`WHERE col < :cutoff` + `COMMIT`). It does **not** exercise Postgres-specific DELETE behaviour — row locks,
cascade timing, statement timeouts. Out of scope, named rather than assumed.

### RED → GREEN

**RED, before any edit to `api/server.py`:** `5 failed`, every one
`AttributeError: module 'api.server' has no attribute '_cleanup_pass'`.

⚠️ **That red is "symbol absent", not "order wrong"** — stated plainly rather than presented as stronger
evidence than it is. The **ordering-specific** red is mutation **M1**, run after green, which fails T1 on the
assertion itself:

```
>       assert events[0] == "pass", (
E       AssertionError: the first thing the loop did was 'sleep' — a pass must run BEFORE the
E       first sleep, or a process that lives under 24 h never deletes anything
E       assert 'sleep' == 'pass'
```

**GREEN, after 2a + 2b + 2c:** `5 passed`.

### MUTATIONS — 5/5 CAUGHT

Harness applied one mutation at a time to `api/server.py`, ran the suite, restored the file byte-for-byte from a
backup in a `finally`; it asserted the baseline was green before starting, and `git diff --stat` confirmed the
file was intact afterwards.

| # | mutation | result | caught by |
|---|---|---|---|
| M1 | sleep moved back to the top of the loop body | **CAUGHT** (2 failed) | T1, T5 |
| M2 | `if deleted_audit or deleted_chat:` guard re-added around the log | **CAUGHT** (1 failed) | T2 |
| M3 | cutoff sign flipped (`utcnow() + 180d`) | **CAUGHT** (2 failed) | T2, T3 |
| M4 | one of the two table deletes removed (`ChatHistory`) | **CAUGHT** (2 failed) | T3, T4 |
| M5 | `db.commit()` removed | **CAUGHT** (2 failed) | T3, T4 |

---

## §4 — THE FOUNDER FACTS, AND WHAT THEY DO AND DO NOT ESTABLISH

### Provenance (Rule 20) — stated, not implied

A founder-run **READ-ONLY** `SELECT` on the Neon **production** branch (branch + database confirmed in the UI as
`production` / `neondb`; single statement; no write):

```sql
SELECT MIN(created_at), MAX(created_at), COUNT(*) FROM chat_history;
-- min = 2026-03-19 02:43:19.292984 | max = 2026-09-11 04:55:48.109034 | count = 1394

SELECT MIN(created_at), COUNT(*) FROM chat_history WHERE created_at < NOW() - INTERVAL '180 days';
-- min = NULL | count = 0
```

⚠️ **Claude Code did NOT run these and did NOT view the screenshots.** They are **founder observations
transcribed** under the build authorization — the zh-TW transcription precedent. **Rule 20's escape clause
applies and is invoked rather than worked around:** the artifact is a **live-DB snapshot**, so re-running the
statements produces a **NEW** snapshot, not this one. Nothing here is reproducible by another party; it is a
dated observation, and that is why it is written down verbatim instead of being regenerated.

### What the numbers establish — arithmetic re-checked, not inherited

- `2026-03-19 02:43:19.292984 + 180 days` = **2026-09-15 02:43:19 UTC** — the instant the first row becomes
  eligible. From 2026-09-14 00:00 UTC that is **26.7 hours**.
- **0 rows are currently over 180 days**, so `/privacy` §4 (`pages/privacy.tsx:46`) is **TRUE RIGHT NOW**.
- `min` sitting **1 day 8 h AFTER** the 180-day line rather than tracking it is the evidence that **no pass has
  ever deleted anything on prod.**

### ⚠️ THE LIMIT OF THAT EVIDENCE, STATED PRECISELY

**That is NOT "the task never ran."** A pass that deletes zero rows is **correct behaviour** before
2026-09-15 02:43 UTC, and — until this commit — **completely silent**, because the log was guarded.
**Never-ran and ran-but-deleted-nothing are indistinguishable from both the database and the logs.**

**THAT INDISTINGUISHABILITY IS THE DEFECT**, and §2b is the part of this change that removes it. §2a removes
the separate defect that the pass may genuinely never have executed.

### Sweep granularity — an open question, not resolved here

The sweep is **daily**, so a row can persist **up to 24 h past its 180-day mark**. Whether "up to 6 months" in
`/privacy` §4 tolerates that overshoot is a **founder / counsel reading**, recorded as open. It is not resolved
by this build, and this build does not change it either way.

---

## §5 — READBACKS

| check | before | after |
|---|---|---|
| pytest (`uv run python -m pytest -q --ignore=tests/results`) | **442 passed, 28 skipped** | **447 passed, 28 skipped** — +5, all `tests/test_cleanup_retention.py`; derived +5 = expected +5 |
| `npx tsc --noEmit` | 0 | **0** |
| `npm run lint` | 22 problems (7 errors, 15 warnings) | **22 problems (7 errors, 15 warnings)** |
| i18n keys | — | **+0** |

**Rule 16 — CHECKED, not assumed. NON-APPLICABLE, derived:**
`git diff --stat -- pages/ components/ utils/ styles/ public/ content/` → **EMPTY**. A background task has no
UI and this change adds no user-visible string. The one new string is a server log line, which is operator-facing.

**Lint identity, not count:** ESLint reads only the frontend, and the frontend diff above is **empty**, so the
problem set is identical **by construction** — a stronger statement than two counts agreeing at 22.

**`npm run build` — NOT RUN, and the choice is stated.** Zero frontend files change, so the bundle is unaffected
**by construction**; the empty diff above is the derivation, and a build would re-verify nothing about this
change. The cheaper path was taken deliberately.

**Rule 19 — what `_cleanup_old_records` did AROUND the delete, and where each piece landed:**

| behaviour at `e64d157` | carried to | status |
|---|---|---|
| `db = SessionLocal()` + `try/finally: db.close()` | inside `_cleanup_pass()` | ✅ carried verbatim |
| `except Exception` **inside** the `while True:` body | stays in `_cleanup_old_records()`, still inside the loop | ✅ carried — and now guarded by T5 |
| cancellation at lifespan shutdown (`cleanup_task.cancel()`, `:216`) | `await asyncio.sleep(86400)` remains the only await, so cancellation still unwinds there; `asyncio.CancelledError` derives from `BaseException`, so `except Exception` does not swallow it | ✅ carried, and reasoned rather than assumed |
| cutoff computed per pass (not once) | inside `_cleanup_pass()` | ✅ carried — a long-lived process must not freeze its cutoff |

**Rule 5 — flagged, deliberately not fixed:** `logger.error("Data cleanup error: %s", e)` interpolates the
exception. Rule 5 governs **API responses**, not logs, so this is in policy — but it is the same shape as the
`[sec][OTHER][P3]` `str(httpx.HTTPStatusError)` URL-echo entry. A comment at the call site says so.

**Rule 4** — `logging.getLogger("vela")`, no `print()`. **Rule 18** — the §1(a) stop condition was evaluated
**before** editing and did not fire; nothing was skipped or exception-swallowed in this build.

---

## §6 — GATE FORM (BLANK — founder fills)

| # | where | check | EXPECTED | result |
|---|---|---|---|---|
| **1** | LOCAL | **⚠️⚠️ FIRST: `DATABASE_URL` on the DEV branch, printed without credentials.** Then `TEST_MODE=true uvicorn api.server:app --reload --port 8000` | the cleanup INFO line within **seconds** of boot, carrying both counts and the cutoff | **✅ PASS** — boot 11:46:43 → line 11:46:53 (**10 s**). DEV branch confirmed first (`ep-spring-voice-a127ye10-pooler…`). `2026-09-14 11:46:53,392 vela INFO Data cleanup pass: deleted 0 audit logs, 0 chat history records older than 180 days (cutoff=2026-03-18T03:46:52.944808 UTC)` — **both counts 0, which is the point: a zero-delete pass is now visible** |
| **2** | LOCAL | `GET /health` right after boot | **200**, startup not blocked by the boot-time DB pass | **✅ PASS** — 200 in the same boot, after `Application startup complete` |
| **3** | LOCAL | restart the server | the line appears **again**, proving per-boot execution | **✅ PASS** — restart 11:47:57 → line 11:48:06 (**9 s**). ⭐ **And the `cutoff` ADVANCED 03:46:52 → 03:48:05, by exactly the 73 s between boots — proving the cutoff is recomputed per pass, not frozen at import.** That is a stronger result than the row asked for |
| **4** | MACHINE | pytest count; T1/T2 RED-then-GREEN; mutations | 442 → 447; 5/5 caught | **✅ PASS** — 442 → **447** / 28 skipped (+5). RED = 5 failed on `AttributeError: no _cleanup_pass`; the ordering-specific RED is M1 (T1 assertion). **5/5 mutations caught** |
| **5** | POST-DEPLOY | `fly logs`: the cleanup line on **BOTH** machines at boot | present on both, with counts and `cutoff=` | **✅ PASS — ⭐ THE DELIVERABLE. Verbatim:**<br>`683d447c2e5428` @ `2026-09-14T03:58:23Z` → `2026-09-14 03:58:23,291 vela INFO Data cleanup pass: deleted 0 audit logs, 0 chat history records older than 180 days (cutoff=2026-03-18T03:58:22.829299 UTC)`<br>`2879720c66d478` @ `2026-09-14T03:58:59Z` → `2026-09-14 03:58:59,156 vela INFO Data cleanup pass: deleted 0 audit logs, 0 chat history records older than 180 days (cutoff=2026-03-18T03:58:58.794788 UTC)`<br>**Boot-to-log latency 20 s on both** (machines started 03:58:03Z / 03:58:39Z) |
| **6** | POST-DEPLOY *(**FOUNDER ONLY** — not Claude Code; prod DB is not touched by this session)* | re-run the two prod `SELECT`s **after 2026-09-15 02:43:19 UTC**:<br>`SELECT MIN(created_at), MAX(created_at), COUNT(*) FROM chat_history;`<br>`SELECT MIN(created_at), COUNT(*) FROM chat_history WHERE created_at < NOW() - INTERVAL '180 days';` | `min(created_at)` has advanced past the 180-day line and the second query returns `count = 0` again. ⚠️ **A daily sweep means `min` may lag the line by UP TO 24 h — EXPECTED, not a failure.** Beyond ~25 h of lag is the failure signal | **✅ PASS — founder, 2026-09-15.** **Primary (`fly logs`, read by Claude Code, read-only, 2026-09-15 ~05:55 UTC; window `2026-09-14T05:58:36Z` → `2026-09-15T05:45:24Z`, 88 lines, 0 from `2879720c66d478`, 0 `Data cleanup error`), verbatim:**<br>`2026-09-15T03:58:26Z app[683d447c2e5428] nrt [info]2026-09-15 03:58:26,284 vela INFO Data cleanup pass: deleted 3 audit logs, 4 chat history records older than 180 days (cutoff=2026-03-19T03:58:24.808924 UTC)`<br>**86,403 s after the 09-14 boot pass** = `sleep(86400)` + ~3 s; cutoff **1 h 15 m past** the measured `min` 02:43:19.29.<br>**Corroboration — founder's READ-ONLY prod `SELECT`s (Neon `production`, 2026-09-15; transcribed — Claude Code ran none, viewed no screenshot):**<br>`SELECT MIN(created_at), MAX(created_at), COUNT(*) FROM chat_history;` → **2026-03-19 04:02:30.968111** · 2026-09-11 04:55:48.109034 · **1390**<br>`SELECT COUNT(*) FROM chat_history WHERE created_at < NOW() - INTERVAL '180 days';` → **1**<br>`SELECT MIN(timestamp) FROM audit_logs;` → **2026-03-19 04:02:30.351771**<br>**Readings, pre-agreed:** 1394 → 1390 = **−4 = the line's 4** (two independent sources agree to the row) · `min` 02:43:19 → 04:02:30 — everything before the cutoff gone, first survivor 4 min after it · overdue **1** = that row, past the SELECT's line but not yet swept = **daily-sweep lag, EXPECTED** (failure signal was > ~25 h) · `audit_logs` `min` **0.6 s before** `chat_history` `min` (same request, AuditLog first) — both tables on one cutoff; the 2026-08-17 entry's own recheck query passes on its own terms |

### Backfill separation, and why a backfill line is impossible here

The captured `fly logs` window runs `2026-09-13T15:51:51Z` → `2026-09-14T03:59:37Z` and contains **exactly two**
cleanup lines, both timestamped after the v257 rollout. 🔑 More than that: **a backfill cleanup line could not
exist by construction** — under the pre-257 code the log was guarded by `if deleted_audit or deleted_chat:` and
every pass was zero-delete, so no such line was ever writable. Row 5 is therefore not "we found it in the
window"; it is "the line exists for the first time."

### ✅ The arithmetic that ties this deploy to the measured deadline

| machine | cutoff logged | prod `min(created_at)` | gap | reading |
|---|---|---|---|---|
| `683d447c2e5428` | `2026-03-18T03:58:22.829299` | `2026-03-19 02:43:19.292984` | **22.75 h before** | 0 deletions is **arithmetically correct** |
| `2879720c66d478` | `2026-03-18T03:58:58.794788` | `2026-03-19 02:43:19.292984` | **22.74 h before** | same |

**That reading was impossible before this deploy.** A silent zero-delete pass and a dead task produced identical
evidence; now the cutoff is in the line, so "nothing was old enough yet" is checkable against a number.

### Deploy readbacks (a–g), derived

| # | check | result |
|---|---|---|
| a | release number **READ** from `fly releases` | **v257**, 1m32s after the deploy. Above it: **v256** (Sep 11 04:55) and **v255** (Sep 11 04:54) — the `LEMON_SQUEEZY` secrets-unset rolling releases — then **v254** (Sep 11 02:54), the previous code deploy. ⚠️ "254+1" would have been **wrong** |
| b | `/health` `revision` | `e12d3f0bb4bb37006834e8eaa19fe77537000944` — **full 40 chars, exact, FIRST poll**, 2026-09-14 **03:59:12 UTC** |
| c | `fly status` | both machines **257**, **started**, nrt |
| d | deploy.ps1 parser | Steps 1–6 all present, **exit 0**. Step 3 found `2879720c66d478` **`stopped`** — the `auto_stop_machines = true` behaviour, checked before being called anything else — and **Step 4 started it. NO manual `flyctl machine start` was needed.** Transcript: `tests/probes/deploy_parser/fly257_deploy_transcript.txt` (988 lines, ANSI-stripped), the **10th** consecutive clean-run record |
| e | unauth `GET /api/history` | **403** `{"detail":"Missing token"}` |
| f | the cleanup line, both machines | **✅ present** — gate row 5 above |
| g | frontend unaffected **by construction** | `git diff --stat 93d704c..e12d3f0 -- pages/ components/ utils/ styles/` → **EMPTY** |

### ⏱️ Timing, in UTC

Push at **2026-09-14 03:55:03 UTC**, with **+22.80 h** of margin to the **2026-09-15 02:43:19 UTC** deadline.
⚠️ Recorded in **UTC** deliberately: the local clock here is +08:00, and a previous session converted to local,
read the window as closed, and was wrong by ~16 h.

---

---

## §7 — WHAT THIS BUILD DID NOT DO

Not pushed, not deployed, no `fly` call of any kind, no DB access of any kind by Claude Code. The gate above is
**blank**. Prod remains **fly 254 = `93d704c`**, machine version 256. Rows 1-4 are the founder's to fill before
push/deploy authorization is considered; rows 5-6 come after.

**✍️ 2026-09-16 — SUPERSEDED; kept as the build-time record.** Prod has been **fly 257** since 2026-09-14 03:57 UTC (§5, §6); gate §6 is **filled 6/6** (rows 1–4 2026-09-14 local · row 5 2026-09-14 post-deploy · row 6 2026-09-15). Claude Code's `fly` use in this car, all READ-ONLY and all on 2026-09-15: `fly releases`, `fly status`, `fly logs --no-tail` (row 6's primary evidence). Still **NO DB access of any kind by Claude Code** — every `SELECT` in this baton is the founder's.

---

## §8 — SEGMENT 1 CLOSEOUT (founder rulings R1–R9 of 2026-09-15; written 2026-09-16)

### §8.1 Row 6 — provenance first, then the reading

| source | who | when | what |
|---|---|---|---|
| `fly logs -a vela-ai-medical --no-tail` | Claude Code, read-only | 2026-09-15 ~05:55 UTC | window `2026-09-14T05:58:36Z` → `2026-09-15T05:45:24Z`, **88 lines** (86 app lines, all from `683d447c2e5428`; **0** from `2879720c66d478`; 2 `proxy ord` "invalid authority" lines, unrelated); **exactly one** cleanup line — quoted verbatim in §6 row 6 |
| `fly status` · `fly releases` | Claude Code, read-only | 2026-09-15 05:52 UTC | v257 at the top of `fly releases` (Sep 14 03:57); `683d447c2e5428` **started**, `2879720c66d478` **stopped** (last updated 2026-09-14T04:06:03Z) |
| three prod `SELECT`s | **founder**, Neon `production`, read-only | 2026-09-15 | transcribed in §6 row 6 — Claude Code ran none and viewed no screenshot |

Reading, in the order the criteria were fixed BEFORE the numbers: the log line is the primary evidence and says **the first real deletion happened** (3 + 4 rows, cutoff stated); the `SELECT`s corroborate it **row for row** (1394 → 1390 = −4); overdue **1** is the daily-sweep lag the gate pre-declared EXPECTED; `audit_logs` `min` 0.6 s before `chat_history` `min` shows both tables swept on one cutoff and discharges the 2026-08-17 entry's own recheck on its own terms. **Row 6 = PASS. Segment 1 = CLOSED.**

⚠️ Rule 20: both sources are live snapshots — dated observations, not regenerable artifacts. The quoted line is committed (§6 row 6 · `TECH_DEBT.md` E1 row-6 bullet · `STATE.md`); the 88-line window stays in a session scratchpad outside the tree, deliberately — it is request-log noise around one line.

### §8.2 What the closeout changed in the ledgers (all docs-only)

| # | ruling | where | what |
|---|---|---|---|
| R1 | row 6 PASS, segment 1 CLOSED | this baton :3 · :15 · §6 · `STATE.md` header + Next Up + Recently Shipped | the `STATE` Recently Shipped entry for fly 257 was MISSING (CLAUDE.md step 9) — added at closeout, terse |
| R2 | MERGE | `TECH_DEBT.md`: the 2026-08-17 `[COMPLIANCE][P2 · retention automation]` entry → heading-kept stub; body → `docs/archive/tech_debt_done.md` VERBATIM; E1 carries the MERGED IN bullet; the COMPLIANCE nav-list title annotated | mechanics DERIVED from the 2026-09-09 httpx / credential-hygiene stub: heading words kept with the status struck and the merge status appended inside the bracket; body relocated verbatim under a dated relocation comment; pointer both ways. ⚠️ Derived ≠ briefed on one point: the brief said "heading verbatim" — the precedent's own heading was NOT byte-verbatim (it struck `NOT fixed, NOT rotated` and appended the merge status); followed the precedent, every original word kept. Class: the precedent stub went `[DONE]` because its canonical closed that day; this stub KEEPS `[COMPLIANCE]` because E1 is OPEN — NAV delta 0 |
| R3 | E1 P1 → P2 | E1 heading + dated bullet; the two `[P1]` cross-references in the `ChatHistory.answer` entry annotated; the sec-probe baton §6 E1 row annotated | class unchanged; no NAV movement |
| R4 | grep-before-filing | NAV block 2026-09-16 | PROMOTED to CLAUDE.md Rule 27 in the following commit — not a candidate |
| R5 | credential hygiene | `TECH_DEBT.md`: the httpx canonical's 2026-09-10 bullet (in-place premise) + a new 2026-09-14 bullet; the merged stub's 2026-09-10 bullet (in-place premise) + a new bullet | third rotation NOT DONE, founder 2026-09-14; the value entered one Claude Code transcript via an IDE selection; not git (`.gitignore:4`, `git log --all -- .env` = 0), not Fly logs (`api/server.py:18`); "never logged on Fly" stays TRUE with its premise; founder rationale recorded as the founder's |
| R6 | the `:272` citation | `TECH_DEBT.md` 2026-09-14 [sec] NAV note (e) · sec-probe baton §2.9 | **nothing to fix in code** — done in `c96a31b` (this car's build), fragment cleared in `e12d3f0`; both "to ride the next commit" lines annotated, old text kept. Derived: the sentence was at `:272`; both ledger lines said `:271` |
| R7 | STATE + baton current | `STATE.md` :3 header · Next Up 🏁 block · item 1 DONE · Recently Shipped fly 257 · this baton :3 / :15 / §6 / §7 / §8 | E5 next, then render-leftovers segment 2, then E2 / E3 / E4 (founder order 2026-09-15) |
| R8 | stopped machine | E1 bullet 📏 · §8.3 | residual (1) MEASURED, not a coverage gap, not fixed by design |
| R9 | adjacent notes 4 + 5 | §8.4 | one line each; no new entries |

### §8.3 R8 — the stopped machine, measured

`2879720c66d478` booted 2026-09-14T03:58:39Z, logged its boot pass at 03:58:59Z, and has been `stopped` since **2026-09-14T04:06:03Z** — 8 min later (`fly.toml:21` `auto_stop_machines = true`). It produced **0** lines in the 88-line window; its `sleep(86400)` will never return. Only `683d447c2e5428` — the `fly.toml:23` `min_machines_running = 1` floor — reached the 24 h tick. **Why this is not a coverage gap:** run-then-sleep (§2) makes every boot a pass, so auto-stop churn yields MORE passes, not fewer, and the floor machine's daily tick covers the quiet days. A persisted last-run marker would let the schedule survive restarts; it would not add a pass this design lacks. **Not fixed, by design; stays residual (1) in E1.**

### §8.4 R9 — adjacent notes, one line each, no entries

- **`STATE.md:3` is a single 75,918-byte line** (at `c590c77`) stacking three generations of header — four after this closeout; a ledger-slimming candidate under the 2026-08-27 founder ruling. Noted, not acted on.
- **Scanner paths return 200 on prod** (`/.git/config`, `/.svn/wc.db`, `//wp-includes/wlwmanifest.xml` in the log window): `curl` 2026-09-15 — all three return the SAME `text/html` body as `/`, **22,043 bytes**, i.e. the static-export SPA fallback, not a real file. Same class as the fly-233 static-serving note in the `[OTHER][P3 · caching]` entry (`HEAD /media/research-demo.mp4`, no `Cache-Control`). Recorded so it is not re-diagnosed.

### §8.5 What this closeout did NOT do

No code, no deploy (docs are not deployed by design — `/health` still reads `e12d3f0`), no DB access by Claude Code, no change to the 180-day constant, no persisted marker, no ruling on the daily-sweep-vs-「6 months」 reading (founder / counsel). `stash@{0}` untouched. `tests/probes/baton_check/check_baton.py` re-run on this baton and the sec-probe baton after editing — see §8.6.

### §8.6 Baton checker — before and after this closeout's edits

`tests/probes/baton_check/check_baton.py`, run 2026-09-16 on the HEAD (`c590c77`) copy and on the edited working copy of each baton. It never blocks; "not a unique anchor" means a back-ticked phrase matches more than one ledger line — informational, not a wrong fact.

| baton | HEAD copy | edited copy |
|---|---|---|
| this baton | DRIFTED 4 · ADVISORY 6 · VERIFIED 20 | DRIFTED 8 · ADVISORY 6 · VERIFIED 27 — the 4 new drifts are all non-unique-anchor notes on phrases this closeout quotes ("[COMPLIANCE][P2] retention automation", "NOT fixed, NOT rotated", "git log --all -- .env", "min_machines_running = 1"); 0 NOT IN REPO, 0 STALE |
| `recon_20260914_sec_probe.md` | DRIFTED 5 · ADVISORY 6 · VERIFIED 68 | DRIFTED 5 · ADVISORY 6 · VERIFIED 71 — no new drift |

The table describes the state before this §8.6 was appended; the final re-run after it is in the closeout commit's readback.
