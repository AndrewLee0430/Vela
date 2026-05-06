"""PRD § 4.5 PHASE B Step 8 — backend smoke test driver.

Cases 8a-8i (backend). 8j-8m are UI-only and must be exercised in
the browser; this script reports them as SKIPPED.

Runs in-process via FastAPI TestClient against a temporary SQLite
DB so we don't pollute the production Neon DB with 50 quota rows.
TEST_MODE=true is required so Clerk JWT validation is bypassed.

Usage:
    set DATABASE_URL=sqlite:///./tmp_share_smoke.db
    set TEST_MODE=true
    set SHARE_CREATED_BY_SALT=smoke_salt_v1
    python scripts/smoke_share_phase_b.py
"""
from __future__ import annotations

import os
import sys
import json
import pathlib

# Make the repo root importable when running as `python scripts/...`.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

# Force a temp sqlite DB BEFORE importing the app
os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///./tmp_share_smoke.db")
os.environ.setdefault("SHARE_CREATED_BY_SALT", "smoke_salt_v1")
os.environ.setdefault("VELA_PUBLIC_BASE_URL", "https://vela.an-tho.com")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# Reset the temp DB each run for determinism
db_path = pathlib.Path("tmp_share_smoke.db")
if db_path.exists():
    db_path.unlink()

# Reset OG output dir for the run
import shutil
og_dir = pathlib.Path("static/og")
if og_dir.exists():
    for f in og_dir.glob("*.png"):
        try:
            f.unlink()
        except OSError:
            pass

from fastapi.testclient import TestClient  # noqa: E402
from api.server import app  # noqa: E402
from api.database.sql_db import Base, engine  # noqa: E402

# TestClient does not always run the lifespan handler in older
# httpx versions. Initialize the schema explicitly.
Base.metadata.create_all(bind=engine)

client = TestClient(app)
RESULTS: list[tuple[str, str, str]] = []


def case(name: str, status: str, detail: str = "") -> None:
    RESULTS.append((name, status, detail))
    print(f"[{status:5}] {name}: {detail}")


# ── 8a: TEST_MODE bypasses Clerk auth, so true 'anonymous=403' can't be
# observed in TestClient. Document and skip.
case(
    "8a (anon → 403)",
    "SKIP",
    "TEST_MODE bypasses Clerk auth (require_auth returns None → falls back to TEST_USER_ID). "
    "Cannot exercise the anonymous-blocked path in TestClient. "
    "Verified by inspection: require_auth raises HTTPException(403) when not TEST_MODE and no Bearer header.",
)

# 8b: clean query → 201
clean_body = {
    "query_id": "qid-clean-1",
    "query_text": "Is metformin first-line for type 2 diabetes?",
    "answer_text": "Metformin remains first-line therapy for most patients with T2DM...",
    "citations": [{"title": "ADA 2025 Standards of Care", "url": "https://example.com/ada"}],
    "locale": "en",
}
r = client.post("/api/share/create", json=clean_body)
if r.status_code == 201 and r.json().get("created") is True:
    sid_8b = r.json()["share_id"]
    og_path = pathlib.Path(f"static/og/{sid_8b}.png")
    case("8b (clean → 201)", "PASS", f"share_id={sid_8b} og_exists={og_path.exists()}")
else:
    case("8b (clean → 201)", "FAIL", f"status={r.status_code} body={r.text[:200]}")
    sys.exit(1)

# 8c: same query_id, same user → 200 created:false
r = client.post("/api/share/create", json=clean_body)
if r.status_code == 200 and r.json().get("created") is False and r.json().get("share_id") == sid_8b:
    case("8c (idempotent → 200)", "PASS", f"same share_id={sid_8b}")
else:
    case("8c (idempotent → 200)", "FAIL", f"status={r.status_code} body={r.text[:200]}")

# 8d: TW NHI 12-digit (keyword-anchored) → 422
r = client.post("/api/share/create", json={
    "query_id": "qid-nhi-1",
    "query_text": "健保號 123456789012, metformin 適合嗎",
    "answer_text": "...",
    "citations": [],
    "locale": "zh-TW",
})
if r.status_code == 422 and r.json().get("type") == "share_sensitive_blocked" and r.json().get("reasons"):
    case("8d (NHI 健保 → 422)", "PASS", f"reasons={r.json()['reasons']}")
else:
    case("8d (NHI 健保 → 422)", "FAIL", f"status={r.status_code} body={r.text[:200]}")

# 8e: zh-TW name+age → 422
r = client.post("/api/share/create", json={
    "query_id": "qid-name-age-1",
    "query_text": "王小明 65 歲 metformin 適合嗎",
    "answer_text": "...",
    "citations": [],
    "locale": "zh-TW",
})
if r.status_code == 422 and r.json().get("type") == "share_sensitive_blocked":
    case("8e (zh-TW name+age → 422)", "PASS", f"reasons={r.json()['reasons']}")
else:
    case("8e (zh-TW name+age → 422)", "FAIL", f"status={r.status_code} body={r.text[:200]}")

# 8f: 51 unique queries → 51st returns 429
print("\n  [8f] inserting 49 more unique queries to fill quota (50 total)...")
for i in range(2, 51):  # i=2..50 → fills slots after 8b
    rr = client.post("/api/share/create", json={
        "query_id": f"qid-bulk-{i}",
        "query_text": f"Bulk test query number {i} about metformin and diabetes management.",
        "answer_text": "Standard answer text.",
        "citations": [],
        "locale": "en",
    })
    if rr.status_code != 201:
        case("8f (51st → 429)", "FAIL", f"unexpected status at i={i}: {rr.status_code} {rr.text[:120]}")
        break
else:
    rr = client.post("/api/share/create", json={
        "query_id": "qid-bulk-51",
        "query_text": "Quota-busting query.",
        "answer_text": "...",
        "citations": [],
        "locale": "en",
    })
    if rr.status_code == 429 and rr.json().get("type") == "share_daily_limit" and rr.json().get("limit") == 50:
        case(
            "8f (51st → 429)",
            "PASS",
            f"limit={rr.json()['limit']} retry_after={rr.json().get('retry_after_seconds')}",
        )
    else:
        case("8f (51st → 429)", "FAIL", f"status={rr.status_code} body={rr.text[:200]}")

# 8g: revoke as wrong user — simulate by switching TEST_USER_ID env var
# (require_auth uses get_user_id which reads TEST_USER_ID at request time)
prev_user = os.environ.get("TEST_USER_ID", "test_user")
os.environ["TEST_USER_ID"] = "other_user_for_8g"
r = client.post(f"/api/share/{sid_8b}/revoke")
if r.status_code == 403 and r.json().get("type") == "share_not_owner":
    case("8g (wrong user revoke → 403)", "PASS", "share_not_owner")
else:
    case("8g (wrong user revoke → 403)", "FAIL", f"status={r.status_code} body={r.text[:200]}")
os.environ["TEST_USER_ID"] = prev_user

# 8h: revoke as owner → 200, public page returns revoked notice
r = client.post(f"/api/share/{sid_8b}/revoke")
if r.status_code == 200 and r.json().get("is_public") is False:
    rr = client.get(f"/q/{sid_8b}")
    revoked_visible = rr.status_code == 200 and "revoked" in rr.text.lower()
    case("8h (owner revoke → 200)", "PASS" if revoked_visible else "FAIL",
         f"public page revoked_visible={revoked_visible}")
else:
    case("8h (owner revoke → 200)", "FAIL", f"status={r.status_code} body={r.text[:200]}")

# 8i: GET /api/share/list contains 8b's share_id (revoked but still listed)
r = client.get("/api/share/list")
if r.status_code == 200:
    ids = [s["share_id"] for s in r.json().get("shares", [])]
    if sid_8b in ids:
        case("8i (list)", "PASS", f"count={len(ids)} contains_8b=True")
    else:
        case("8i (list)", "FAIL", f"sid_8b={sid_8b} not in {ids[:5]}...")
else:
    case("8i (list)", "FAIL", f"status={r.status_code} body={r.text[:200]}")

# track-visit smoke (sanity check the new endpoint)
r = client.post("/api/share/track-visit", json={
    "share_id": sid_8b,
    "referrer_domain": "example.com",
    "is_first_view": True,
})
if r.status_code == 204:
    case("track-visit 204", "PASS", "logged")
else:
    case("track-visit 204", "FAIL", f"status={r.status_code} body={r.text[:200]}")

# 8j-8m frontend
for label in (
    "8j (Research page Share button → modal opens)",
    "8k (Anonymous Share click → AnonymousUpgradeCTA / sign-up)",
    "8l (public /q/{id} → track-visit POST + localStorage)",
    "8m ('Try it on Vela' → /?from_share strip → share_to_query_clicked)",
):
    case(label, "MANUAL", "browser-only verification required")

# Print summary table
print("\n=== SMOKE TEST SUMMARY ===")
pass_count = sum(1 for _, s, _ in RESULTS if s == "PASS")
fail_count = sum(1 for _, s, _ in RESULTS if s == "FAIL")
skip_count = sum(1 for _, s, _ in RESULTS if s in ("SKIP", "MANUAL"))
print(f"PASS: {pass_count}  FAIL: {fail_count}  SKIP/MANUAL: {skip_count}")
sys.exit(0 if fail_count == 0 else 1)
