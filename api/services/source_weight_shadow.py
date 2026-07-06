# -*- coding: utf-8 -*-
"""Source-weighting SHADOW observer (PRD §2.10.3 + §2.10.6 front half).

MEASUREMENT-ONLY. This module computes would-be rankings and logs raw per-doc
signals; it NEVER mutates a document's relevance_score and NEVER changes what the
retriever returns. It is a pure function library shared by two callers:
  1. server.py `_run_source_weight_shadow_background` (behind SOURCE_WEIGHT_SHADOW)
  2. scripts/source_weight_shadow_eval.py (the offline data-report battery)

Design constraints (2026-07-04 probe):
  - The reranker OVERWRITES relevance_score, so any composite computed PRE-rerank is
    erased. We therefore compute variants POST-rerank (blend over the reranker score)
    and log RAW signals so offline re-simulation (incl. feeding signals INTO the
    reranker) can sweep weights later.
  - NO additional LLM calls. Tier classification is deterministic.

Weights are spec hypotheses (PRD §2.10.3 :902 + §2.10.6 :943-951); they live in ONE
config dict so offline sweeps can vary them without touching logic.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ── Weight config (spec defaults; offline sweeps override this dict) ─────────────────
SOURCE_WEIGHTS = {
    "fda": 1.5,      # openFDA official label
    "dailymed": 1.5, # (reserved — no dailymed source in code yet)
    "tfda": 1.5,     # TFDA official 核准適應症 label
    "local": 1.5,    # cached FDA drug labeling (relabels to FDA) → label-source weight
    "who": 1.3,      # (reserved — Phase 1C)
    "pubmed": 1.0,   # literature baseline
}
DEFAULT_SOURCE_WEIGHT = 1.0

TIER_WEIGHTS = {1: 2.0, 2: 1.5, 3: 1.2, 4: 1.0, 5: 0.7}
DEFAULT_TIER = 4          # observational baseline when nothing else matches
DEFAULT_TIER_WEIGHT = 1.0

# Label sources default to Tier 2 per PRD §2.10.6 :963 (official label, not a study).
LABEL_SOURCE_DEFAULT_TIER = 2
# ⚠ FOUNDER DECISION (flagged): the PRD does NOT specify a tier for the LOCAL drug
# vector store. It is cached FDA drug labeling (relabels to FDA in the UI), so we treat
# it as a label source → Tier 2, consistent with openFDA. Flagged in TECH_DEBT for review.
LOCAL_DEFAULT_TIER = 2

# ── Deterministic tier classification (PubMed publication_type + keyword fallback) ──
# PublicationType (efetch) → tier. Longest/most-specific intent first.
_PUBTYPE_TIER = {
    "practice guideline": 1,
    "guideline": 1,
    "consensus development conference": 1,
    "systematic review": 2,
    "meta-analysis": 2,
    "randomized controlled trial": 3,
    "controlled clinical trial": 3,
    "clinical trial, phase iii": 3,
    "clinical trial, phase iv": 3,
    "multicenter study": 3,
    "clinical trial": 3,
    "observational study": 4,
    "comparative study": 4,
    "case reports": 5,   # a single case report is the weakest evidence
    "review": 4,         # narrative review (NOT systematic) — commentary-tier
    "editorial": 4,
    "comment": 4,
}

# Title/journal keyword fallback (PRD :962) when publication_type is absent/unhelpful.
_TITLE_TIER_RULES = [
    (1, ("clinical practice guideline", "practice guideline", "consensus statement", "guideline for")),
    (2, ("systematic review", "meta-analysis", "meta analysis", "cochrane")),
    (3, ("randomized controlled trial", "randomised controlled trial", "double-blind", "randomized trial", "rct")),
    (5, ("survey of", "questionnaire", "knowledge, attitude", "knowledge and attitude", "cross-sectional survey")),
    (4, ("observational", "case-control", "cohort study", "case report", "case series", "commentary")),
]
_JOURNAL_TIER_HINTS = [
    (2, ("cochrane database",)),
]


def classify_tier(doc) -> tuple[int, str]:
    """Return (tier 1..5, reason). Deterministic; no LLM, no network.

    Precedence: PubMed publication_type → title keyword → journal hint → source default.
    """
    try:
        source = _source_key(doc)
        # Non-PubMed sources: source-default tiers (PRD §2.10.6 :963).
        if source in ("fda", "dailymed", "tfda"):
            return LABEL_SOURCE_DEFAULT_TIER, f"label-source default (source={source})"
        if source == "local":
            return LOCAL_DEFAULT_TIER, "local drug store default (cached FDA labeling; FOUNDER-FLAGGED)"
        if source == "who":
            return 1, "WHO global guideline default"

        # PubMed: publication_type first (most specific wins by lowest tier number).
        pubtypes = [str(p).strip().lower() for p in (getattr(doc, "publication_types", None) or [])]
        best = None
        for p in pubtypes:
            t = _PUBTYPE_TIER.get(p)
            if t is not None and (best is None or t < best[0]):
                best = (t, f"publication_type='{p}'")
        if best is not None:
            return best

        # Title/journal keyword fallback.
        title = (getattr(doc, "title", "") or "").lower()
        for tier, needles in _TITLE_TIER_RULES:
            if any(n in title for n in needles):
                return tier, f"title-keyword ({tier})"
        journal = (getattr(doc, "journal", "") or "").lower()
        for tier, needles in _JOURNAL_TIER_HINTS:
            if any(n in journal for n in needles):
                return tier, f"journal-hint ({tier})"

        return DEFAULT_TIER, "pubmed default (no publication_type / keyword match)"
    except Exception as e:  # classification must never break the shadow
        logger.warning("[SourceWeightShadow] classify_tier failed: %s", e)
        return DEFAULT_TIER, f"error-default ({type(e).__name__})"


def _source_key(doc) -> str:
    st = getattr(doc, "source_type", None)
    raw = getattr(st, "value", st)
    return str(raw or "").strip().lower()


def source_weight(doc, weights: dict | None = None) -> float:
    w = weights or SOURCE_WEIGHTS
    return w.get(_source_key(doc), DEFAULT_SOURCE_WEIGHT)


def tier_weight(tier: int, weights: dict | None = None) -> float:
    w = weights or TIER_WEIGHTS
    return w.get(tier, DEFAULT_TIER_WEIGHT)


def _is_label_source(doc) -> bool:
    return _source_key(doc) in ("fda", "dailymed", "tfda", "local")


# ── Composite variants (post-rerank blend over the reranker score) ──────────────────
def _variant_scores(rerank_score: float, sw: float, tw: float) -> dict[str, float]:
    """V1 = rerank × source × tier; V2 = rerank × tier; V3 = rerank × source."""
    return {
        "V1": rerank_score * sw * tw,
        "V2": rerank_score * tw,
        "V3": rerank_score * sw,
    }


def build_shadow_record(pool, *, top_k: int, source_weights=None, tier_weights=None,
                        query_label: str | None = None) -> dict:
    """Build ONE structured shadow record from the full reranked candidate pool.

    `pool` = list of (doc, rerank_score_0_1) in the reranker's returned order
    (highest first). `top_k` = citation cutoff (what the user sees). Pure math —
    reads the docs, never mutates them.
    """
    n = len(pool)
    per_doc = []
    for cur_rank, (doc, rr) in enumerate(pool):
        tier, reason = classify_tier(doc)
        sw = source_weight(doc, source_weights)
        tw = tier_weight(tier, tier_weights)
        variants = _variant_scores(rr, sw, tw)
        per_doc.append({
            "source_type": _source_key(doc),
            "is_label_source": _is_label_source(doc),
            "tier": tier,
            "tier_reason": reason,
            "year": getattr(doc, "year", None),
            "seed_or_semantic": None,   # pre-rerank score is erased; kept for schema stability
            "rerank_score": round(float(rr), 4),
            "source_weight": sw,
            "tier_weight": tw,
            "current_rank": cur_rank,
            "_v": variants,
            "title": (getattr(doc, "title", "") or "")[:80],
            "source_id": getattr(doc, "source_id", ""),
        })

    # Would-be ranks under each variant (stable sort desc by variant score).
    for v in ("V1", "V2", "V3"):
        order = sorted(range(n), key=lambda i: per_doc[i]["_v"][v], reverse=True)
        for new_rank, idx in enumerate(order):
            per_doc[idx][f"{v}_rank"] = new_rank

    # Summary: did the top_k SET change under each variant?
    cur_topk = {d["source_id"] for d in per_doc if d["current_rank"] < top_k}
    summary = {"pool_size": n, "top_k": top_k}
    for v in ("V1", "V2", "V3"):
        v_topk = {d["source_id"] for d in per_doc if d[f"{v}_rank"] < top_k}
        summary[f"top_k_changed_under_{v}"] = (v_topk != cur_topk)
        summary[f"{v}_entered_topk"] = sorted(v_topk - cur_topk)
        summary[f"{v}_left_topk"] = sorted(cur_topk - v_topk)

    # Inversion flags: a label source currently ranked BELOW a Tier-4/5 doc that V1
    # would place above it (the §2.10.3 :903 "study drowns the label" case).
    inversions = []
    for lab in per_doc:
        if not lab["is_label_source"]:
            continue
        for study in per_doc:
            if study["is_label_source"] or study["tier"] < 4:
                continue
            if lab["current_rank"] > study["current_rank"] and lab["V1_rank"] < study["V1_rank"]:
                inversions.append({
                    "label": lab["source_id"], "label_source": lab["source_type"],
                    "study": study["source_id"], "study_tier": study["tier"],
                    "cur": [lab["current_rank"], study["current_rank"]],
                    "v1": [lab["V1_rank"], study["V1_rank"]],
                })

    # Danger-signal: a TFDA (or any label) doc that V1 would PROMOTE across the cutoff
    # (surfaced for the danger-path safety recheck — is a label promoted INTO top_k?).
    label_promoted_into_topk = [
        d["source_id"] for d in per_doc
        if d["is_label_source"] and d["current_rank"] >= top_k and d["V1_rank"] < top_k
    ]
    tfda_promoted_into_topk = [
        d["source_id"] for d in per_doc
        if d["source_type"] == "tfda" and d["current_rank"] >= top_k and d["V1_rank"] < top_k
    ]

    # Strip the internal `_v` before emitting.
    for d in per_doc:
        d.pop("_v", None)

    record = {
        "query_label": query_label,
        "summary": summary,
        "inversion_flags": inversions,
        "label_promoted_into_topk": label_promoted_into_topk,
        "tfda_promoted_into_topk": tfda_promoted_into_topk,
        "tier_distribution": _tier_dist(per_doc),
        "per_doc": per_doc,
    }
    return record


def _tier_dist(per_doc) -> dict:
    dist = {}
    for d in per_doc:
        dist[d["tier"]] = dist.get(d["tier"], 0) + 1
    return {str(k): dist[k] for k in sorted(dist)}


def to_sink_dict(record: dict) -> dict:
    """Privacy-compliant subset stored on AuditLog.extra_data (no raw query text;
    the AuditLog row already carries the sanitized query_content). Drops per-doc
    titles to keep the sink compact."""
    slim = dict(record)
    slim.pop("query_label", None)
    slim["per_doc"] = [
        {k: v for k, v in d.items() if k != "title"} for d in record.get("per_doc", [])
    ]
    return slim
