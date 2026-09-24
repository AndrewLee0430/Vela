# PHI-BOUNDARY car — E2 · E3 · E4 (built 2026-09-23)

**Car tag:** `phi_boundary`. **Mode:** BUILD LOCAL — committed locally, **NOT pushed, NOT deployed**. Prod = fly 258 at
`9044d46502c9837376ffb7e438aa8cd5bd5c05d9`, unchanged.
**Base:** `2805f8c543a849fba7e85af893c031069e08fe9e` == origin/main (Rule 24 asserted: toplevel `C:/Users/andre/projects/Vela`).
**Line numbers** below are at `2805f8c` unless marked otherwise (commits B and C shift `api/server.py` below `:712` by +1 and
+13 respectively).

## §0 Founder rulings 2026-09-23 (verbatim)

- **R1** E2 = [COMPLIANCE][P2] CONFIRMED. Scope = ALL SIX raw Verify write sites derived at 2805f8c: ChatHistory.question :1470 / :1521 /
  :1653 AND AuditLog.query_content :1295 / :1429 / :1651 (the entry cited one AuditLog site; three derived — append a Rule 25
  correction bullet, old text kept).
- **R2** E3 = [COMPLIANCE][P2] CONFIRMED. `patient_context` joins the `_check_phi` input; a block returns the UNCHANGED
  `_phi_blocked_response` (phi_type is per-text, not per-field), so the frontend `phi_blocked` branch (pages/verify.tsx:235-250)
  needs no change.
- **R3** E4: CLAUDE.md Rule 1 COVERS route-level gates. `_check_phi` becomes FAIL-CLOSED. Class [OTHER] → [COMPLIANCE][P2]
  (RE-CLASSED, founder ruling). The blocking response MIRRORS the run_guards fail-closed precedent (guards.py:180-184 / :271-275,
  "Security check temporarily unavailable. Please try again.") in status AND body shape — no new user-visible string (Rule 16).
- **R4** azp: the Clerk instance is SOLE-TENANT to Vela (founder, 2026-09-23, Clerk dashboard: Vela is its own application; sela-dev /
  Arbor / SaaS are separate, unused legacy applications). Correction (3) is theoretical; [P2] STANDS. Record beside :2482. No azp
  code change in this car.

## §1 Baseline (at `2805f8c`)

pytest **458 passed / 28 skipped** · `npx tsc --noEmit` exit 0 · `npm run lint` **22 problems = 7 errors / 15 warnings**. All
three match the prompt's figures.

## §2 Commit A `09173e9` — E2: mask the six raw Verify write sites

**Anchor re-derive (Rule 25):** `grep -n "query_content=\|question=" api/server.py` → Verify raw sites **6** (unit = one
`question=` / `query_content=` expression): `ChatHistory.question` `:1470` (fallback success) · `:1521` (fallback failure) ·
`:1653` (main); `AuditLog.query_content` `:1295` (TFDA defer-ambiguous) · `:1429` (LLM fallback) · `:1651` (main). **6 = R1's 6:
MATCH.** The entry's 1 cited AuditLog site vs 3 derived: mismatch by 2, recorded as the R1 correction bullet.

**Diff:** exactly six one-line wraps `PHIDetector.sanitize_for_log(f"…")` — 6 insertions / 6 deletions in `api/server.py`.
f-string content unchanged. **Observation, not fixed:** `:1295` / `:1429` / `:1651` interpolate the Python list repr
(`['a', 'b']`); the mask reaches inside it (unit test below), the shape stays.

**Tests — `tests/test_verify_phi_mask.py` (6):** precondition (`detect("AB1234567") is None`, `sanitize_for_log` → `***`) · unit
twin (list-repr masked at all three AuditLog shapes) · main path (DB read-back of `question`; `query_content` via a
pass-through `_safe_db_write` spy) · fallback success (same) · fallback failure (`question`) · **defer path REACHED** via a
`tfda_lookup.resolve_brand` stub returning `ambiguous` (`query_content`). Harness `_run_verify` is imported, not copied; the
request body is overlaid by subclassing the `TestClient` the harness imports at call time. **RED at `2805f8c`: 4 endpoint tests
fail on the raw token; GREEN after.** CONTROL cited, not duplicated: `tests/test_verify_history_payload.py:233`
(`question == "Drugs: aspirin, warfarin"`) stays GREEN.

**Mutation 1/1:** `:1653` unwrapped (uncommitted) → `test_main_path_masks_question_and_audit` RED, the other 5 GREEN; restored
byte-identical — sha256-16 `4cd733e6b6d8e55f` before and after.

**Rule 19 checklist — what Research / Explain do AROUND the mask:**

| item on surface #1 | Verify | how |
|---|---|---|
| anonymous guard (`if not is_anonymous`) | CARRIED — already present at all six | unchanged |
| Explain's `[:500]` truncation (`:1762` / `:1768`) | **DECLINED** | `drugs` is bounded by schema: `max_length=10` (`api/models/schemas.py:182`) × `MAX_DRUG_NAME_CHARS = 100` (`:8`), enforced per item by the `@field_validator("drugs")` at `:197-209` |
| `_safe_db_write` labels | CARRIED — unchanged | diff shows no label edit |
| mask runs before `_safe_db_write` | CARRIED — same | the mask is evaluated in the constructor argument |

`tests/test_verify_write_ordering.py` (rindex anchors on `answer=_verify_history_payload` / `summary=summary`) GREEN after A.

## §3 Commit B `3f042e5` — E3: `patient_context` passes the PHI gate

`:1207-1208` → `verify_input = " ".join(body.drugs) + (f" {body.patient_context}" if body.patient_context else "")` is now
built ONCE at the gate and REUSED by `run_guards` (the former `:1239` line removed). **Byte-identical by construction** — the same
expression moved up; `body` is not reassigned in between. `drugs_text` had no other use (`grep -n "drugs_text\|verify_input"`
→ 2 lines each before the change).

**Tests — `tests/test_verify_patient_context_gate.py` (3):** precondition (`detect("0912345678")` not None — the first positive of
`tests/test_phi_taiwan_phone.py:24`) · blocked: 400, `type == "phi_blocked"`, `detail` + `suggestion` strings present, **0
ChatHistory rows, 0 AuditLog rows, credits unchanged** (`UserUsage.credits_used_today`, seeded 5, DB read) · CONTROL
`"65歲男性，糖尿病"` → 200, 1 row, charged +1. CONTROL 2 (`None`) = the harness default, cited `:233`. **RED at `09173e9`: the
blocked case returned 200 with a full analysis; GREEN after.**

**Rule 19 checklist — the drugs gate's behaviour carried to `patient_context`:**

| item | carried? | proof |
|---|---|---|
| response body `_phi_blocked_response(phi_type)` | CARRIED unchanged (R2) | test asserts the keys `pages/verify.tsx:235-245` reads: top-level `type` (the branch unwraps `detail` only if it is an object — here a string), `detail`, `suggestion` |
| gate runs BEFORE credits / quota / budget | CARRIED — same call site | test: credits unchanged |
| both tiers | CARRIED — gate precedes the tier split | not separately tested for anon |
| no rows on block | CARRIED | test: 0 / 0 |
| frontend change | NONE needed | `pages/` untouched — `git diff --stat 2805f8c..HEAD -- pages/` empty |

**Adjacent:** `pages/verify.tsx:230` always sends `patient_context: null`, so this surface is reachable only by a direct API
caller (the entry's mitigating fact still holds).

## §4 Commit C `298ab01` — E4: `_check_phi` fails CLOSED

**4a derived:** the Verify route converts a run_guards block at `:1240-1242` (at `3f042e5`) into
`JSONResponse(status_code=400, content={"detail": guard_error})`. In `pages/verify.tsx` the `res.status === 400` branch (`:235`)
computes `d = data` (detail is a string), `code = d.type ?? d.error` = undefined → neither `phi_blocked` nor
`invalid_fingerprint` → falls through 403/429/503/401 → `if (!res.ok) throw new Error("Server error (400)…")` (`:295`; the prompt's range `:251-293` ends two lines short). **So the
user sees the generic error, exactly as for a guard block today.** Research (`fetchEventSource`) and Explain rendering of this
400 were **NOT derived** (Rule 18).

**4b:** `except Exception:` → `logger.exception("PHI check failed; blocking request (fail-closed)")` → return
`JSONResponse(400, {"detail": "Security check temporarily unavailable. Please try again."})`. No `str(e)`. Callers (`grep -n
"_check_phi("`): **4** — feedback `:742` (inside `audit_middleware`), research `:808`, verify `:1209`, explain `:1723` (at
`3f042e5`) — all `if phi_resp: return phi_resp`. Feedback confirmed **ad hoc** (TestClient, detector patched → 400 + the same
body); not a committed test. The feedback gate runs only when `feedback_text` is non-empty.

**Tests — `tests/test_check_phi_fail_closed.py` (4):** (i) unit → non-None 400 with the precedent body · (ii) `/api/verify` → 400,
0 rows, credits unchanged, exception text absent from the body · (iii) `/api/research` → 400 before the stream (run_guards stubbed
to fail fast so the pre-fix run ends as a 200 SSE, not a network call) · (iv) CONTROL detector not patched → 200, 1 row, +1.
**RED at `3f042e5`: (i)–(iii); GREEN after. Mutation (except → `return None`, uncommitted): (i)–(iii) RED; restored
byte-identical — sha256-16 `900b37145e148de8` before and after.**

**Rule 19 checklist — the run_guards fail-closed precedent carried to `_check_phi`:**

| item | carried? |
|---|---|
| fixed string "Security check temporarily unavailable. Please try again." | CARRIED verbatim (`guards.py:184` / `:275`) |
| status + body shape | CARRIED — the Verify guard-block `400 {"detail": …}` |
| exception to the log only | CARRIED — `logger.exception` (stack trace; guards.py uses `logger.error` with `%s`) |
| new i18n string | NONE (Rule 16) |
| `_phi_blocked_response` (the entry's fix-path option) | DECLINED — a detector failure is not a PHI detection |

## §5 Ledger (commit D)

TECH_DEBT: E2 / E3 headings "— RATIFIED 2026-09-23 (founder ruling R1 / R2)"; E4 `[OTHER]` → `[COMPLIANCE]` with the
RE-CLASSED note appended; `#### [COMPLIANCE]` title list gains E4's row (12 of 12); ruling + STATUS bullets; R1 Rule 25
correction; R4 beside the azp OPEN FOUNDER QUESTION bullet. **NAV pre** (at `298ab01`) 0 + 11 + 18 + 61 + 102 = 192; `^- ` 229 =
192 + 37; [sec] loose 15 / strict 14 → **post** 0 + 12 + 18 + 61 + 101 = 192, delta 0; `^- ` 230 = 192 + 38 (+1 = the new E4
title row); [sec] 15 / 14 unchanged. Rule 27: no new entry. CLAUDE.md Rule 1 gains the scope clause (§5c) — **the founder
re-uploads CLAUDE.md to Project Knowledge from the committed file.**

**PRD:** `docs/PRD.md` §6.4 儲存策略 (`:2202`) states the storage and request-boundary rules these commits implement
(`:2222`, `:2227-2229`), so A / B / C carry `[PRD 6.4]`. **Drift flagged, not edited (PRD is outside this car's files):** `:2228`
still describes the Verify question as the plain `"Drugs: {drug1, drug2, ...}"` string — now masked.

## §6 Eye gate — ✅ GATE PASSED 4/4 — PUSHING (founder; localhost; `DATABASE_URL` = Dev) *(was: BLANK)*

| # | step | expected | result |
|---|---|---|---|
| 1 | UI `/verify`: warfarin + aspirin | normal result; a `/history` row as before, question "Drugs: warfarin, aspirin" || **PASS** |
| 2 | `POST /api/verify` with `patient_context` = a phone (e.g. `0912345678`) | 400, `type` = `phi_blocked`; no new `/history` row || **PASS** |
| 3 | `POST /api/verify` with `drugs` = `["AB1234567"]` | a result; the new `/history` row's question reads `Drugs: ***` || **PASS** |
| 4 | CONTROL: one Research query + one Explain run | both still run normally || **PASS** |

**Provenance (transcribed under the 2026-09-23 closeout authorization, zh-TW transcription precedent):** founder statement 2026-09-23 in the strategy conversation, blanket 「都pass」 — all four rows. Run on localhost at `c51f36e`, `TEST_MODE`, `DATABASE_URL` = Dev; rows 2–3 sent with `curl.exe` (not Invoke-RestMethod as the recipe named). No screenshots; no per-row readings transcribed. **STATUS: GATE PASSED 4/4 — PUSHING.**

## §7 Open after this car

- Push + deploy: pending founder authorization.
- The **PHI-at-rest (`ChatHistory.answer`) entry body** named in STATE item 4 is **NOT** in this car.
- Research / Explain frontend rendering of the fail-closed 400: not derived.
