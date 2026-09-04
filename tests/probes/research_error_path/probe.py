# -*- coding: utf-8 -*-
"""HISTORY HONESTY car segment 2 — §4 gate probe for the MACHINE-READABLE facts.

Drives a LOCAL backend (TEST_MODE, port 8010, the dev DB from `.env`) through
the four §4 rows that have DB / log facts and writes every reading to
result.json next to this file. The founder still eyes the VISUAL rows; this
probe never fills a PASS/FAIL cell.

  A. good model (default env)
     1. c0 = user_usage.credits_used_today for the TEST_MODE user
     2. POST /api/research "metformin renal dosing" → newest chat_history row:
        kind / fallback (expect False) / len(citations); credits c1 (expect c0+3)
     3. POST a nonsense drug until the SSE stream carries type:'fallback' →
        newest row fallback (expect True); which query did it is recorded
  B. bad model — BOTH GENERATOR_MODEL and GENERATOR_FALLBACK_MODEL set to a
     non-existent model. recon_20260901 §10 row 10 set only GENERATOR_MODEL;
     that is not enough for row 4 because the ANON path runs on
     `generator._fallback_model` (api/server.py `model_override`), so an anon
     request would have succeeded on gpt-4.1-mini instead of erroring.
     4. c2 = credits, n2 = chat_history rows for the user
     5. authed POST "warfarin bleeding risk" → SSE error then done; c3 == c2;
        n3 == n2; the server log line `… anon=False …` captured verbatim
     6. the same POST with an X-Anon-Fingerprint header (the L0 path —
        api/server.py require_auth_or_anonymous) → error then done; the
        anonymous_usage row for the derived anon_id unchanged; log line
        `… anon=True …`; rows unchanged
  C. server stopped, port 8010 free again.

Run (repo root, cp950 console needs the UTF-8 flag):
    PYTHONUTF8=1 python tests/probes/research_error_path/probe.py
Server logs go to tests/results/ (gitignored); the lines that matter are
copied into result.json.
"""
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

# BEFORE any api.* import: api/database/sql_db.py reads DATABASE_URL at import
# time and silently falls back to SQLite when it is unset.
load_dotenv(ROOT / ".env", override=False)

import requests  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from api.services.anonymous_identity import derive_anon_id  # noqa: E402

PORT = 8010
BASE = f"http://127.0.0.1:{PORT}"
USER = os.getenv("TEST_USER_ID", "test_user")
ANON_FP = "seg2-probe-fingerprint-0001"          # 16-128 chars, URL-safe base64 alphabet
ANON_CLIENT_IP = "127.0.0.1"                     # request.client.host for a loopback call
BAD_MODEL = "gpt-does-not-exist"
CREDIT_COST_RESEARCH = 3
HERE = Path(__file__).resolve().parent
RESULT = HERE / "result.json"
LOG_DIR = ROOT / "tests" / "results"
LOG_DIR.mkdir(parents=True, exist_ok=True)

GOOD_QUERY = "metformin renal dosing"
NONSENSE_CANDIDATES = [
    "zorblaxin 500mg dosing",
    "zorblaxitide 40 mg dosing in renal impairment",
    "recommended adult dose of fluxomab",
]
ERROR_QUERY = "warfarin bleeding risk"

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL or DATABASE_URL.startswith("sqlite"):
    raise SystemExit("DATABASE_URL missing or SQLite — the silent-SQLite trap; load .env first")
engine = create_engine(DATABASE_URL)


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ── DB readings ──────────────────────────────────────────────────────────────

def credits():
    with engine.connect() as c:
        row = c.execute(text(
            "SELECT credits_used_today, last_daily_reset, plan_type FROM user_usage "
            "WHERE clerk_user_id = :u"), {"u": USER}).first()
    return {"credits_used_today": row[0], "last_daily_reset": str(row[1]), "plan_type": row[2]} if row else None


def newest_row():
    with engine.connect() as c:
        row = c.execute(text(
            "SELECT id, question, answer, created_at FROM chat_history "
            "WHERE user_id = :u AND session_type = 'research' ORDER BY id DESC LIMIT 1"),
            {"u": USER}).first()
    if not row:
        return None
    out = {"id": row[0], "question": row[1], "created_at": str(row[3]), "answer_chars": len(row[2] or "")}
    try:
        p = json.loads(row[2])
        out.update({
            "kind": p.get("kind"),
            "fallback": p.get("fallback", "<absent>"),
            "citations_len": len(p.get("citations", [])) if isinstance(p.get("citations"), list) else None,
            "keys": sorted(p.keys()),
            "answer_markdown_chars": len(p.get("answer", "")) if isinstance(p.get("answer"), str) else None,
        })
    except (TypeError, ValueError):
        out.update({"kind": "<not JSON>", "fallback": "<not JSON>", "citations_len": None})
    return out


def row_counts():
    with engine.connect() as c:
        total = c.execute(text("SELECT count(*) FROM chat_history WHERE user_id = :u"), {"u": USER}).scalar()
        research = c.execute(text(
            "SELECT count(*) FROM chat_history WHERE user_id = :u AND session_type = 'research'"),
            {"u": USER}).scalar()
        max_id = c.execute(text("SELECT max(id) FROM chat_history")).scalar()
    return {"all_sessions": total, "research": research, "max_id_any_user": max_id}


def anon_rows():
    with engine.connect() as c:
        rows = c.execute(text(
            "SELECT anon_id, credits_used_today, last_reset_date, last_active_at FROM anonymous_usage")).all()
    return {r[0]: {"credits_used_today": r[1], "last_reset_date": str(r[2]), "last_active_at": str(r[3])}
            for r in rows}


# ── server control ───────────────────────────────────────────────────────────

def port_in_use():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def start_server(label, extra_env):
    if port_in_use():
        raise SystemExit(f"port {PORT} already in use — refusing to start server {label}")
    env = os.environ.copy()
    env.update({"TEST_MODE": "true", "PYTHONUTF8": "1"})
    env.update(extra_env)
    log_path = LOG_DIR / f"research_error_path_server_{label}.log"
    log_fh = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.server:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(ROOT), env=env, stdout=log_fh, stderr=subprocess.STDOUT,
    )
    deadline = time.time() + 240
    health = None
    while time.time() < deadline:
        if proc.poll() is not None:
            log_fh.close()
            raise SystemExit(f"server {label} exited early (code {proc.returncode}) — see {log_path}")
        try:
            r = requests.get(BASE + "/health", timeout=3)
            if r.status_code == 200:
                health = r.json()
                break
        except requests.RequestException:
            pass
        time.sleep(1.5)
    if health is None:
        stop_server(proc)
        log_fh.close()
        raise SystemExit(f"server {label} never became healthy — see {log_path}")
    return proc, log_fh, log_path, health


def stop_server(proc):
    if proc.poll() is None:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           capture_output=True, timeout=30)
        else:
            proc.terminate()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
    for _ in range(20):
        if not port_in_use():
            return True
        time.sleep(0.5)
    return False


def log_lines(log_path, needle):
    try:
        with open(log_path, encoding="utf-8", errors="replace") as fh:
            return [ln.rstrip("\n") for ln in fh if needle in ln]
    except FileNotFoundError:
        return []


# ── the request ──────────────────────────────────────────────────────────────

def research(question, anonymous=False):
    headers = {"Content-Type": "application/json"}
    if anonymous:
        headers["X-Anon-Fingerprint"] = ANON_FP
    t0 = time.time()
    started = now()
    events = []
    with requests.post(BASE + "/api/research",
                       json={"question": question, "response_language": "en"},
                       headers=headers, stream=True, timeout=(15, 600)) as r:
        status = r.status_code
        body = None
        if status == 200:
            r.encoding = "utf-8"
            for line in r.iter_lines(decode_unicode=True):
                if line and line.startswith("data: "):
                    try:
                        events.append(json.loads(line[len("data: "):]))
                    except ValueError:
                        events.append({"type": "_unparsed", "raw": line[:200]})
        else:
            body = r.text[:500]
    types = [e.get("type") for e in events]
    answer_chars = sum(len(e.get("content") or "") for e in events if e.get("type") == "answer")
    citations_evt = [e for e in events if e.get("type") == "citations"]
    error_evt = [e for e in events if e.get("type") == "error"]
    return {
        "question": question,
        "anonymous": anonymous,
        "started_utc": started,
        "elapsed_s": round(time.time() - t0, 1),
        "http_status": status,
        "http_body_if_not_200": body,
        "query_id": next((e.get("query_id") for e in events if e.get("type") == "query_id"), None),
        "event_types": types,
        "has_fallback_event": "fallback" in types,
        "has_error_event": bool(error_evt),
        "error_content": error_evt[0].get("content") if error_evt else None,
        "error_then_done": bool(error_evt) and bool(types) and types[-1] == "done"
                           and types.index("error") < len(types) - 1,
        "ends_with_done": bool(types) and types[-1] == "done",
        "answer_chars": answer_chars,
        "citations_len_sse": len(citations_evt[0].get("content") or []) if citations_evt else None,
    }


def check(name, expected, actual):
    return {"name": name, "expected": expected, "actual": actual, "ok": expected == actual}


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), capture_output=True,
                          text=True).stdout.strip()
    parts = urlsplit(DATABASE_URL)
    result = {
        "probe": "tests/probes/research_error_path/probe.py",
        "purpose": "HISTORY HONESTY car segment 2 — §4 gate rows 1-4 machine facts",
        "run_started_utc": now(),
        "head": head,
        "port": PORT,
        "test_mode_user": USER,
        "db": {"scheme": parts.scheme, "host": parts.hostname, "database": (parts.path or "").lstrip("/")},
        "bad_model": BAD_MODEL,
        "bad_model_env_vars": ["GENERATOR_MODEL", "GENERATOR_FALLBACK_MODEL"],
        "checks": [],
    }
    checks = result["checks"]

    # ── A. good model ────────────────────────────────────────────────────────
    procA, fhA, logA, healthA = start_server("A_good_model", {})
    result["A"] = {"server_health": healthA, "server_log": str(logA.relative_to(ROOT))}
    A = result["A"]
    try:
        A["step1_c0"] = credits()
        A["step1_newest_row_before"] = newest_row()
        c0 = A["step1_c0"]["credits_used_today"]
        id_before = (A["step1_newest_row_before"] or {}).get("id")

        A["step2_request"] = research(GOOD_QUERY)
        A["step2_newest_row"] = newest_row()
        A["step2_c1"] = credits()
        c1 = A["step2_c1"]["credits_used_today"]
        row2 = A["step2_newest_row"] or {}
        checks.append(check("A2 new row written (id advanced)", True, row2.get("id") is not None and row2.get("id") != id_before))
        checks.append(check("A2 row.kind", "research_v1", row2.get("kind")))
        checks.append(check("A2 row.fallback", False, row2.get("fallback")))
        checks.append(check("A2 row.citations_len >= 1", True, (row2.get("citations_len") or 0) >= 1))
        checks.append(check("A2 SSE has no fallback event", False, A["step2_request"]["has_fallback_event"]))
        checks.append(check("A2 credits c1 == c0 + 3", c0 + CREDIT_COST_RESEARCH, c1))

        A["step3_attempts"] = []
        chosen = None
        for q in NONSENSE_CANDIDATES:
            r = research(q)
            A["step3_attempts"].append(r)
            if r["has_fallback_event"]:
                chosen = q
                break
        A["step3_query_that_yielded_fallback"] = chosen
        A["step3_newest_row"] = newest_row()
        A["step3_c1b"] = credits()
        row3 = A["step3_newest_row"] or {}
        checks.append(check("A3 some nonsense query yielded the SSE fallback event", True, chosen is not None))
        checks.append(check("A3 row.question is the fallback query", chosen, row3.get("question")))
        checks.append(check("A3 row.fallback", True, row3.get("fallback")))
        checks.append(check("A3 row.citations_len", 0, row3.get("citations_len")))
    finally:
        A["server_stopped_port_free"] = stop_server(procA)
        fhA.close()

    # ── B. bad model (both generator bindings) ───────────────────────────────
    bad_env = {"GENERATOR_MODEL": BAD_MODEL, "GENERATOR_FALLBACK_MODEL": BAD_MODEL}
    procB, fhB, logB, healthB = start_server("B_bad_model", bad_env)
    result["B"] = {"server_health": healthB, "server_log": str(logB.relative_to(ROOT)), "env": bad_env}
    B = result["B"]
    try:
        B["step4_c2"] = credits()
        B["step4_n2"] = row_counts()
        B["step4_newest_row"] = newest_row()
        c2 = B["step4_c2"]["credits_used_today"]
        n2 = B["step4_n2"]

        B["step5_request"] = research(ERROR_QUERY)
        time.sleep(1.0)  # let the log flush
        B["step5_c3"] = credits()
        B["step5_n3"] = row_counts()
        B["step5_newest_row"] = newest_row()
        qid5 = B["step5_request"]["query_id"]
        B["step5_log_skip_lines"] = log_lines(logB, "generator ERROR before DONE")
        B["step5_log_generation_error_lines"] = [ln[:300] for ln in log_lines(logB, "Generation error")][:3]
        c3 = B["step5_c3"]["credits_used_today"]
        checks.append(check("B5 SSE error then done", True, B["step5_request"]["error_then_done"]))
        checks.append(check("B5 credits c3 == c2", c2, c3))
        checks.append(check("B5 rows n3 == n2 (all sessions)", n2["all_sessions"], B["step5_n3"]["all_sessions"]))
        checks.append(check("B5 rows n3 == n2 (research)", n2["research"], B["step5_n3"]["research"]))
        checks.append(check("B5 newest row id unchanged", (B["step4_newest_row"] or {}).get("id"),
                            (B["step5_newest_row"] or {}).get("id")))
        line5 = [ln for ln in B["step5_log_skip_lines"] if qid5 and qid5 in ln]
        B["step5_log_line_for_this_query"] = line5[0] if line5 else None
        checks.append(check("B5 log line present for this audit_id", True, bool(line5)))
        checks.append(check("B5 log line says anon=False", True, bool(line5) and "anon=False" in line5[0]))

        B["step6_expected_anon_id"] = derive_anon_id(ANON_CLIENT_IP, ANON_FP)
        anon_before = anon_rows()
        B["step6_anon_row_before"] = anon_before.get(B["step6_expected_anon_id"])
        B["step6_anon_rows_before_count"] = len(anon_before)
        B["step6_request"] = research(ERROR_QUERY, anonymous=True)
        time.sleep(1.0)
        anon_after = anon_rows()
        B["step6_anon_row_after"] = anon_after.get(B["step6_expected_anon_id"])
        B["step6_anon_rows_after_count"] = len(anon_after)
        # A row that did not exist before and exists after WITH 0 credits is not a
        # charge: check_anonymous_credits (pre-stream, api/server.py) creates the
        # anonymous_usage row at 0 via _get_or_create_anonymous_usage. Run 1 of this
        # probe (result_run1_20260904.json) flagged exactly that as a "change" —
        # a probe-side false positive, fixed here by comparing missing-as-0.
        B["step6_anon_rows_created_at_zero"] = [
            k for k in anon_after if k not in anon_before
            and (anon_after[k].get("credits_used_today") or 0) == 0
        ]
        B["step6_anon_rows_changed"] = {
            k: {"before": anon_before.get(k), "after": anon_after.get(k)}
            for k in set(anon_before) | set(anon_after)
            if ((anon_before.get(k) or {}).get("credits_used_today") or 0)
            != ((anon_after.get(k) or {}).get("credits_used_today") or 0)
        }
        B["step6_n4"] = row_counts()
        B["step6_c4"] = credits()
        qid6 = B["step6_request"]["query_id"]
        lines6 = [ln for ln in log_lines(logB, "generator ERROR before DONE") if qid6 and qid6 in ln]
        B["step6_log_line_for_this_query"] = lines6[0] if lines6 else None
        before_credits = (B["step6_anon_row_before"] or {}).get("credits_used_today", 0) or 0
        after_credits = (B["step6_anon_row_after"] or {}).get("credits_used_today")
        checks.append(check("B6 SSE error then done", True, B["step6_request"]["error_then_done"]))
        checks.append(check("B6 anon row exists after (created by the pre-stream quota check)", True, after_credits is not None))
        checks.append(check("B6 anon credits unchanged (before or 0 if no row)", before_credits, after_credits))
        checks.append(check("B6 no anonymous_usage row changed its credits", {}, B["step6_anon_rows_changed"]))
        checks.append(check("B6 rows unchanged (all sessions)", n2["all_sessions"], B["step6_n4"]["all_sessions"]))
        checks.append(check("B6 authed credits untouched by the anon call", c2, B["step6_c4"]["credits_used_today"]))
        checks.append(check("B6 log line present for this audit_id", True, bool(lines6)))
        checks.append(check("B6 log line says anon=True", True, bool(lines6) and "anon=True" in lines6[0]))
    finally:
        B["server_stopped_port_free"] = stop_server(procB)
        fhB.close()

    # ── C ────────────────────────────────────────────────────────────────────
    result["C"] = {"port_8010_in_use_after": port_in_use(), "run_finished_utc": now()}
    result["summary"] = {
        "checks_total": len(checks),
        "checks_ok": sum(1 for c in checks if c["ok"]),
        "checks_failed": [c["name"] for c in checks if not c["ok"]],
    }
    RESULT.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))
    print(f"wrote {RESULT.relative_to(ROOT)}")
    return 0 if not result["summary"]["checks_failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
