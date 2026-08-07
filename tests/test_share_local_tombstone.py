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
