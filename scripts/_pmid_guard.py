# -*- coding: utf-8 -*-
"""NOT-APPLICABLE vs FAILED for source_id -> PMID extraction. Shared by the dev harnesses.

THE INVARIANT, stated once here and enforced by `tests/test_source_id_pmid_guard.py`:
digits may be scraped out of a `source_id` ONLY when that document's `source_type` is
PubMed. Non-PubMed source_ids carry 5+ digit runs and mis-resolve to real-but-unrelated
PMIDs — measured 2026-08-23, a DailyMed source_id yields PMID `84432` and a TFDA one
yields `057803`. PMID 84432 exists, so the harness fetches a genuine unrelated abstract,
judges a drug-label claim against it, and prints `N/N resolve`. It looks clean.

⚠️ A GUARD ALONE SHIPS A SECOND DEFECT, which is why this module exists rather than a
bare `return None`. Returning None for BOTH "not PubMed" and "PubMed but no id" collapses
two different facts into one: a genuine extraction failure then vanishes from the
denominator in exactly the same way an out-of-scope document does, and the run again looks
clean. So the two cases are distinguished:

  NOT_PUBMED   out of scope. FALSY on purpose, so every existing `if p:` / walrus filter
               keeps excluding it with no call-site rewrite — and it is NEVER counted as
               a failure, because it is not one.
  None         PubMed, but no id could be extracted. A REAL failure. Recorded here, so it
               cannot be silently dropped at ANY call site, including ones added later.

The recording lives in the module rather than at each call site deliberately: eleven call
sites across three harnesses would each have had to remember, and the one that forgot
would be invisible.
"""
from __future__ import annotations


class _NotPubMed:
    """Falsy sentinel — out of scope, not a failure."""

    __slots__ = ()

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "NOT_PUBMED"


NOT_PUBMED = _NotPubMed()

_UNEXTRACTABLE: list[str] = []


def record_unextractable(source_id: str) -> None:
    """A PubMed document whose source_id yielded no id. Never silent."""
    _UNEXTRACTABLE.append(source_id or "<empty source_id>")


def report_unextractable(where: str = "") -> int:
    """Print any recorded extraction FAILURES and clear. -> how many. Call once per section.

    Silence here means zero failures, not zero checks — non-PubMed documents never reach
    this list, because excluding them is correct rather than a failure.
    """
    n = len(_UNEXTRACTABLE)
    if n:
        print(f"  WARNING: {n} PubMed doc(s) with UNEXTRACTABLE source_id"
              f"{' in ' + where if where else ''}: {sorted(set(_UNEXTRACTABLE))}")
        print("     These are extraction FAILURES, not out-of-scope documents. Non-PubMed "
              "sources are excluded silently and correctly; these are not.")
    _UNEXTRACTABLE.clear()
    return n
