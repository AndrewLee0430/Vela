"""Canary gate — non-safety Research queries must NOT cite DailyMed safety sections.

ENFORCING GATE (founder ruling 2026-08-21). The predecessor
(`tests/results/_pairaware_m1.py`, untracked) printed `(want 0)` and **asserted
nothing** — it was a measurement script that read as a gate. That is the defect
this file fixes: every criterion below is asserted, and a violation exits
non-zero.

⚠️⚠️ CRITERION AMENDED 2026-08-21 — THIS IS A DELIBERATE LOOSENING OF AN
EXISTING GATE, NOT A REFINEMENT. Founder ruling, recorded verbatim:

  OLD: zero whitelisted DailyMed safety LOINC in the final top-5.
  NEW: zero WRONG-OBJECT safety LOINC in the final top-5 — a whitelisted
       safety section whose moiety is OUTSIDE the query's key set. An OWNED
       safety section no longer fails the gate.

  WHY: "The canary was born on the wrong-drug line; what it exists to catch is
  wrong-DRUG intrusion. The reserved-seat mechanism (主線 A) injects a queried
  drug's OWN safety sections by key, so under the old criterion the seat fails
  `metformin mechanism of action` — measured in seat_v2.json: METFORMIN owns
  four whitelisted safety sections (Warnings 0.5263, Boxed Warning 0.5139,
  Contraindications 0.4945, Drug Interactions 0.4711), all below the 0.6 floor
  and therefore all seatable. Blocking the seat on that basis would use a proxy
  metric to veto the fix the metric exists to enable. The other five canaries
  are unaffected: statin / SGLT2 / GLP-1 are class terms with no corpus key."

  WHAT IT COSTS — KNOWN UNCOVERED CASE, stated plainly: the old criterion also
  caught an OWNED safety section appearing in a mechanism-of-action question,
  i.e. TOPICAL MISMATCH. That is now UNGUARDED. Accepted on the founder ruling
  that an owned section is at worst noise, whereas a wrong-drug section is a
  safety claim about the wrong substance. WHAT WOULD RE-OPEN IT: user-visible
  evidence that owned-but-off-topic sections degrade answers.

  BOTH COUNTERS ARE RECORDED PER QUERY (`safety_cited` = old criterion,
  `wrong_object_cited` = new) so the two eras stay comparable and a future
  reader can see exactly what the loosening covered.

CRITERION, per query:
  N=8 real `retrieve()` calls — FULL PIPELINE / REWRITE ARM, the same arm the
  predecessor used. PASS iff ZERO usable runs cite a WRONG-OBJECT whitelisted
  DailyMed safety LOINC in the final top-`max_results`.
  · usable = status not in ("no_results","error"); those two are network noise
    (retrieve() short-circuits before any filter/rerank stage) and are counted
    separately. status=="irrelevant" IS usable — docs were retrieved.
  · usable_runs < MIN_USABLE_RUNS fails the query: a canary that mostly errored
    is not a pass.

KEY-ONLY DETECTION (CLAUDE.md Rule 21): a citation is a safety section iff its
`source_id` parses as `DailyMed:{setid}#{loinc}` and `loinc` is in the
production whitelist, which is IMPORTED from `api/rag/retriever.py` and never
copied. OWNERSHIP is decided by the same key discipline: `setid` → `moiety`
joined from `data/dailymed/label_docs.json` (a TOTAL, conflict-free join —
1,038 setids, 0 conflicts), compared against the query's key set. No
title/content text is ever inspected, and ownership is never decided by
substring.

THE QUERY'S KEY SET comes from `tests/probes/ownership_eval/resolver.py`,
loaded by file path — the shared module that also serves the ownership work.
It is NOT copied here; it in turn IMPORTS `strip_salt_suffixes` from
`seat_measurement.py`. A query that resolves to NOTHING (a class term such as
`statin` / `SGLT2` / `GLP-1`) has an EMPTY key set, so EVERY whitelisted safety
section is wrong-object for it — meaning the new criterion is EXACTLY AS STRICT
as the old one for class queries. That equivalence is ASSERTED at runtime per
query and recorded in the JSON as `class_query_equivalence`.

PRODUCTION PARITY (CLAUDE.md TECH_DEBT open item #8): the predecessor
constructed `HybridRetriever()` BARE, so when the `enable_local` default flipped
on 2026-07-29 its 2026-07-27 baseline silently expired — it had measured five
sources, production now runs four. This gate therefore names EVERY flag and
sources each one from `api/server.py` at runtime, cross-checking what it cannot
parse, and records the fully resolved configuration in the result JSON. A parse
miss or a cross-check mismatch is a LOUD STOP, never a default.

Run:   python tests/probes/canary/canary_gate.py            # full gate, 48 real calls
       python tests/probes/canary/canary_gate.py --self-test  # negative control only, 0 API calls
Exit:  0 = all queries clean · 1 = gate FAILED · 2 = could not establish config/run
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# The stores' load-status print()s carry emoji (vector_store.py:44/:52 — the recorded
# cp950 console class, TECH_DEBT queue #9). Reconfigure THIS process's stdio; no api/ change.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

N_RUNS = 8
MIN_USABLE_RUNS = 6          # of N_RUNS; below this the query FAILS (founder ruling)

# ── THE CANONICAL CANARY SET (founder ruling 2026-08-21) ──────────────────────
# Six queries. Five are the M1 set; the sixth is the statin variant that reached
# TRACKED files, kept deliberately — see README "The two statin variants".
# Byte identity against the untracked sources is CHECKED at runtime by
# `check_string_provenance()` below, not asserted from memory.
CANARIES: tuple[tuple[str, str], ...] = (
    ("metformin_moa", "metformin mechanism of action"),
    ("statin_moa", "statin mechanism of action pharmacology"),
    ("glp1_weight", "GLP-1 減重機轉"),
    ("statin_efficacy", "statin primary prevention efficacy"),
    ("sglt2_cv", "SGLT2 inhibitor cardiovascular outcomes"),
    ("statin_moa_tracked", "What is the mechanism of action of statins?"),
)

# Where each string came from. `id_in_source` differs for the sixth: the founder
# named it `statin_moa_tracked`; its source calls it `canary_statin_moa`.
STRING_PROVENANCE = {
    "metformin_moa": ("tests/results/_pairaware_m1.py", "metformin_moa"),
    "statin_moa": ("tests/results/_pairaware_m1.py", "statin_moa"),
    "glp1_weight": ("tests/results/_pairaware_m1.py", "glp1_weight"),
    "statin_efficacy": ("tests/results/_pairaware_m1.py", "statin_efficacy"),
    "sglt2_cv": ("tests/results/_pairaware_m1.py", "sglt2_cv"),
    "statin_moa_tracked": ("tests/results/_c1_freedslot_probe.py", "canary_statin_moa"),
}

HISTORICAL_FIVE_SOURCE = (
    "0/8 each, 2026-07-27, enable_local=True, NOT reproducible at HEAD"
)

HISTORICAL_HEAD_OLD_CRITERION = (
    "0/8 each on the OLD criterion (any whitelisted safety LOINC), 2026-08-21, "
    "HEAD four-source config, 6 queries, 48/48 usable runs, zero exclusions — "
    "canary_baseline_20260821.json, the pre-amendment baseline"
)

REPRODUCIBILITY_NOTE = (
    "PubMed drift makes exact reproduction impossible — the baseline is a dated "
    "snapshot. Every run queries live PubMed/FDA and calls a non-deterministic LLM "
    "rewrite (temperature=0 but no seed and no cache), so pool composition varies "
    "between runs and between days. Re-running this gate re-measures; it does not "
    "reproduce. The PASS criterion (zero safety citations) is stable under that "
    "drift by design — it asserts an absence, not a pool identity."
)


def _fail(msg: str, code: int = 2):
    print(f"LOUD STOP: {msg}", flush=True)
    raise SystemExit(code)


# ── production configuration: parsed / cross-checked, never silently defaulted ──

def load_production_config() -> dict:
    """Resolve production's retriever construction from api/server.py + api/rag/retriever.py.

    Anything not parseable from server.py is cross-checked against its real source
    and recorded with provenance. A parse miss or mismatch is a LOUD STOP.
    """
    server_src = (ROOT / "api" / "server.py").read_text(encoding="utf-8")
    retr_src = (ROOT / "api" / "rag" / "retriever.py").read_text(encoding="utf-8")

    m = re.search(r"^retriever = HybridRetriever\((.*?)^\)", server_src, re.S | re.M)
    if not m:
        _fail("could not locate the production `retriever = HybridRetriever(...)` "
              "construction in api/server.py")
    block = m.group(1)
    # strip full-line comments so kwargs parse cleanly (the block is heavily commented)
    body = "\n".join(ln for ln in block.splitlines() if not ln.strip().startswith("#"))

    def kw(name: str, cast):
        mm = re.search(rf"\b{name}\s*=\s*([A-Za-z0-9_.]+)", body)
        return None if not mm else cast(mm.group(1))

    def as_bool(s: str) -> bool:
        if s not in ("True", "False"):
            _fail(f"non-literal boolean for a production flag: {s!r}")
        return s == "True"

    cfg: dict = {}
    prov: dict = {}

    for flag in ("enable_local", "enable_pubmed", "enable_fda", "enable_tfda",
                 "enable_dailymed"):
        val = kw(flag, as_bool)
        if val is None:
            # not passed by production → it takes the constructor default; assert that
            # default against the real signature rather than assuming it.
            dm = re.search(rf"\b{flag}:\s*bool\s*=\s*(True|False)", retr_src)
            if not dm:
                _fail(f"{flag} is neither passed by api/server.py nor parseable as a "
                      f"constructor default in api/rag/retriever.py")
            val = dm.group(1) == "True"
            prov[flag] = ("NOT passed by api/server.py; constructor default in "
                          "api/rag/retriever.py")
        else:
            prov[flag] = "api/server.py HybridRetriever(...) construction"
        cfg[flag] = val

    thr = kw("local_threshold", float)
    if thr is None:
        _fail("local_threshold not parseable from the production construction")
    thr_def = re.search(r"local_threshold:\s*float\s*=\s*([0-9.]+)", retr_src)
    if not thr_def:
        _fail("local_threshold default not parseable from api/rag/retriever.py")
    if float(thr_def.group(1)) != thr:
        _fail(f"local_threshold MISMATCH — server.py {thr} vs retriever.py default "
              f"{thr_def.group(1)}; re-derive before trusting this gate")
    cfg["local_threshold"] = thr
    prov["local_threshold"] = ("api/server.py construction, cross-checked against the "
                               "api/rag/retriever.py constructor default")

    mr = re.search(r"max_results=body\.max_results\s+or\s+(\d+)", server_src)
    if not mr:
        _fail("could not parse production max_results from api/server.py")
    mr_def = re.search(r"max_results:\s*int\s*=\s*(\d+)", retr_src)
    if not mr_def:
        _fail("could not parse retrieve() max_results default from api/rag/retriever.py")
    if mr.group(1) != mr_def.group(1):
        _fail(f"max_results MISMATCH — server.py fallback {mr.group(1)} vs retrieve() "
              f"default {mr_def.group(1)}")
    cfg["max_results"] = int(mr.group(1))
    prov["max_results"] = ("api/server.py retrieve(max_results=body.max_results or N), "
                           "cross-checked against the retrieve() signature default")

    # source_weight_active is a RUNTIME env flag, not a code literal. Assert the exact
    # read exists in server.py; its deployed value is an operational fact, recorded.
    if not re.search(r'os\.getenv\(\s*"SOURCE_WEIGHT_ACTIVE"\s*,\s*""\s*\)\.lower\(\)\s*==\s*"true"',
                     server_src):
        _fail("the SOURCE_WEIGHT_ACTIVE read expected at api/server.py is missing or "
              "changed shape — production parity for this flag can no longer be asserted")
    cfg["source_weight_active"] = True
    prov["source_weight_active"] = (
        "env flag read at api/server.py (shape asserted here). Deployed value ON per "
        "docs/kunion_cut_exemption_build.md:72 and docs/local_corpus_deprecation_c1_build.md:20 "
        "(secret digest d8c5ac2e11c8e492, Deployed). Mirrors the predecessor probe."
    )

    # Production annotates the question before retrieval; the predecessor did too.
    if not re.search(r"_annotate_research_question\(body\.question\)", server_src):
        _fail("api/server.py no longer annotates the Research question via "
              "_annotate_research_question(body.question) — the gate's input shape "
              "would diverge from production")
    cfg["annotate_research_question"] = True
    prov["annotate_research_question"] = "api/server.py applies it before retrieve()"

    cfg["arm"] = "rewrite (full pipeline — real retrieve())"
    cfg["n_runs"] = N_RUNS
    cfg["min_usable_runs"] = MIN_USABLE_RUNS
    cfg["provenance"] = prov
    return cfg


# ── string provenance: verify byte identity against the untracked sources, if present ──

def check_string_provenance() -> dict:
    """Confirm each canary string is byte-identical to its source script.

    The sources are untracked (`.gitignore:113` hides tests/results/), so this is a
    one-machine check: absent sources are recorded as such, never treated as a pass.
    """
    out = {}
    for cid, query in CANARIES:
        rel, src_id = STRING_PROVENANCE[cid]
        p = ROOT / rel
        if not p.exists():
            out[cid] = {"source": rel, "id_in_source": src_id,
                        "status": "SOURCE ABSENT (untracked) — byte identity not checkable here"}
            continue
        text = p.read_text(encoding="utf-8")
        # look for the exact ("<id_in_source>", "<query>") tuple opening
        needle = f'("{src_id}", "{query}"'
        out[cid] = {"source": rel, "id_in_source": src_id,
                    "status": "BYTE-IDENTICAL" if needle in text else "MISMATCH"}
    return out


# ── key-only safety detection (Rule 21) ──

def make_safety_detector(whitelist: dict):
    def is_safety(source_id: str):
        """-> loinc when source_id is a whitelisted DailyMed safety section, else None."""
        sid = source_id or ""
        if not sid.startswith("DailyMed:") or "#" not in sid:
            return None
        loinc = sid.split("#", 1)[1].split("~", 1)[0]
        return loinc if loinc in whitelist else None
    return is_safety


def parse_setid(source_id: str) -> str:
    sid = source_id or ""
    if not sid.startswith("DailyMed:") or "#" not in sid:
        return ""
    return sid.split("DailyMed:", 1)[1].split("#", 1)[0]


def make_owner_detector(whitelist: dict, setid_to_moiety: dict, key_set: set):
    """-> is_wrong_object(source_id): True iff a whitelisted safety section whose
    OWNER MOIETY is outside `key_set`. Key-only: setid -> moiety join, never text.

    An EMPTY key_set makes every safety section wrong-object — the class-query
    case, where the amended criterion is exactly as strict as the old one."""
    is_safety = make_safety_detector(whitelist)

    def is_wrong_object(source_id: str) -> bool:
        if is_safety(source_id) is None:
            return False
        moiety = setid_to_moiety.get(parse_setid(source_id))
        if moiety is None:
            # unresolved setid: cannot prove ownership -> treat as wrong-object
            # (fail toward the stricter reading, never toward a silent pass)
            return True
        return moiety.upper().strip() not in key_set

    return is_wrong_object


# ── the decision function: PURE, so the negative control exercises the real path ──

def evaluate(query_records: list[dict]) -> tuple[int, dict, list[str]]:
    """-> (exit_code, aggregate, reasons). The single source of PASS/FAIL truth."""
    reasons: list[str] = []
    failed_safety, failed_usable = [], []
    for q in query_records:
        # AMENDED 2026-08-21: the gate keys on wrong_object_cited, NOT safety_cited.
        # safety_cited is still recorded (old criterion) so the eras stay comparable.
        if q["wrong_object_cited"] > 0:
            failed_safety.append(q["id"])
            reasons.append(
                f"{q['id']}: {q['wrong_object_cited']}/{q['usable_runs']} usable runs cited a "
                f"WRONG-OBJECT whitelisted DailyMed safety section (want 0)")
        if q["usable_runs"] < MIN_USABLE_RUNS:
            failed_usable.append(q["id"])
            reasons.append(
                f"{q['id']}: only {q['usable_runs']}/{N_RUNS} usable runs "
                f"(minimum {MIN_USABLE_RUNS}) — insufficient evidence, not a pass")
    agg = {
        "queries": len(query_records),
        "passed": len(query_records) - len(set(failed_safety) | set(failed_usable)),
        "failed": len(set(failed_safety) | set(failed_usable)),
        "failed_on_wrong_object_citation": failed_safety,
        "failed_on_insufficient_runs": failed_usable,
        "verdict": "PASS" if not reasons else "FAIL",
        "criterion": "wrong-object safety LOINC in the final top-N (AMENDED 2026-08-21; "
                     "the old criterion was ANY safety LOINC and is still recorded per "
                     "query as safety_cited)",
        "old_criterion_would_have_failed": [q["id"] for q in query_records
                                            if q["safety_cited"] > 0],
    }
    return (0 if not reasons else 1), agg, reasons


def summarize_runs(cid: str, query: str, runs: list[dict], key_info: dict) -> dict:
    usable = [r for r in runs if "error" not in r
              and r.get("status") not in ("no_results", "error")]
    netexc = [r for r in runs if "error" not in r
              and r.get("status") in ("no_results", "error")]
    errored = [r for r in runs if "error" in r]
    safety_cited = sum(1 for r in usable if r.get("safety_cited_ids"))
    wrong_cited = sum(1 for r in usable if r.get("wrong_object_cited_ids"))
    rec = {
        "id": cid,
        "query": query,
        "resolved_key_set": sorted(key_info["keys"]),
        "resolver_matched": key_info["matched"],
        "resolver_via": key_info["via"],
        "runs": runs,
        "usable_runs": len(usable),
        "network_excluded": len(netexc),
        "errored": len(errored),
        "safety_cited": safety_cited,            # OLD criterion — recorded, not gated on
        "wrong_object_cited": wrong_cited,       # NEW criterion — what the gate keys on
    }
    # ASSERTION: for a class query (empty key set) the two criteria MUST coincide.
    if not key_info["keys"]:
        rec["class_query_equivalence"] = {
            "empty_key_set": True,
            "safety_cited": safety_cited,
            "wrong_object_cited": wrong_cited,
            "equivalent": safety_cited == wrong_cited,
            "note": "empty key set => every safety section is wrong-object => the amended "
                    "criterion is EXACTLY as strict as the old one for this query",
        }
        if safety_cited != wrong_cited:
            _fail(f"{cid}: empty key set but safety_cited={safety_cited} != "
                  f"wrong_object_cited={wrong_cited} — the class-query equivalence the "
                  f"amendment depends on is BROKEN")
    else:
        rec["class_query_equivalence"] = {"empty_key_set": False}
    return rec


# ── the negative control (CLAUDE.md Rule 17): the gate must be able to FAIL ──

SYNTHETIC_SAFETY_ID = "DailyMed:00000000-0000-0000-0000-000000000000#34073-7"


def _blank(cid: str, safety: int, wrong: int) -> dict:
    return {"id": cid, "query": "(fabricated control record)", "runs": [],
            "usable_runs": N_RUNS, "network_excluded": 0, "errored": 0,
            "safety_cited": safety, "wrong_object_cited": wrong}


def run_self_test(query_records: list[dict], is_safety) -> dict:
    """TWO required injections (Rule 17), both driving the SAME evaluate().

    (a) a WRONG-OBJECT safety doc  -> the gate MUST exit non-zero.
    (b) an OWNED safety doc into metformin_moa -> the gate MUST exit ZERO under
        the amended criterion, with safety_cited=1 and wrong_object_cited=0.
        (b) is what proves the 2026-08-21 loosening actually landed and that the
        two counters are independent.
    """
    detected = is_safety(SYNTHETIC_SAFETY_ID)
    if detected is None:
        return {"outcome": "BROKEN", "detail":
                "the synthetic id was NOT recognised as a whitelisted safety section — "
                "the detector cannot see what it must catch"}

    base = copy.deepcopy(query_records) if query_records else [_blank("synthetic", 0, 0)]
    basis = (f"real result set ({len(query_records)} queries)" if query_records
             else "fabricated records (--self-test, zero API calls)")

    # ── (a) WRONG-OBJECT injection: must FAIL ──
    inj_a = copy.deepcopy(base)
    inj_a[0]["usable_runs"] = max(inj_a[0]["usable_runs"], MIN_USABLE_RUNS)
    inj_a[0]["safety_cited"] = 1
    inj_a[0]["wrong_object_cited"] = 1
    code_a, _, reasons_a = evaluate(inj_a)

    # ── (b) OWNED injection into metformin_moa: must PASS ──
    inj_b = copy.deepcopy(base)
    target_b = next((q for q in inj_b if q["id"] == "metformin_moa"), None)
    if target_b is None:
        target_b = _blank("metformin_moa", 0, 0)
        inj_b.append(target_b)
    target_b["usable_runs"] = max(target_b["usable_runs"], MIN_USABLE_RUNS)
    target_b["safety_cited"] = 1        # an OWNED safety section WAS cited
    target_b["wrong_object_cited"] = 0  # ...but it belongs to the queried drug
    code_b, agg_b, reasons_b = evaluate(inj_b)

    # ── clean control: neither counter set -> must PASS ──
    clean = copy.deepcopy(base)
    for q in clean:
        q["usable_runs"] = max(q["usable_runs"], MIN_USABLE_RUNS)
        q["safety_cited"] = 0
        q["wrong_object_cited"] = 0
    code_clean, _, _ = evaluate(clean)

    ok = (code_a != 0) and (code_b == 0) and (code_clean == 0)
    return {
        "outcome": ("PASS — the gate fails on wrong-object and passes on owned"
                    if ok else "BROKEN"),
        "basis": basis,
        "injected_source_id": SYNTHETIC_SAFETY_ID,
        "detected_loinc": detected,
        "a_wrong_object_injection": {
            "expect": "non-zero", "exit_code": code_a, "ok": code_a != 0,
            "reasons_seen": reasons_a,
        },
        "b_owned_injection_into_metformin_moa": {
            "expect": "zero (the amendment)", "exit_code": code_b, "ok": code_b == 0,
            "safety_cited": target_b["safety_cited"],
            "wrong_object_cited": target_b["wrong_object_cited"],
            "counters_independent": (target_b["safety_cited"] == 1
                                     and target_b["wrong_object_cited"] == 0),
            "old_criterion_would_have_failed": agg_b["old_criterion_would_have_failed"],
            "note": "THIS is the control that proves the 2026-08-21 loosening landed: an "
                    "owned safety section is cited (safety_cited=1, the OLD criterion would "
                    "have failed) yet the gate exits 0 because it is not wrong-object.",
        },
        "clean_control": {"expect": "zero", "exit_code": code_clean, "ok": code_clean == 0},
        "note": ("A gate that has never failed has not been shown to work. Both controls "
                 "drive the SAME evaluate() the real gate uses."),
    }


# ── the run ──

async def run_query(retriever, annotate, cid, query, is_safety, cfg,
                    is_wrong_object) -> list[dict]:
    runs = []
    annotated = annotate(query)
    for i in range(N_RUNS):
        t0 = time.perf_counter()
        try:
            docs, status = await retriever.retrieve(
                query=annotated,
                max_results=cfg["max_results"],
                source_weight_active=cfg["source_weight_active"],
            )
            cited = [d.source_id for d in docs]
            runs.append({
                "run": i,
                "status": status,
                "latency_s": round(time.perf_counter() - t0, 1),
                "cited_ids": cited,
                "safety_cited_ids": [s for s in cited if is_safety(s)],
                "wrong_object_cited_ids": [s for s in cited if is_wrong_object(s)],
            })
        except Exception as e:
            runs.append({"run": i, "error": f"{type(e).__name__}: {e}",
                         "latency_s": round(time.perf_counter() - t0, 1)})
        print(f"    {cid} run {i + 1}/{N_RUNS}: {runs[-1].get('status', 'ERROR')}"
              f"  cited={len(runs[-1].get('cited_ids', []))}"
              f"  safety={len(runs[-1].get('safety_cited_ids', []))}", flush=True)
    return runs


async def main_async(self_test_only: bool) -> int:
    from api.rag.retriever import _SAFETY_SECTION_WHITELIST
    is_safety = make_safety_detector(_SAFETY_SECTION_WHITELIST)

    if self_test_only:
        st = run_self_test([], is_safety)
        print(json.dumps(st, ensure_ascii=False, indent=1))
        return 0 if st["outcome"].startswith("PASS") else 1

    # the SHARED resolver + the setid->moiety key join (loaded by path, never copied)
    import importlib.util as _ilu
    _rp = ROOT / "tests" / "probes" / "ownership_eval" / "resolver.py"
    _spec = _ilu.spec_from_file_location("ownership_resolver", _rp)
    _res = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_res)
    _bqs_path = ROOT / "tests" / "probes" / "ownership_eval" / "build_query_set.py"
    _bspec = _ilu.spec_from_file_location("ownership_build_query_set_for_canary", _bqs_path)
    _bqs = _ilu.module_from_spec(_bspec)
    _bspec.loader.exec_module(_bqs)
    corpus = _bqs.load_corpus()
    moiety_index = _res.MoietyIndex(corpus)
    setid_to_moiety = _res.MoietyIndex.setid_to_moiety(corpus)

    cfg = load_production_config()
    provenance = check_string_provenance()
    bad = {k: v for k, v in provenance.items() if v["status"] == "MISMATCH"}
    if bad:
        _fail(f"canary string(s) differ from their source script: {bad}")

    os.environ["TEST_MODE"] = os.environ.get("TEST_MODE", "true")
    os.environ["SOURCE_WEIGHT_ACTIVE"] = "true" if cfg["source_weight_active"] else ""

    from api.rag.retriever import HybridRetriever
    from api.server import _annotate_research_question

    retriever = HybridRetriever(
        local_threshold=cfg["local_threshold"],
        enable_local=cfg["enable_local"],
        enable_pubmed=cfg["enable_pubmed"],
        enable_fda=cfg["enable_fda"],
        enable_tfda=cfg["enable_tfda"],
        enable_dailymed=cfg["enable_dailymed"],
    )

    print(f"config: {json.dumps({k: v for k, v in cfg.items() if k != 'provenance'}, ensure_ascii=False)}\n",
          flush=True)

    t_start = time.perf_counter()
    started = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    records = []
    for cid, query in CANARIES:
        key_info = _res.resolve_key_set(query, moiety_index)
        is_wrong_object = make_owner_detector(_SAFETY_SECTION_WHITELIST, setid_to_moiety,
                                              {k.upper() for k in key_info["keys"]})
        print(f"  [{cid}] {query!r}  key_set={sorted(key_info['keys']) or 'EMPTY (class query)'}",
              flush=True)
        runs = await run_query(retriever, _annotate_research_question, cid, query,
                               is_safety, cfg, is_wrong_object)
        rec = summarize_runs(cid, query, runs, key_info)
        records.append(rec)
        print(f"  -> wrong_object_cited={rec['wrong_object_cited']}/{rec['usable_runs']} "
              f"(gate)  safety_cited={rec['safety_cited']}/{rec['usable_runs']} (old) "
              f"net_excl={rec['network_excluded']} err={rec['errored']}\n", flush=True)
    wall = round(time.perf_counter() - t_start, 1)

    exit_code, agg, reasons = evaluate(records)
    self_test = run_self_test(records, is_safety)
    if not self_test["outcome"].startswith("PASS"):
        exit_code = max(exit_code, 1)
        reasons.append("negative control BROKEN — the gate could not be shown to fail")

    git_head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, cwd=ROOT).stdout.strip()
    result = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"),
        "started": started,
        "git_head": git_head,
        "config": cfg,
        "string_provenance": provenance,
        "queries": records,
        "aggregate": {**agg, "exit_code": exit_code, "reasons": reasons},
        "self_test": self_test,
        "exclusions": {
            "network_zero_doc_runs": sum(r["network_excluded"] for r in records),
            "errored_runs": sum(r["errored"] for r in records),
            "rule": 'status in ("no_results","error") is network noise — retrieve() '
                    "short-circuits before any filter/rerank stage, so those runs cannot "
                    'distinguish a miss from an outage. status=="irrelevant" is USABLE.',
        },
        "wall_clock": {"seconds": wall, "retrieve_calls": len(CANARIES) * N_RUNS,
                       "note": f"{len(CANARIES)} queries x {N_RUNS} runs, each a real "
                               f"retrieve() with an LLM rewrite and live PubMed/FDA"},
        "criterion_amendment": {
            "date": "2026-08-21",
            "type": "DELIBERATE LOOSENING of an existing gate — not a refinement",
            "old": "zero whitelisted DailyMed safety LOINC in the final top-N",
            "new": "zero WRONG-OBJECT safety LOINC in the final top-N (moiety outside the "
                   "query's key set); an OWNED safety section no longer fails",
            "reason_verbatim": (
                "The canary was born on the wrong-drug line; what it exists to catch is "
                "wrong-DRUG intrusion. The reserved-seat mechanism (主線 A) injects a "
                "queried drug's OWN safety sections by key, so under the old criterion the "
                "seat fails `metformin mechanism of action` — measured in seat_v2.json: "
                "METFORMIN owns four whitelisted safety sections (Warnings 0.5263, Boxed "
                "Warning 0.5139, Contraindications 0.4945, Drug Interactions 0.4711), all "
                "below the 0.6 floor and therefore all seatable. Blocking the seat on that "
                "basis would use a proxy metric to veto the fix the metric exists to "
                "enable. The other five canaries are unaffected: statin / SGLT2 / GLP-1 "
                "are class terms with no corpus key."),
            "known_uncovered_case": (
                "The old criterion ALSO caught an OWNED safety section appearing in a "
                "mechanism-of-action question — topical mismatch. That is now UNGUARDED. "
                "Accepted on the founder ruling that an owned section is at worst noise, "
                "whereas a wrong-drug section is a safety claim about the wrong substance."),
            "what_would_reopen_it": (
                "User-visible evidence that owned-but-off-topic sections degrade answers."),
            "resolver": "tests/probes/ownership_eval/resolver.py (SHARED module, loaded by "
                        "path; it imports strip_salt_suffixes from seat_measurement.py — no "
                        "logic is copied)",
        },
        "reproducibility_note": REPRODUCIBILITY_NOTE,
        "historical": {"five_source_baseline": HISTORICAL_FIVE_SOURCE,
                       "head_old_criterion_baseline": HISTORICAL_HEAD_OLD_CRITERION,
                       "detail": "tests/results/pairaware_m1_20260727_161811.json "
                                 "(untracked): 5 canaries, 0/8 each, 8 usable runs, 0 "
                                 "exclusions, measured with enable_local=True before the "
                                 "2026-07-29 c1 default flip (c9d36cf). Retained as a "
                                 "dated historical figure for the FIVE-SOURCE ERA; it is "
                                 "not a HEAD baseline and must not be compared as one."},
    }
    out = HERE / f"canary_baseline_{datetime.now().strftime('%Y%m%d')}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    print("=" * 72)
    for r in records:
        print(f"  {r['id']:20} safety_cited={r['safety_cited']}/{r['usable_runs']}"
              f"  net_excl={r['network_excluded']}  err={r['errored']}")
    print(f"\n  verdict: {agg['verdict']}   exit={exit_code}   wall_clock={wall}s")
    print(f"  self-test: {self_test['outcome']}")
    for x in reasons:
        print(f"  REASON: {x}")
    print(f"  wrote {out}")
    return exit_code


def main() -> int:
    ap = argparse.ArgumentParser(description="Canary gate — enforcing.")
    ap.add_argument("--self-test", action="store_true",
                    help="run ONLY the negative control (zero API calls)")
    args = ap.parse_args()
    return asyncio.run(main_async(args.self_test))


if __name__ == "__main__":
    raise SystemExit(main())
