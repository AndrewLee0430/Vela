# RECON 2026-08-25 — Payment-surface coverage ground truth

Read-only recon scoping the coverage-build car for the TECH_DEBT 2026-08-21
[OTHER][P2] filing "BOTH payment webhooks have ZERO executable coverage". No
product code, tests, TECH_DEBT, STATE, or nav counts were touched. Every count
below states its deriving command and its unit (CLAUDE.md Rule 25).

---

## §0 Repo assertion (Rule 24)

- `git rev-parse --show-toplevel` → `C:/Users/andre/projects/Vela`
- `git rev-parse HEAD` → `6864ea88bdd7f5e2d868e6290aeae7c39f18a918`
- `git ls-remote origin main` → `89caa063ddaad8cce51e29ec59b730562abf0b4c`
- `git log --oneline origin/main..HEAD` → exactly one commit, `6864ea8`
  (docs-only STATE annotation)

**Matches the briefed expectation exactly**: origin/main = `89caa06`, local
ahead by one docs-only commit. Every line number in this document is at HEAD
`6864ea8`; symbols are cited first because line numbers rot.

---

## §1 Surface map (derived at HEAD)

### 1.1 Handlers and their ranges

| Symbol | Route | Lines (HEAD) |
|---|---|---|
| `create_dodo_checkout` | POST `/api/checkout/dodo` | `api/server.py:1878-1949` |
| `lemonsqueezy_webhook` | POST `/api/webhooks/lemonsqueezy` | `api/server.py:1953-2026` |
| `dodo_webhook` | POST `/api/webhook/dodo` (singular — route asymmetry vs LS) | `api/server.py:2033-2181` |
| `user_status` | GET `/api/user/status` | `api/server.py:2330-2349` |
| `user_portal` | GET `/api/user/portal` | `api/server.py:2352-2365` |
| `cancel_subscription` | POST `/api/subscription/cancel` | `api/server.py:2368-2404` |

Command: `grep -n "dodo_webhook\|lemonsqueezy_webhook\|create_dodo_checkout\|cancel_subscription" api/` plus full read of `api/server.py:1870-2450`.

### 1.2 `plan_type` write sites — the full key set (Rule 23: plural by construction)

Command: `grep -n "usage\.plan_type = " api/server.py` → **5 assignment
statements** (unit: `usage.plan_type = …` statements inside the two webhook
handlers): `:2000` (LS→pro), `:2013` (LS cancelled/expired→free), `:2016`
(LS refunded→free), `:2161` (Dodo active→pro), `:2164` (Dodo
cancelled/expired/failed→free).

The wider set of sites that can put a value into `user_usage.plan_type`
(derived via `Grep plan_type\s*=` over `api/` + `UserUsage\(` repo-wide):

- Column default `"free"` — `api/models/sql_models.py:49`, applied at the three
  `UserUsage()` construction sites: `api/server.py:1994` (LS handler),
  `api/server.py:2149` (Dodo handler), `api/services/usage_service.py:48`.
- `scripts/deletion_dryrun.py:139` — constructor kwarg `plan_type="pro"` (script scaffold).
- `tests/run_golden_tests.py:396` — raw SQL `UPDATE user_usage SET plan_type='pro'` (test-user reset against a live `DATABASE_URL`).

`cancel_subscription` does **not** write `plan_type` — it PATCHes Dodo
(`status: cancelled`) and the downgrade arrives later via
`subscription.cancelled` on the webhook. `create_dodo_checkout` does not touch
`user_usage` at all.

### 1.3 Handler mechanics

**`lemonsqueezy_webhook`** (`api/server.py:1953`):
- **Signature**: header `X-Signature`; HMAC-SHA256 **hexdigest** of raw body
  with `LEMON_SQUEEZY_SIGNING_SECRET`; `hmac.compare_digest` (`:1962-1968`).
  500 if secret unset (`:1957`); 401 on mismatch (`:1969`). **No timestamp /
  replay protection.**
- **Identity**: `meta.custom_data.clerk_user_id`; missing → `{"status":
  "ignored"}` with **no WebhookEvent row written** (`:1978-1979`).
- **Idempotency**: read-then-write TOCTOU (see §3.5) on bare `event_id` =
  `meta.uuid` (`:1983-1987` SELECT, `:2023-2024` INSERT+commit).
- **Events branched** (no `handled_events` tuple): `subscription_created`
  →pro; `subscription_updated` → `current_period_end` only;
  `subscription_cancelled`/`subscription_expired` →free;
  `subscription_payment_refunded` →free; `subscription_payment_failed` →
  explicit grace-period no-op. **Any other event name is still recorded as
  processed and answered `{"status": "ok"}`.**

**`dodo_webhook`** (`api/server.py:2033`):
- **Signature**: Standard Webhooks. Headers `webhook-id` / `webhook-timestamp`
  / `webhook-signature` only (no `svix-*` fallback — that lives in the Clerk
  handler). 500 if `DODO_WEBHOOK_SECRET` unset (`:2041`); 401 missing headers
  (`:2047-2048`); 401 timestamp outside ±300 s or non-integer (`:2051-2056`);
  secret is `whsec_`-stripped and base64-decoded (`:2060-2061`); signed payload
  `{id}.{ts}.{body}` (`:2064`); HMAC-SHA256 **base64** (`:2067-2069`);
  space-separated `v1,<sig>` entries, `compare_digest` any (`:2072-2078`).
- **Event id**: `payload.data.id or payload.id`, else a **generated**
  `dodo_<uuid>` (`:2083-2085`) — a generated id makes idempotency vacuous for
  payloads carrying neither. Stored prefixed as `dodo_{event_id}`.
- **Idempotency**: read-then-write TOCTOU (`:2089-2091` SELECT, `:2179-2180`
  INSERT+commit).
- **`handled_events` tuple** (`:2094`): `subscription.active`, `.cancelled`,
  `.expired`, `.failed` — **all four are branched** (`:2160`, `:2163`); no
  tuple member is unbranched and no branch handles an event outside the tuple.
  Unhandled events are **recorded + committed** then answered `ignored`
  (`:2096-2098` — one of Rule 7's five baseline direct-commit debt sites).
- **Identity**: TEST_MODE (`api/server.py:318`, module-level) reads
  `clerk_user_id` from the payload; production path does an **awaited Clerk
  email lookup** (`:2126-2140`, timeout 10.0 s), 422 on no email / no user.
- **Plan flips**: `subscription.active` →pro (`:2161`);
  `cancelled`/`expired`/`failed` →free + `dodo_subscription_id` cleared,
  `dodo_customer_id` retained (`:2164-2165`). Audit-log row written
  (`:2171-2177`).

### 1.4 Frontend dual-source (derived, not trusted)

- `pages/_app.tsx:74,101` **still reads** `user.publicMetadata.plan` to derive
  the analytics tier (L1/L2).
- **Nothing in the repo writes `publicMetadata`** — repo-wide grep over
  `*.py/*.ts/*.tsx` returns only the two `_app.tsx` reads plus two `api/server.py`
  comments declaring it non-authoritative (G4, `:2414`, `:2435`).
- Six frontend sites consume `plan_type` from `/api/user/status`:
  `components/Navbar.tsx:89`, `components/PlanBadge.tsx:64`,
  `components/OnboardingOverlay.tsx:46`, `pages/history.tsx:80`,
  `pages/explain.tsx:295`, `pages/research.tsx:256`; `utils/analytics.ts:152-153`
  maps `traits.plan_type` → tier.
- **Precision on TECH_DEBT.md:1792's "that dual-source is LIVE"**: the live
  effect is analytics-only — a real pro user has `publicMetadata.plan`
  undefined, so `_app.tsx` identifies them as **L1** until a page-level
  `identify()` with backend `plan_type` corrects it. Backend entitlement is
  unaffected (G4 holds). The 2026-05-19 entry's proposed fix (drop the
  `publicMetadata.plan` read path) remains unimplemented.

---

## §2 Coverage census (derived)

### 2.1 Test-directory sweep

Command: `grep -rn --include=*.py "dodo\|lemonsqueezy\|plan_type\|subscription"
tests/ | grep -v __pycache__` (extensions: `.py` source only; `__pycache__`
excluded per Rule 21) → **exactly 1 hit**: `tests/run_golden_tests.py:396`, the
golden-runner's test-user plan reset. Zero hits for
dodo/lemonsqueezy/subscription. The filing's narrower pattern
(`dodo_webhook|lemonsqueezy_webhook|subscription.cancelled|subscription_cancelled|LEMON_SQUEEZY`)
returns nothing at HEAD — **the ZERO-executable-coverage claim stands**.

### 2.2 Test-file census

Command: `find tests -name "test_*.py" -not -path "*__pycache__*"` → **34
files** (unit: pytest-collectable `test_*.py`; `run_golden_tests.py` and
`scripts/smoke_webhook_cancel.py` fall outside the pattern by name).

Files that actually import `api.server` (each hit line read; Rule 21):
**4 of 34** —

| File | What it imports | DB handling |
|---|---|---|
| `tests/test_verify_tfda_payload.py` | symbols + `TestClient(server.app)` | env-before-import: `TEST_MODE=true`, `DATABASE_URL=sqlite:///:memory:`; tolerates missing tables (tested path is `_safe_db_write` fail-soft); no lifespan |
| `tests/test_verify_dailymed.py` | symbols + `TestClient(server.app)` | same env-before-import pattern (`:27`) |
| `tests/test_tfda_text_detector.py` | one helper function | sets `:memory:` (`:161`); no HTTP, no DB use |
| `tests/test_share_local_tombstone.py` | two Pydantic models only | no app execution |

`tests/models/test_user_profile.py:15` mentions `api.server` only to say it is
**deliberately not imported** (see §3.6). Adjacent patterns that are raw
material for the build car: per-test `create_engine("sqlite:///:memory:")` +
`Base.metadata.create_all` + sessionmaker fixture
(`tests/models/test_user_profile.py:74-80`); `TestClient` against a
**locally-built** FastAPI app (`tests/services/test_og_image.py:75-78`);
mock-session, DB-free-by-construction contract test
(`tests/test_deletion_coverage.py:25-26` — "lazy Engine; no connection is
opened").

### 2.3 `scripts/smoke_webhook_cancel.py` — shape and salvage value

Derived: **171 lines** (`wc -l`), **0 `assert` statements**
(`grep -c '^\s*assert '`), renamed out of the suite in `ca4bb7d`
(`git log --diff-filter=R`). Shape: module-level `pytest.skip` when
`TEST_USER_EMAIL`/`TEST_USER_ID`/`DODO_WEBHOOK_SECRET` unset (`:44-50`);
verdicts are prints; three `sys.exit(1)` at `:112`, `:142`, `:147`; the two
**plan-flip verifications — the actual business effect — only WARN/SKIP,
never fail** (`:126`, `:162`). Requires a live backend at `API_URL` with
`TEST_MODE=true` and a matching real webhook secret. Its docstring's example
`TEST_USER_ID` (`user_3B939…`) is a Clerk user TECH_DEBT.md:1793 records as
deleted (harmless under TEST_MODE payload bypass, but stale).

**Salvage assessment (no changes made)**: the reusable parts are
`sign_webhook()` (`:71-89` — a correct Standard Webhooks signer, byte-for-byte
the scheme the handler verifies) and `make_webhook_payload()` (`:53-68` — the
TEST_MODE-bypass payload shape), ~40 lines. The orchestration (live `requests`
against localhost) is exactly what a pytest strategy would replace with
`TestClient`, so converting the script in place would keep its live-backend
requirement and buy little. Extracting the two helpers into a pytest module and
writing fresh in-process tests costs about the same as the in-place conversion
and removes the live-backend and env-secret requirements. Its one
irreplaceable role today: it is the only artifact that exercises the **real
deployed** signature path end-to-end; a pytest suite replaces its logic
coverage, not its live-smoke role.

---

## §3 Constraints the build car must respect (reported, not decided)

1. **Import-time bindings.** `TEST_MODE` is a module constant
   (`api/server.py:318`) and the engine binds `DATABASE_URL` at import
   (`api/database/sql_db.py:8,14-29`; connections are lazy, creation is not).
   Env must be set before the **first** `import api.server` in the pytest
   process — and the existing verify-tests already do this with
   `sqlite:///:memory:` via `setdefault`, so **whichever test imports first
   wins for the whole process**. Alternatively `monkeypatch.setattr(server,
   "TEST_MODE", …)` flips the flag post-import.
2. **Secrets are read per-request**, not at import —
   `LEMON_SQUEEZY_SIGNING_SECRET` (`:1955`) and `DODO_WEBHOOK_SECRET` (`:2038`)
   via `os.getenv` inside the handlers — so `monkeypatch.setenv` with a
   test-generated `whsec_` secret works without re-import. Signature forging is
   already demonstrated in-repo (smoke script's `sign_webhook`).
3. **Both handlers commit directly** (`:2024`, `:2097`, `:2180`) — the Rule-7
   census records why `_safe_db_write` cannot express their semantics, and
   TECH_DEBT (TOCTOU entry) notes the eventual idempotency fix needs a narrow
   `except IntegrityError`. A test executing them end-to-end therefore needs
   **real tables** on whatever engine serves `get_db` — unlike the verify-tests,
   which tolerate missing tables because their writes are fail-soft. Concretely:
   `Base.metadata.create_all` on the serving engine, or a dependency override.
4. **DB fixture options visible in-repo** (founder-visible strategy choice —
   effort/risk ranked in §3.8, no recommendation):
   - **(i) `app.dependency_overrides[get_db]`** + per-test engine +
     `create_all` (pattern named in `test_user_profile.py`'s docstring; both
     handlers take `db: Session = Depends(get_db)` so the override reaches
     them). Caveat: SQLite `:memory:` is per-connection; a per-test engine
     needs a shared-connection arrangement (StaticPool or a temp **file** DB)
     so the handler's writes are visible to the test's readback session.
   - **(ii) process-global env `:memory:` engine** (`verify_tfda_payload`
     pattern) + `create_all` on `api.database.sql_db.engine`. Caveats:
     cross-test row bleed within a pytest process, and FastAPI runs sync
     dependencies in a threadpool — SQLite `:memory:` connection-pooling
     semantics across threads are exactly the kind of silent variable Rule 21
     warns about; needs one deliberate verification, not an assumption.
   - **(iii) real Postgres fixture** — no in-repo precedent, new env/service
     cost, highest fidelity to prod (`pg` IntegrityError + concurrency).
5. **TOCTOU window quantified (per brief; not fixed).** LS: SELECT
   (`:1983-1986`) → COMMIT (`:2024`) with **no awaits between** — the window is
   in-process CPU + DB round-trips, order of milliseconds. Dodo: SELECT
   (`:2089`) → COMMIT (`:2180`) spans, on the production path, an **awaited
   Clerk HTTP lookup with a 10.0 s timeout** (`:2126-2140`) — a window of
   hundreds of ms to ~10 s, network-bound, materially wider than LS. Neither
   handler catches `IntegrityError`, so a duplicate landing inside the window
   is a 500 (matches the TOCTOU filing; its line numbers have drifted, §4 row 6).
6. **Windows import hazard, unverified either way.**
   `tests/models/test_user_profile.py:15-18` records that importing
   `api.server` on Windows crashed on cp950 console encoding at
   `api/database/vector_store.py:52` — and that line is **still a `print` with
   a ✅ emoji at HEAD**, executed at import when the vector index file exists.
   Yet two suite files import `api.server` today and the 291-passing baseline
   includes them (pytest's capture typically absorbs the encode). The build car
   should verify `uv run pytest` on this machine imports cleanly **before**
   choosing a TestClient strategy, and treat fixing the `print` (also a Rule 4
   violation) as a separate, flagged item — not scope-creep into this car.
7. **Clerk-lookup path**: TEST_MODE payload bypass avoids Clerk HTTP entirely;
   covering the **production** identity path needs an httpx mock. Installed
   test deps (`requirements.txt`): `pytest==8.2.2`, `pytest-asyncio==0.23.7`,
   `httpx==0.27.0` — **no respx/responses**; mocking Clerk means either adding
   a dev dependency or monkeypatching `httpx.AsyncClient` (founder-visible
   tradeoff).
8. **Effort/risk ranking only** (low→high effort):
   1. Extract smoke helpers + TestClient + option (ii) global engine —
      least new machinery, inherits (ii)'s pooling/bleed caveats.
   2. Same but option (i) dependency override + temp-file SQLite — slightly
      more fixture code, cleanest isolation, sqlite-vs-postgres fidelity gap
      remains (IntegrityError class fires on both; concurrency semantics differ).
   3. Option (iii) Postgres fixture — highest fidelity (needed if the build car
      must pin TOCTOU behavior itself), highest env cost; TOCTOU coverage can
      also be explicitly declined instead.

### §3.9 C9 — does `webhook_events` support replay-idempotency tests locally?

**Yes.** `WebhookEvent` (`api/models/sql_models.py:81-86`): `event_id` is a
`String` **primary key** (plus `event_type`, `processed_at`) — derived from the
model, not BACKLOG. SQLite enforces the PK, so locally testable: sequential
replay of the same `event_id` → `already_processed` via the SELECT; a
concurrent duplicate → `IntegrityError` → 500 (current TOCTOU behavior).
Whether a test pins the current 500 or the desired `already_processed` is a
build-car decision tied to whether that car also fixes TOCTOU.

---

## §4 Count reconciliation (derived vs filed; unit stated)

| # | Claim (source) | Filed | Derived at HEAD (command) | Unit | Verdict |
|---|---|---|---|---|---|
| 1 | plan-flip assignment sites (payment filing) | "six assignment sites", listing 5 lines | **5**: `:2000,:2013,:2016,:2161,:2164` (`grep -n "usage\.plan_type = " api/server.py`) | `usage.plan_type = …` statements inside the two webhook handlers | **MISMATCH by 1 — the word "six" is the error; the filing's own 5-line list matches the derivation.** Candidate sixth under a wider unit: column default `sql_models.py:49`, or `scripts/deletion_dryrun.py:139` kwarg — neither is in the handlers |
| 2 | app-importing test files (mp4 entry, echoed by filing) | "4 of 24" | **4 of 34** (`find tests -name "test_*.py"` = 34; per-hit-verified import grep = 4) | pytest-collectable `test_*.py` files | numerator **matches**; denominator grew 24→34 since the 2026-08-15-era count |
| 3 | webhook grep in `tests/` returns nothing (filing) | 0 hits | 0 hits on the filing's pattern; 1 hit on a broader `plan_type` pattern (`run_golden_tests.py:396`, not webhook coverage) | grep hits in `tests/` `.py` source, `__pycache__` excluded | **matches** |
| 4 | smoke script shape (filing) | 171 lines, 0 asserts, `sys.exit(1)` at `:112/:142/:147`, 2 of 4 checks WARN/SKIP | 171 (`wc -l`), 0 (`grep -c '^\s*assert '`), same three lines, confirmed by read | lines / assert statements / exit sites | **matches exactly** |
| 5 | filing's uncovered-surface line refs (`dodo :2033`, LS `:1953`, sig/idempotency/flip lines) | as listed 2026-08-21 | every cited line re-read at HEAD and confirmed | line numbers in `api/server.py` | **matches** — no drift since filing |
| 6 | TOCTOU entry line refs (2026-08-17 entry) | `:1946, :2026, :1977-1981, :2017-2018, :2083-2085, :2173-2174` | now `:1953, :2033, :1983-1987/:2023-2024, :2089-2091/:2179-2180` | line numbers | **drifted by ~+7 lines**; symbols and mechanism remain correct — cite symbols |
| 7 | rename claim (filing) | `ca4bb7d` renamed `tests/test_webhook_cancel.py` → `scripts/smoke_webhook_cancel.py` | confirmed (`git log --diff-filter=R -- "*webhook_cancel*"`) | commit | **matches** |

**Ledger conflicts found: none that overturn a filing.** Row 1 is a word-level
count error inside an otherwise-accurate filing; row 2 is denominator staleness;
row 6 is ordinary line rot. Per the fresh-measurement-vs-ledger rule, the
corrections themselves belong to the build car, not this recon.

---

## §5 Observations for the build car (report-only; none acted on)

1. **Dodo `event_id` prefers `data.id` over top-level `id`** (`:2083`). If a
   real Dodo `subscription.cancelled` carries the **same `data.id`** as the
   earlier `subscription.active` (i.e. `data` is the subscription object), the
   cancellation is swallowed as `already_processed` — a silent
   cancelled-user-keeps-pro path, precisely the filing's "WHAT BREAKS"
   direction. The smoke script's `:140-142` FAIL branch exists to detect
   exactly this collision, and its payload factory avoids it with unique ids —
   so **no local artifact establishes real Dodo id semantics**. Ground truth is
   available read-only: prod `webhook_events.event_id` rows for the real
   subscriber. Worth settling before the coverage car pins payload fixtures.
2. **Cross-provider policy asymmetry**: LS `subscription_payment_failed` is a
   deliberate grace-period no-op (`:2018-2020`); Dodo `subscription.failed`
   downgrades immediately (`:2163-2164`). Also: Dodo never sets
   `current_period_end` (only LS does), and LS answers unknown events
   `"ok"` while Dodo answers `"ignored"` (both record). Tests will freeze
   whichever behavior they assert — worth a deliberate choice.
3. **Checkout metadata is not the production join key**:
   `create_dodo_checkout` sends `metadata.clerk_user_id` (`:1922`), but the
   webhook's production path joins by **customer email → Clerk lookup**
   (`:2124-2140`); only TEST_MODE reads a payload `clerk_user_id`. Email
   mismatch between Clerk and Dodo checkout is therefore a real 422 path.
4. **LS missing-`clerk_user_id` deliveries are acknowledged but never
   recorded** (`:1978-1979` returns before the WebhookEvent insert) — invisible
   to any later replay audit.
5. `pages/_app.tsx` analytics-tier read of `publicMetadata.plan` (§1.4): the
   2026-05-19 G4 fix (drop the read path) is still unimplemented; with a real
   paying user this now misclassifies their first identify as L1.
