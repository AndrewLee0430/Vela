"""Exercise the ownership assertion against RECORDED evidence. No network, no retrieval.

Why replay and not a live run: the T1 baton scopes this to the test/harness layer with
no network. Every input here is a committed artifact, so the probe is deterministic and
its findings are reproducible by anyone with the repo — which is precisely what
tests/probes/README.md exists to guarantee.

Three replay sources:
  1. tests/probes/c2/c2_ab_retrieval.json   — fixture pools, control + treatment, N=3
  2. tests/probes/c2/c2_variance.json       — fixture pools, control + treatment, N=6
  3. tests/results/golden_results_20260729_230006.json — the c1-ship §2.7 gate (20/0/0)

Source 3 is the CALIBRATION: it answers "would this assertion have changed the verdict
of a gate we already passed?" If the answer were 'nothing, anywhere', the assertion would
have no discriminating power and the design would be wrong.

Run:  python tests/probes/wrongdrug/replay_probe.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from owner_assertion import (  # noqa: E402
    OUTCOMES,
    CorpusIndex,
    assert_whitelist_in_sync,
    classify_citation,
    classify_fixture,
    parse_setid,
    tally,
)

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
AB = ROOT / "tests/probes/c2/c2_ab_retrieval.json"
VAR = ROOT / "tests/probes/c2/c2_variance.json"
GOLDEN = ROOT / "tests/results/golden_results_20260729_230006.json"
GOLDEN_DATASET = ROOT / "tests/golden_dataset.json"

# §2.7 query shapes, hand-read from tests/golden_dataset.json. Recorded here rather than
# inferred: shape gates the whole classification, so it must be auditable, not heuristic.
# 'single' entries list SYNONYMS OF ONE SUBSTANCE — never class rosters (decision (a)).
GOLDEN_SHAPES = {
    "R01": ("single", "METFORMIN", ["METFORMIN", "METFORMIN HCL"]),
    "R02": ("class", "", []),
    "R03": ("class", "", []),
    "R04": ("class", "", []),
    "R05": ("class", "", []),
    "R06": ("class", "", []),
    "R07": ("class", "", []),
    "R08": ("single", "ASPIRIN", ["ASPIRIN", "ACETYLSALICYLIC ACID"]),
    "R09": ("single", "LITHIUM", ["LITHIUM", "LITHIUM CARBONATE"]),
    "R10": ("single", "DIGOXIN", ["DIGOXIN"]),
    "R11": ("single", "METFORMIN", ["METFORMIN", "METFORMIN HCL"]),
    "R12": ("class", "", []),
    "R13": ("pair", "WARFARIN", ["WARFARIN", "WARFARIN SODIUM"]),
    "R14": ("class", "", []),
    "R15": ("class", "", []),
    "R16": ("class", "", []),
    "R17": ("class", "", []),
    "R18": ("class", "", []),
    "R19": ("class", "", []),
    "R20": ("class", "", []),
}

OUT = HERE / "wrongdrug_replay.json"


def banner(t: str) -> None:
    print("\n" + "=" * 96)
    print(t)
    print("=" * 96)


def print_tally(counts: dict[str, int], label: str) -> None:
    print(f"\n  {label}")
    for k in OUTCOMES:  # all six, always, including zeros
        print(f"      {k:<28} {counts[k]}")


def self_test(corpus: CorpusIndex, report: dict) -> bool:
    """Prove the instrument does what it claims. Rule 17: verify intent, not behaviour.

    Each check names the business rule it protects. A green tally over an instrument
    that was never shown to discriminate is exactly the dead weight Rule 17 forbids.
    """
    banner("PART 0 — instrument self-test")
    checks: list[tuple[str, bool, str]] = []

    # 1. The join is exact for every doc in the shipped corpus. If this drifts, every
    #    ownership verdict silently becomes unresolved_source_id.
    docs = json.loads((ROOT / "data/dailymed/label_docs.json").read_text(encoding="utf-8"))["documents"]
    ok = all(parse_setid(d["source_id"]) == d["setid"] for d in docs)
    checks.append(("source_id -> setid is exact for all 4608 docs", ok,
                   "ownership cannot be resolved at all if the id format drifts"))

    # 2. THE decisive check. The committed c2 evidence records own_drug=true for the
    #    ACECLOFENAC document on an aspirin query — a mention-based false positive,
    #    because that label legitimately contains "acetylsalicylic acid". The ownership
    #    assertion must contradict it. If this check ever passes as correct_owner, the
    #    module has regressed to mention-based logic and is worthless.
    acl = "DailyMed:8a023942-01e8-4849-aa3c-1a640ffc7fd3#34070-3"
    v = classify_citation(acl, {"ASPIRIN", "ACETYLSALICYLIC ACID"}, "ASPIRIN", corpus, True)
    recorded_mention_flag = True  # own_drug:true, tests/probes/c2/c2_ab_retrieval.json
    ok = (v.outcome == "wrong_owner_cited" and v.owner_moiety == "ACECLOFENAC"
          and recorded_mention_flag)
    checks.append(("ownership CONTRADICTS the recorded mention flag on ACECLOFENAC", ok,
                   "the mention-based instrument scored this label as the queried drug's own; "
                   "this is the single worst recorded wrong-drug citation in the project"))

    # 3. Coverage must not masquerade as ranking (Constraint 2 at citation level).
    a = classify_citation(acl, {"IBUPROFEN"}, "IBUPROFEN", corpus, owned_doc_exists=False)
    b = classify_citation(acl, {"IBUPROFEN"}, "IBUPROFEN", corpus, owned_doc_exists=True)
    ok = a.outcome == "no_right_owner_in_corpus" and b.outcome == "wrong_owner_cited"
    checks.append(("same citation splits ranking vs coverage on owned_doc_exists", ok,
                   "collapsing them would attribute a corpus gap to the reranker"))

    # 4. An unresolvable id is never silently dropped and never counted correct (Rule 18).
    v = classify_citation("DailyMed:not-a-real-setid#34070-3", {"ASPIRIN"}, "ASPIRIN", corpus, True)
    ok = v.outcome == "unresolved_source_id"
    checks.append(("unknown setid -> unresolved_source_id, never correct_owner", ok,
                   "a citation we cannot verify must not be reported as verified"))

    # 5. No mention/text path exists in the module at all (Constraint 1, structural).
    src = (HERE / "owner_assertion.py").read_text(encoding="utf-8")
    body = src.split('"""', 2)[-1]  # exclude the module docstring, which discusses mention
    banned = [t for t in ("content", ".lower()", "in text", "TARGET_TERMS") if t in body]
    ok = not banned
    checks.append(("no text-matching primitives in the module body", ok,
                   f"found {banned}" if banned else "ownership is resolved only by the corpus join"))

    for name, ok, why in checks:
        print(f"  {'PASS' if ok else '🔴 FAIL'}  {name}\n           why it matters: {why}")
    allok = all(c[1] for c in checks)
    print(f"\n  self-test: {sum(c[1] for c in checks)}/{len(checks)}")
    report["self_test"] = {"passed": sum(c[1] for c in checks), "total": len(checks),
                           "all_passed": allok,
                           "checks": [{"name": n, "ok": o} for n, o, _ in checks]}
    if not allok:
        print("  🔴 instrument self-test FAILED — findings below are NOT trustworthy")
    return allok


def replay_fixtures(corpus: CorpusIndex, report: dict) -> None:
    banner("PART 1 — fixtures replayed against committed c2 retrieval evidence")
    fx = json.loads((HERE / "fixtures.json").read_text(encoding="utf-8"))["fixtures"]
    by_query = {f["query"]: f for f in fx}

    pools: dict[str, list[str]] = {}
    runs_seen: dict[str, int] = {}
    for src in (AB, VAR):
        if not src.exists():
            print(f"  ⚠️ SKIPPED (Rule 18): {src} not found")
            continue
        d = json.loads(src.read_text(encoding="utf-8"))
        for arm_name, arm in d["arms"].items():
            for _key, entry in arm.items():
                q = entry["query"]
                if q not in by_query:
                    continue
                for run in entry.get("runs", []):
                    if run.get("status") != "ok":
                        continue
                    tag = f"{q}||{arm_name}"
                    runs_seen[tag] = runs_seen.get(tag, 0) + 1
                    for doc in run.get("final", []):
                        pools.setdefault(tag, []).append(doc["source_id"])

    # Shape-gated fixtures are decided by shape alone and MUST appear in every report
    # even when no retrieval evidence exists — a pair fixture that silently vanished
    # would be scored as "fine", which is the failure this instrument exists to prevent.
    verdicts, informational = [], []
    for f in fx:
        if f["shape"] in ("class", "pair"):
            v = classify_fixture(f, [], corpus)
            verdicts.append(v)
            print(f"\n  {f['id']} [shape-gated]  {f['query']!r}")
            print(f"       FIXTURE OUTCOME: {v.fixture_outcome}")
            for d in v.diagnostics:
                print(f"         · {d}")
            if f["query"] not in {q for q, _ in (t.split("||", 1) for t in pools)}:
                print("         · note: no recorded c2 retrieval evidence for this query; "
                      "the outcome above is from the shape gate, not from an empty pool")
            continue

        for arm in ("control", "treatment"):
            tag = f"{f['query']}||{arm}"
            ids = pools.get(tag)
            if ids is None:
                print(f"\n  {f['id']} [{arm}] — ⚠️ no recorded evidence for this fixture/arm "
                      f"(Rule 18: reported, not silently omitted)")
                continue
            uniq = sorted(set(ids))
            v = classify_fixture(f, uniq, corpus)
            (verdicts if arm == "control" else informational).append(v)
            print(f"\n  {f['id']} [{arm}]  {f['query']!r}"
                  + ("" if arm == "control" else
                     "   ⚠️ NON-AUTHORITATIVE — treatment arm was retrieved against the c2 "
                     "E-A scratch index, not the shipped one; excluded from the tally"))
            print(f"       recorded runs={runs_seen.get(tag,0)}  distinct cited identities={len(uniq)}")
            print(f"       FIXTURE OUTCOME: {v.fixture_outcome}")
            for c in v.citations:
                print(f"         - {c.row()}")
            if v.non_dailymed_citations:
                print(f"         (+{v.non_dailymed_citations} non-DailyMed citations — "
                      f"outside this assertion's scope, not an outcome)")
            for d in v.diagnostics:
                print(f"         · {d}")

            alt = f.get("owner_moieties_alt")
            if alt:
                g = dict(f, owner_moieties=alt["moieties"])
                va = classify_fixture(g, uniq, corpus)
                print(f"       ── ALT reading ({alt['label']}): {va.fixture_outcome}")
                if va.fixture_outcome != v.fixture_outcome:
                    print(f"          🔴 the two readings DISAGREE "
                          f"({v.fixture_outcome} vs {va.fixture_outcome}) — founder decision")
                report["alt_readings"].append({
                    "fixture": f["id"], "arm": arm, "label": alt["label"],
                    "primary": v.fixture_outcome, "alt": va.fixture_outcome,
                })

    print_tally(tally(verdicts, per="citation"),
                "PART 1 tally — per citation  [AUTHORITATIVE: shipped index / control arm only]")
    print_tally(tally(verdicts, per="fixture"),
                "PART 1 tally — per fixture   [AUTHORITATIVE: shipped index / control arm only]")
    print_tally(tally(informational, per="citation"),
                "PART 1 tally — per citation  [informational only: c2 E-A scratch index]")
    report["part1"] = {
        "authoritative_scope": "control arm = shipped index; treatment arm excluded",
        "per_citation": tally(verdicts, per="citation"),
        "per_fixture": tally(verdicts, per="fixture"),
        "per_citation_informational_EA_index": tally(informational, per="citation"),
        "detail": [
            {"fixture": v.fixture_id, "shape": v.shape, "outcome": v.fixture_outcome,
             "citations": [{"source_id": c.source_id, "owner": c.owner_moiety,
                            "outcome": c.outcome} for c in v.citations]}
            for v in verdicts + informational
        ],
    }


def calibrate_golden(corpus: CorpusIndex, report: dict) -> None:
    banner("PART 2 — CALIBRATION: c1-ship §2.7 gate (recorded 20 PASS / 0 WARN / 0 FAIL)")
    if not GOLDEN.exists():
        print(f"  ⚠️ SKIPPED (Rule 18): {GOLDEN} not found — calibration NOT performed")
        report["part2"] = {"status": "SKIPPED — artifact missing"}
        return
    g = json.loads(GOLDEN.read_text(encoding="utf-8"))
    print(f"  artifact: {GOLDEN.name}  summary={g['summary']}  gate_valid={g.get('gate_valid')}")

    verdicts, changed = [], []
    for r in g["results"]:
        cid = r["id"]
        pi = r.get("pool_identity") or {}
        if not pi:
            print(f"  {cid} ⚠️ no pool_identity — citation identity NOT reconstructible")
            continue
        cited = set(pi.get("cited_in_answer") or [])
        ids = [p["source_id"] for p in pi.get("retrieved_pool", []) if p.get("id") in cited]
        shape, queried, owners = GOLDEN_SHAPES[cid]
        f = {"id": cid, "query": r.get("query", cid), "shape": shape,
             "queried_moiety": queried, "owner_moieties": owners}
        v = classify_fixture(f, ids, corpus)
        verdicts.append(v)
        if v.fixture_outcome in ("wrong_owner_cited", "unresolved_source_id"):
            changed.append(cid)
        dm = sum(1 for s in ids if parse_setid(s))
        print(f"  {cid} {r['status']:<5} {shape:<7} {v.fixture_outcome:<26} "
              f"(DailyMed cited={dm})")
        for c in v.citations:
            if c.outcome != "correct_owner":
                print(f"        - {c.row()}")

    print_tally(tally(verdicts, per="fixture"), "PART 2 tally — per §2.7 case")
    print_tally(tally(verdicts, per="citation"), "PART 2 tally — per citation")
    print(f"\n  §2.7 cases whose VERDICT would flip under the ownership rule: "
          f"{len(changed)} {changed}")
    report["part2"] = {
        "artifact": GOLDEN.name,
        "recorded_summary": g["summary"],
        "per_case": tally(verdicts, per="fixture"),
        "per_citation": tally(verdicts, per="citation"),
        "cases_that_would_flip": changed,
    }


def main() -> int:
    print(f"corpus: {(ROOT / 'data/dailymed/label_docs.json')}")
    corpus = CorpusIndex.load(ROOT / "data/dailymed/label_docs.json")
    sync = assert_whitelist_in_sync()
    print(f"corpus docs={corpus.n_docs}  moiety keys={len(corpus.moiety_to_safety_sections)}")
    print(f"whitelist: {sync}")

    report: dict = {"generated": "2026-08-05", "whitelist_check": sync,
                    "corpus_docs": corpus.n_docs, "alt_readings": []}
    self_test(corpus, report)
    replay_fixtures(corpus, report)
    calibrate_golden(corpus, report)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
