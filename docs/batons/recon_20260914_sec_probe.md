# RECON — `[sec]` probe, 2026-09-14

**Read-only security probe of two TECH_DEBT candidates: Clerk JWT `authorized_parties` (azp), and
`ChatHistory.answer` stored unsanitized (PHI at rest).** Findings only. No product code changed, nothing
pushed, nothing deployed.

---

## §0 — REPO ASSERTION (Rule 24)

```
git rev-parse --show-toplevel   ->  C:/Users/andre/projects/Vela
git rev-parse HEAD              ->  9b24c19a8d0886ed4b45ee93b4e65a5471f56962
git status --short              ->  4 known untracked (.superpowers/ + 3 public/media/*.png), nothing else
git stash list                  ->  stash@{0}: On main: PHASE D partial work before crash  (PRE-EXISTING, untouched)
```

Every line number in this baton is **at `9b24c19`** unless stated otherwise. Prod at the time of the probe:
**fly 254 = `93d704c286c752cb56edcef80cc0131c9720be19`**, machine version 256 (v255 / v256 were
`LEMON_SQUEEZY` secrets-unset rolling releases, **not** rebuilds).

---

## §1 — SCOPE AND THE CONSTRAINTS IT RAN UNDER

Two candidates, both pre-existing TECH_DEBT entries:

1. `[OTHER][P2]` Clerk JWT `authorized_parties` (azp) claim 未驗證 — discovered 2026-04-22, **not re-read since**.
2. `[COMPLIANCE][P2 · R5 privacy]` `ChatHistory.answer` stored unsanitized — logged 2026-06-08, **re-pointed
   2026-08-11** by written legal counsel (ACCEPTED AS-IS, kept OPEN), sanitization **declined by founder ruling
   2026-09-01** when the HISTORY car's Verify change fired the entry's own named trigger.

For (2) the question was **not** "how bad is it". It was: **have any of the four acceptance grounds changed
since 2026-08-11, and has the cited site set drifted?**

### ⚠️ Read-only, and exactly how read-only

- **NO DATABASE ACCESS OF ANY KIND.** Not prod, not the Dev branch `ep-spring-voice-a127ye10`, not a `SELECT`,
  not a dry-run. Every number below is derived from **code and git history**.
- **ONE** external call in the whole probe: `fly secrets list` filtered to `CLERK`, returning **NAMES and
  DIGESTS only**. **No secret value was read, printed, grepped-for or written at any point.** No other `fly`
  call — no `releases`, no `logs`, no `ssh`.
- No prod HTTP request. No edits to any file under `api/` `pages/` `components/` `utils/` `styles/`.
- The mask-over-JSON measurement (§3) runs against **synthetic payloads built from the real helpers' shapes**,
  never against stored rows. See `tests/probes/phi_mask_over_json/README.md`.

### ⚠️ A PREMISE IN THE TASK BRIEF WAS WRONG — corrected here rather than inherited

The brief asserted that HISTORY-HONESTY **segment 2b ADDED a `ChatHistory` write** (the `failed_analysis` row),
and that the cited five-site set had therefore grown. **It did not.**
`docs/batons/history_honesty_car_20260903.md:454` rules the write policy as *"ONE `_safe_db_write` … branch the
status expression inside the EXISTING write … (no second write; the write-ordering guard's rindex anchor must
not move)"*, and the code at `:1585-1613` does exactly that — `status` is a local assigned above and passed into
the single site-C write. **The write-site count has been 5 throughout**, re-derived here as
`git grep -c "ChatHistory(" -- api/server.py` → **5**.

---

## §2 — CLERK azp

### 2.1 The decode sites — set closed

`git grep -n "jose_jwt\|jwt.decode\|jwks\|JWKS\|clerk" -- api/` then narrowed:
`git grep -c "jose_jwt.decode" -- api/server.py` → **2**. No other file under `api/` decodes a JWT, and no
second JWT library is called from repo code (PyJWT is present only transitively inside `fastapi_clerk_auth`,
which is never instantiated).

| # | site | function | on failure | reached by |
|---|---|---|---|---|
| 1 | `api/server.py:390-395` | `require_auth()` | raises **403** | `/api/history`, `/api/history/{id}`, `/api/share/*`, `/api/admin/costs`, billing, feedback — and the three feature routes via `require_auth_or_anonymous()` (`:405`) when a Bearer header is present |
| 2 | `api/server.py:1915-1917` | `_optional_user_id()` | returns **None** (anonymous) | `/api/bug-report` only |

### 2.2 ⭐ The rating-determining fact — THE JWKS ENDPOINT IS FIXED

`get_jwks()` (`api/server.py:353-360`), literal source line **`:357`**:

```python
r = await client.get(os.getenv("CLERK_JWKS_URL"))
```

**A deployed env var. NOT derived from the token's own `iss` / `kid` or any unverified claim.** The token's
claims are read only *after* the key set is fetched. A key set fetched from an endpoint the token itself names
is a different **class** of defect; this is **the benign class**, and that is what holds the entry at `[P2]`.

Refs repo-wide: `.env.example:57`, `README.md:159`, `README.md:300`, `docs/architecture.md:233`,
`api/server.py:357`.

### 2.3 Decode options, resolved against python-jose 3.3.0

`requirements.txt:15` pins `python-jose[cryptography]==3.3.0`; installed version confirmed `3.3.0`. Defaults live in the installed `python-jose` package under `venv` (module `jwt`, the `decode` defaults
dict), merged by `defaults.update(options)` — a site-packages path, deliberately not written as a repo path.

| option | effective | note |
|---|---|---|
| `verify_signature` | **True** | enforced |
| `algorithms` | **`["RS256"]`** | passed explicitly at both sites → `alg:none` / HS256 confusion blocked |
| `verify_exp` | True | but **`require_exp: False`** — **an `exp`-less token passes**. Clerk always sets `exp`, so LATENT |
| `verify_nbf` / `verify_iat` | True | `require_*: False` |
| `verify_aud` | **False** (explicit) | |
| `verify_iss` | True **but inert** | see 2.4 |
| `leeway` | **0** | never passed |

### 2.4 `iss` is read by NOTHING

`git grep -n "issuer=" -- api/` → **0 hits**. python-jose's `_validate_iss` (installed package) guards its whole body with
`if issuer is not None:`, so `verify_iss: True` is decorative without the kwarg. **「issuer 隱式信任」 is
understated: `iss` is not implicitly trusted, it is not read at all.**

`kid` is likewise not matched — the installed package's `_get_keys` returns `key["keys"]` wholesale and
`_sig_matches_keys` tries every key until one verifies. Not a vulnerability (the signature must still verify); it means a
rotated-but-still-published key stays usable.

### 2.5 Downstream — what an accepted `sub` gets

Traced `/api/research` (`api/server.py:749`) end to end:

`require_auth_or_anonymous` → `require_auth` → `get_user_id(creds)` returns **`creds.decoded["sub"]` verbatim**
(`:450`) → `check_credits()` (`api/services/usage_service.py:120`) → `get_or_create_usage()` →
`_resolve_usage(create=True)` → **`UserUsage(clerk_user_id=user_id)` created and committed**
(`usage_service.py:47-50`) with `plan_type` default **`"free"`** (`api/models/sql_models.py:48`), i.e.
`FREE_DAILY_LIMIT = 10` credits/day.

**No second check on any authed request path** — no Clerk API call, no pre-existence requirement.
`CLERK_SECRET_KEY` is used only in the Dodo webhook lookups (`:2113-2137`, `:2359-2372`), never on a request
path. The only gate that can reject a `sub` is the account-deletion freeze (`AccountDeleted`, 403), which by
construction applies only to a `sub` that already existed.

**So: a signature-valid token minted by the same Clerk instance for a DIFFERENT application decodes cleanly
here and auto-provisions a free account.**

### 2.6 `fastapi_clerk_auth` — the entry's third Resolution option does not solve the problem

- `grep -n "azp\|authorized_part"` over the installed `fastapi_clerk_auth/__init__.py` → **0 hits.**
- Its `ClerkConfig` defaults **`verify_iss: bool = False`** and **`verify_aud: bool = False`**.
- It would add `kid`-based selection via `PyJWKClient.get_signing_key_from_jwt(token)` against a **likewise
  fixed** `jwks_url`.
- 「import 未使用」 is **half right**: of the three names at `api/server.py:53`, `ClerkConfig` and
  `ClerkHTTPBearer` are unreferenced, but **`HTTPAuthorizationCredentials` is live** at `:369` and `:446`.
- Still pinned: `requirements.txt:14` → `fastapi-clerk-auth==0.0.9`.

### 2.7 Mitigations present, item by item

| mitigation | present? | note |
|---|---|---|
| CORS allowlist (Rule 6) | ✅ present, ❌ not a mitigation for this | `:310-319`, env-driven, never `["*"]`. Browser-enforced; does not touch a token replayed from curl |
| server-side Origin / Referer check | ❌ **absent** | `git grep -n "Referer\|referer" -- api/` → 0 hits |
| rate limiting | ⚠️ partial | `RATE_LIMITS` `:237-253`, **IP-keyed** (`key = f"{ip}:{path}"`, `:293`), in-process. **`/api/history` and `/api/share/create` are not in the table** |
| credit ceiling | ✅ | 10/day free — caps blast radius per accepted `sub` |
| admin second factor | ✅ | `/api/admin/costs` `:2750` also compares `ADMIN_USER_ID` |
| algorithm allowlist | ✅ | both sites |

### 2.8 JWKS failure behaviour — fail-CLOSED, by accident of a narrow `except`

`get_jwks()` has **no try/except and no `raise_for_status()`**. A transport failure, or an unset
`CLERK_JWKS_URL` (→ `client.get(None)`), propagates past `require_auth()`'s `except JWTError` (`:398`) as an
uncaught **500** — the request is blocked. Rule 1 satisfied in outcome.

⚠️ One poisoning path: a 200 response carrying non-key-set JSON is assigned to `_jwks_cache` at `:358`
**before any validation** and its timestamp stamped, so every authed user 403s for up to `_JWKS_TTL` = **6
hours** (`:351`). Loud, self-inflicted, long-lived. Recorded in the azp entry, not filed separately.

### 2.9 TEST_MODE

Bypass: `require_auth` returns `None` when `TEST_MODE` (`:378-379`); `get_user_id(None)` returns
`TEST_USER_ID` (`:448-449`). `_optional_user_id` has the same bypass at `:1907-1908`.

Production guard **exists** at **`api/server.py:325-327`**, the `raise` at **`:327`**:

```python
if TEST_MODE and os.getenv("FLY_APP_NAME"):
    raise RuntimeError("TEST_MODE cannot be enabled in production (FLY_APP_NAME detected)")
```

⚠️ The in-code comment at `api/server.py:271` says *"Production guard at module init (server.py:305-308)"* —
**stale**. Not fixed in the ledger commit (docs-only); filed to ride the next commit touching `server.py`.

### 2.10 Rating

**Fixed JWKS endpoint + RS256 allowlist ⇒ azp is defense-in-depth, `[P2]` STANDS.** The forgery scenario the
entry's 風險 line describes requires **Clerk's private signing key** — not the public JWKS and not the issuer
string, both of which are public by design.

**THE ONE FACT THAT WOULD MOVE IT, and it is not derivable from the repo:**
⚠️ **is this Clerk instance shared with another product?** Sole-tenant → 2.5 is theoretical. Shared → 2.5 is
reachable. Settled by a Clerk dashboard read.

**Fix cost:** 1 file, ~8-15 lines across 2 decode sites, **zero frontend change** (`git grep -n "getToken" --
pages/ components/ utils/` → 15 hits, **none templated**, so these are default Clerk session tokens). **A new
secret is required** — `fly secrets list` shows `CLERK_JWKS_URL`, `CLERK_SECRET_KEY`,
`NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_WEBHOOK_SECRET`; **`CLERK_AUTHORIZED_PARTIES` does not exist** →
`fly secrets set` + a rolling release. **Failure mode if the allowlist is wrong: every signed-in user 403s on
every authed route immediately** — loud in effect, **thin in signal**, since `logger.error("JWT decode error")`
(`:399`) fires only for `JWTError` and an azp rejection is not one.

---

## §3 — PHI AT REST

### 3.1 The five write sites, re-derived

`git grep -c "ChatHistory(" -- api/server.py` → **5**. Widening check (`git grep -n "ChatHistory" -- api/`)
finds no indirect constructor, factory or bulk insert. **Set closed at 5. Derived == the cited 5.**

| file:line | symbol | session_type | `question` | `answer` | `question` masked? | `answer` masked? |
|---|---|---|---|---|---|---|
| `:964` | `research_query` → `event_stream()` | `research` | `body.question` | `_research_history_payload(...)` | ✅ `:967` | ❌ |
| `:1421` | Verify no-label fallback, success | `verify` | `f"Drugs: …"` (`:1422`) | `_verify_history_payload(...)`, status `ok` | ❌ **raw** | ❌ |
| `:1472` | Verify fallback, exception path | `verify` | `f"Drugs: …"` (`:1473`) | …status `failed_no_data` | ❌ **raw** | ❌ |
| `:1604` | Verify main path (one `_safe_db_write` with `AuditLog`) | `verify` | `f"Drugs: …"` (`:1605`) | …status `ok` \| `failed_analysis` | ❌ **raw** | ❌ |
| `:1717` | `explain_report` → `event_stream()` | `explain` | `body.report_text[:500]` | `json.dumps(event["content"])` (`:1707`) | ✅ `:1720` | ❌ |

🔴 **The asymmetry counsel assessed holds at only 2 of 5.** `git grep -n "sanitize_for_log" -- api/` → **6 call
sites** (`:931`, `:967`, `:1714`, `:1720`, `:1876`, `:1943`) — **none is a Verify site**. Adjacent: the Verify
`AuditLog` at `:1603` writes `query_content` raw, where Research (`:931`) and Explain (`:1714`) mask it.
Filed as its own entry (§6 E2), **not folded in**.

### 3.2 What `answer` now holds — verified at HEAD, not repeated from 2026-06

| mode | serializer | can it echo an input identifier? |
|---|---|---|
| Research | `_research_history_payload` `:1087-1112` → `{kind, answer, citations, fallback}` | **YES** — `answer` is raw LLM markdown, unbounded |
| Verify | `_verify_history_payload` `:1114-1145`, all three sites | **YES, three ways** — `summary`; `interactions[].description` / `.clinical_recommendation` / `.mechanism`; and **`tfda_groundings[].query`, whose schema comment reads `# user-entered token, verbatim` (`api/models/schemas.py:242`) — a verbatim copy of user input** |
| Explain | inline `json.dumps` `:1707` → `{items, clinical_correlations, disclaimer}` (`api/services/explain_service.py:453-457`) | **YES** — `ExplainItem.term` / `.value` / `.explanation`; **no `[:500]` truncation on `answer`** |

Corrections to the entry's two 2026-06 claims: *"Verify stores drug-names-only"* is **true of `question`, false
of `answer`**. *"Explain stores `report_text[:500]` after the PHI gate"* is **true of `question` only**, and
stronger than stated (`sanitize_for_log` of the truncation — masked as well as gated).

### 3.3 🔴 THE MASK-OVER-JSON MEASUREMENT — the entry's own fix path is measured wrong

Probe committed at **`tests/probes/phi_mask_over_json/`** (script + `result.json` + README, commit `a98768e`).
Inputs are **synthetic payloads built from the real helpers' shapes; no database was read.**

```
=== research_v1 ===            bytes 1116 -> 1090 | changed=True  | PARSES OK
=== verify ===                 bytes  655 ->  655 | changed=False | PARSES OK
=== explain ===                bytes  273 ->  273 | changed=False | PARSES OK
=== HYPOTHETICAL_bare_int ===  bytes  103 ->   91 | changed=True
    JSON.parse WOULD FAIL: JSONDecodeError: Expecting value: line 1 column 71 (char 70)
negative control valid: True
```

1. **No structural break on today's shapes.** `***` is JSON-string-safe and no pattern's separator class
   (`[-\s]`) can span a `"` or `,`, so the only break is masking a **bare numeric literal** — and none of the
   three payloads has an 8+-digit bare number.
2. **But that is a property of TODAY'S SHAPES, not of the approach.** Add one integer field (a unix timestamp,
   an integer PMID, a row id) and `JSON.parse` throws; `parseResearchAnswer` / `parseVerifyAnswer`
   (`pages/history.tsx:101-113` / `:73-78`) hit `catch {} return null` and `/history` drops **silently** to the
   legacy pre-wrap path. The **negative control** is the case that proves the probe can fail.
3. **Where it parses, it silently destroys data.** `MEDICAL_RECORD_PATTERNS[1]` = `\b\d{8,12}\b`
   (`api/middleware/phi_handler.py:153`, the list at `:151-154`) masks 8-digit PMIDs and the `pubmed.ncbi.nlm.nih.gov` URLs holding
   them; `MEDICAL_RECORD_PATTERNS[0]` masks NCT ids. `/history` renders `PMID:***` and a dead link.
4. **And inconsistently** — a **7-digit PMID survives** while an 8-digit one is destroyed, because the floor
   is 8. Half a citation panel breaks per row, with nothing logged.

**Therefore the fix path splits into two operations the 2026-06 entry could not distinguish** (answers were
prose then, JSON now): **(a)** mask the JSON string (~5 lines, carries 1-4 above) vs **(b)** mask the free-text
fields before serialization (~10-20 lines, does not touch `citations` / `source_id` / `url`). Different costs,
different blast radius. **Disposition is the founder's.**

### 3.4 The four grounds, re-verified at `9b24c19`

**(1) INPUT-SIDE BLOCKING — CHANGED.** `_check_phi()` is at **`:664-674`**. Caller set closed:
`git grep -n "_check_phi(" -- api/` → 5 hits = def + **4 call sites** (`:694` feedback, `:760` research,
`:1160` verify, `:1675` explain). All three features pass through it, each gate preceding its writes in source
order with an unconditional early return. **Two gaps, both pre-dating 2026-08-11** — a record error, not a
change of fact: `patient_context` never reaches the gate (§6 E3), and the gate is fail-open (§6 E4).

**(2) 180-DAY RETENTION — CHANGED IN SUBSTANCE.** `_cleanup_old_records()` at **`:190-208`** (entry cited
`:183-197`). Cutoff `timedelta(days=180)` inline at `:195`, no named constant. Deletes `AuditLog` (`:199`) and
**`ChatHistory` (`:200`)**. Trigger: `asyncio.create_task(...)` in the lifespan (`:214`) — no cron, no
scheduler, no route. **It sleeps first** (`await asyncio.sleep(86400)`, `:194`), the timer is per-process with
no persisted marker, and a zero-delete pass is **completely silent** (log at `:202-204` guarded by
`if deleted_audit or deleted_chat:`). Code unchanged since 2026-08-11 — what is derived is that its
**execution was never established**. Filed as §6 E1 with its 2026-09-18 clock.

**(3) NON-PUBLIC STORAGE — UNCHANGED, re-confirmed.** Readers of `ChatHistory.answer`: `get_user_history()`
(`:2012-2037`, `Depends(require_auth)` + owner filter, `response_model=ChatHistoryEntry` which omits
`user_id`), `delete_history_entry()` (`:2048-2070`, delete only), `_cleanup_old_records` (delete only),
`deletion_service` (`:125` count / `:204` delete). `/api/admin/costs` (`:2750`) reads `ApiCostLog` + `UserUsage`
and never touches this table.

The 2026-08-11 share finding **re-confirmed at a new line**: `share_create()` is at **`:3276`** (entry cited
`:3022`, now the blog locale resolver) and stores `answer_text=body.answer_text` at **`:3411`** — from the
**client request**, into the separate `shared_query` table (`api/models/sql_models.py:126`). The public
renderers read `share.answer_text` / `page.answer_text` (`api/services/share_renderer.py:457`,
`api/services/explore_renderer.py:174`), **never `ChatHistory`.** ⚠️ One precision: the share gate at `:3291`
runs `PHIDetector.detect(body.query_text, …)` — **`query_text` only, not `answer_text`**. That is a fact about
the share surface, recorded, not re-rated here.

**⭐ The RULED segment 2 does NOT touch this ground.** `STATE.md` records transport ruled **(ii)** —
`/api/history` fills a `disclaimer` at READ time from `get_disclaimer(lang)` — and **NOT started**. Verified:
`ChatHistoryEntry` (`:1991-2010`) has no `disclaimer` field. When built as ruled it **adds no new reader of
`answer`** and the route is **authed and owner-filtered**. Stated rather than left implied.

**(4) OPERATOR-ONLY ACCESS — UNCHANGED.** No admin route reading this table; no export endpoint
(`git grep -n "@app.get\|@app.post\|@app.delete" -- api/server.py | grep -i "admin\|export\|dump"` → 1 hit,
`/api/admin/costs`); no `scripts/` dump (`git grep -ln "chat_history\|ChatHistory" -- scripts/` →
`deletion_dryrun.py` only, which **writes** a fixture row and reads none); **zero logging of the answer body**
(`git grep -n "logger\..*answer\b" -- api/` → 0 hits).

### 3.5 On the entry's own lapse clause — a question, not a legal reading

The clause names three triggers: *retention lengthened · answers surfaced publicly · broader access.*
**180 days has NOT been lengthened.** What is derived is that its **execution was never established**, which is
a different thing from a change, and **the clause's three examples do not cover it.** Whether a ground that was
never verified to execute trips the clause is **the founder's reading to make.** Grounds (3) and (4) are
UNCHANGED and are not in question.

---

## §4 — DERIVED vs CITED

| # | claim / citation | source | derived at `9b24c19` | verdict |
|---|---|---|---|---|
| 1 | toplevel `C:/Users/andre/projects/Vela` | brief | identical | **MATCH** |
| 2 | HEAD `9b24c19a…f56962` | brief | identical | **MATCH** |
| 3 | 4 untracked files | brief | exactly those 4 | **MATCH** |
| 4 | `stash@{0}` PHASE D | brief | present, untouched | **MATCH** |
| 5 | azp entry span "around `:1968`" | brief | `TECH_DEBT.md:1968-1976` | **MATCH** |
| 6 | "at least one cross-ref at ~`:2123`" | brief | **2** in TECH_DEBT (`:41`, `:2123`) + 1 in `STATE.md:758` | **DRIFT (undercount)** |
| 7 | JWT decode site count | none cited | **2** (`:390`, `:1915`) | n/a |
| 8 | "hand-rolled `jose_jwt.decode` with `verify_aud: False`" | TD azp 現況 | exact, both sites | **MATCH** |
| 9 | "issuer 隱式信任" | TD azp 現況 | stronger — `issuer=` never passed, `_validate_iss` a no-op, `iss` read by nothing | **MATCH in effect, UNDERSTATED** |
| 10 | "未檢查 `azp` claim" | TD azp 現況 | `git grep -n "azp" -- api/ pages/ components/ utils/` → **0** | **MATCH** |
| 11 | risk barrier = "Clerk 公開 JWKS + issuer" | TD azp 風險 | both public; barrier is the **private signing key** | **DRIFT (mis-stated barrier)** |
| 12 | `fastapi_clerk_auth` "import 未使用" | TD azp Resolution | **2 of 3** unused; `HTTPAuthorizationCredentials` live at `:369`, `:446` | **DRIFT (partial)** |
| 13 | that package's "完整驗證鏈" fixes azp | TD azp Resolution | **no `azp` anywhere**; `verify_iss` / `verify_aud` default **False** | **DRIFT (option ineffective)** |
| 14 | `CLERK_AUTHORIZED_PARTIES` is new | TD azp Resolution | not among the 4 `CLERK_*` names on Fly | **MATCH** |
| 15 | JWKS endpoint is fixed, `:357` | task prompt | exact | **MATCH** |
| 16 | `HTTPAuthorizationCredentials` at `:369`, `:446` | task prompt | exact | **MATCH** |
| 17 | `_check_phi` cited `:1088` → real `:664-674` | task prompt | `:1088` = `_research_history_payload` docstring | **STALE, as claimed — MATCH** |
| 18 | `_cleanup_old_records` cited `:183-197` → real `:190-208` | task prompt | `:183` = `db.rollback()`, `:197` = `db = SessionLocal()` | **STALE, as claimed — MATCH** |
| 19 | five writes cited `:928,1324,1366,1462,1570` → real `:964,1421,1472,1604,1717` | task prompt | exact; the five now land on an `AuditLog` field, a DailyMed assignment, `if correction_tasks:`, a `disclaimer=` kwarg, a blank line | **STALE, as claimed — MATCH** |
| 20 | share/create cited `:3022` → route `:3276`, `answer_text=` `:3411` | task prompt | exact; `:3022` = `return "zh-TW"` | **STALE, as claimed — MATCH** |
| 21 | TEST_MODE guard cited `:319-320` → real `:325-327`, raise `:327` | task prompt | exact | **STALE, as claimed — MATCH** |
| 22 | that citation is "in the prod test_user entry" | task prompt | **in TWO entries** — `:892` (test_user) **and `:888` (the pytest/Sentry entry)** | **DRIFT (second copy)** |
| 23 | **"EIGHT stale line citations"** | task prompt | **TWELVE** line references across **7 lines** in **3 entries** — the extra 4 are the second `:319-320` and `:432` / `:441-443` in the same sentence | **DRIFT (unit + undercount)** |
| 24 | `:432` / `:441-443` = TEST_USER_ID resolution | TD test_user entry | `:432` = `validate_fingerprint(fp_header)`; `:441-443` = the anonymous `raise HTTPException(403)`. Real: `:440`, `:448-449` | **STALE — NOT in the prompt's list** |
| 25 | in-code comment `:271` "guard at `:305-308`" | probe | guard at `:326-327` | **STALE (in-code, not fixed here)** |
| 26 | write-site count = **5** | TD entry | `git grep -c "ChatHistory(" -- api/server.py` → **5** | **MATCH** |
| 27 | segment 2b ADDED a write | task brief | **No** — `history_honesty_car_20260903.md:454` rules "no second write" | **DRIFT (premise wrong)** |
| 28 | asymmetry holds everywhere | TD entry ground | holds at Research + Explain; **all 3 Verify sites mask NEITHER** | **DRIFT — NEW FINDING (E2)** |
| 29 | "Verify stores drug-names-only" | TD entry (2026-06) | true of `question`, **false of `answer`** | **STALE** |
| 30 | "Explain stores `report_text[:500]` after the PHI gate" | TD entry (2026-06) | true of `question` only, and stronger (masked too); `answer` untruncated | **STALE (wrong column)** |
| 31 | retention covers `chat_history` | ground (2) | yes, `:200` | **MATCH** |
| 32 | retention constant 180 days | ground (2) | `timedelta(days=180)` inline `:195` | **MATCH** |
| 33 | retention "executes" | ground (2) | sleep-first, per-process, no marker, silent on zero-delete | **CHANGED in substance (E1)** |
| 34 | share flow does not read `ChatHistory` | TD entry | re-confirmed at `:3411` | **MATCH** |
| 35 | share `answer_text` "behind its own PHI gate" | TD entry | gate at `:3291` checks **`query_text` only** | **DRIFT (not this entry's scope)** |
| 36 | segment 2 touches ground (3) | task prompt | **No** — ruled (ii), NOT started, adds no reader, authed + owner-filtered | **MATCH (stated, not implied)** |
| 37 | TW-mobile gap fixed at `751705b` | TD | `TAIWAN_PHONE_PATTERN` `phi_handler.py:99` covers dashed/spaced/`+886` | **MATCH** |
| 38 | `_check_phi` caller set | Rule 23 | **4 call sites** + def = 5 grep hits | closed |
| 39 | `patient_context` passes `_check_phi` | implied by ground (1) | **NO** — gate sees `" ".join(body.drugs)` only | **NEW FINDING (E3)** |
| 40 | `_check_phi` fails closed | implied by ground (1) | **fail-OPEN** (`:672-674`) | **NEW FINDING (E4)** |
| 41 | E1 lines `:190-208` / `:214` / sleep / `:202-204` | task prompt | sleep at **`:194`**; all others exact | **MATCH** |
| 42 | E2 lines `:1421` / `:1472` / `:1604`, AuditLog `:1603`, mask `:931` / `:1714` | task prompt | exact; the `question=` f-strings are one line lower (`:1422` / `:1473` / `:1605`) | **MATCH (unit noted)** |
| 43 | E3 lines `:1160`, `:1390`, `:1509`, `verify.tsx:230` | task prompt | exact; `drugs_text` at `:1159` | **MATCH** |
| 44 | E4 lines `:672-674` | task prompt | exact | **MATCH** |
| 45 | NAV pre-check `0+8+18+60+99 = 185` | task prompt | identical; `grep -c "^- \["` = 185 | **MATCH** |
| 46 | NAV expected after = **189** (+4) | task prompt | derived `0+11+18+60+100 = 189`; cross-check 189 | **MATCH** |
| 47 | `[sec]` heading count expected **13** (1+8+4) | task prompt | derived **13** | **MATCH** |
| 48 | 8 OPEN + 2 [DONE] `[sec]` candidates | NAV 2026-09-11 | all 10 located: OPEN `:855`, `:891`, `:1178`, `:1198`, `:1285`, `:1968`, `:2108`, `:2222`; DONE `:844`, `:1171` | **MATCH** |
| 49 | the NAV's stated grep produced that list | NAV 2026-09-11 | grep of `credential\|secret\|auth\|token\|leak\|PHI\|webhook` over headings → 21 headings, and **#3 and #4 are NOT among them** | **DRIFT (method ≠ list)** |
| 50 | `2026-03-22 + 180d = 2026-09-18` | task prompt | computed: **2026-09-18** (4 days from 2026-09-14) | **MATCH** |
| 51 | Explain legacy set starts 2026-03-22 (Dev) | task prompt | `history_render_leftovers_car_20260911.md:216`, `:317` — set runs 2026-03-22 → 2026-04-20, **prod count never read** | **MATCH** |
| 52 | Dev branch cut from prod 2026-06-05 | task prompt | `docs/archive/state_shipped_2026.md:126` (v172) | **MATCH** |
| 53 | `/privacy` §4 carries the public promise | task prompt | `pages/privacy.tsx:46` — *"Data is automatically deleted after 6 months."* | **MATCH** |
| 54 | prod = fly 254 = `93d704c`, machine 256 | task prompt | as recorded in `STATE.md`; **not re-verified — no `fly` call made beyond `secrets list`** | **CARRIED, not verified** |

---

## §5 — COULD NOT DETERMINE READ-ONLY

| # | open question | what would settle it |
|---|---|---|
| 1 | **Has `_cleanup_old_records` ever completed a pass on prod?** The single most load-bearing unknown — ground (2) of four. | Prod log search for `"Data cleanup: deleted"` — ⚠️ **but a zero-delete pass logs nothing, so absence proves nothing** — **and** a founder-side `SELECT min(created_at) FROM chat_history` on the **prod** branch. The `SELECT` is the real question. |
| 2 | **Is this Clerk instance shared with another product?** The azp rating's hinge (§2.5, §2.10). | Clerk dashboard read. |
| 3 | **Do the tokens actually carry `azp`?** `getToken()` is untemplated, so these are default session tokens, but the claim set is Clerk's. | Clerk dashboard, or one decoded live token (header/claims only). |
| 4 | **Is anything enforced Clerk-side** — allowed origins, satellite domains, instance restrictions? | Clerk dashboard. |
| 5 | **The live value of `ALLOWED_ORIGINS` on prod.** How much the CORS allowlist actually constrains browser callers. | A config read beyond the one permitted names-only call, or a founder fact. |
| 6 | **Does any stored `answer` currently contain an identifier?** The entry is about theoretical echo; nobody has measured it. | A DB `SELECT` with the `PHIDetector` patterns applied — itself an operator-access event worth ruling on first. |
| 7 | **Deploy cadence vs the 24 h sleep** — how often the process actually restarted. | `fly releases` timestamps; not called (the one permitted `fly` call was spent on `secrets list`). |
| 8 | **Has `patient_context` ever been populated in production?** The shipped UI sends `null`; a direct API caller could send anything. | A DB read, or prod request logs. |
| 9 | **Was the 2026-08-11 counsel opinion written from the code or from the entry?** Bears on whether ground (2) was ever independently checked. | The written opinion — a founder-held document. |

---

## §6 — THE FOUR NEW ENTRIES AS FILED

All four carry **Class / P PROPOSED 2026-09-14 by derivation; founder ratification pending** — the posture the
`LEMON_SQUEEZY` entry used when it filed `[OTHER][P1]` with the class DISPUTED in its heading.

| id | filed as | one line | why that class / P |
|---|---|---|---|
| **E1** | `[sec][COMPLIANCE][P1]` | the 180-day retention task cannot be shown ever to have run | `[COMPLIANCE]` against this file's own definition — a published retention promise (`pages/privacy.tsx:46`) backed by a mechanism whose execution is unestablished. **`[P1]` because it is the only item in this batch with a DATE: 2026-09-18** |
| **E2** | `[sec][COMPLIANCE][P2]` | the masked/unmasked asymmetry holds at only 2 of 5 sites; all three Verify sites mask NEITHER field | widens an accepted asymmetry rather than opening a new surface; `/api/history` stays authed + owner-filtered |
| **E3** | `[sec][COMPLIANCE][P2]` | `VerifyRequest.patient_context` never reaches `_check_phi` | a gap in the input-side blocking ground itself; **`[P2]` not higher because `pages/verify.tsx:230` sends `null`** — reachable only by a direct API caller |
| **E4** | `[sec][OTHER][P2]` | `_check_phi` is fail-open | ⚠️ **Rule 1 tension FLAGGED, NOT asserted as a violation** — `_check_phi` is not in the `run_guards` chain Rule 1 names. `[OTHER]` reflects that undecided scope; if the founder rules Rule 1 covers it, `[COMPLIANCE]` is likelier |

**Also recorded, deliberately NOT filed as a fifth entry** (so this batch stays at four): `pages/privacy.tsx:30`
tells signed-in users that query and answer content are *"de-identified (via PHI masking as a primary
safeguard)"*, while at the three Verify sites neither column is masked and `answer` is masked nowhere in any
mode. Whether that is a `[HONESTY]` item in its own right is the founder's call. Noted inside E2.

---

## §7 — WHAT THIS PROBE DID NOT DO

No product code changed (zero diff under `api/` `pages/` `components/` `utils/` `styles/`, comments included).
Nothing pushed, nothing deployed, no migration, no DB access, no secret value read. **No recommendation on
sequencing, and no disposition proposed for either probed entry** — this baton produces facts; the rulings are
the founder's.
