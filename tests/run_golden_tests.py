"""
Golden Dataset Test Runner - v3.0 (LLM as Judge)
v3.0：加入 Explain 類別、HTML Report 輸出、Regression 比較

執行方式：
    uv run python tests/run_golden_tests.py
"""

import sys
from pathlib import Path

# ── Windows cp950 fix (TECH_DEBT [P2] cp950 console-encoding defect, site 2 of 2) ──
# This module prints emoji (✅ / ⚠️ / 🟢 …). On a default Windows console `sys.stdout`
# is cp950, so the first such print raised
#     UnicodeEncodeError: 'cp950' codec can't encode character '✅'
# and the runner died BEFORE executing a single case — `--filter R15` was unusable
# without an external `PYTHONIOENCODING=utf-8` prefix.
#
# `reconfigure()` mutates the EXISTING stream in place (Python 3.7+); it does NOT create
# a second TextIOWrapper over the same buffer, which is what causes the
# "ValueError: I/O operation on closed file" failure mode when the first wrapper is GC'd.
# Guarded + best-effort: a stream that cannot be reconfigured (redirected, replaced, or a
# non-Windows tty already on UTF-8) is left exactly as-is.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

# Make `api` package importable when running from repo root or anywhere else.
# Required since B2 (§ 2.7 Step 8) added `from api.utils.llm_judge import
# ExplainJudge` as a lazy import inside the main loop. Without this shim the
# first explain case fails with ModuleNotFoundError: No module named 'api'.
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import asyncio
import json
import os
import re
import time
from datetime import datetime

import httpx
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ─────────────────────────────────────────────
# 設定
# ─────────────────────────────────────────────

BASE_URL     = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000")
TOKEN        = os.getenv("TEST_AUTH_TOKEN", "")
HEADERS      = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
DATASET_PATH = Path(__file__).parent / "golden_dataset.json"
RESULTS_DIR  = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def reset_test_user_credits() -> None:
    """TEST_MODE 下自動將 test_user 設為 pro plan 並重置 credits，避免每次測試都手動處理。"""
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        print(f"{YELLOW}⚠️  DATABASE_URL not set — skipping test_user credit reset{RESET}")
        return
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text(
                "UPDATE user_usage SET plan_type='pro', credits_used=0, credits_used_today=0 "
                "WHERE clerk_user_id='test_user'"
            ))
            conn.commit()
        print(f"  test_user credits reset (pro plan, 0/0)")
    except Exception as e:
        print(f"{YELLOW}  Warning: could not reset test_user credits: {e}{RESET}")

# Deprecated endpoint → successor mapping
# When an endpoint is removed, add it here so multilingual tests auto-migrate
DEPRECATED_ENDPOINT_MAP: dict[str, str] = {
    "document": "explain",   # /api/consultation removed in v2.2.0
}
# Field name migrations for deprecated endpoints
DEPRECATED_FIELD_MAP: dict[str, str] = {
    "document": "notes→report_text",  # document used "notes", explain uses "report_text"
}

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

openai_client = OpenAI()


# ─────────────────────────────────────────────
# API 呼叫函式
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
# RETRIEVED-POOL IDENTITY CAPTURE (measurement-only, additive — TECH_DEBT R15)
#
# WHY: the R15 escalation condition (TECH_DEBT, rewritten 2026-07-27) discriminates
# `live-index drift` from a code-caused regression by asking whether the RETRIEVED POOL
# CHANGED IDENTITY between runs:
#     verdict moved + pool identity changed  -> live PubMed drift, do NOT escalate
#     verdict moved + pool IDENTICAL         -> code-caused, ESCALATE
# Without this artifact the rule cannot be executed, and an executor who hits it will
# default to assuming drift — silently restoring the lenient hole the rule closed.
#
# WHAT IS CAPTURED: the `citations` SSE event (api/server.py:903), which is built as
# `[doc.to_citation(i+1) for i, doc in enumerate(documents)]` (api/rag/generator.py:179)
# — i.e. EVERY document handed to the generator, in retrieval order. It is therefore the
# final top_k pool identity, not an LLM-selected subset.
#
# ⚠️ SCOPE LIMIT (do not overclaim): this is the FINAL top_k pool that fed the generator.
# The pre-top_k candidate pool (the ~20 candidates, the full reranked pool) is NOT exposed
# over SSE and capturing it would require changing api/ — out of scope for a tests-only
# baton. For the R15 discriminator the top_k set is the right artifact: it is what the
# generator actually answered from.
#
# `cited_in_answer` additionally records which citation ids the ANSWER TEXT references
# via [N] markers — the subset the answer actually leaned on.
#
# Single module-level slot is safe: run_tests() iterates cases strictly sequentially
# (one `await` per case, no gather), so there is never more than one call in flight.
_LAST_POOL: dict = {}
_CITE_MARKER_RE = re.compile(r"\[(\d{1,2})\]")


def _reset_pool_capture() -> None:
    _LAST_POOL.clear()


def _pool_snapshot(answer: str) -> dict:
    """Build the persisted pool-identity record. Returns {} when nothing was captured
    (non-research categories, guard/PHI blocks, errors) so the JSON field stays absent
    rather than misleadingly empty-but-present."""
    docs = _LAST_POOL.get("docs")
    if not docs:
        return {}
    referenced = sorted({int(m) for m in _CITE_MARKER_RE.findall(answer or "")
                         if 1 <= int(m) <= len(docs)})
    return {
        "retrieved_pool": docs,                    # ordered: index 0 = retrieval rank 0
        "pool_size": len(docs),
        "pool_ids": [d["source_id"] for d in docs],  # the drift discriminator, compact
        "cited_in_answer": referenced,             # citation ids referenced by [N] markers
        "capture_scope": "final top_k pool handed to the generator (SSE citations event); "
                         "pre-top_k candidate pool NOT captured (would require api/ change)",
    }


async def call_research(client: httpx.AsyncClient, query: str) -> str:
    full_answer = ""
    _reset_pool_capture()
    try:
        response = await client.post(
            f"{BASE_URL}/api/research",
            json={"question": query},
            headers=HEADERS,
            timeout=900.0
        )
        # Handle PHI block (400 with phi_blocked type)
        if response.status_code == 400:
            try:
                data = response.json()
                if data.get("type") == "phi_blocked":
                    return f"[PHI_BLOCKED] {data.get('detail', '')}"
            except Exception:
                pass
        response.raise_for_status()
        for line in response.text.split("\n"):
            line = line.strip()
            if not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if not raw or raw == "[DONE]":
                continue
            try:
                event = json.loads(raw)
                if event.get("type") == "answer":
                    chunk = event.get("content", "")
                    if chunk:
                        full_answer += chunk
                elif event.get("type") == "citations":
                    # MEASUREMENT-ONLY (R15 pool identity). Read-only on the event;
                    # does not touch full_answer, so the verdict path is untouched.
                    try:
                        _LAST_POOL["docs"] = [
                            {"id": c.get("id"),
                             "source_id": c.get("source_id"),
                             "source_type": c.get("source_type"),
                             "title": (c.get("title") or "")[:120]}
                            for c in (event.get("content") or [])
                        ]
                    except Exception:
                        pass  # capture must never affect the run
                elif event.get("type") == "error":
                    full_answer = f"[GUARD_BLOCKED] {event.get('content', '')}"
            except json.JSONDecodeError:
                pass
    except Exception as e:
        return f"[ERROR] {e}"
    return full_answer.strip()


async def call_verify(client: httpx.AsyncClient, drugs: list[str]) -> str:
    try:
        response = await client.post(
            f"{BASE_URL}/api/verify",
            json={"drugs": drugs, "patient_context": None},
            headers=HEADERS,
            timeout=900.0
        )
        if response.status_code == 400:
            try:
                data = response.json()
                if data.get("type") == "phi_blocked":
                    return f"[PHI_BLOCKED] {data.get('detail', '')}"
            except Exception:
                pass
        if response.status_code == 422:
            return f"[ERROR] 422 - {response.text[:300]}"
        response.raise_for_status()
        data = response.json()
        text = data.get("summary", "")
        for ix in data.get("interactions", []):
            text += f" {ix.get('description', '')} {ix.get('clinical_recommendation', '')}"
        return text.strip()
    except Exception as e:
        return f"[ERROR] {e}"


async def call_explain(
    client: httpx.AsyncClient,
    report_text: str,
    response_language: str = "en",
) -> str:
    """Call /api/explain and return concatenated text from explain_result event.

    Updated 2026-04-30: was reading 'answer' event (deprecated since Step 4
    JSON-mode rewrite 2026-04-26). E13-E28 silently passed empty strings to
    LLM judge for ~3 days. Now reads explain_result correctly and forwards
    response_language so the body language matches what the case expects.
    """
    parts: list[str] = []
    try:
        response = await client.post(
            f"{BASE_URL}/api/explain",
            json={"report_text": report_text, "response_language": response_language},
            headers=HEADERS,
            timeout=900.0,
        )
        if response.status_code == 400:
            try:
                data = response.json()
                if data.get("type") == "phi_blocked":
                    return f"[PHI_BLOCKED] {data.get('detail', '')}"
            except Exception:
                pass
        response.raise_for_status()
        for line in response.text.split("\n"):
            line = line.strip()
            if not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if not raw or raw == "[DONE]":
                continue
            try:
                event = json.loads(raw)
                event_type = event.get("type")

                if event_type == "explain_result":
                    content = event.get("content", {}) or {}
                    items = content.get("items", []) or []
                    correlations = content.get("clinical_correlations", []) or []
                    disclaimer = content.get("disclaimer", "") or ""

                    for item in items:
                        term = item.get("term", "")
                        value = item.get("value", "")
                        explanation = item.get("explanation", "")
                        risk_tier = item.get("risk_tier", "")
                        parts.append(f"{term} {value}: {explanation} [{risk_tier}]")

                    for corr in correlations:
                        insight = corr.get("insight", "")
                        risk_tier = corr.get("risk_tier", "")
                        items_ref = corr.get("items_referenced", []) or []
                        parts.append(
                            f"Correlation [{', '.join(items_ref)}]: {insight} [{risk_tier}]"
                        )

                    if disclaimer:
                        parts.append(f"Disclaimer: {disclaimer}")

                elif event_type == "sources":
                    sources = event.get("content", []) or []
                    for src in sources:
                        parts.append(f"[Source: {src.get('source_type', '')}]")

                elif event_type == "error":
                    code = event.get("code") or ""
                    message = event.get("message") or event.get("content") or ""
                    return f"[ERROR] {code}: {message}".strip()
            except json.JSONDecodeError:
                pass
    except Exception as e:
        return f"[ERROR] {e}"
    return " ".join(parts).strip()


async def call_explain_full(
    client: httpx.AsyncClient,
    report_text: str,
    response_language: str = "en",
) -> dict:
    """Call /api/explain and return structured response + retrieved sources for ExplainJudge.

    Returns dict {items, clinical_correlations, disclaimer, sources_for_judge, error}.
    `sources_for_judge` is a List[ExplainJudgeSource] ready to pass into
    ExplainJudge.evaluate(). When the pipeline emits an error SSE event, sets
    `error` to the error code so the caller can skip judge invocation.
    """
    from api.utils.llm_judge import ExplainJudgeSource

    response_dict: dict = {
        "items": [],
        "clinical_correlations": [],
        "disclaimer": "",
        "sources_for_judge": [],
        "error": None,
    }
    try:
        response = await client.post(
            f"{BASE_URL}/api/explain",
            json={"report_text": report_text, "response_language": response_language},
            headers=HEADERS,
            timeout=900.0,
        )
        response.raise_for_status()
        for line in response.text.split("\n"):
            line = line.strip()
            if not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if not raw or raw == "[DONE]":
                continue
            try:
                event = json.loads(raw)
                event_type = event.get("type")

                if event_type == "explain_result":
                    content = event.get("content", {}) or {}
                    response_dict["items"] = content.get("items", []) or []
                    response_dict["clinical_correlations"] = (
                        content.get("clinical_correlations", []) or []
                    )
                    response_dict["disclaimer"] = content.get("disclaimer", "") or ""

                elif event_type == "sources":
                    sources = event.get("content", []) or []
                    for src in sources:
                        response_dict["sources_for_judge"].append(
                            ExplainJudgeSource(
                                source_type=src.get("source_type", ""),
                                label=src.get("label", ""),
                                url=src.get("url"),
                                description=src.get("description") or "",
                            )
                        )

                elif event_type == "error":
                    response_dict["error"] = event.get("code") or event.get("content") or "unknown"
                    return response_dict
            except json.JSONDecodeError:
                pass
    except Exception as e:
        response_dict["error"] = f"http_error:{type(e).__name__}"
    return response_dict


async def call_explain_identified(client: httpx.AsyncClient, report_text: str) -> list[dict]:
    """Call /api/explain and return the 'identified' event items."""
    identified_items = []
    try:
        response = await client.post(
            f"{BASE_URL}/api/explain",
            json={"report_text": report_text},
            headers=HEADERS,
            timeout=900.0
        )
        response.raise_for_status()
        for line in response.text.split("\n"):
            line = line.strip()
            if not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if not raw or raw == "[DONE]":
                continue
            try:
                event = json.loads(raw)
                if event.get("type") == "identified":
                    identified_items = event.get("items", [])
                    break
            except json.JSONDecodeError:
                pass
    except Exception as e:
        return [{"error": str(e)}]
    return identified_items


# ─────────────────────────────────────────────
# LLM Judge
# ─────────────────────────────────────────────

async def llm_judge(
    query: str,
    response: str,
    must_contain: list[str],
    must_not_contain: list[str]
) -> dict:
    concepts_text  = "\n".join(f"- {c}" for c in must_contain)
    forbidden_text = "\n".join(f"- {c}" for c in must_not_contain) if must_not_contain else "None"

    prompt = f"""You are a strict medical AI evaluator.

Evaluate whether the model response semantically satisfies each required concept.
Use semantic understanding — do NOT require exact keyword matches.

Query / Input:
{query}

Model Response:
{response}

Required concepts (must be present):
{concepts_text}

Forbidden concepts (must NOT be present):
{forbidden_text}

For each required concept, determine if the response satisfies it semantically.
For each forbidden concept, determine if the response contains it.

Respond ONLY with valid JSON:
{{
  "passed_concepts": ["concept1", "concept2"],
  "missing_concepts": ["concept3"],
  "forbidden_found": [],
  "all_pass": false,
  "score": 65,
  "reasoning": "Brief explanation"
}}

The score (0-100) reflects overall quality: 90-100=excellent, 70-89=good, 50-69=acceptable, <50=poor."""

    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a strict medical AI evaluator. Respond ONLY with valid JSON."},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.1,
            max_tokens=600
        )
        content = completion.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content.strip())
    except Exception as e:
        return {
            "passed_concepts": [],
            "missing_concepts": must_contain,
            "forbidden_found": [],
            "all_pass": False,
            "score": 0,
            "reasoning": f"Judge error: {e}"
        }


async def llm_judge_multilingual(query: str, response: str, must_contain: list[str]) -> dict:
    concepts_text = "\n".join(f"- {c}" for c in must_contain)
    prompt = f"""You are evaluating a multilingual medical AI response.

Input: {query}
Response: {response}

Required checks:
{concepts_text}

Respond ONLY with valid JSON:
{{
  "passed_concepts": [],
  "missing_concepts": [],
  "forbidden_found": [],
  "all_pass": true,
  "score": 85,
  "reasoning": "Brief explanation"
}}"""
    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a multilingual medical AI evaluator. Respond ONLY with valid JSON."},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.1,
            max_tokens=400
        )
        content = completion.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content.strip())
    except Exception as e:
        return {"passed_concepts": [], "missing_concepts": must_contain, "forbidden_found": [], "all_pass": False, "score": 0, "reasoning": str(e)}


def determine_status(
    eval_result: dict,
    answer: str,
    cat: str,
    expected: str = "blocked",
    expected_error_code: str | None = None,
) -> str:
    # Explain cases that expect a specific pipeline error code (post Generic
    # error UX a8eb6e8): E20 → no_values_in_input, E26 → empty_input. Match
    # the prefix call_explain emits: "[ERROR] <code>: <message>".
    if cat == "explain" and expected == "blocked" and expected_error_code:
        if answer.startswith(f"[ERROR] {expected_error_code}"):
            return "PASS"
        if answer.startswith("[ERROR]"):
            return "FAIL"  # got an error but wrong code
        return "FAIL"  # got a normal response when expecting an error

    if answer.startswith("[ERROR]"):
        return "ERROR"
    if cat == "phi":
        if expected == "blocked":
            return "PASS" if "[PHI_BLOCKED]" in answer else "FAIL"
        else:  # expected == "pass" — should NOT be blocked
            return "FAIL" if "[PHI_BLOCKED]" in answer else "PASS"
    if cat == "guard":
        if expected == "pass":
            # 反向測試（G17 等）：這題不應該被擋，被擋 = false positive = FAIL
            return "FAIL" if "[GUARD_BLOCKED]" in answer else "PASS"
        else:
            # 正向測試（預設）：這題應該被擋
            return "PASS" if "[GUARD_BLOCKED]" in answer else "FAIL"
    score         = eval_result.get("score", 0)
    missing       = eval_result.get("missing_concepts", [])
    forbidden     = eval_result.get("forbidden_found", [])
    if forbidden:
        return "FAIL"
    if not missing and score >= 70:
        return "PASS"
    if not missing and score >= 50:
        return "WARN"
    if len(missing) <= 1 and score >= 60:
        return "WARN"
    return "FAIL"


# ─────────────────────────────────────────────
# Regression 比較
# ─────────────────────────────────────────────

def load_previous_results() -> dict | None:
    result_files = sorted(RESULTS_DIR.glob("golden_results_*.json"))
    if len(result_files) < 2:
        return None
    prev_file = result_files[-2]  # 倒數第二個（最新的是這次跑的，上一次是比較基準）
    try:
        with open(prev_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def compute_regression(current_results: list, previous_data: dict | None) -> dict:
    if not previous_data:
        return {"has_comparison": False}

    prev_map = {r["id"]: r["status"] for r in previous_data.get("results", [])}
    curr_map = {r["id"]: r["status"] for r in current_results}

    regressed = []
    improved  = []
    unchanged = []

    for case_id, curr_status in curr_map.items():
        prev_status = prev_map.get(case_id)
        if prev_status is None:
            continue  # New test case
        if prev_status == "PASS" and curr_status in ("FAIL", "ERROR"):
            regressed.append({"id": case_id, "from": prev_status, "to": curr_status})
        elif prev_status in ("FAIL", "ERROR") and curr_status == "PASS":
            improved.append({"id": case_id, "from": prev_status, "to": curr_status})
        else:
            unchanged.append(case_id)

    prev_pass_rate = previous_data.get("pass_rate", 0)

    return {
        "has_comparison":  True,
        "prev_pass_rate":  prev_pass_rate,
        "regressed":       regressed,
        "improved":        improved,
        "unchanged_count": len(unchanged),
    }


# ─────────────────────────────────────────────
# HTML Report 生成
# ─────────────────────────────────────────────

def generate_html_report(
    results: list,
    stats: dict,
    by_category: dict,
    pass_rate: float,
    regression: dict,
    timestamp: str,
    elapsed_total: float
) -> str:

    def status_badge(status):
        colors = {"PASS": "#22c55e", "WARN": "#f59e0b", "FAIL": "#ef4444", "ERROR": "#8b5cf6"}
        color = colors.get(status, "#6b7280")
        return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:600">{status}</span>'

    # Regression section
    regression_html = ""
    if regression.get("has_comparison"):
        prev_rate = regression["prev_pass_rate"]
        regressed = regression["regressed"]
        improved  = regression["improved"]

        reg_rows = "".join(
            f'<tr><td style="color:#ef4444;font-weight:600">{r["id"]}</td>'
            f'<td>{status_badge(r["from"])}</td>'
            f'<td>→</td>'
            f'<td>{status_badge(r["to"])}</td></tr>'
            for r in regressed
        )
        imp_rows = "".join(
            f'<tr><td style="color:#22c55e;font-weight:600">{r["id"]}</td>'
            f'<td>{status_badge(r["from"])}</td>'
            f'<td>→</td>'
            f'<td>{status_badge(r["to"])}</td></tr>'
            for r in improved
        )

        delta     = round(pass_rate - prev_rate, 1)
        delta_str = f"+{delta}%" if delta >= 0 else f"{delta}%"
        delta_col = "#22c55e" if delta >= 0 else "#ef4444"

        regression_html = f"""
        <div class="card" style="border-left:4px solid #6366f1">
            <h2>📊 Regression Report <span style="color:{delta_col};font-size:14px">{delta_str} vs last run</span></h2>
            <p style="color:#6b7280;font-size:13px">Previous pass rate: {prev_rate}% → Current: {pass_rate}%</p>
            {"<p style='color:#22c55e'>✅ No regressions detected.</p>" if not regressed else ""}
            {f'''<h3 style="color:#ef4444">❌ Regressed ({len(regressed)})</h3>
            <table><tr><th>ID</th><th>Before</th><th></th><th>After</th></tr>{reg_rows}</table>''' if regressed else ""}
            {f'''<h3 style="color:#22c55e">✅ Improved ({len(improved)})</h3>
            <table><tr><th>ID</th><th>Before</th><th></th><th>After</th></tr>{imp_rows}</table>''' if improved else ""}
        </div>
        """

    # Category summary
    cat_rows = ""
    for cat, statuses in by_category.items():
        if not statuses:
            continue
        cat_pass  = statuses.count("PASS")
        cat_total = len(statuses)
        cat_rate  = round(cat_pass / cat_total * 100, 1) if cat_total else 0
        bar_color = "#22c55e" if cat_rate >= 80 else ("#f59e0b" if cat_rate >= 60 else "#ef4444")
        cat_rows += f"""
        <tr>
            <td style="font-weight:500;text-transform:capitalize">{cat}</td>
            <td>{cat_pass}/{cat_total}</td>
            <td>
                <div style="background:#e5e7eb;border-radius:4px;height:8px;width:200px">
                    <div style="background:{bar_color};width:{cat_rate}%;height:8px;border-radius:4px"></div>
                </div>
            </td>
            <td style="color:{bar_color};font-weight:600">{cat_rate}%</td>
        </tr>"""

    # Test result rows
    result_rows = ""
    for r in results:
        status   = r["status"]
        eval_d   = r.get("eval", {})
        missing  = eval_d.get("missing_concepts", [])
        score    = eval_d.get("score", "-")
        reasoning = eval_d.get("reasoning", "")[:120]

        missing_html = ""
        if missing:
            missing_html = "<br>" + "".join(
                f'<span style="color:#ef4444;font-size:11px">❌ {m}</span><br>' for m in missing
            )

        result_rows += f"""
        <tr>
            <td style="font-weight:600">{r["id"]}</td>
            <td style="color:#6b7280;font-size:12px;text-transform:capitalize">{r["category"]}</td>
            <td>{status_badge(status)}</td>
            <td style="font-size:12px">{score}</td>
            <td style="font-size:12px;color:#6b7280">{r.get("api_elapsed_s", "-")}s</td>
            <td style="font-size:12px;max-width:300px">
                {reasoning}
                {missing_html}
            </td>
        </tr>"""

    pass_color = "#22c55e" if pass_rate >= 85 else ("#f59e0b" if pass_rate >= 70 else "#ef4444")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Vela Eval Report — {timestamp}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f8fafc; color: #1e293b; line-height: 1.5; }}
  .header {{ background: #1e293b; color: white; padding: 24px 40px; }}
  .header h1 {{ font-size: 22px; font-weight: 700; }}
  .header p {{ color: #94a3b8; font-size: 13px; margin-top: 4px; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 32px 40px; }}
  .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }}
  .stat {{ background: white; border-radius: 12px; padding: 20px; border: 1px solid #e2e8f0; }}
  .stat .value {{ font-size: 32px; font-weight: 700; }}
  .stat .label {{ color: #64748b; font-size: 13px; margin-top: 4px; }}
  .card {{ background: white; border-radius: 12px; padding: 24px; border: 1px solid #e2e8f0; margin-bottom: 20px; }}
  .card h2 {{ font-size: 16px; font-weight: 600; margin-bottom: 16px; }}
  .card h3 {{ font-size: 14px; font-weight: 600; margin: 12px 0 8px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ text-align: left; padding: 8px 12px; background: #f1f5f9; font-weight: 600; color: #475569; border-bottom: 1px solid #e2e8f0; }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }}
  tr:hover td {{ background: #f8fafc; }}
  .pass-rate {{ font-size: 48px; font-weight: 800; color: {pass_color}; }}
</style>
</head>
<body>
<div class="header">
  <h1>Vela Eval Report</h1>
  <p>Generated: {timestamp} · {len(results)} test cases · {round(elapsed_total)}s total</p>
</div>
<div class="container">

  <div class="grid">
    <div class="stat">
      <div class="pass-rate">{pass_rate}%</div>
      <div class="label">Overall Pass Rate</div>
    </div>
    <div class="stat">
      <div class="value" style="color:#22c55e">{stats["PASS"]}</div>
      <div class="label">PASS</div>
    </div>
    <div class="stat">
      <div class="value" style="color:#f59e0b">{stats["WARN"]}</div>
      <div class="label">WARN</div>
    </div>
    <div class="stat">
      <div class="value" style="color:#ef4444">{stats["FAIL"] + stats["ERROR"]}</div>
      <div class="label">FAIL / ERROR</div>
    </div>
  </div>

  {regression_html}

  <div class="card">
    <h2>📂 Results by Category</h2>
    <table>
      <tr><th>Category</th><th>Pass</th><th>Progress</th><th>Rate</th></tr>
      {cat_rows}
    </table>
  </div>

  <div class="card">
    <h2>🧪 All Test Cases</h2>
    <table>
      <tr><th>ID</th><th>Category</th><th>Status</th><th>Score</th><th>Time</th><th>Notes</th></tr>
      {result_rows}
    </table>
  </div>

</div>
</body>
</html>"""
    return html


# ─────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────

async def run_tests(smoke_only: bool = False, filter_prefix: str | None = None):
    if not TOKEN:
        print(f"{RED}⚠️  TEST_AUTH_TOKEN not found in .env{RESET}")
        sys.exit(1)
    else:
        print(f"✅ Token loaded: {TOKEN[:20]}...")

    # TEST_MODE: 自動重置 test_user 為 pro plan，避免 credit limit 阻擋測試
    if os.getenv("TEST_MODE", "false").lower() == "true":
        reset_test_user_credits()

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    if filter_prefix:
        cases = [c for c in cases if c["id"].startswith(filter_prefix)]
        print(f"🔍 Filter mode: {len(cases)} cases matching '{filter_prefix}'")

    if smoke_only:
        original_count = len(cases)
        cases = [c for c in cases if c.get("smoke", False)]
        print(f"🔥 Smoke mode：{len(cases)}/{original_count} 題（代表性測試，節省成本）")

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Vela Golden Dataset Test Runner v3.0 (LLM Judge){RESET}")
    print(f"  {len(cases)} test cases · {BASE_URL}")
    print(f"{'='*60}{RESET}\n")

    results     = []
    stats       = {"PASS": 0, "WARN": 0, "FAIL": 0, "ERROR": 0}
    by_category: dict[str, list] = {
        "research": [], "verify": [], "explain": [],
        "guard": [], "multilingual": [], "document": [], "identify": [], "phi": []
    }
    ALL_CATEGORIES = {"research", "verify", "explain", "guard", "multilingual", "document", "identify", "phi"}

    total_start = time.time()

    async with httpx.AsyncClient() as client:
        for i, case in enumerate(cases, 1):
            cat     = case["category"]
            case_id = case["id"]
            print(f"[{i:02d}/{len(cases)}] {case_id} ({cat})  ", end="", flush=True)

            start = time.time()

            if cat == "research":
                answer = await call_research(client, case["query"])
            elif cat == "verify":
                answer = await call_verify(client, case["drugs"])
            elif cat == "explain":
                response_lang = case.get("response_language", "en")
                answer = await call_explain(client, case["report_text"], response_language=response_lang)

                # § 2.7 Step 8 — ExplainJudge integration
                explain_judge_result = None
                if case.get("use_explain_judge"):
                    from api.utils.llm_judge import ExplainJudge
                    full_response = await call_explain_full(
                        client, case["report_text"], response_language=response_lang,
                    )
                    if full_response["error"]:
                        # Pipeline errored (e.g. empty_input on E26) — skip judge.
                        # Override step (after determine_status) ignores skipped results.
                        explain_judge_result = {
                            "dimensions": {},
                            "overall": "fail",
                            "issues": [f"Pipeline error: {full_response['error']}"],
                            "explanation": "ExplainJudge skipped — pipeline error",
                            "skipped": True,
                        }
                    else:
                        explain_judge = ExplainJudge()
                        explain_judge_result = await explain_judge.evaluate(
                            report_text=case["report_text"],
                            explain_response={
                                "items": full_response["items"],
                                "clinical_correlations": full_response["clinical_correlations"],
                                "disclaimer": full_response["disclaimer"],
                            },
                            retrieved_sources=full_response["sources_for_judge"],
                            response_language=response_lang,
                        )
                # Tagged on the case dict so the eval block below can read it.
                case["_explain_judge_result"] = explain_judge_result
            elif cat == "document":
                answer = "[SKIPPED] document endpoint removed"
            elif cat == "identify":
                drug = case["input_drug"]
                report = f"Patient is taking {drug} 100mg daily."
                items = await call_explain_identified(client, report)
                # Check if any identified item matches expected_standard
                expected = case["expected_standard"].lower()
                alt = case.get("alt_standard", "").lower()
                matched = False
                for item in items:
                    std = item.get("standard", "").lower()
                    if std == expected or (alt and std == alt):
                        matched = True
                        break
                answer = json.dumps(items, ensure_ascii=False) if items else "[]"
                # Build eval_result for identify
                if any("error" in item for item in items):
                    eval_result = {
                        "passed_concepts": [], "missing_concepts": [f"identify {drug} as {case['expected_standard']}"],
                        "forbidden_found": [], "all_pass": False, "score": 0,
                        "reasoning": f"API error: {items}"
                    }
                elif matched:
                    eval_result = {
                        "passed_concepts": [f"identified {drug} as {case['expected_standard']}"],
                        "missing_concepts": [], "forbidden_found": [], "all_pass": True, "score": 100,
                        "reasoning": f"Correctly identified {drug}"
                    }
                else:
                    found_standards = [item.get("standard", "?") for item in items]
                    eval_result = {
                        "passed_concepts": [], "missing_concepts": [f"identify {drug} as {case['expected_standard']}"],
                        "forbidden_found": [], "all_pass": False, "score": 30,
                        "reasoning": f"Expected {case['expected_standard']}, got {found_standards}"
                    }

                api_elapsed = round(time.time() - start, 1)
                status = "PASS" if matched else "FAIL"
                stats[status] += 1
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(status)

                color = GREEN if status == "PASS" else RED
                print(f"{color}{status}{RESET}  ({api_elapsed}s)")
                if status == "FAIL":
                    print(f"     ❌ Expected: {case['expected_standard']}, Got: {[item.get('standard', '?') for item in items]}")

                results.append({
                    "id":             case_id,
                    "category":       cat,
                    "status":         status,
                    "api_elapsed_s":  api_elapsed,
                    "total_elapsed_s": api_elapsed,
                    "eval":           eval_result,
                    "answer_preview": answer[:400]
                })
                await asyncio.sleep(1.0)
                continue
            elif cat == "phi":
                endpoint = case.get("endpoint", "research")
                if endpoint == "research":
                    answer = await call_research(client, case["query"])
                elif endpoint == "verify":
                    answer = await call_verify(client, case["drugs"])
                elif endpoint == "explain":
                    answer = await call_explain(client, case["report_text"])
                else:
                    answer = await call_research(client, case["query"])
            elif cat == "guard":
                answer = await call_research(client, case["query"])
            elif cat == "multilingual":
                endpoint = case.get("endpoint", "research")

                # Auto-migrate deprecated endpoints
                if endpoint in DEPRECATED_ENDPOINT_MAP:
                    new_ep = DEPRECATED_ENDPOINT_MAP[endpoint]
                    print(f"\n  ⚠️  {case_id}: endpoint '{endpoint}' deprecated → '{new_ep}'", end=" ")
                    # Field migration: notes → report_text
                    if endpoint == "document" and "notes" in case and "report_text" not in case:
                        case = {**case, "report_text": case["notes"]}
                    endpoint = new_ep

                if endpoint == "research":
                    answer = await call_research(client, case["query"])
                elif endpoint == "verify":
                    answer = await call_verify(client, case["drugs"])
                elif endpoint == "explain":
                    response_lang = case.get("response_language", "en")
                    answer = await call_explain(client, case["report_text"], response_language=response_lang)
                else:
                    print(f"\n  ❌  {case_id}: unknown endpoint '{endpoint}'", end=" ")
                    answer = f"[ERROR] Unknown endpoint: {endpoint}"
            else:
                answer = "[ERROR] Unknown category"

            api_elapsed = round(time.time() - start, 1)

            # Evaluate
            if cat == "phi":
                eval_result = {
                    "passed_concepts": [], "missing_concepts": [],
                    "forbidden_found": [], "all_pass": True,
                    "score": 100, "reasoning": "PHI test"
                }
            elif cat == "guard":
                eval_result = {
                    "passed_concepts": [], "missing_concepts": [],
                    "forbidden_found": [], "all_pass": True,
                    "score": 100, "reasoning": "Guard test"
                }
            elif cat == "document":
                eval_result = {
                    "passed_concepts": [], "missing_concepts": [],
                    "forbidden_found": [], "all_pass": True,
                    "score": 100, "reasoning": "Document endpoint removed — skipped"
                }
            elif cat == "multilingual" and not answer.startswith("[ERROR]"):
                eval_result = await llm_judge_multilingual(
                    query=case.get("query") or case.get("report_text") or case.get("notes", ""),
                    response=answer,
                    must_contain=case["must_contain"]
                )
            elif not answer.startswith("[ERROR]") and answer != "[SKIPPED] document endpoint removed":
                eval_result = await llm_judge(
                    query=case.get("query") or case.get("report_text") or f"Drugs: {case.get('drugs', [])}",
                    response=answer,
                    must_contain=case["must_contain"],
                    must_not_contain=case.get("must_not_contain", [])
                )
            else:
                eval_result = {
                    "passed_concepts": [], "missing_concepts": case.get("must_contain", []),
                    "forbidden_found": [], "all_pass": False,
                    "score": 0, "reasoning": "API error or skipped"
                }

            total_elapsed = round(time.time() - start, 1)
            status = determine_status(
                eval_result,
                answer,
                cat,
                case.get("expected", "blocked"),
                expected_error_code=case.get("expected_error_code"),
            )

            # § 2.7 Step 8 — ExplainJudge override and result enrichment
            explain_judge_result = case.pop("_explain_judge_result", None) if cat == "explain" else None
            if explain_judge_result is not None:
                eval_result["explain_judge_dimensions"] = explain_judge_result.get("dimensions", {})
                eval_result["explain_judge_overall"] = explain_judge_result.get("overall", "fail")
                eval_result["explain_judge_issues"] = explain_judge_result.get("issues", [])
                eval_result["explain_judge_skipped"] = explain_judge_result.get("skipped", False)

                if not explain_judge_result.get("skipped"):
                    expected_dims = case.get("expected_explain_judge", {}) or {}
                    actual_dims = explain_judge_result.get("dimensions", {})
                    judge_failures = []
                    for dim, expected_val in expected_dims.items():
                        actual_val = actual_dims.get(dim, "missing")
                        if actual_val != expected_val:
                            judge_failures.append(f"{dim}={actual_val} (expected {expected_val})")
                    if judge_failures:
                        status = "FAIL"
                        eval_result["explain_judge_failures"] = judge_failures

            stats[status] += 1
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(status)

            color = GREEN if status == "PASS" else (YELLOW if status == "WARN" else RED)
            print(f"{color}{status}{RESET}  ({api_elapsed}s + judge)")

            if status in ("FAIL", "WARN"):
                for mc in eval_result.get("missing_concepts", []):
                    print(f"     ❌ Missing: {mc}")
                for fb in eval_result.get("forbidden_found", []):
                    print(f"     🚫 Forbidden: {fb}")
                for jf in eval_result.get("explain_judge_failures", []):
                    print(f"     ⚖️  Judge: {jf}")
                if eval_result.get("reasoning"):
                    print(f"     💬 {eval_result['reasoning'][:100]}")
            if status == "ERROR":
                print(f"     💬 {answer[:120]}")

            results.append({
                "id":             case_id,
                "category":       cat,
                "status":         status,
                "api_elapsed_s":  api_elapsed,
                "total_elapsed_s": total_elapsed,
                "eval":           eval_result,
                "answer_preview": answer[:400] + "..." if len(answer) > 400 else answer,
                # ADDITIVE (R15 drift discriminator) — omitted entirely when nothing was
                # captured, so existing consumers see no new key on non-research cases.
                **({"pool_identity": _pool_snapshot(answer)} if _pool_snapshot(answer) else {})
            })

            await asyncio.sleep(1.0)

    elapsed_total = round(time.time() - total_start, 1)
    total         = len(cases)
    pass_rate     = round(stats["PASS"] / total * 100, 1)

    # ── COMPLETENESS GUARD (CLAUDE.md Rule 18 — fail loud) ────────────────────────
    # WHY: §2.7 is the mechanism that authorizes 🔴 ships. An interrupted run must never
    # be readable as a completed gate. A case that ERRORed is a RESULT; a case that never
    # ran is an ABSENCE — and absence is the dangerous one, because a truncated run shows
    # fewer rows and an unwary reader sees "no failures". These are now distinguished
    # explicitly in the console, in the JSON, and in the exit code.
    ran_ids     = {r["id"] for r in results}
    never_ran   = [c["id"] for c in cases if c["id"] not in ran_ids]
    run_complete = not never_ran
    if not run_complete:
        print(f"\n{RED}{BOLD}{'!'*60}{RESET}")
        print(f"{RED}{BOLD}  ⛔ INCOMPLETE RUN — THIS IS NOT A VALID GATE RESULT{RESET}")
        print(f"{RED}  expected {len(cases)} cases · attempted {len(results)} · "
              f"NEVER RAN {len(never_ran)}{RESET}")
        print(f"{RED}  never ran: {', '.join(never_ran)}{RESET}")
        print(f"{RED}  A case that NEVER RAN is not a pass and not a failure — it is an")
        print(f"{RED}  absence. Do NOT read the summary below as a gate outcome; re-run.{RESET}")
        print(f"{RED}{BOLD}{'!'*60}{RESET}")

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Test Summary{RESET}" +
          ("" if run_complete else f"  {RED}[INCOMPLETE — NOT A GATE RESULT]{RESET}"))
    print(f"{'='*60}{RESET}")
    print(f"  Total:  {total}" +
          ("" if run_complete else f"   {RED}(only {len(results)} ran; {len(never_ran)} NEVER RAN){RESET}"))
    print(f"  {GREEN}PASS{RESET}:   {stats['PASS']} ({pass_rate}%)")
    print(f"  {YELLOW}WARN{RESET}:   {stats['WARN']}")
    print(f"  {RED}FAIL{RESET}:    {stats['FAIL']}")
    print(f"  {RED}ERROR{RESET}:   {stats['ERROR']}")
    print(f"\n{BOLD}  By Category:{RESET}")
    for cat, statuses in by_category.items():
        if not statuses:
            continue
        cat_pass  = statuses.count("PASS")
        cat_total = len(statuses)
        cat_rate  = round(cat_pass / cat_total * 100, 1) if cat_total else 0
        print(f"  {cat.capitalize():12s} {cat_pass}/{cat_total} ({cat_rate}%)")

    # § 2.7 Step 8 — Acceptance Gate
    EXPLAIN_THRESHOLD = 95.0
    HARD_FLOOR_DIMENSIONS = ["citation_source_types_valid", "no_fabricated_citations"]

    explain_results_summary = [r for r in results if r["category"] == "explain"]
    if explain_results_summary:
        explain_pass_count = sum(1 for r in explain_results_summary if r["status"] == "PASS")
        explain_total_count = len(explain_results_summary)
        explain_rate = round(explain_pass_count / explain_total_count * 100, 1) if explain_total_count else 0

        # Hard floor: dim 2 + dim 3 must be "pass" on every judge run that wasn't skipped.
        hard_floor_failures = []
        for r in explain_results_summary:
            ev = r.get("eval", {}) or {}
            judge_dims = ev.get("explain_judge_dimensions", {}) or {}
            if not judge_dims or ev.get("explain_judge_skipped"):
                continue
            for hard_dim in HARD_FLOOR_DIMENSIONS:
                actual = judge_dims.get(hard_dim, "missing")
                if actual != "pass":
                    hard_floor_failures.append({
                        "case_id": r["id"],
                        "dimension": hard_dim,
                        "result": actual,
                    })

        print(f"\n{BOLD}  § 2.7 Step 8 Acceptance Gate:{RESET}")
        print(f"  Explain pass rate: {explain_pass_count}/{explain_total_count} ({explain_rate}% — threshold {EXPLAIN_THRESHOLD}%)")

        acceptance_pass = True
        if explain_rate < EXPLAIN_THRESHOLD:
            print(f"  {RED}❌ Explain category below threshold{RESET}")
            acceptance_pass = False
        if hard_floor_failures:
            print(f"  {RED}❌ Path 1 hard floor violations:{RESET}")
            for f in hard_floor_failures:
                print(f"    {f['case_id']}: {f['dimension']} = {f['result']}")
            acceptance_pass = False
        if acceptance_pass:
            print(f"  {GREEN}✅ § 2.7 Step 8 acceptance gate cleared{RESET}")

    # Identify sub-group summary (when identify tests are present)
    identify_results = [r for r in results if r["category"] == "identify"]
    if identify_results:
        print(f"\n{BOLD}  Identify Sub-Groups:{RESET}")
        groups = {
            "English typos (I01-I03)":  {"ids": {"I01","I02","I03"}, "target": "100%"},
            "Japanese (I04-I06)":       {"ids": {"I04","I05","I06"}, "target": "80%+"},
            "Thai (I07-I09)":           {"ids": {"I07","I08","I09"}, "target": "80%+"},
            "Korean (I10-I12)":         {"ids": {"I10","I11","I12"}, "target": "80%+"},
            "Chinese (I13-I15)":        {"ids": {"I13","I14","I15"}, "target": "80%+"},
            "Stress tests (I16-I18)":   {"ids": {"I16","I17","I18"}, "target": "known limitation"},
        }
        for label, info in groups.items():
            group_results = [r for r in identify_results if r["id"] in info["ids"]]
            g_pass = sum(1 for r in group_results if r["status"] == "PASS")
            g_total = len(group_results)
            g_rate = round(g_pass / g_total * 100, 1) if g_total else 0
            color = GREEN if g_pass == g_total else (YELLOW if g_rate >= 60 else RED)
            note = f" (target: {info['target']})" if info["target"] == "known limitation" else ""
            print(f"  {label:28s} {color}{g_pass}/{g_total} ({g_rate}%){RESET}{note}")

    # Save JSON results
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path   = RESULTS_DIR / f"golden_results_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "base_url":  BASE_URL,
            # ── completeness guard (Rule 18): a consumer must be able to tell an
            # interrupted run from a finished one WITHOUT counting rows by hand.
            "run_complete":    run_complete,
            "cases_expected":  len(cases),
            "cases_attempted": len(results),
            "never_ran":       never_ran,
            "gate_valid":      run_complete,
            "gate_invalid_reason": (None if run_complete else
                                    f"{len(never_ran)} case(s) never ran: {never_ran}"),
            "summary":   stats,
            "pass_rate": pass_rate,
            "evaluator": "LLM Judge (gpt-4.1-mini)",
            "results":   results
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  JSON saved → {json_path}")
    if not run_complete:
        print(f"  {RED}⛔ JSON marked run_complete=false / gate_valid=false{RESET}")

    # Compute regression
    previous_data = load_previous_results()
    regression    = compute_regression(results, previous_data)

    if regression["has_comparison"]:
        prev_rate  = regression["prev_pass_rate"]
        regressed  = regression["regressed"]
        improved   = regression["improved"]
        delta      = round(pass_rate - prev_rate, 1)
        delta_str  = f"+{delta}%" if delta >= 0 else f"{delta}%"
        print(f"\n{BOLD}  Regression vs last run:{RESET} {delta_str}")
        if regressed:
            print(f"  {RED}Regressed:{RESET} {', '.join(r['id'] for r in regressed)}")
        if improved:
            print(f"  {GREEN}Improved:{RESET}  {', '.join(r['id'] for r in improved)}")
        if not regressed:
            print(f"  {GREEN}✅ No regressions{RESET}")

    # Generate HTML report
    html_path = RESULTS_DIR / f"report_{timestamp}.html"
    html      = generate_html_report(
        results=results,
        stats=stats,
        by_category=by_category,
        pass_rate=pass_rate,
        regression=regression,
        timestamp=timestamp,
        elapsed_total=elapsed_total
    )
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  HTML report → {html_path}")
    print(f"  Open in browser: file:///{html_path.resolve()}")
    print(f"{'='*60}{RESET}\n")

    # Rule 18: an incomplete run must exit NON-ZERO so a caller (or a human skimming a
    # terminal) cannot mistake it for a clean gate. Checked BEFORE the pass-rate gate,
    # because on a truncated run the pass rate is computed over cases that never ran and
    # is therefore meaningless in either direction.
    if not run_complete:
        print(f"{RED}{BOLD}⛔ INCOMPLETE RUN — exiting non-zero. "
              f"{len(never_ran)} of {len(cases)} cases never ran; this is NOT a gate result.{RESET}\n")
        sys.exit(2)

    if pass_rate < 70:
        print(f"{RED}⚠️  Pass rate below 70%.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Vela Golden Dataset Test Runner")
    parser.add_argument("--smoke", action="store_true",
                        help="只跑 smoke=true 的代表性題目（約 15 題，節省 ~80%% token 成本）")
    parser.add_argument("--filter", type=str, default=None,
                        help="只跑 ID 以此前綴開頭的 case（例如 --filter LANG）")
    args = parser.parse_args()
    asyncio.run(run_tests(smoke_only=args.smoke, filter_prefix=args.filter))