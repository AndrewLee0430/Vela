# RETENTION EXECUTION CAR — opened 2026-09-14

**Segment 1 (E1) BUILT LOCAL. NOT pushed, NOT deployed.** Prod is unchanged at **fly 254 =
`93d704c286c752cb56edcef80cc0131c9720be19`**, machine version 256 *(carried from `STATE.md`; no `fly` call was
made in this task)*.

| segment | item | status |
|---|---|---|
| **1** | **E1** — `[sec][COMPLIANCE][P1]` the 180-day retention task cannot be shown to have ever run | **🔧 BUILT LOCAL 2026-09-14** — run-then-sleep + unconditional log + `_cleanup_pass()` extraction; gate §6 written BLANK |
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
| **1** | LOCAL | **⚠️⚠️ FIRST, BEFORE STARTING ANYTHING: confirm `DATABASE_URL` in your local `.env` points at the DEV branch (`ep-spring-voice-a127ye10`), NOT prod. Print it and read it. THIS TASK ISSUES `DELETE` STATEMENTS AT BOOT — this is the one row on this form where getting the branch wrong destroys production data, and it now fires within seconds of startup instead of 24 h later.** Then: `TEST_MODE=true uvicorn api.server:app --reload --port 8000` | the `Data cleanup pass: deleted N audit logs, M chat history records older than 180 days (cutoff=… UTC)` INFO line appears in the terminal **within seconds of boot**, not 24 h later, carrying **both counts and the cutoff** | |
| **2** | LOCAL | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health` immediately after boot | **200** — startup is not blocked by the sweep | |
| **3** | LOCAL | stop the server, start it again | the same INFO line appears **again**, proving per-boot execution rather than a one-off | |
| **4** | MACHINE | pytest count; T1/T2 RED-then-GREEN evidence pasted; mutation table | **442 → 447**; RED = 5 failed on `AttributeError`, M1 = T1 assertion failure, GREEN = 5 passed; **5/5 mutations caught** | |
| **5** | POST-DEPLOY *(founder, after authorization)* | `fly logs` at boot | the cleanup line present on **BOTH** machines | |
| **6** | POST-DEPLOY *(founder)* | re-run the two prod `SELECT`s **after 2026-09-15 02:43 UTC**; record whether `min(created_at)` has moved past the 180-day line | `min` has advanced. ⚠️ **The sweep is daily, so a row can persist UP TO 24 h past its 180-day mark — `min` lagging the line by less than a day is EXPECTED, not a failure.** A lag of more than ~25 h is the failure signal | |

---

## §7 — WHAT THIS BUILD DID NOT DO

Not pushed, not deployed, no `fly` call of any kind, no DB access of any kind by Claude Code. The gate above is
**blank**. Prod remains **fly 254 = `93d704c`**, machine version 256. Rows 1-4 are the founder's to fill before
push/deploy authorization is considered; rows 5-6 come after.
