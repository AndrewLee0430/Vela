"""SEGMENT 1 spend meter — READ-ONLY SELECT on the Dev branch `api_cost_log`.

Every production LLM call site logs tokens + `estimated_cost_usd` (cost_tracker.MODEL_COSTS)
to `api_cost_log`, whether it runs behind the server (golden runner → /api/research) or
in-process (canary / danger-path / straddle / step3_trace via `log_api_cost_standalone`).
This sums that table since a UTC timestamp, grouped by feature and model.

NOT LOGGED, added as a hand estimate in the README: the golden runner's judge
(gpt-4.1-mini, in the runner process), the danger-path harness's own judge call, and
embeddings (text-embedding-3-small, ~$0.02 / 1M tokens — negligible).

Usage: python step6_spend.py --since 2026-09-29T08:00:00Z [--label control]
"""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from _harness import ROOT, assert_dev_db  # noqa: F401  (load_dotenv + Dev-branch assert)

HERE = Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True)
    ap.add_argument("--label", default="")
    args = ap.parse_args()
    assert_dev_db()
    from sqlalchemy import create_engine, text
    since = datetime.fromisoformat(args.since.replace("Z", "+00:00")).astimezone(timezone.utc).replace(tzinfo=None)
    eng = create_engine(os.environ["DATABASE_URL"])
    with eng.connect() as c:
        rows = c.execute(text(
            "SELECT feature, model, count(*), sum(prompt_tokens), sum(completion_tokens), "
            "sum(estimated_cost_usd) FROM api_cost_log WHERE created_at >= :s "
            "GROUP BY feature, model ORDER BY 6 DESC"), {"s": since}).fetchall()
    out = [{"feature": f, "model": m, "calls": n, "prompt_tokens": int(pt or 0),
            "completion_tokens": int(ct or 0), "usd": round(float(usd or 0), 4)}
           for f, m, n, pt, ct, usd in rows]
    total = round(sum(x["usd"] for x in out), 4)
    res = {"since_utc": since.isoformat(), "label": args.label, "rows": out, "logged_usd_total": total,
           "at_utc": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()}
    for x in out:
        print(f"  {x['feature']:<28} {x['model']:<14} n={x['calls']:<4} in={x['prompt_tokens']:<8} "
              f"out={x['completion_tokens']:<7} ${x['usd']}")
    print(f"LOGGED TOTAL since {since.isoformat()}Z: ${total}")
    if args.label:
        json.dump(res, open(HERE / f"step6_spend_{args.label}.json", "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
