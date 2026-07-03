# -*- coding: utf-8 -*-
"""a1-i fallback-forced probe (B2 case 2, the verdict that gates 2b).

Enters the Research NO-RETRIEVAL fallback DIRECTLY (generator._generate_fallback_stream)
so retrieval success cannot mask the fallback behavior — this is the deterministic
version of "construct a query that retrieves nothing". Two arms, N runs each, SAME
question (冠脂妥 identity):

  baseline arm : raw question            (pre-fix behavior — expect mis-ID risk)
  annotated arm: _annotate_research_question(question)  (v195 2a QUERY-AUGMENT)

String-level checks per run (full answers saved for eyeball):
  identity_ok   — names rosuvastatin (rosuvastatin / 瑞舒伐 / 羅舒伐 / ROSUVASTATIN)
  wrong_statin  — mentions simvastatin/atorvastatin/辛伐他汀/阿托伐他汀 (context printed;
                  a mention is only a mis-ID if it IS the asserted identity — eyeball)
  over_read     — phrases treating the mapping as approval/safety clearance (loose net)

Output: tests/results/a1i_fallback_probe_<ts>.json
Usage:  python scripts/a1i_fallback_probe.py   (needs OPENAI_API_KEY via .env)
"""
import asyncio
import io
import json
import os
import re
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from dotenv import load_dotenv  # noqa: E402
load_dotenv()

QUESTION = "冠脂妥高血脂可以吃嗎"
N_RUNS = 3

ROSU = re.compile(r"rosuvastatin|瑞舒伐|羅舒伐|ROSUVASTATIN", re.IGNORECASE)
WRONG = re.compile(r"simvastatin|atorvastatin|辛伐他汀|阿托伐他汀|立普妥|素果", re.IGNORECASE)
OVER = re.compile(r"TFDA (?:已)?(?:核准|批准|認可)(?:用於|使用)|approved by TFDA for|TFDA 許可證(?:證明|保證)", re.IGNORECASE)


async def run_arm(gen, question: str, label: str):
    from api.models.schemas import StreamEventType
    runs = []
    for i in range(N_RUNS):
        answer = ""
        async for ev in gen._generate_fallback_stream(question, "research", "zh-TW"):
            if ev.type == StreamEventType.ANSWER and ev.content:
                answer += ev.content
        wrong_ctx = [answer[max(0, m.start() - 60):m.end() + 60].replace("\n", " ")
                     for m in WRONG.finditer(answer)]
        runs.append({
            "run": i + 1,
            "identity_ok": bool(ROSU.search(answer)),
            "wrong_statin_mentions": wrong_ctx,
            "over_read_hits": OVER.findall(answer),
            "answer": answer,
        })
        r = runs[-1]
        print(f"  [{label} run {i+1}] identity_ok={r['identity_ok']} "
              f"wrong_statin_mentions={len(wrong_ctx)} over_read={len(r['over_read_hits'])}")
    return runs


async def main():
    from api.rag.generator import AnswerGenerator
    from api.server import _annotate_research_question

    gen = AnswerGenerator()
    annotated = _annotate_research_question(QUESTION)
    print("QUESTION:", QUESTION)
    print("ANNOTATED:", annotated)
    assert annotated != QUESTION, "annotation must have been applied"

    print(f"\n── baseline arm (raw question, N={N_RUNS}) ──")
    base = await run_arm(gen, QUESTION, "baseline")
    print(f"\n── annotated arm (v195 2a, N={N_RUNS}) ──")
    anno = await run_arm(gen, annotated, "annotated")

    out = {
        "timestamp": time.strftime("%Y%m%d_%H%M%S"),
        "question": QUESTION,
        "annotated_question": annotated,
        "n_runs": N_RUNS,
        "model": gen._fallback_model,
        "baseline": base,
        "annotated": anno,
        "summary": {
            "baseline_identity_ok": sum(r["identity_ok"] for r in base),
            "annotated_identity_ok": sum(r["identity_ok"] for r in anno),
            "baseline_wrong_mention_runs": sum(bool(r["wrong_statin_mentions"]) for r in base),
            "annotated_wrong_mention_runs": sum(bool(r["wrong_statin_mentions"]) for r in anno),
            "annotated_over_read_runs": sum(bool(r["over_read_hits"]) for r in anno),
        },
    }
    path = Path("tests/results") / f"a1i_fallback_probe_{out['timestamp']}.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nSUMMARY:", json.dumps(out["summary"], ensure_ascii=False))
    print("saved:", path)


if __name__ == "__main__":
    asyncio.run(main())
