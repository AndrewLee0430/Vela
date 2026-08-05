"""Ownership assertion for DailyMed citations — a measurement instrument, not a fix.

═══════════════════════════════════════════════════════════════════════════════
THE BUSINESS RULE THIS PROTECTS  (CLAUDE.md Rule 17)
═══════════════════════════════════════════════════════════════════════════════
A Research answer about drug X must not present drug Y's official label as the
evidence for X.

What breaks if this assertion fails: the fly-215 production human-eye gate scored
8/8 PASS while `aspirin contraindications` was answered **entirely** from
`Clanza (Aceclofenac) — Contraindications` — its sole source. The gate criterion
read "a single DailyMed Contraindications citation is a PASS". It asserted HOW
MANY citations appeared and never WHOSE LABEL they were. This module supplies the
missing predicate. It does not repair retrieval; it makes the defect visible.

═══════════════════════════════════════════════════════════════════════════════
CONSTRAINT 1 — OWNERSHIP, NEVER MENTION  (founder-locked, non-negotiable)
═══════════════════════════════════════════════════════════════════════════════
Ownership is resolved **only** by the corpus join:

    source_id -> setid -> data/dailymed/label_docs.json -> moiety

There is NO text matching in this module. Not in the primary path, not in a
secondary bucket, not as a tie-breaker.

WHY (docs/c2_phase1c_20260804.md §171-183): the ACECLOFENAC contraindications
section literally contains the words "acetylsalicylic acid", because NSAID
cross-sensitivity genuinely belongs in an aceclofenac label. That is clinically
correct drafting. A mention-based check therefore PASSES the single worst
recorded wrong-drug citation in the project. Mention is not evidence of
ownership; on this corpus it is actively anti-correlated with it.

The prior instrument (`tests/results/_pairaware_m1_content_audit.py`) had a
mention-based `ON-TARGET-COUNTERPART` bucket for exactly this reason and is
deliberately NOT reused here.

═══════════════════════════════════════════════════════════════════════════════
CONSTRAINT 2 — RANKING AND COVERAGE ARE SEPARATE OUTCOMES  (founder-locked)
═══════════════════════════════════════════════════════════════════════════════
`wrong_owner_cited` (a RANKING failure — the right document existed and lost) and
`no_right_owner_in_corpus` (a COVERAGE gap — no right document exists) have
different fixes and must never share a bucket. They are never collapsed, never
summed, and both always appear in a report.

This separation is load-bearing, not cosmetic. See the DEFINITIONAL WARNING below.

═══════════════════════════════════════════════════════════════════════════════
DEFINITIONAL WARNING — coverage is decided by the CORPUS, never by the POOL
═══════════════════════════════════════════════════════════════════════════════
`no_right_owner_in_corpus` asks "does an owned safety document EXIST in the
shipped index?" — NOT "was one retrieved?". Those differ, and conflating them is
how the c1 adjudication reached a wrong conclusion:

  BACKLOG.md:860 records "in 6 of 6 adjudicated cases the queried drug's own
  reference label has no safety section". For aspirin that is FALSE at the corpus
  level. The corpus keys aspirin under TWO moiety strings:

      ASPIRIN               -> VAZALORE (OTC)   safety sections: NONE
      ACETYLSALICYLIC ACID  -> DURLAZA  (Rx)    34070-3, 34073-7, 43685-7

  `DURLAZA — Contraindications` is row 57 of the shipped index, 375 chars, unit-
  norm embedding, row-aligned. An owned aspirin Contraindications document was
  present in the index that cited Aceclofenac instead. That makes the flagship
  fixture a RANKING failure, not a coverage gap — the opposite of the record.

  The c1 adjudication looked up one moiety key and never looked at its synonym.
  That is why `owner_moieties` below is a SET, and why an owner set that matches
  zero corpus moieties is reported LOUDLY rather than silently becoming a
  coverage gap (CLAUDE.md Rule 18).

═══════════════════════════════════════════════════════════════════════════════
SCOPE EXCLUSION — class-level queries are NOT classified  (founder decision (a))
═══════════════════════════════════════════════════════════════════════════════
A query like "contraindications for using beta-blockers" names a CLASS, not a
drug. A class member cited on a class query is **legitimately owned** — the
fly-215-era §2.7 run cited metoprolol, esmolol, nebivolol and atenolol on R07,
all genuine beta-blockers. If such a citation is unhelpful, the defect is
ANSWER-RELEVANCE, which is a different defect with a different fix, and it must
not share a bucket with wrong-object citation.

These queries emit `out_of_scope_class_query` and are never scored.

We deliberately do NOT hardcode class-membership lists to rescue these cases. A
curated membership list is a new correctness dependency of exactly the kind that
invalidated the "c2-iii is cheapest" claim: it is unverifiable, silently
incomplete, and its errors present as instrument results.

═══════════════════════════════════════════════════════════════════════════════
SCOPE EXCLUSION — pair/interaction queries are v1-unclassified  (decision (b)-i)
═══════════════════════════════════════════════════════════════════════════════
On "spironolactone + potassium → hyperkalemia", the POTASSIUM CHLORIDE label is a
legitimate answer even though it is not owned by spironolactone. Judging that
correctly needs counterpart reasoning, and every available form of it is
mention-based — which Constraint 1 forbids.

So pair fixtures are reported `unclassified`. They are NEVER reported as passing.
An instrument that silently scored a known-defective case as fine would be a new
instance of the "instrument blind to its own target" class it exists to detect.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# ── The six outcomes. Fixed order. Every report emits all six, including zeros. ──
OUTCOMES = (
    "correct_owner",
    "wrong_owner_cited",
    "no_right_owner_in_corpus",
    "out_of_scope_class_query",
    "unclassified",
    "unresolved_source_id",
)

# Mirrors api/rag/retriever.py:_SAFETY_SECTION_WHITELIST (founder-locked 2026-07-20).
# Duplicated rather than imported so this probe has no api/ import weight; drift is
# checked at runtime by assert_whitelist_in_sync() and reported loudly, never assumed.
SAFETY_SECTIONS = {
    "34073-7": "Drug Interactions",
    "34070-3": "Contraindications",
    "43685-7": "Warnings",
    "34066-1": "Boxed Warning",
}

DEFAULT_CORPUS = Path("data/dailymed/label_docs.json")


# ─────────────────────────── the ownership join ───────────────────────────

def parse_setid(source_id: str) -> str | None:
    """'DailyMed:{setid}#{loinc}[~chunk]' -> setid. None if not a DailyMed id.

    Verified exact against the shipped corpus: for all 4608 docs,
    source_id.split('DailyMed:')[1].split('#')[0] == doc['setid'].
    """
    if not source_id or not source_id.startswith("DailyMed:"):
        return None
    return source_id.split("DailyMed:", 1)[1].split("#", 1)[0]


def parse_loinc(source_id: str) -> str | None:
    if not source_id or "#" not in source_id:
        return None
    return source_id.split("#", 1)[1].split("~", 1)[0]


@dataclass
class CorpusIndex:
    """setid -> moiety, plus moiety -> the safety sections that exist for it."""

    setid_to_moiety: dict[str, str]
    moiety_to_safety_sections: dict[str, set[str]]
    moiety_to_ref_title: dict[str, str]
    n_docs: int

    @classmethod
    def load(cls, corpus_path: Path | str = DEFAULT_CORPUS) -> "CorpusIndex":
        p = Path(corpus_path)
        if not p.exists():
            raise FileNotFoundError(
                f"DailyMed corpus not found at {p}. This assertion cannot resolve "
                f"ownership without it and must not fall back to text matching."
            )
        docs = json.loads(p.read_text(encoding="utf-8"))["documents"]
        s2m: dict[str, str] = {}
        m2s: dict[str, set[str]] = {}
        m2t: dict[str, str] = {}
        for d in docs:
            moiety = (d.get("moiety") or "").upper().strip()
            setid = d.get("setid")
            if setid:
                s2m[setid] = moiety
            loinc = parse_loinc(d.get("source_id") or "") or ""
            m2s.setdefault(moiety, set())
            if loinc in SAFETY_SECTIONS:
                m2s[moiety].add(loinc)
            m2t.setdefault(moiety, (d.get("title") or "").split(" — ")[0])
        return cls(s2m, m2s, m2t, len(docs))


# ─────────────────────────── per-citation verdict ───────────────────────────

@dataclass
class CitationVerdict:
    source_id: str
    queried_moiety: str          # what the fixture declares it asked about
    setid: str | None
    owner_moiety: str | None     # resolved from the corpus, never from text
    loinc: str | None
    outcome: str

    def row(self) -> str:
        return (
            f"{self.outcome:<26} queried={self.queried_moiety:<22} "
            f"owner={str(self.owner_moiety):<26} setid={self.setid} loinc={self.loinc}"
        )


@dataclass
class FixtureVerdict:
    fixture_id: str
    query: str
    shape: str
    queried_moiety: str
    owner_moieties: list[str]
    citations: list[CitationVerdict] = field(default_factory=list)
    fixture_outcome: str = ""
    diagnostics: list[str] = field(default_factory=list)
    non_dailymed_citations: int = 0


def classify_citation(
    source_id: str,
    owner_moieties: set[str],
    queried_moiety: str,
    corpus: CorpusIndex,
    owned_doc_exists: bool,
) -> CitationVerdict:
    """Classify ONE DailyMed citation by ownership. No text matching anywhere.

    `owned_doc_exists` is what keeps Constraint 2 honest at the CITATION level, not
    just the fixture level. A non-owned citation is only a RANKING failure if a right
    answer existed to lose to. Where no owned safety document exists in the corpus at
    all, the same citation is a COVERAGE gap — the retriever had nothing better to
    rank. Emitting `wrong_owner_cited` in that case would fold coverage into ranking,
    which is exactly the collapse Constraint 2 forbids.
    """
    setid = parse_setid(source_id)
    loinc = parse_loinc(source_id)
    if setid is None:
        # Caller must filter non-DailyMed ids before calling; reaching here is a bug.
        raise ValueError(f"not a DailyMed source_id: {source_id!r}")

    owner = corpus.setid_to_moiety.get(setid)
    if owner is None:
        # Rule 18: an id we cannot resolve is reported as such. NEVER dropped, and
        # never counted as correct — an unresolvable citation is an unverified one.
        return CitationVerdict(source_id, queried_moiety, setid, None, loinc,
                               "unresolved_source_id")

    if owner in owner_moieties:
        outcome = "correct_owner"
    else:
        outcome = "wrong_owner_cited" if owned_doc_exists else "no_right_owner_in_corpus"
    return CitationVerdict(source_id, queried_moiety, setid, owner, loinc, outcome)


def classify_fixture(fixture: dict, source_ids: list[str], corpus: CorpusIndex) -> FixtureVerdict:
    """Classify one fixture's citation list. Shape gates the whole fixture."""
    shape = fixture["shape"]
    owner_moieties = {m.upper().strip() for m in fixture.get("owner_moieties", [])}
    v = FixtureVerdict(
        fixture_id=fixture["id"],
        query=fixture["query"],
        shape=shape,
        queried_moiety=fixture["queried_moiety"],
        owner_moieties=sorted(owner_moieties),
    )

    if shape == "class":
        v.fixture_outcome = "out_of_scope_class_query"
        v.diagnostics.append(
            "class-level query — a class member cited here is legitimately owned; "
            "not scored (see module docstring, decision (a))"
        )
        return v

    if shape == "pair":
        v.fixture_outcome = "unclassified"
        v.diagnostics.append(
            f"pair/interaction query, {fixture.get('pair_query', 'out_of_scope_v1')} — "
            "a counterpart label can be a legitimate answer and judging that requires "
            "mention-based reasoning, which Constraint 1 forbids. Reported unclassified, "
            "NEVER as passing. This fixture is the recorded evidence for BACKLOG surface 3."
        )
        return v

    if shape != "single":
        raise ValueError(f"unknown fixture shape {shape!r} for {fixture['id']}")

    # ── single-drug fixture: ownership is well-defined ──
    # Rule 18: an owner set that matches NOTHING in the corpus is almost certainly an
    # incomplete synonym list, not a coverage gap. Say so loudly instead of silently
    # emitting no_right_owner_in_corpus — that is the exact error the c1 adjudication made.
    known = {m for m in owner_moieties if m in corpus.moiety_to_safety_sections}
    if not known:
        v.diagnostics.append(
            f"⚠️ LOUD: owner set {sorted(owner_moieties)} matches ZERO moiety keys in the "
            f"corpus. This is more likely an incomplete synonym list than a real coverage "
            f"gap. Verify before trusting the outcome below."
        )

    owned_sections: set[str] = set()
    for m in known:
        owned_sections |= corpus.moiety_to_safety_sections.get(m, set())
    owned_doc_exists = bool(owned_sections)

    dm_ids = [s for s in source_ids if parse_setid(s) is not None]
    v.non_dailymed_citations = len(source_ids) - len(dm_ids)
    for sid in dm_ids:
        v.citations.append(
            classify_citation(sid, owner_moieties, v.queried_moiety, corpus, owned_doc_exists)
        )

    if not owned_doc_exists:
        # No owned safety document EXISTS in the shipped index -> coverage gap, and every
        # non-owned citation above was classified as coverage too, not as a ranking loss.
        v.fixture_outcome = "no_right_owner_in_corpus"
        v.diagnostics.append(
            f"corpus contains no whitelisted safety section for {sorted(owner_moieties)} "
            f"— COVERAGE gap; non-owned citations here are NOT ranking failures"
        )
        if any(c.outcome == "correct_owner" for c in v.citations):
            v.diagnostics.append(
                "🔴 CONTRADICTION: an owned document was CITED although the shipped corpus "
                "contains no owned whitelisted safety section. The replayed pool was almost "
                "certainly produced against a DIFFERENT index than the one joined here. "
                "Treat this fixture/arm as non-authoritative."
            )
        return v

    # An owned safety document exists. Any non-owned citation is therefore a RANKING failure.
    v.diagnostics.append(
        "owned safety sections EXIST in the shipped index: "
        + ", ".join(f"{c} ({SAFETY_SECTIONS[c]})" for c in sorted(owned_sections))
        + f" via {sorted(known)} — so a non-owned citation here is a RANKING failure"
    )
    if any(c.outcome == "unresolved_source_id" for c in v.citations):
        v.fixture_outcome = "unresolved_source_id"
    elif any(c.outcome == "wrong_owner_cited" for c in v.citations):
        v.fixture_outcome = "wrong_owner_cited"
    elif v.citations:
        v.fixture_outcome = "correct_owner"
    else:
        v.fixture_outcome = "unclassified"
        v.diagnostics.append(
            "no DailyMed citations in this run — nothing to judge; NOT counted as passing"
        )
    return v


# ─────────────────────────── reporting ───────────────────────────

def tally(verdicts: list[FixtureVerdict], per: str = "citation") -> dict[str, int]:
    """Counts over all six outcomes. Always all six keys, including zeros."""
    counts = {k: 0 for k in OUTCOMES}
    for v in verdicts:
        if per == "fixture":
            counts[v.fixture_outcome] += 1
        else:
            if v.fixture_outcome in ("out_of_scope_class_query", "unclassified") or not v.citations:
                counts[v.fixture_outcome] += 1
            else:
                for c in v.citations:
                    counts[c.outcome] += 1
    return counts


def assert_whitelist_in_sync() -> str:
    """Rule 18: report drift against api/rag/retriever.py rather than assume parity.

    Returns a human-readable status. Never raises on import failure — but never
    silently claims parity either.
    """
    try:
        import re
        src = Path("api/rag/retriever.py").read_text(encoding="utf-8")
        block = re.search(r"_SAFETY_SECTION_WHITELIST\s*=\s*\{(.*?)\}", src, re.S)
        if not block:
            return "⚠️ whitelist drift check SKIPPED — constant not found in api/rag/retriever.py"
        found = set(re.findall(r'"(\d{5}-\d)"', block.group(1)))
        if found == set(SAFETY_SECTIONS):
            return f"whitelist in sync with api/rag/retriever.py ({len(found)} LOINCs)"
        return (f"⚠️ WHITELIST DRIFT — probe has {sorted(SAFETY_SECTIONS)}, "
                f"api/rag/retriever.py has {sorted(found)}")
    except Exception as e:  # noqa: BLE001 - reported, not swallowed
        return f"⚠️ whitelist drift check SKIPPED — {type(e).__name__}: {e}"
