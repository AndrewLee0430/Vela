# -*- coding: utf-8 -*-
"""Ownership-eval harness labeler — the label must be KEY-based, never mention-based.

WHAT BREAKS IF THESE FAIL: the ownership-anchored eval harness
(tests/probes/ownership_eval/) reports wrong-object rates from a labeler that
matches TEXT instead of KEYS. On this corpus mention is anti-correlated with
ownership — the ACECLOFENAC contraindications label legitimately contains
"acetylsalicylic acid" (NSAID cross-sensitivity), so a substring labeler scores
the single worst recorded wrong-drug citation as fine
(tests/probes/wrongdrug/owner_assertion.py, Constraint 1). These tests feed the
labeler adversarial docs whose CONTENT names the drug; a mention-based labeler
fails them (mutation-tested at build: labeler swapped to substring matching →
both direction tests fail; restored → green).

DB-free by construction: the labeler module is loaded by file path, no api/
import, no store, no network. The whitelist is injected as a parameter — the
harness itself imports the production whitelist from api/rag/retriever.py; that
import path is not under test here (parity is the harness's own concern).
"""

import importlib.util
from pathlib import Path

_MOD_PATH = (
    Path(__file__).resolve().parent / "probes" / "ownership_eval" / "build_query_set.py"
)


def _load():
    spec = importlib.util.spec_from_file_location("ownership_build_query_set", _MOD_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WHITELIST = {"34073-7", "34070-3", "43685-7", "34066-1"}  # test fixture, injected
KEY_SET = {"ASPIRIN", "ACETYLSALICYLIC ACID"}


def test_mentioning_doc_outside_key_set_is_wrong_object():
    """A safety-section doc whose CONTENT names the drug but whose moiety is
    outside the key set MUST label wrong_object — mention is not ownership."""
    mod = _load()
    doc = {
        "moiety": "ACECLOFENAC",
        "loinc": "34070-3",
        "title": "Clanza (Aceclofenac) — Contraindications",
        "content": "Hypersensitivity to aceclofenac, acetylsalicylic acid (aspirin) "
                   "or other NSAIDs — cross-sensitivity reactions have been reported.",
    }
    assert mod.label_doc(doc, KEY_SET, WHITELIST) == "wrong_object"


def test_key_set_doc_with_no_mention_is_relevant():
    """A doc IN the key set whose content never mentions the query drug string
    MUST label relevant — ownership is the moiety key, not the words."""
    mod = _load()
    doc = {
        "moiety": "ACETYLSALICYLIC ACID",
        "loinc": "34070-3",
        "title": "DURLAZA — Contraindications",
        "content": "Do not use in patients with a recent history of "
                   "gastrointestinal bleeding or severe hepatic impairment.",
    }
    assert mod.label_doc(doc, KEY_SET, WHITELIST) == "relevant"


def test_non_safety_non_owned_is_other_never_wrong_object():
    """A non-whitelisted section outside the key set is 'other' — it never
    counts against the wrong-object rate (Constraint 2's spirit: coverage and
    ranking judgments stay scoped to safety sections)."""
    mod = _load()
    doc = {
        "moiety": "METFORMIN HYDROCHLORIDE",
        "loinc": "34067-9",  # Indications & Usage — not whitelisted
        "content": "aspirin aspirin aspirin",  # adversarial mention, must not matter
    }
    assert mod.label_doc(doc, KEY_SET, WHITELIST) == "other"


def test_the_guards_actually_fire():
    """Positive controls: the labeler distinguishes by KEY, so flipping only the
    moiety (all text held constant) flips the label."""
    mod = _load()
    base = {
        "loinc": "34070-3",
        "title": "X — Contraindications",
        "content": "no drug names here at all",
    }
    a = dict(base, moiety="ASPIRIN")
    b = dict(base, moiety="KETOPROFEN")
    assert mod.label_doc(a, KEY_SET, WHITELIST) == "relevant"
    assert mod.label_doc(b, KEY_SET, WHITELIST) == "wrong_object"
