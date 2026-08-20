"""Ownership-eval v1 — HTML report renderer.

THE HTML IS A RENDER OF result_v1.json AND NOTHING ELSE (Rule 20: the JSON is
the evidence; this file adds zero data). Static tables only — no JS, no fetch.

Run:  python tests/probes/ownership_eval/render_report.py
Reads: result_v1.json · Writes: report_v1.html
"""

from __future__ import annotations

import html
import json
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / "result_v1.json"
OUT = HERE / "report_v1.html"


def esc(x) -> str:
    return html.escape("" if x is None else str(x))


def table(rows: list[dict], cols: list[str]) -> str:
    head = "".join(f"<th>{esc(c)}</th>" for c in cols)
    body = "".join(
        "<tr>" + "".join(f"<td>{esc(r.get(c))}</td>" for c in cols) + "</tr>"
        for r in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def main() -> int:
    r = json.loads(SRC.read_text(encoding="utf-8"))
    agg = r["aggregate"]

    parts = [
        "<meta charset='utf-8'><title>Ownership eval v1</title>",
        "<style>body{font-family:system-ui,sans-serif;margin:24px;max-width:1200px}"
        "table{border-collapse:collapse;margin:10px 0 22px;font-size:13px}"
        "th,td{border:1px solid #bbb;padding:3px 8px;text-align:left}"
        "th{background:#eee}h2{margin-top:28px}code{background:#f3f3f3;padding:1px 4px}"
        ".bar{background:#fff3cd;padding:8px 12px;border:1px solid #dfc36a}</style>",
        "<h1>Ownership-anchored retrieval eval — v1</h1>",
        f"<p>generated {esc(r['generated'])} · git_head <code>{esc(r['git_head'][:12])}</code> · "
        f"store <b>{esc(r['store'])}</b> · arm <b>{esc(r['arm'])}</b> · level <b>{esc(r['level'])}</b> · "
        f"seed {esc(r['seed'])} · min_score {esc(r['min_score'])} · n_results {esc(r['n_results'])} · "
        f"corpus_docs {esc(r['corpus_docs'])} · eligible_drugs {esc(r['eligible_drugs'])} · "
        f"embedding_calls {esc(r['embedding_calls'])}</p>",
        f"<p>multi-key sets: <code>{esc(r['multi_key_sets'])}</code></p>",
        "<h2>Aggregate (100 sampled queries, pool level)</h2>",
        table([{"metric": k, "value": v} for k, v in agg.items()], ["metric", "value"]),
        f"<p class='bar'>Consultant bar (restated for this scope): wrong-object-in-pool &lt;1% — "
        f"measured <b>{agg['wrong_object_in_pool_rate']:.0%}</b>.</p>",
        "<h2>Smoke — WD01 raw-arm gate (recorded facts reproduced)</h2>",
        table([{"check": k, "value": v} for k, v in r["smoke"]["wd01_gate"].items()],
              ["check", "value"]),
        "<h2>Self-refutation samples (Rule 21 — hand-checkable labels)</h2>",
        "<h3>relevant-labeled</h3>",
        table(r["self_refutation"]["relevant_samples"], ["qid", "query", "moiety", "title"]),
        "<h3>wrong_object-labeled</h3>",
        table(r["self_refutation"]["wrong_object_samples"], ["qid", "query", "moiety", "title"]),
        "<h3>moiety contains key but labeled wrong_object (salt/ester/hydrate — listed, not relabeled)</h3>",
        table(r["self_refutation"]["moiety_contains_key_but_wrong_object"],
              ["qid", "key_used", "moiety", "title"]),
        "<h2>Per-query summary</h2>",
        table(
            [{
                "qid": q["qid"], "query": q["query"], "n_pool": q["n_pool"],
                "first_rel": q["first_relevant_rank"],
                "wrong_obj": q["has_wrong_object"], "wo@1": q["wrong_object_at_rank1"],
                "ndcg5": q["ndcg5"],
                "best_owned": (q["best_corpus_relevant"] or {}).get("score"),
                "best_owned_safety": (q["best_corpus_relevant_safety"] or {}).get("score"),
                "shortfall": (q["best_corpus_relevant"] or {}).get("shortfall_vs_min_score"),
            } for q in r["queries"]],
            ["qid", "query", "n_pool", "first_rel", "wrong_obj", "wo@1", "ndcg5",
             "best_owned", "best_owned_safety", "shortfall"],
        ),
        "<h2>Pools (every returned doc, labeled)</h2>",
    ]
    for q in r["queries"]:
        if not q["pool"]:
            continue
        parts.append(f"<h3>{esc(q['qid'])} — {esc(q['query'])}</h3>")
        parts.append(table(q["pool"], ["rank", "score", "moiety", "loinc", "label", "title"]))

    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes) — a render of {SRC.name}, nothing else")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
