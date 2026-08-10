# -*- coding: utf-8 -*-
"""Open-item #7 — a PUBLIC page must never present a `local`-sourced citation as
carrying a credibility claim.

THE BUSINESS RULE (CLAUDE.md Rule 17)
-------------------------------------
Every document in the deprecated 690-doc `local` corpus is field-label scaffolding
with no values (<=20 chars, max 5, median 1). Four rows stored on prod BEFORE c1
deprecated the corpus still serve 8 such stubs on public `/q/` and `/explore`
pages, each carrying `credibility: "official"` and an empty `url` — i.e. an empty
document presented under an "Official" pill on an SEO-indexed medical surface.

What breaks if these tests fail: a public medical page again asserts official
provenance for a document that contains no clinical content.

WHY TOMBSTONE AND NOT REMOVAL — the property that makes this subtle
-------------------------------------------------------------------
`q_public.jinja2:51` numbers citations by `loop.index`, NOT by a stored field, and
the stored `answer_text` cites `[N]` by position. Dropping a stub from the list
therefore RENUMBERS every later citation and silently re-points the prose at the
WRONG source. Measured on the 4 affected prod rows: filtering mis-points all four
(e.g. `7xI-q0dxnVg` prose cites [1]..[5]; filtering leaves two entries renumbered
to [1],[2] while the prose still means [2],[3]).

So the stub KEEPS ITS SLOT and its number, and loses only the credibility claim.
`test_prose_marker_alignment_is_preserved` is the regression guard for that — it
fails if anyone "cleans up" by filtering instead.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("TEST_MODE", "true")

from api.services import share_renderer as sr  # noqa: E402

# Shaped exactly like the rows measured on prod 2026-08-06: source_type 'local',
# credibility 'official', empty url, 35-64 chars of scaffolding.
_STUB = {
    "source_type": "local",
    "credibility": "official",
    "title": "Warfarin - Safety",
    "url": "",
    "snippet": "Drug: Warfarin\n\nContraindications:\n4\n\nWarnings and Precautions:",
    "source_id": "fda-warfarin-safety",
}
_REAL = {
    "source_type": "pubmed",
    "credibility": "peer-reviewed",
    "title": "Management of warfarin-related intracerebral hemorrhage.",
    "url": "https://pubmed.ncbi.nlm.nih.gov/18271712/",
    "snippet": "# Management of warfarin-related intracerebral hemorrhage.",
    "source_id": "PMID:18271712",
}


def _aug(citations, locale="en"):
    return sr._augment_citations(citations, locale)


def test_local_citation_never_carries_a_credibility_claim():
    """THE RULE. A stub must not render any credibility pill, in any locale."""
    for locale in ("en", "zh-TW"):
        aug, _ = _aug([_STUB], locale)
        assert len(aug) == 1
        c = aug[0]
        assert c["cred_label"] is None, f"{locale}: stub still renders a credibility pill"
        assert c["credibility"] is None, f"{locale}: stub still carries a credibility value"
        assert c["cred_bg"] is None and c["cred_color"] is None


def test_local_citation_claims_no_source_and_is_localised():
    """It must not read 'Local' (share_renderer) nor 'FDA' (sourceLabels.ts:68) —
    the second is the very chip c1 shipped to remove."""
    en, _ = _aug([_STUB], "en")
    zh, _ = _aug([_STUB], "zh-TW")
    assert en[0]["source_label"] == "Source withdrawn"
    assert zh[0]["source_label"] == "來源已撤回"
    for c in (en[0], zh[0]):
        assert c["source_label"] not in ("Local", "FDA")
        assert c["is_tombstone"] is True


def test_prose_marker_alignment_is_preserved():
    """REGRESSION GUARD against 'cleaning up' by filtering.

    The stored answer_text cites [1]..[5] by position. A tombstone keeps its slot,
    so every marker still resolves and every real citation keeps its number. This
    mirrors prod row `7xI-q0dxnVg` exactly: local at positions 1, 4, 5.
    """
    citations = [_STUB, _REAL, dict(_REAL, source_id="PMID:33653862"), _STUB, _STUB]
    aug, _ = _aug(citations, "en")

    assert len(aug) == len(citations), (
        "a citation was DROPPED — this renumbers the list and re-points the prose "
        "at the wrong source; tombstone, do not filter"
    )
    # The real citations must still sit at 1-based positions 2 and 3.
    assert aug[1]["source_id"] == "PMID:18271712"
    assert aug[2]["source_id"] == "PMID:33653862"
    assert [i for i, c in enumerate(aug) if c["is_tombstone"]] == [0, 3, 4]


def test_tombstones_are_not_counted_as_backing_sources():
    """The source-chip summary says which sources back the answer. A withdrawn
    stub backs nothing, so it must not appear and must not inflate a count."""
    aug, chips = _aug([_STUB, _REAL, _STUB], "en")
    labels = {ch["label"]: ch["count"] for ch in chips}
    assert "Local" not in labels and "Source withdrawn" not in labels and "FDA" not in labels
    assert labels == {"PubMed": 1}


def test_a_stub_is_never_presented_as_clickable_provenance():
    """Stored `url` is empty, so the template's `{% if c.url %}` must not offer a
    'View source' link. Asserted here so a future default-URL change cannot
    silently turn a tombstone back into a provenance claim."""
    aug, _ = _aug([_STUB], "en")
    assert not aug[0].get("url")


def test_real_citations_are_untouched_by_the_tombstone_path():
    """Negative control: the change must alter nothing for a normal citation."""
    aug, chips = _aug([_REAL], "en")
    c = aug[0]
    assert c["is_tombstone"] is False
    assert c["source_label"] == "PubMed"
    assert c["cred_label"] == "Peer Reviewed"
    assert c["credibility"] == "peer-reviewed"
    assert chips == [{"label": "PubMed", "count": 1}]


# ═══════════════════════════════════════════════════════════════════════════
# WRITE-PATH CASES — TECH_DEBT [P2 · API contract], tombstone-at-write (2026-08-10)
#
# THE BUSINESS RULE (Rule 17): /api/share/create must never PERSIST a `local`
# citation still carrying a credibility claim, and must never accept an
# unbounded payload onto a public page — while staying LENIENT about unknown
# values, because rejecting them would break stale clients replaying pre-c1
# answers (the open #7 population) and valid-but-unmapped CredibilityLevel
# members like clinical-trial / review.
#
# These assert the STORED object, not the rendered page. Render coverage is
# above; test_write_and_render_tombstones_are_identical pins the two together.
# ═══════════════════════════════════════════════════════════════════════════
import pytest  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from api.server import CitationIn, ShareCreateRequest  # noqa: E402


def _store(citations):
    """Mirror the store site: validate, dump, tombstone `local`. Returns stored JSON."""
    body = ShareCreateRequest(
        query_id="q1", query_text="t", answer_text="a", citations=citations
    )
    cits = [c.model_dump() for c in (body.citations or [])]
    return [
        sr.tombstone_citation(c) if sr.is_local_citation(c) else c
        for c in cits
    ]


def test_write_persists_local_citation_already_tombstoned():
    """(a) A `local` citation is stored WITHOUT its credibility claim."""
    stored = _store([_STUB])
    assert len(stored) == 1, "the slot must be kept — dropping it renumbers the prose"
    assert stored[0]["credibility"] is None, "an empty stub was persisted claiming 'official'"
    assert stored[0]["url"] == ""
    assert stored[0]["source_type"] == "local", "must stay recognisable to the renderer"
    assert stored[0]["title"] == _STUB["title"]
    assert stored[0]["snippet"] == _STUB["snippet"], "snippet stays — it shows WHY it was withdrawn"


@pytest.mark.parametrize("stype", ["pubmed", "tfda", "dailymed"])
def test_write_does_not_mutate_normal_citations(stype):
    """(b) No collateral mutation: a real citation survives byte-identical."""
    src = dict(_REAL, source_type=stype)
    stored = _store([src])[0]
    for k, v in src.items():
        assert stored[k] == v, f"{stype}: field {k!r} was mutated on the write path"


def test_write_accepts_unknown_source_type_and_leaves_it_alone():
    """(c) LENIENT: an unknown source_type is accepted, stored, NOT tombstoned.

    Rejecting here would break stale clients and unmapped-but-valid values.
    """
    src = dict(_REAL, source_type="some-future-source", credibility="clinical-trial")
    stored = _store([src])[0]
    assert stored["source_type"] == "some-future-source"
    assert stored["credibility"] == "clinical-trial", "a valid enum member must not be stripped"


@pytest.mark.parametrize("bad,why", [
    (["not-an-object"], "a non-object citation item"),
    ([{"source_type": "pubmed"}] * 51, "more than 50 citations"),
    ([{"source_type": "x" * 65}], "an over-bounds source_type"),
    ([{"url": "u" * 2049}], "an over-bounds url"),
    ([{"snippet": "s" * 8001}], "an over-bounds snippet"),
])
def test_structurally_invalid_payloads_are_rejected(bad, why):
    """(d) The ONLY new rejection class is structural — it becomes a 422."""
    with pytest.raises(ValidationError):
        ShareCreateRequest(query_id="q", query_text="t", answer_text="a", citations=bad)


def test_write_and_render_tombstones_are_identical():
    """(e) PARITY PIN — the single-transform guarantee (Rule 19).

    A row tombstoned AT WRITE must render exactly as a row tombstoned AT RENDER.
    If these ever diverge, two implementations have appeared and the 8 pre-c1
    stubs in prod would render differently from anything created after fly 218.
    """
    # Compare what the TEMPLATE consumes, not the raw dicts. Raw equality is too
    # strict and would fail for a reason invisible to the reader: the write path
    # goes through `model_dump()`, which materialises undeclared optionals as
    # explicit `None`, whereas the render path sees the original dict with those
    # keys absent. Jinja treats missing and None identically (`{% if c.authors %}`
    # is falsy for both), so the PAGE is the same — asserting dict equality would
    # pin an implementation detail and fail on a non-difference.
    consumed = ("is_tombstone", "source_label", "source_color", "cred_label",
                "cred_bg", "cred_color", "abstract_truncated", "url", "title",
                "authors", "journal", "year", "source_type")
    for locale in ("en", "zh-TW"):
        at_write, chips_w = _aug(_store([_STUB, _REAL]), locale)
        at_render, chips_r = _aug([_STUB, _REAL], locale)
        assert len(at_write) == len(at_render)
        for i, (w, r) in enumerate(zip(at_write, at_render)):
            for f in consumed:
                assert w.get(f) == r.get(f), (
                    f"{locale}: citation[{i}] field {f!r} differs between a row "
                    f"tombstoned AT WRITE and one tombstoned AT RENDER — two "
                    f"implementations have appeared (Rule 19)"
                )
        assert chips_w == chips_r, f"{locale}: source chips diverged"


def test_citation_model_covers_every_field_the_renderer_reads():
    """Guard: the typed model must not silently DROP a field the renderer needs.

    Pydantic ignores undeclared extras, so a field the renderer reads but the
    model omits would vanish at write and degrade the page.
    """
    for field in ("source_type", "url", "credibility", "snippet", "abstract", "text",
                  "title", "authors", "journal", "year"):
        assert field in CitationIn.model_fields, f"renderer reads {field!r}; model would drop it"
