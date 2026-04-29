"""§ 2.7 Step 8 acceptance protocol runner.

Loads 20 test cases, invokes Explain pipeline + ExplainJudge,
aggregates pass/fail per dimension. Run only at acceptance time —
NOT real-time, NOT CI-gated, NOT golden-test regression.

Usage:
    python -m tests.run_explain_acceptance

Step 7 (commit TBD) ships this scaffold + ExplainJudge class +
api/prompts/explain_judge.md. Step 8 fills in the 20 cases at
tests/explain_acceptance_cases.json and removes the stub guard
in run_one_case.

Cases file shape (Step 8 will design):
    [
      {
        "id": "case_01",
        "report_text": "Hemoglobin 9.2 g/dL",
        "response_language": "zh-TW",
        "expected_pass": true,         // optional: known-good case
        "notes": "..."                 // optional: human context
      },
      ...
    ]
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, List

from openai import AsyncOpenAI

from api.utils.llm_judge import ExplainJudge, ExplainJudgeSource
from api.services.explain_service import run_explain_pipeline

CASES_PATH = Path(__file__).parent / "explain_acceptance_cases.json"
RESULTS_DIR = Path(__file__).parent / "results"


async def _consume_pipeline(report_text: str, response_language: str, openai_client: AsyncOpenAI) -> Dict:
    """Run the SSE pipeline to completion and assemble a response dict.

    Mirrors the shape the frontend reconstructs from SSE events:
      {"items": [...], "clinical_correlations": [...], "disclaimer": "...",
       "sources": [...], "error_code": "<code>" or None}
    """
    assembled: Dict = {
        "items": [],
        "clinical_correlations": [],
        "disclaimer": "",
        "sources": [],
        "error_code": None,
    }
    async for event in run_explain_pipeline(
        report_text=report_text,
        openai_client=openai_client,
        response_language=response_language,
    ):
        if not isinstance(event, dict):
            continue
        kind = event.get("type")
        if kind == "sources":
            assembled["sources"] = event.get("content", []) or []
        elif kind == "explain_result":
            content = event.get("content") or {}
            assembled["items"] = content.get("items", []) or []
            assembled["clinical_correlations"] = content.get("clinical_correlations", []) or []
            assembled["disclaimer"] = content.get("disclaimer", "") or ""
        elif kind == "error":
            assembled["error_code"] = event.get("code") or "generic"
    return assembled


def _sources_to_judge(sources_payload: List[dict]) -> List[ExplainJudgeSource]:
    """Convert pipeline `sources` SSE event payload into ExplainJudgeSource list."""
    return [
        ExplainJudgeSource(
            source_type=s.get("source_type", "Unknown"),
            label=s.get("label", ""),
            url=s.get("url"),  # None preserved for LOINC code-only refs
            description=s.get("description") or "",
        )
        for s in sources_payload
    ]


async def run_one_case(case: dict, judge: ExplainJudge, openai_client: AsyncOpenAI) -> dict:
    """Invoke pipeline + judge for one case. Returns:
      {id, response_language, pipeline_error, judge_result, elapsed_ms}
    """
    case_id = case.get("id", "unknown")
    report_text = case["report_text"]
    response_language = case.get("response_language", "en")

    t0 = time.time()
    pipeline_response = await _consume_pipeline(report_text, response_language, openai_client)

    # If the pipeline emitted an error event, skip judge (no body to evaluate).
    if pipeline_response["error_code"]:
        return {
            "id": case_id,
            "response_language": response_language,
            "pipeline_error": pipeline_response["error_code"],
            "judge_result": None,
            "elapsed_ms": int((time.time() - t0) * 1000),
        }

    explain_response_for_judge = {
        "items": pipeline_response["items"],
        "clinical_correlations": pipeline_response["clinical_correlations"],
        "disclaimer": pipeline_response["disclaimer"],
    }
    retrieved = _sources_to_judge(pipeline_response["sources"])
    judge_result = await judge.evaluate(
        report_text=report_text,
        explain_response=explain_response_for_judge,
        retrieved_sources=retrieved,
        response_language=response_language,
    )
    return {
        "id": case_id,
        "response_language": response_language,
        "pipeline_error": None,
        "judge_result": judge_result,
        "elapsed_ms": int((time.time() - t0) * 1000),
    }


def _aggregate(results: List[dict]) -> dict:
    """Per-dimension and overall pass-rate aggregation."""
    n = len(results)
    pipeline_errors = sum(1 for r in results if r.get("pipeline_error"))
    judged = [r for r in results if r.get("judge_result")]
    dim_pass = {d: 0 for d in ExplainJudge.DIMENSIONS}
    overall_pass = 0
    for r in judged:
        jr = r["judge_result"]
        for d in ExplainJudge.DIMENSIONS:
            if jr["dimensions"].get(d) == "pass":
                dim_pass[d] += 1
        if jr.get("overall") == "pass":
            overall_pass += 1
    return {
        "total": n,
        "pipeline_errors": pipeline_errors,
        "judged": len(judged),
        "overall_pass": overall_pass,
        "overall_pass_rate": (overall_pass / len(judged)) if judged else 0.0,
        "per_dimension_pass": dim_pass,
        "per_dimension_pass_rate": {
            d: (dim_pass[d] / len(judged)) if judged else 0.0
            for d in ExplainJudge.DIMENSIONS
        },
    }


def _print_summary(summary: dict) -> None:
    print("\n=== Explain Acceptance Summary ===")
    print(f"Total cases: {summary['total']}")
    print(f"Pipeline errors (skipped judge): {summary['pipeline_errors']}")
    print(f"Judged: {summary['judged']}")
    print(f"Overall pass: {summary['overall_pass']}/{summary['judged']} "
          f"({summary['overall_pass_rate']:.1%})")
    print("\nPer-dimension pass rate:")
    for d, rate in summary["per_dimension_pass_rate"].items():
        cnt = summary["per_dimension_pass"][d]
        print(f"  {d:32s} {cnt}/{summary['judged']} ({rate:.1%})")


async def main() -> int:
    if not CASES_PATH.exists():
        print(f"[!] Acceptance cases file not found: {CASES_PATH}")
        print("  Step 8 hasn't designed the 20 test cases yet.")
        print("  Step 7 ships ExplainJudge + this scaffold; Step 8 fills the cases.")
        return 0

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    if not cases:
        print("[!] Cases file is empty.")
        return 0

    openai_client = AsyncOpenAI()
    judge = ExplainJudge(client=openai_client)

    print(f"Running {len(cases)} acceptance cases…")
    results: List[dict] = []
    for i, case in enumerate(cases, start=1):
        print(f"  [{i}/{len(cases)}] {case.get('id', '?')} ({case.get('response_language', 'en')})…")
        try:
            r = await run_one_case(case, judge, openai_client)
        except Exception as e:
            r = {
                "id": case.get("id", "?"),
                "response_language": case.get("response_language", "en"),
                "pipeline_error": f"runner_exception:{type(e).__name__}",
                "judge_result": None,
                "elapsed_ms": 0,
            }
        results.append(r)

    summary = _aggregate(results)
    _print_summary(summary)

    RESULTS_DIR.mkdir(exist_ok=True)
    out_path = RESULTS_DIR / f"explain_acceptance_{int(time.time())}.json"
    out_path.write_text(
        json.dumps({"summary": summary, "cases": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nResults written to: {out_path}")

    return 0 if summary["overall_pass_rate"] >= 0.8 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
