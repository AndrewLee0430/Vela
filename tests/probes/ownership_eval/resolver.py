"""Shared free-text → DailyMed key-set resolver (offline, key-only).

WHERE THIS LIVES AND WHY: the key logic already lives in this directory —
`build_query_set.build_key_sets` (Rule-23 key-set expansion) and
`seat_measurement.strip_salt_suffixes` (the founder-fixed 17-suffix list). This
module is the third piece, placed beside them so all key logic stays in one
place. `tests/probes/canary/canary_gate.py` loads it BY FILE PATH (the same
mechanism it already uses for sibling modules) rather than copying any of it.
`strip_salt_suffixes` is IMPORTED from `seat_measurement.py`, never duplicated.

WHAT IT IS: the trivial string resolver whose ceiling was measured during the
2026-08-21 recon — exact WHOLE-TOKEN match over the corpus moiety strings, plus
base→salt expansion. It is NOT the production resolver (none exists); it is the
best available offline stand-in, and its limits are recorded below.

KEY-ONLY (Rule 21): it matches the query text against MOIETY KEY STRINGS. It
never inspects a document's content or title, and it never decides ownership by
substring — `NYSTATIN` is not a match for `statin`.

RULE 23 (plural by construction): a resolved base expands to EVERY key that
strips to it, so `metformin` resolves to `{METFORMIN, METFORMIN HCL}`, never to
one key.

KNOWN FALSE-POSITIVE MODE, recorded rather than silently patched: base→salt
expansion can fire on a common word that happens to be a salt base — measured
during the recon, "very low dietary **sodium** intake" resolves via the base
`SODIUM` (from `SODIUM ACETATE`). ⚠️ For a GATE this direction matters: a
spurious resolve makes the key set LARGER, which makes an ownership-based gate
LESS strict, because more documents count as owned. Any consumer that uses this
for a safety decision must state that exposure. No deny-list is applied here —
inventing one is the Rule-21 hazard this module exists to avoid.
"""

from __future__ import annotations

import importlib.util as _ilu
import re
from pathlib import Path

HERE = Path(__file__).parent


def _load(name: str, path: Path):
    spec = _ilu.spec_from_file_location(name, path)
    m = _ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# IMPORTED, never copied — the founder-fixed 17-suffix list and its stripper.
_seat = _load("ownership_seat_measurement_for_resolver", HERE / "seat_measurement.py")
strip_salt_suffixes = _seat.strip_salt_suffixes
SALT_SUFFIXES = _seat.SALT_SUFFIXES


class MoietyIndex:
    """Precompiled whole-token matchers over the corpus's distinct moiety keys."""

    def __init__(self, corpus: list[dict]):
        self.moieties = sorted(
            {(d.get("moiety") or "").upper().strip() for d in corpus} - {""})
        self._key_set = set(self.moieties)
        self._pat = {
            m: re.compile(r"(?<![a-z0-9])" + re.escape(m.lower()) + r"(?![a-z0-9])")
            for m in self.moieties
        }
        # base (after stripping listed salt suffixes) -> every key that strips to it
        self.base_to_keys: dict[str, set[str]] = {}
        for m in self.moieties:
            self.base_to_keys.setdefault(strip_salt_suffixes(m), set()).add(m)
        # bases that are NOT themselves keys need their own matcher (warfarin -> WARFARIN SODIUM)
        self._base_pat = {
            b: re.compile(r"(?<![a-z0-9])" + re.escape(b.lower()) + r"(?![a-z0-9])")
            for b in self.base_to_keys
            if b not in self._key_set
        }

    # ── setid → moiety, a TOTAL and CONFLICT-FREE join on the shipped corpus ──
    @staticmethod
    def setid_to_moiety(corpus: list[dict]) -> dict[str, str]:
        out: dict[str, str] = {}
        for d in corpus:
            sid = (d.get("setid") or "").strip()
            if sid:
                out[sid] = (d.get("moiety") or "").upper().strip()
        return out


def resolve_key_set(query: str, index: MoietyIndex) -> dict:
    """free text -> {'keys': set[str], 'matched': [...], 'via': 'exact'|'base'|None}.

    Longest-match wins: a hit fully contained in a longer hit is dropped, so
    `ATROPINE SULFATE MONOHYDRATE` beats `ATROPINE SULFATE`. An UNRESOLVED query
    returns an EMPTY key set — and an empty key set means every whitelisted
    safety section is wrong-object for that query, which is deliberate.
    """
    q = (query or "").lower()

    exact = [m for m in index.moieties if index._pat[m].search(q)]
    exact = [h for h in exact
             if not any(h != o and index._pat[h].search(o.lower()) for o in exact)]
    if exact:
        keys: set[str] = set()
        for h in exact:
            # Rule 23: expand to every key sharing the base (METFORMIN -> +METFORMIN HCL)
            keys |= index.base_to_keys.get(strip_salt_suffixes(h), {h})
            keys.add(h)
        return {"keys": keys, "matched": sorted(exact), "via": "exact"}

    based = [b for b, p in index._base_pat.items() if p.search(q)]
    based = [b for b in based
             if not any(b != o and index._base_pat[b].search(o.lower()) for o in based)]
    if based:
        keys = set()
        for b in based:
            keys |= index.base_to_keys[b]
        return {"keys": keys, "matched": sorted(based), "via": "base"}

    return {"keys": set(), "matched": [], "via": None}
