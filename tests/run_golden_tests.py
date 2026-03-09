"""
Golden Dataset Test Runner - v3.0 (LLM as Judge)
v3.0：加入 Explain 類別、HTML Report 輸出、Regression 比較

執行方式：
    uv run python tests/run_golden_tests.py
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

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

async def call_research(client: httpx.AsyncClient, query: str) -> str:
    full_answer = ""
    try:
        response = await client.post(
            f"{BASE_URL}/api/research",
            json={"question": query},
            headers=HEADERS,
            timeout=90.0
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
                if event.get("type") == "answer":
                    chunk = event.get("content", "")
                    if chunk:
                        full_answer += chunk
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
            timeout=60.0
        )
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


async def call_explain(client: httpx.AsyncClient, report_text: str) -> str:
    full_answer = ""
    try:
        response = await client.post(
            f"{BASE_URL}/api/explain",
            json={"report_text": report_text},
            headers=HEADERS,
            timeout=90.0
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
                if event.get("type") == "answer":
                    chunk = event.get("content", "")
                    if chunk:
                        full_answer += chunk
                elif event.get("type") == "sources":
                    # Append source labels to answer for evaluation
                    sources = event.get("content", [])
                    for src in sources:
                        full_answer += f" [Source: {src.get('source_type', '')}]"
                elif event.get("type") == "error":
                    return f"[ERROR] {event.get('content', '')}"
            except json.JSONDecodeError:
                pass
    except Exception as e:
        return f"[ERROR] {e}"
    return full_answer.strip()


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


def determine_status(eval_result: dict, answer: str, cat: str, expected: str = "blocked") -> str:
    if answer.startswith("[ERROR]"):
        return "ERROR"
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

async def run_tests(smoke_only: bool = False):
    if not TOKEN:
        print(f"{RED}⚠️  TEST_AUTH_TOKEN not found in .env{RESET}")
        sys.exit(1)
    else:
        print(f"✅ Token loaded: {TOKEN[:20]}...")

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

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
        "guard": [], "multilingual": [], "document": []
    }
    ALL_CATEGORIES = {"research", "verify", "explain", "guard", "multilingual", "document"}

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
                answer = await call_explain(client, case["report_text"])
            elif cat == "document":
                answer = "[SKIPPED] document endpoint removed"
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
                    answer = await call_explain(client, case["report_text"])
                else:
                    print(f"\n  ❌  {case_id}: unknown endpoint '{endpoint}'", end=" ")
                    answer = f"[ERROR] Unknown endpoint: {endpoint}"
            else:
                answer = "[ERROR] Unknown category"

            api_elapsed = round(time.time() - start, 1)

            # Evaluate
            if cat == "guard":
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
            status = determine_status(eval_result, answer, cat, case.get("expected", "blocked"))
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
                "answer_preview": answer[:400] + "..." if len(answer) > 400 else answer
            })

            await asyncio.sleep(1.0)

    elapsed_total = round(time.time() - total_start, 1)
    total         = len(cases)
    pass_rate     = round(stats["PASS"] / total * 100, 1)

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Test Summary{RESET}")
    print(f"{'='*60}{RESET}")
    print(f"  Total:  {total}")
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

    # Save JSON results
    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path   = RESULTS_DIR / f"golden_results_{timestamp}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "base_url":  BASE_URL,
            "summary":   stats,
            "pass_rate": pass_rate,
            "evaluator": "LLM Judge (gpt-4.1-mini)",
            "results":   results
        }, f, ensure_ascii=False, indent=2)
    print(f"\n  JSON saved → {json_path}")

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

    if pass_rate < 70:
        print(f"{RED}⚠️  Pass rate below 70%.{RESET}\n")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Vela Golden Dataset Test Runner")
    parser.add_argument("--smoke", action="store_true",
                        help="只跑 smoke=true 的代表性題目（約 15 題，節省 ~80%% token 成本）")
    args = parser.parse_args()
    asyncio.run(run_tests(smoke_only=args.smoke))