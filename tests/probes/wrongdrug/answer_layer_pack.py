# -*- coding: utf-8 -*-
"""Answer-layer wrong-drug REVIEW PACK builder — MEASUREMENT ONLY, in-process.

WHAT THIS IS: it produces a pack a FOUNDER scores. It does NOT judge correctness.
There is NO LLM judge anywhere in this file, and no PASS/FAIL is ever emitted.

WHY A NEW RUNNER (checked before writing one, per the baton):
  · scripts/citation_truth_check.py — emits question + full answer + citations, but ONLY
    over HTTP to a RUNNING SERVER (BASE_URL + /api/research). Not viable on this box: the
    uvicorn server is OOM-killed after ~10 requests (8.1 GB RAM, ~1.0 GB free) — reproduced
    twice and documented in docs/poolsize_distribution_harvest.md's deviation box. Its whole
    flow is also judge-based.
  · tests/run_golden_tests.py — same HTTP transport, plus an LLM judge.
  · scripts/dailymed_danger_path_verify.py — in-process and closest in shape, but truncates
    the answer to 400 chars, covers 3 fixed queries, and runs a judge.
None emits {question + FULL answer + every citation with source_id/title + status} without a
server or a judge. Hence this file, in tests/probes/<topic>/ per Rule 20.

OWNERSHIP IS REUSED, NOT REIMPLEMENTED: moiety comes from owner_assertion.CorpusIndex
(source_id -> setid -> corpus -> moiety). No text matching decides ownership.

⚠️ THE ONE PIECE OF TEXT MATCHING, AND WHAT IT IS NOT: the MECHANICAL flag compares the
QUESTION text against corpus moiety strings to ORDER THE FOUNDER'S READING. It is not an
ownership determination and never becomes one — owner_assertion.py's Constraint 1 forbids
mention-based ownership, and nothing here contradicts it. The flag runs in the opposite
direction (question -> moiety, to sort), and it is labelled MECHANICAL in every output.

PARITY with the recorded runs: bare HybridRetriever() (matches production post-c1),
_annotate_research_question applied, max_results=5, source_weight_active=True, in-process.
READ-ONLY on product code.
"""
import asyncio, io, json, os, re, sys, time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(r"C:\Users\andre\projects\Vela")
HERE = Path(__file__).parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TEST_MODE", "true")
os.environ["SOURCE_WEIGHT_ACTIVE"] = "true"
from dotenv import load_dotenv                              # noqa: E402
load_dotenv(ROOT / ".env", override=True)
from api.rag.retriever import HybridRetriever               # noqa: E402
from api.rag.generator import AnswerGenerator               # noqa: E402
from api.models.schemas import StreamEventType              # noqa: E402
from api.server import _annotate_research_question          # noqa: E402

import importlib.util as _ilu                               # noqa: E402


def _load(name, path):
    """⚠️ The module MUST be registered in sys.modules BEFORE exec_module: owner_assertion.py
    uses @dataclass, and dataclasses resolves annotations via sys.modules[cls.__module__].
    Without the registration that lookup returns None and the decorator raises."""
    spec = _ilu.spec_from_file_location(name, path)
    mod = _ilu.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_oa = _load("owner_assertion_pack", HERE / "owner_assertion.py")
_res = _load("resolver_pack", ROOT / "tests/probes/ownership_eval/resolver.py")

STAMP = time.strftime("%Y%m%d_%H%M%S")
OUT_JSON = HERE / f"answer_layer_pack_{STAMP}.json"
OUT_MD = HERE / f"answer_layer_pack_{STAMP}.md"

MISFIRES = [
    ("MF01", "calcium channel blocker mechanism"),
    ("MF02", "atorvastatin calcium side effects"),
    ("MF03", "low sodium diet and blood pressure"),
    ("MF04", "potassium supplements in CKD"),
]


def load_cases():
    d = json.load(open(ROOT / "tests" / "golden_dataset.json", encoding="utf-8"))
    cases = d if isinstance(d, list) else d.get("cases", [])
    r = [(c["id"], c["query"]) for c in sorted(cases, key=lambda x: x["id"])
         if c.get("category") == "research" and c["id"].startswith("R") and c["id"][1:].isdigit()]
    return r + MISFIRES


def mechanical_flag(question: str, moiety: str, idx) -> str:
    """MECHANICAL ONLY. Whole-token presence of the moiety (or its salt-base form) in the
    QUESTION. Never a verdict. Returns MATCH / NO-MATCH / NO-DRUG-IN-QUESTION."""
    q = (question or "").lower()
    if not _res.resolve_key_set(question, idx)["keys"]:
        return "NO-DRUG-IN-QUESTION"
    forms = {moiety, _res.strip_salt_suffixes(moiety)}
    for f in forms:
        if f and re.search(r"(?<![a-z0-9])" + re.escape(f.lower()) + r"(?![a-z0-9])", q):
            return "MATCH"
    return "NO-MATCH"


async def main():
    corpus = _oa.CorpusIndex.load()
    docs_all = json.loads((ROOT / "data/dailymed/label_docs.json").read_text(encoding="utf-8"))["documents"]
    idx = _res.MoietyIndex(docs_all)

    retriever = HybridRetriever()
    generator = AnswerGenerator()
    cases = load_cases()
    rep = {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "n_cases": len(cases), "N_per_case": 1,
           "config": {"max_results": 5, "source_weight_active": True,
                      "annotate_research_question": True,
                      "retriever": "bare HybridRetriever() — matches production post-c1",
                      "transport": "in-process; NO server, NO LLM judge"},
           "units": []}
    print(f"=== answer-layer pack: {len(cases)} cases x N=1 ===\n", flush=True)

    for cid, q in cases:
        t0 = time.perf_counter()
        annotated = _annotate_research_question(q)
        try:
            docs, status = await retriever.retrieve(query=annotated, max_results=5,
                                                    source_weight_active=True)
            parts = []
            async for ev in generator.generate_stream(q, docs, retrieval_status=status,
                                                      query_type="research"):
                if ev.type == StreamEventType.ANSWER and ev.content:
                    parts.append(ev.content)
            answer = "".join(parts)
            cits = []
            for i, d in enumerate(docs, 1):
                st = str(getattr(d.source_type, "value", d.source_type))
                setid = _oa.parse_setid(d.source_id or "")
                moiety = corpus.setid_to_moiety.get(setid) if setid else None
                cits.append({
                    "n": i, "source_type": st, "source_id": d.source_id, "title": d.title,
                    "moiety": moiety,
                    "mechanical_flag": (mechanical_flag(q, moiety, idx) if moiety else None),
                })
            rep["units"].append({
                "id": cid, "question": q, "status": status,
                "latency_s": round(time.perf_counter() - t0, 1),
                "answer": answer, "citations": cits,
                "resolver_keys": sorted(_res.resolve_key_set(q, idx)["keys"]),
                "n_dailymed": sum(1 for c in cits if c["source_type"] == "dailymed"),
                "n_no_match": sum(1 for c in cits if c["mechanical_flag"] == "NO-MATCH"),
            })
        except Exception as e:
            rep["units"].append({"id": cid, "question": q, "error": f"{type(e).__name__}: {e}"})
        OUT_JSON.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
        u = rep["units"][-1]
        print(f"  {cid:6} status={u.get('status','ERR'):<11} dm={u.get('n_dailymed','-')} "
              f"no_match={u.get('n_no_match','-')}  {u.get('latency_s','-')}s", flush=True)

    rep["complete"] = True
    OUT_JSON.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n-> {OUT_JSON}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
