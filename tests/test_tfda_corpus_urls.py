# -*- coding: utf-8 -*-
"""TFDA indication-corpus citation URLs — a1-iii deep-link invariants (v196).

Business rule pinned (CLAUDE.md Rule 17): every corpus doc with a 許可證字號 must
cite the per-字號 deep-link (https://mcp.fda.gov.tw/im_detail_pdf/{URL-encoded 字號})
so a user can open THAT drug's 仿單資料 page; docs without a 字號 fall back to the
portal base (never a broken path). The host must stay *.fda.gov.tw or the frontend
chip mapping (utils/sourceLabels.ts detectSourceType) would stop resolving 'tfda'.

Run: python tests/test_tfda_corpus_urls.py   (or via pytest)
"""
import json
import os
import sys
from urllib.parse import quote, unquote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CORPUS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "tfda", "indication_corpus.json")

DEEP_PREFIX = "https://mcp.fda.gov.tw/im_detail_pdf/"
PORTAL = "https://mcp.fda.gov.tw/"


def _docs():
    with open(CORPUS, encoding="utf-8") as fh:
        return json.load(fh)["documents"]


def test_deep_link_iff_license_present():
    docs = _docs()
    assert len(docs) > 10_000, "corpus unexpectedly small"
    deep = portal = 0
    for i, d in enumerate(docs):
        lic = d["source_id"]
        if lic:
            assert d["url"] == DEEP_PREFIX + quote(lic, safe=""), \
                f"doc {i} ({d['title']}): url is not the encoded deep-link: {d['url']}"
            assert unquote(d["url"][len(DEEP_PREFIX):]) == lic, \
                f"doc {i}: URL does not decode back to the 字號"
            deep += 1
        else:
            assert d["url"] == PORTAL, f"doc {i}: missing-字號 doc must use the portal base"
            portal += 1
    assert deep > 0, "no deep-links found — regen missing?"


def test_host_keeps_tfda_chip_mapping():
    # frontend detectSourceType maps host contains 'fda.gov.tw' → 'tfda' chip;
    # the deep-link must not move off that host.
    for d in _docs()[:50]:
        assert "mcp.fda.gov.tw" in d["url"]


def test_content_untouched_by_url_change():
    # the embedded content (what the LLM sees + what got embedded) must still carry
    # the self-scoping framing — the a1-iii change was url-field-only, no re-embed.
    for d in _docs()[:50]:
        assert d["content"].startswith("[TFDA 核准適應症"), "content framing changed!"
        assert d["source_id"] in d["content"] or not d["source_id"]


# ── v197: representative-row self-consistency (P1 citation-integrity guard) ─────
# The v193 build selected rep name and rep 字號 INDEPENDENTLY per group, so 12.1%
# of docs showed drug A's name with drug B's 字號 (冠脂妥 ↔ 諾脂替 057803). Fixed
# v197: both must come from ONE row. This pins the mismatch count at 0 — if it
# ever rises, the citation card lies about which product the deep-link opens.

def test_representative_name_and_license_are_one_row():
    from api.services.tfda_lookup import load_snapshot_records, norm_ws
    snapshot = os.path.join(os.path.dirname(CORPUS), "snapshot_20260630", "drug_license_id37.zip")
    lic_to_names = {}
    for r in load_snapshot_records(snapshot):
        lic_to_names.setdefault(norm_ws(r.get("許可證字號", "")), set()).add(
            norm_ws(r.get("中文品名", "")))
    mismatches = []
    for d in _docs():
        if d["source_id"] and d["title"] not in lic_to_names.get(d["source_id"], set()):
            mismatches.append((d["title"], d["source_id"]))
    assert not mismatches, (
        f"{len(mismatches)} docs show a name with another product's 字號 "
        f"(first: {mismatches[:3]}) — the v193 independent-selection defect is back")


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS  {name}")
            except AssertionError as e:
                failures += 1
                print(f"FAIL  {name}: {e}")
    print(f"\n{'ALL PASS' if failures == 0 else f'{failures} FAILED'}")
    sys.exit(1 if failures else 0)
