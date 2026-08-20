"""Ownership-anchored retrieval eval harness v1 — query-set builder (deterministic).

Scope (founder ruling 2026-08-20): DailyMed store ONLY · raw arm ONLY · pool-level
metrics ONLY. TFDA = v1.5, citation/rerank level = v2. See README.md.

GROUND TRUTH IS KEY-DERIVED, NEVER HAND-LABELED (CLAUDE.md Rules 21/23):
  relevant     = doc.moiety ∈ the query's target KEY SET
  wrong_object = doc.loinc ∈ the production safety-section whitelist
                 AND doc.moiety ∉ the key set
  other        = everything else (never counted against)
The labeler reads ONLY `moiety` and `loinc`. It never reads `content` or `title` —
mention is not ownership, and on this corpus it is anti-correlated with it
(tests/probes/wrongdrug/owner_assertion.py, Constraint 1). The DB-free tests in
tests/test_ownership_eval_labels.py feed it adversarial docs whose CONTENT names
the drug; a substring labeler fails them (mutation-tested).

KEY SETS (Rule 23 — one moiety string is not the entity):
A drug's key set is built ONLY from keys, merged by union-find over:
  (1) an explicit alias table, seeded with the recorded dual-key case
      {ASPIRIN, ACETYLSALICYLIC ACID} (docs/c2_line_closeout_20260804.md §0;
      tests/probes/wrongdrug/fixtures.json WD01);
  (2) moieties sharing a `setid` (vacuously empty on the shipped corpus —
      1,038 moieties ↔ 1,038 setids — kept because it is a KEY rule and a
      future rebuild could change the cardinality);
  (3) moieties sharing a non-empty `rxcui` (a KEY, not a string).
Salt/acid-suffix NORMALIZATION IS DELIBERATELY ABSENT — that is substring
derivation, the exact hazard Rule 23 forbids (STATIN→NYSTATIN).

This module is import-pure: no api/ imports at module level (the DB-free label
tests import it without the provider stack). `get_production_whitelist()` does
the api import lazily and is the ONLY sanctioned whitelist source for the
harness — the whitelist is IMPORTED from api/rag/retriever.py, never copied.

Run:  python tests/probes/ownership_eval/build_query_set.py
Writes: tests/probes/ownership_eval/query_set_v1.json
"""

from __future__ import annotations

import json
import random
from pathlib import Path

CORPUS_PATH = Path("data/dailymed/label_docs.json")
OUT_PATH = Path(__file__).parent / "query_set_v1.json"

SEED = 20260820          # fixed; recorded in the JSON
SAMPLE_N = 100           # (drug, template) pairs; multi-key drugs expand after sampling

# EN templates, fixed (founder baton 2026-08-20). {drug} = the moiety string lowercased.
TEMPLATES = (
    "{drug} contraindications",
    "{drug} warnings and precautions",
    "{drug} drug interactions",
)

# (1) Explicit alias table — KEY-set seeds. Adding an entry is a recorded decision,
# not a normalization rule. Source for the seed: the corpus's recorded dual-key case.
ALIAS_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"ASPIRIN", "ACETYLSALICYLIC ACID"}),
)


def _repo_root_on_path() -> Path:
    """Repo root (…/Vela) importable — needed when run as a script from anywhere."""
    import sys
    root = Path(__file__).resolve().parents[3]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def get_production_whitelist() -> dict:
    """The production safety-section whitelist, IMPORTED (never copied).

    Lazy so that importing this module stays free of the api/ provider stack —
    the DB-free label tests inject their own whitelist parameter instead.
    """
    _repo_root_on_path()
    from api.rag.retriever import _SAFETY_SECTION_WHITELIST
    return dict(_SAFETY_SECTION_WHITELIST)


def load_corpus(path: Path = CORPUS_PATH) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["documents"]


# ───────────────────────────── labeler (key-based ONLY) ─────────────────────────────

def label_doc(doc: dict, key_set: set[str], whitelist) -> str:
    """relevant / wrong_object / other — from `moiety` and `loinc` ONLY.

    Deliberately never reads doc['content'] or doc['title']: a label that
    MENTIONS the queried drug is not OWNED by it (owner_assertion Constraint 1).
    """
    moiety = (doc.get("moiety") or "").upper().strip()
    loinc = (doc.get("loinc") or "").strip()
    if moiety in key_set:
        return "relevant"
    if loinc in whitelist:
        return "wrong_object"
    return "other"


# ───────────────────────────── key-set construction ─────────────────────────────

class _UnionFind:
    def __init__(self):
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[rb] = ra


def build_key_sets(docs: list[dict]) -> dict[str, set[str]]:
    """moiety-key → its full key set (Rule 23). Merges by alias table, shared
    setid, and shared non-empty rxcui — keys only, no string normalization."""
    uf = _UnionFind()
    moieties = sorted({(d.get("moiety") or "").upper().strip() for d in docs} - {""})
    for m in moieties:
        uf.find(m)

    # (1) explicit alias table
    for group in ALIAS_GROUPS:
        members = [m for m in group if m in set(moieties)]
        for other in members[1:]:
            uf.union(members[0], other)

    # (2) shared setid  (3) shared non-empty rxcui — both KEYS
    by_setid: dict[str, set[str]] = {}
    by_rxcui: dict[str, set[str]] = {}
    for d in docs:
        m = (d.get("moiety") or "").upper().strip()
        if not m:
            continue
        sid = (d.get("setid") or "").strip()
        rx = str(d.get("rxcui") or "").strip()
        if sid:
            by_setid.setdefault(sid, set()).add(m)
        if rx:
            by_rxcui.setdefault(rx, set()).add(m)
    for grouping in (by_setid, by_rxcui):
        for members in grouping.values():
            members = sorted(members)
            for other in members[1:]:
                uf.union(members[0], other)

    return {m: {x for x in moieties if uf.find(x) == uf.find(m)} for m in moieties}


def multi_key_sets(key_sets: dict[str, set[str]]) -> list[list[str]]:
    """The distinct key sets with more than one member, sorted for determinism."""
    seen: set[frozenset[str]] = set()
    out: list[list[str]] = []
    for ks in key_sets.values():
        f = frozenset(ks)
        if len(f) > 1 and f not in seen:
            seen.add(f)
            out.append(sorted(f))
    return sorted(out)


# ───────────────────────────── query-set build ─────────────────────────────

def eligible_drugs(docs: list[dict], key_sets: dict[str, set[str]], whitelist) -> list[list[str]]:
    """Distinct key sets owning ≥1 safety-section doc (loinc ∈ whitelist).
    Returned as sorted lists of keys, sorted by first key — deterministic."""
    owners_of_safety = {
        (d.get("moiety") or "").upper().strip()
        for d in docs
        if (d.get("loinc") or "").strip() in whitelist
    }
    seen: set[frozenset[str]] = set()
    out: list[list[str]] = []
    for m, ks in key_sets.items():
        f = frozenset(ks)
        if f in seen:
            continue
        seen.add(f)
        if f & owners_of_safety:
            out.append(sorted(f))
    return sorted(out)


def build_query_set(docs: list[dict], whitelist, seed: int = SEED, n: int = SAMPLE_N) -> dict:
    key_sets = build_key_sets(docs)
    eligible = eligible_drugs(docs, key_sets, whitelist)
    multi = multi_key_sets(key_sets)

    # population = (drug_id, template) pairs; drug_id = "|".join(sorted keys)
    pairs = [("|".join(ks), t) for ks in eligible for t in TEMPLATES]
    pairs.sort()
    rng = random.Random(seed)
    sampled = rng.sample(pairs, n)

    queries = []
    for drug_id, template in sorted(sampled):
        keys = drug_id.split("|")
        # multi-key drugs: one query per KEY STRING, tagged with the key used
        for key in keys:
            queries.append({
                "qid": f"Q{len(queries):03d}",
                "drug_id": drug_id,
                "key_set": keys,
                "key_used": key,
                "template": template,
                "query": template.format(drug=key.lower()),
                "scope": "sampled",
            })

    return {
        "seed": seed,
        "sample_n_pairs": n,
        "templates": list(TEMPLATES),
        "alias_groups": [sorted(g) for g in ALIAS_GROUPS],
        "corpus_docs": len(docs),
        "distinct_moieties": len(key_sets),
        "eligible_drugs": len(eligible),
        "multi_key_sets": multi,
        "n_queries": len(queries),
        "queries": queries,
    }


def main() -> int:
    docs = load_corpus()
    whitelist = get_production_whitelist()
    qs = build_query_set(docs, whitelist)
    OUT_PATH.write_text(json.dumps(qs, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"corpus_docs={qs['corpus_docs']} distinct_moieties={qs['distinct_moieties']}")
    print(f"eligible_drugs={qs['eligible_drugs']} (own >=1 whitelisted safety-section doc)")
    print(f"multi_key_sets={len(qs['multi_key_sets'])}:")
    for g in qs["multi_key_sets"]:
        print("   ", g)
    print(f"sampled_pairs={qs['sample_n_pairs']} -> n_queries={qs['n_queries']} (multi-key expansion)")
    print(f"wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
