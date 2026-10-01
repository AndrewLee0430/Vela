"""E6 mini — merge step9_e6_mini.json (runs) with step9_e6_mini_grades.json (HAND grades) → per-Q table + failure rate.

Grades file shape (written by hand after reading all 24 answers; never regex-derived):
  {"Q1": {"r1": {"different_question": false, "mechanism_named": true, "over_trigger": false, "note": "..."}, "r2": {...}}, ...}
A query FAILS when EITHER run answers a different question OR over-triggers (founder's rule). mechanism_named is
reported, not part of the fail rule.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    runs = json.load(open(HERE / "step9_e6_mini.json", encoding="utf-8"))
    grades = json.load(open(HERE / "step9_e6_mini_grades.json", encoding="utf-8"))
    lines = ["| Q | query | rewrite strings (run 1 / run 2, first K=1 call) | DailyMed safety in FINAL | different question (hand) | mechanism named (hand) | over-trigger (hand) | verdict |",
             "|---|---|---|---|---|---|---|---|"]
    fails, run_fail = [], 0
    for row in runs["rows"]:
        qid = row["id"]
        g = grades[qid]
        rw = " / ".join("; ".join(r["rewrite_calls"][0]) if r["rewrite_calls"] else "—" for r in row["runs"])
        dm = " / ".join(str(len(r["dm_safety_in_final"])) for r in row["runs"])
        dq = [g[f"r{i}"]["different_question"] for i in (1, 2)]
        mech = [g[f"r{i}"]["mechanism_named"] for i in (1, 2)]
        over = [g[f"r{i}"]["over_trigger"] for i in (1, 2)]
        q_fail = any(dq) or any(over)
        run_fail += sum(1 for i in range(2) if dq[i] or over[i])
        if q_fail:
            fails.append(qid)
        fmt = lambda xs: " / ".join("Y" if x else "n" for x in xs)
        lines.append(f"| {qid} | {row['query']} | {rw} | {dm} | {fmt(dq)} | {fmt(mech)} | {fmt(over)} | "
                     f"{'**FAIL**' if q_fail else 'pass'} — {g.get('note', '')} |")
    n_q = len(runs["rows"])
    summary = (f"**Failure rate: {run_fail}/{2 * n_q} runs; {len(fails)}/{n_q} queries fail** "
               f"(a query fails when either run answers a different question OR over-triggers): "
               f"{', '.join(fails) if fails else 'none'}. L0 model {runs['l0_model']}; "
               f"{runs['started_utc']} → {runs['finished_utc']}.")
    out = "\n".join(lines) + "\n\n" + summary + "\n"
    (HERE / "step9_e6_mini_table.md").write_text(out, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
