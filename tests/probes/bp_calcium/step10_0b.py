"""SEGMENT 1d · STEP 0b — the L0 generator measurement: gpt-4.1 vs gpt-4.1-mini on IDENTICAL pools.

`step8_l0_trace.json` saved, for every one of the 8 L0 runs, the exact `system_prompt` + `user_prompt` the generator built
(the user prompt EMBEDS the retrieved documents). This replays each pair on gpt-4.1 (`generator.model`, the L1 binding) with
the same request shape `generate_stream` builds (temperature 0.2, max_tokens 2500) via the generator's own provider — so
the two answers of a pair differ ONLY by model. Answers → step10_0b_answer_run{i}_gpt41.md; the L0 answers are the existing
step8_l0_answer_run{i}.md. Veto (i) is HAND-READ per pair (step10_0b_grades.json); regexes here are pre-marks only.
PRE-REGISTERED RULE (baton §10): gpt-4.1 veto (i) FALSE ≥ 7/8 on the same pools → ruling (b).
"""
import asyncio
import json
import re
from pathlib import Path

from _harness import assert_dev_db, production_retriever  # noqa: F401 (dotenv + Dev assert; retriever not needed)

HERE = Path(__file__).resolve().parent
OUT = HERE / "step10_0b_pairs.json"


async def main():
    dev = assert_dev_db()
    from api.rag.generator import AnswerGenerator
    from api.providers.base import CompletionRequest
    gen = AnswerGenerator()
    src = json.load(open(HERE / "step8_l0_trace.json", encoding="utf-8"))
    pairs = []
    for run in src["runs"]:
        g = run["generation"]
        assert g.get("user_prompt") and g.get("system_prompt"), f"run {run['run']} has no saved prompts (fallback path?)"
        req = CompletionRequest(model=gen.model,
                                messages=[{"role": "system", "content": g["system_prompt"]},
                                          {"role": "user", "content": g["user_prompt"]}],
                                temperature=0.2, max_tokens=2500)
        resp = await gen._provider.complete(req)
        ans = resp.content or ""
        (HERE / f"step10_0b_answer_run{run['run']}_gpt41.md").write_text(ans, encoding="utf-8")
        pre_i = bool(re.search(r"calcium[- ]channel", ans, re.I))
        pre_ii = bool(re.search(r"thiazide|hydrochlorothiazide|chlorthalidone|hypercalc", ans, re.I))
        pairs.append({"run": run["run"], "final": [d["source_id"] for d in run["final"]],
                      "l0": {"model": g["model"], "answer_file": f"step8_l0_answer_run{run['run']}.md",
                             "premark_veto_i": g["veto_i_calcium_read_as_ccb"], "premark_veto_ii": g["veto_ii_mentions_thiazide_or_hypercalcemia"]},
                      "gpt41": {"model": gen.model, "answer_file": f"step10_0b_answer_run{run['run']}_gpt41.md",
                                "premark_veto_i": pre_i, "premark_veto_ii": pre_ii,
                                "input_tokens": resp.input_tokens, "output_tokens": resp.output_tokens}})
        print(f"[pair {run['run']}] gpt41 premark veto(i)={pre_i} veto(ii)={pre_ii} tokens in/out={resp.input_tokens}/{resp.output_tokens}", flush=True)
    json.dump({"db_branch": dev, "source": "step8_l0_trace.json (saved prompts = identical docs)",
               "gpt41_model": gen.model, "l0_model": gen._fallback_model, "pairs": pairs},
              open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    asyncio.run(main())
