"""STEP 2c — E6 mini variant set, L0 binding, N=2 each (12 queries → 24 runs), on prod-equivalent code (HEAD a6d59b9).

Generalisation + over-trigger test of the shipped `_rewrite_query` edit (fly 261). Each run = the production retriever
(`_harness.production_retriever`, source_weight_active=True) + generation on the ANONYMOUS path — `model_override =
generator._fallback_model` (gpt-4.1-mini), exactly as api/server.py binds L0 (Decision 001 v0.3 A8). lang follows the UI
locale a user of that query would have: zh-TW for CJK queries, en otherwise. Per run: every rewrite string (observation-only
wrapper), FINAL docs, DailyMed whitelisted safety sections in FINAL, the answer (saved as step9_answer_Q{n}_r{i}.md), and
regex PRE-MARKS only — the grades (answered a different question / expected mechanism named / over-trigger) are
HAND-READ per the founder's instruction and written into step9_e6_mini_grades.json by hand, never by regex.

Budget: 24 retrievals + 24 gpt-4.1-mini generations ≈ $0.25; STOP above US$0.8.
"""
import asyncio
import json
import re
import time
from pathlib import Path

from _harness import assert_dev_db, production_retriever

HERE = Path(__file__).resolve().parent
OUT = HERE / "step9_e6_mini.json"
N = 2
CJK = re.compile(r"[一-鿿]")

# (id, query, expected mechanism (prose, for the hand-read), expected-mechanism PRE-MARK regex, over-trigger regex or None)
THZ = r"thiazide|hydrochlorothiazide|chlorthalidone|indapamide|噻嗪|利尿"
QS = [
    ("Q1", "鈣片和降血壓藥可以一起吃嗎", "thiazide + calcium → hypercalcemia (hero chip, zh-TW)",
     r"thiazide|hypercalc|噻嗪|高血鈣|血鈣", None),
    ("Q2", "Can I take potassium with my BP pills?", "ACEI/ARB/K-sparing diuretic + potassium → hyperkalemia",
     r"hyperkal|ACE|ARB|angiotensin|spironolactone|potassium[- ]sparing", None),
    ("Q3", "Calcium with amlodipine?", "calcium may blunt the CCB effect; NO thiazide content expected",
     r"amlodipine|calcium channel|dihydropyridine", THZ),
    ("Q4", "iron supplements with blood pressure medication", "iron chelation / absorption (e.g. methyldopa; ACEI + IV iron reactions)",
     r"absor|chelat|methyldopa|ACE", None),
    ("Q5", "magnesium and diuretics elderly", "loop/thiazide diuretics → hypomagnesemia (K-sparing raise Mg)",
     r"hypomagnes|magnesium (loss|deplet|wast|excret)|low magnesium", None),
    ("Q6", "Can elderly take vitamin D with water pills?", "thiazide + vitamin D → hypercalcemia",
     r"thiazide|hypercalc|calcium", None),
    ("Q7", "降血壓藥和鉀離子補充劑", "ACEI/ARB/K-sparing + potassium → hyperkalemia (zh-TW)",
     r"hyperkal|高血鉀|血鉀|ACE|ARB|血管收縮素|保鉀|螺內酯", None),
    ("Q8", "sugar pills with BP meds", "LAY-TERM AMBIGUITY (placebo vs diabetes meds) — pass iff the answer flags or reasonably resolves it",
     r"placebo|diabet|glucose|metformin|clarif|unclear|ambig|assum", None),
    ("Q9", "aspirin with BP medication elderly", "CONTROL (named INN + class): aspirin blunts ACEI/diuretic effect, bleeding, renal; NO thiazide-specific content expected",
     r"ACE|bleed|renal|NSAID|antiplatelet|antihypertensive effect", THZ),
    ("Q10", "BP meds with grapefruit", "CYP3A4 inhibition → ↑ CCB (felodipine/nifedipine/amlodipine) levels",
     r"CYP3A4|CYP|felodipine|nifedipine|amlodipine|calcium channel", None),
    ("Q11", "calcium and lisinopril", "no clinically significant interaction expected; NO thiazide content expected",
     r"lisinopril|no (clinically )?significant|not (a )?(significant|known)|minimal|hyperkal", THZ),
    ("Q12", "potassium with spironolactone", "hyperkalemia (K-sparing + potassium) — the straddle family",
     r"hyperkal", None),
]


def d2(doc):
    st = getattr(doc.source_type, "value", doc.source_type)
    return {"source_id": doc.source_id, "source_type": st, "title": (doc.title or "")[:120]}


async def main():
    dev = assert_dev_db()
    from api.rag.retriever import _is_whitelisted_safety_section
    from api.rag.generator import AnswerGenerator
    from api.server import _annotate_research_question
    r, cfg = production_retriever()
    gen = AnswerGenerator()
    l0_model = gen._fallback_model
    captured: list = []
    orig_rw = r._rewrite_query

    async def rw(q):
        out = await orig_rw(q)
        captured.append(list(out))
        return out
    r._rewrite_query = rw

    rows = []
    t_start = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for qid, q, expected, mech_re, over_re in QS:
        lang = "zh-TW" if CJK.search(q) else "en"
        annotated = _annotate_research_question(q)
        runs = []
        for i in range(N):
            captured.clear()
            t0 = time.perf_counter()
            docs, status = await r.retrieve(query=annotated, max_results=cfg["max_results"],
                                            source_weight_active=cfg["source_weight_active"])
            answer, events = "", []
            async for ev in gen.generate_stream(question=annotated, documents=docs, retrieval_status=status,
                                                query_type="research", lang=lang, usage_out=[],
                                                model_override=l0_model):
                t = getattr(ev.type, "value", str(ev.type))
                events.append(t)
                if t == "answer":
                    answer += ev.content or ""
            (HERE / f"step9_answer_{qid}_r{i+1}.md").write_text(answer, encoding="utf-8")
            run = {"run": i + 1, "status": status, "seconds": round(time.perf_counter() - t0, 1),
                   "rewrite_calls": [list(c) for c in captured],
                   "final": [d2(d) for d in docs],
                   "dm_safety_in_final": [d.source_id for d in docs if _is_whitelisted_safety_section(d)],
                   "path": "FALLBACK (no docs)" if not docs else "grounded",
                   "events": sorted(set(events)), "answer_chars": len(answer),
                   "premark_mechanism": bool(re.search(mech_re, answer, re.I)),
                   "premark_thiazide_content": bool(re.search(THZ, answer, re.I)),
                   "premark_over_trigger": bool(over_re and re.search(over_re, answer, re.I))}
            runs.append(run)
            print(f"[{qid} r{i+1}] {status} {run['seconds']}s dm_safety={len(run['dm_safety_in_final'])} "
                  f"mech={run['premark_mechanism']} thz={run['premark_thiazide_content']} "
                  f"over={run['premark_over_trigger']} | rw0={run['rewrite_calls'][0] if run['rewrite_calls'] else None}",
                  flush=True)
        rows.append({"id": qid, "query": q, "annotated": annotated, "lang": lang, "expected_mechanism": expected,
                     "premark_mechanism_regex": mech_re, "over_trigger_regex": over_re, "runs": runs})
    res = {"probe": "E6 mini — generalisation + over-trigger, L0 binding", "head": "a6d59b9 (prod fly 261 code)",
           "db_branch": dev, "n_per_query": N, "l0_model": l0_model, "started_utc": t_start,
           "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "config": {k: v for k, v in cfg.items() if k != "provenance"},
           "grading": "regex columns are PRE-MARKS; the grades of record are hand-read, in step9_e6_mini_grades.json",
           "rows": rows}
    json.dump(res, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("done", t_start, "->", res["finished_utc"])


if __name__ == "__main__":
    asyncio.run(main())
