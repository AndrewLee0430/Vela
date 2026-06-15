#!/usr/bin/env python
"""Stage 2 — CITATION-TRUTH spot-check (Task A, medical answer quality).

Samples Research answers and, for each cited source, checks:
  (a) EXISTENCE — does the PMID resolve to a real PubMed article? (NCBI efetch)
  (b) CLAIM-SUPPORT — does that abstract actually support the specific claim it is
      tagged to? (gpt-4.1 structured judge, abstract-only)
  (c) GROUNDING — the existing LLMJudge has_hallucination / source_support.

This produces EVIDENCE for a human (Andrew + his medical advisor) to judge delivery
readiness. It is NOT a Claude endorsement and does NOT declare quality "proven/safe".

⚠️ The unsupported / wrong_scope counts are a LOWER BOUND: the judge sees only the
ABSTRACT, not the full paper, so a full-text-supported claim can read as
partial/unsupported (false negative). Every flagged pair needs HUMAN full-text review.

Dev-only: generates answers against the dev backend (TEST_BASE_URL); only READS PubMed +
calls judges. No destructive ops.
"""

import os
import re
import sys
import json
import time
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from dotenv import load_dotenv
load_dotenv()

import httpx
from openai import OpenAI

DEV_SUBSTR = "ep-spring-voice-a127ye10"
BASE_URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8000")
TOKEN = os.getenv("TEST_AUTH_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
RESULTS_DIR = _REPO / "tests" / "results"
CLAIM_MODEL = "gpt-4.1"
MAX_PAIRS_PER_ANSWER = 10   # bound cost on citation-dense answers

# Curated sample: 10 narrow + 10 broad/population (broad = where wrong-scope is likeliest)
SAMPLE = [
    ("N01", "narrow", "What are the common side effects of metformin?"),
    ("N02", "narrow", "What is the interaction between warfarin and aspirin?"),
    ("N03", "narrow", "What monitoring is required for patients on lithium therapy?"),
    ("N04", "narrow", "Are ACE inhibitors safe in pregnancy?"),
    ("N05", "narrow", "What causes statin-induced myopathy and how is it managed?"),
    ("N06", "narrow", "What are the symptoms of SSRI discontinuation syndrome?"),
    ("N07", "narrow", "What are the clinical signs of digoxin toxicity?"),
    ("N08", "narrow", "How do DOACs compare to warfarin for stroke prevention in atrial fibrillation?"),
    ("N09", "narrow", "How should metformin be dosed in patients with renal impairment?"),
    ("N10", "narrow", "What are the thyroid effects of amiodarone?"),
    ("B01", "broad", "Why is polypharmacy a serious problem in elderly Asian patients?"),
    ("B02", "broad", "How should cardiovascular disease be prevented in East Asian populations?"),
    ("B03", "broad", "What is the best approach to diabetes management in older adults?"),
    ("B04", "broad", "How is hypertension managed during pregnancy?"),
    ("B05", "broad", "What is the state of antibiotic resistance in Southeast Asia?"),
    ("B06", "broad", "What interventions prevent falls in geriatric patients?"),
    ("B07", "broad", "How is stroke prevented in elderly patients with atrial fibrillation?"),
    ("B08", "broad", "How is osteoporosis treated in postmenopausal Asian women?"),
    ("B09", "broad", "How should depression be treated in adolescents?"),
    ("B10", "broad", "How is chronic kidney disease managed in patients with diabetes?"),
]

CLAIM_JUDGE_SYSTEM = (
    "You are a strict medical citation auditor. You verify whether a cited abstract supports "
    "a specific claim from an AI-generated answer. Base your verdict ONLY on the provided "
    "abstract text — you see the ABSTRACT, not the full paper. Do NOT use outside medical "
    "knowledge to fill gaps; if the abstract is insufficient to judge, that is \"partial\". "
    "Output JSON only.\n\n"
    "Verdict definitions:\n"
    "- supported: the abstract directly states or strongly implies the claim.\n"
    "- partial: supports part of the claim, or the claim is broader than the abstract shows, "
    "or the abstract is insufficient to fully confirm.\n"
    "- unsupported: the abstract does not address the claim (the citation does not back it).\n"
    "- contradicts: the abstract states the opposite of the claim.\n"
    "- wrong_scope: the abstract is about a DIFFERENT population / setting / age-group / region "
    "than the claim implies (e.g. claim says 'Asian elderly' but the cohort is UK-Pakistani; a "
    "pediatric paper cited for an adult claim). Highest-priority label."
)


def _guard_env():
    url = os.environ.get("DATABASE_URL", "")
    host = url.split("@", 1)[-1].split("/", 1)[0] if "@" in url else "(unset)"
    is_dev = DEV_SUBSTR in url
    print(f"[env] backend DATABASE_URL host = {host}  (dev branch: {is_dev})")
    print(f"[env] TEST_BASE_URL = {BASE_URL}")
    print(f"[env] OPENAI_API_KEY set: {bool(os.getenv('OPENAI_API_KEY'))} | token set: {bool(TOKEN)}")
    if not is_dev:
        sys.exit("ABORT: DATABASE_URL is not the dev branch — refusing (answer-gen would hit the wrong DB).")
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("ABORT: OPENAI_API_KEY not set.")


async def gen_answer(client, query):
    """POST /api/research (UI=en), return (answer_text, citations[list of dicts])."""
    answer, citations = "", []
    r = await client.post(f"{BASE_URL}/api/research",
                          json={"question": query, "response_language": "en"},
                          headers=HEADERS, timeout=900.0)
    r.raise_for_status()
    for line in r.text.split("\n"):
        line = line.strip()
        if not line.startswith("data:"):
            continue
        raw = line[5:].strip()
        if not raw or raw == "[DONE]":
            continue
        try:
            ev = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "answer":
            answer += ev.get("content", "") or ""
        elif ev.get("type") == "citations":
            citations = ev.get("content", []) or []
        elif ev.get("type") == "error":
            answer = f"[ERROR] {ev.get('content', '')}"
    return answer.strip(), citations


def extract_pmid(citation):
    sid = (citation.get("source_id") or "")
    m = re.search(r"(\d{5,})", sid) or re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", citation.get("url") or "")
    return m.group(1) if m else None


def claim_pairs(answer, cit_by_id):
    """Pair each sentence carrying [n] marker(s) with the cited PMID(s). Sentence-level."""
    # strip markdown noise, split into sentences
    text = re.sub(r"[#*`>]", " ", answer)
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    pairs = []
    seen = set()
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        for n in re.findall(r"\[(\d+)\]", sent):
            cit = cit_by_id.get(int(n))
            if not cit:
                continue
            pmid = extract_pmid(cit)
            if not pmid:
                continue
            key = (sent, pmid)
            if key in seen:
                continue
            seen.add(key)
            claim = re.sub(r"\[\d+\]", "", sent).strip()
            pairs.append({"claim": claim, "pmid": pmid, "cit_id": int(n)})
    return pairs


def judge_claim(oai, query, claim, pmid, title, abstract):
    user = (f"QUERY (user's question, for population/scope context):\n{query}\n\n"
            f"CLAIM (a sentence from the AI answer, citing this source):\n{claim}\n\n"
            f"CITED ABSTRACT (PMID {pmid}):\nTitle: {title}\nAbstract: {abstract[:3500]}\n\n"
            "Return JSON: {\"verdict\": \"supported|partial|unsupported|contradicts|wrong_scope\", "
            "\"evidence_quote\": \"<short verbatim quote from the abstract, or 'none'>\", "
            "\"scope_note\": \"<if wrong_scope: abstract's actual population/setting vs the claim's; else ''>\", "
            "\"reasoning\": \"<1-2 sentences, abstract-grounded>\"}")
    try:
        resp = oai.chat.completions.create(
            model=CLAIM_MODEL, temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": CLAIM_JUDGE_SYSTEM},
                      {"role": "user", "content": user}],
            max_tokens=400)
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        return {"verdict": "error", "evidence_quote": "", "scope_note": "", "reasoning": str(e)}


async def main_run(throttle: float = 0.0):
    _guard_env()
    if throttle:
        print(f"[throttle] sleeping {throttle}s between answer generations (gentler on API quota)")
    from api.data_sources.pubmed import PubMedClient
    from api.utils.llm_judge import LLMJudge, Source

    oai = OpenAI()
    pubmed = PubMedClient()
    judge = LLMJudge()
    RESULTS_DIR.mkdir(exist_ok=True)

    answers = []
    print(f"\n=== Generating {len(SAMPLE)} answers (dev backend) ===")
    async with httpx.AsyncClient() as client:
        for cid, tag, query in SAMPLE:
            t0 = time.time()
            ans, cits = await gen_answer(client, query)
            cit_by_id = {int(c["id"]): c for c in cits if "id" in c}
            pmids = sorted({p for p in (extract_pmid(c) for c in cits) if p})
            print(f"  [{cid}/{tag}] {len(cits)} citations, {len(pmids)} PMIDs  ({round(time.time()-t0)}s)")
            answers.append({"id": cid, "tag": tag, "query": query, "answer": ans,
                            "citations": cits, "cit_by_id": cit_by_id, "pmids": pmids})
            if throttle:
                await asyncio.sleep(throttle)

    # ---- existence + abstracts (batched efetch per answer) ----
    print("\n=== Existence check (NCBI efetch) ===")
    pmid_abstract = {}   # pmid -> (title, abstract) or None if missing
    for a in answers:
        if not a["pmids"]:
            continue
        try:
            arts = await pubmed.fetch_details(a["pmids"])
        except Exception as e:
            print(f"  [{a['id']}] efetch error: {e}")
            arts = []
        found = {art.pmid: art for art in arts}
        for p in a["pmids"]:
            art = found.get(p)
            pmid_abstract[p] = (art.title, art.abstract) if art else None
        miss = [p for p in a["pmids"] if pmid_abstract.get(p) is None]
        print(f"  [{a['id']}] {len(a['pmids'])-len(miss)}/{len(a['pmids'])} resolve" +
              (f"  ⚠️ MISSING: {miss}" if miss else ""))
        time.sleep(0.5)

    # ---- claim-support + grounding ----
    print("\n=== Claim-support (gpt-4.1, abstract-only) + grounding (LLMJudge) ===")
    support_dist = {"supported": 0, "partial": 0, "unsupported": 0, "contradicts": 0, "wrong_scope": 0, "error": 0}
    scary = []
    exist_total = exist_ok = 0
    halluc_count = 0
    src_support_scores = []

    for a in answers:
        # existence tally
        for p in a["pmids"]:
            exist_total += 1
            if pmid_abstract.get(p) is not None:
                exist_ok += 1
        # grounding (LLMJudge)
        try:
            srcs = [Source(source_id=c.get("source_id", ""), content=c.get("snippet", "") or "")
                    for c in a["citations"]]
            jr = await judge.evaluate(a["query"], a["answer"], srcs) if srcs else {}
            a["has_hallucination"] = bool(jr.get("has_hallucination"))
            a["source_support"] = jr.get("scores", {}).get("source_support")
            if a["has_hallucination"]:
                halluc_count += 1
            if a["source_support"] is not None:
                src_support_scores.append(a["source_support"])
        except Exception as e:
            a["has_hallucination"] = None
            a["source_support"] = None
        # claim-support pairs
        pairs = claim_pairs(a["answer"], a["cit_by_id"])[:MAX_PAIRS_PER_ANSWER]
        a["n_pairs"] = len(pairs)
        a["pair_results"] = []
        for pr in pairs:
            absdata = pmid_abstract.get(pr["pmid"])
            if absdata is None:
                continue   # non-existent PMID handled in existence tally
            title, abstract = absdata
            jc = judge_claim(oai, a["query"], pr["claim"], pr["pmid"], title, abstract)
            v = jc.get("verdict", "error")
            support_dist[v] = support_dist.get(v, 0) + 1
            rec = {"answer_id": a["id"], "tag": a["tag"], "claim": pr["claim"], "pmid": pr["pmid"],
                   "verdict": v, "evidence_quote": jc.get("evidence_quote", ""),
                   "scope_note": jc.get("scope_note", ""), "reasoning": jc.get("reasoning", "")}
            a["pair_results"].append(rec)
            if v in ("unsupported", "contradicts", "wrong_scope"):
                scary.append(rec)
            time.sleep(0.2)
        print(f"  [{a['id']}] pairs={a['n_pairs']} halluc={a['has_hallucination']} "
              f"src_support={a['source_support']}")

    # ---- report ----
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS_DIR / f"citation_truth_{ts}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"timestamp": ts, "sample": len(SAMPLE),
                   "existence": {"ok": exist_ok, "total": exist_total},
                   "support_distribution": support_dist,
                   "hallucination_answers": halluc_count,
                   "mean_source_support": round(sum(src_support_scores)/len(src_support_scores), 1) if src_support_scores else None,
                   "scary_examples": scary,
                   "answers": [{k: v for k, v in a.items() if k != "cit_by_id"} for a in answers]},
                  f, ensure_ascii=False, indent=2)

    total_pairs = sum(support_dist.values())
    print("\n" + "=" * 64)
    print("CITATION-TRUTH REPORT  (EVIDENCE for human review — NOT an endorsement)")
    print("=" * 64)
    print(f"Existence: {exist_ok}/{exist_total} cited PMIDs resolve "
          f"({round(exist_ok/exist_total*100,1) if exist_total else 0}%)")
    print(f"Grounding: {halluc_count}/{len(answers)} answers flagged has_hallucination; "
          f"mean source_support = {round(sum(src_support_scores)/len(src_support_scores),1) if src_support_scores else 'n/a'}")
    print(f"\nClaim-support distribution ({total_pairs} claim-citation pairs):")
    for k in ("supported", "partial", "unsupported", "contradicts", "wrong_scope", "error"):
        n = support_dist.get(k, 0)
        pct = round(n/total_pairs*100, 1) if total_pairs else 0
        print(f"   {k:13s} {n:3d}  ({pct}%)")
    print(f"\n🚩 SCARY EXAMPLES (unsupported / contradicts / wrong_scope) — {len(scary)} — need HUMAN full-text review:")
    for s in scary:
        print(f"\n  [{s['answer_id']}/{s['tag']}] verdict={s['verdict'].upper()} PMID:{s['pmid']}")
        print(f"    CLAIM: {s['claim'][:240]}")
        print(f"    EVIDENCE: {s['evidence_quote'][:240]}")
        if s['scope_note']:
            print(f"    SCOPE:  {s['scope_note'][:240]}")
        print(f"    WHY:    {s['reasoning'][:240]}")
    print("\n⚠️ LOWER BOUND: judge sees the ABSTRACT only — full-text-supported claims can read")
    print("   as partial/unsupported. Every flagged pair above needs human full-text confirmation.")
    print(f"\nSaved → {out}")


# ── Adversarial contradiction set: 16 "famously counterintuitive" + 3 cohort-specific ──
# cohort = surprising result in a SPECIFIC subgroup (polypharmacy profile) where the model is
# likeliest to "average back" to the general intuition — the more realistic / harder failure.
ADVERSARIAL = [
    ("C01", "famous", "What are the clinical outcomes of polypharmacy in elderly patients with atrial fibrillation?", "polypharmacy assoc. LOWER all-cause death (ChiOTEAF, confounding by indication)"),
    ("C02", "famous", "Does higher body weight affect survival in patients with heart failure?", "obesity paradox: higher BMI assoc. LOWER mortality in HF"),
    ("C03", "famous", "What are the benefits of intensive glucose control in type 2 diabetes?", "ACCORD: intensive glycemic control INCREASED mortality"),
    ("C04", "famous", "Should antiarrhythmic drugs be used to suppress premature ventricular contractions after a heart attack?", "CAST: flecainide/encainide INCREASED mortality"),
    ("C05", "famous", "Is supplemental oxygen beneficial in acute myocardial infarction without hypoxia?", "AVOID/DETO2X: routine O2 no benefit / possible harm in normoxic MI"),
    ("C06", "famous", "Are beta-blockers safe in patients with COPD?", "cardioselective beta-blockers SAFE/beneficial, not contraindicated"),
    ("C07", "famous", "Should aspirin be used for primary prevention in healthy older adults?", "ASPREE: no CV benefit, increased bleeding, possible increased mortality"),
    ("C08", "famous", "Do antioxidant supplements like beta-carotene reduce cancer risk in smokers?", "ATBC/CARET: beta-carotene INCREASED lung cancer in smokers"),
    ("C09", "famous", "What is the effect of digoxin on mortality in atrial fibrillation?", "observational analyses: digoxin assoc. INCREASED mortality"),
    ("C10", "famous", "Is very low dietary sodium intake associated with lower cardiovascular risk?", "J-curve: very low sodium assoc. HIGHER CV risk in some cohorts"),
    ("C11", "famous", "Does moderate alcohol consumption protect against cardiovascular disease?", "protective J-curve largely debunked (Mendelian randomization)"),
    ("C12", "famous", "Is bed rest recommended for acute low back pain?", "staying ACTIVE is better than bed rest"),
    ("C13", "famous", "How does smoking affect short-term outcomes after a STEMI?", "smoker's paradox: better short-term outcomes (age-confounded)"),
    ("C14", "famous", "Does a low-fat diet reduce cardiovascular disease risk?", "WHI dietary: no significant CVD reduction"),
    ("C15", "famous", "Is lower diastolic blood pressure always better in elderly hypertensive patients?", "J-curve: excessively low DBP assoc. harm"),
    ("C16", "famous", "Does hormone replacement therapy protect against cardiovascular disease?", "WHI: HRT INCREASED CV events (reversed prior protective belief)"),
    ("K01", "cohort", "What is the effect of non-selective beta-blockers in cirrhosis patients with refractory ascites?", "NSBBs assoc. INCREASED mortality in refractory-ascites subgroup (window hypothesis) — despite benefit in cirrhosis generally"),
    ("K02", "cohort", "Do statins reduce cardiovascular events in patients on hemodialysis?", "4D/AURORA: statins show NO CV benefit in dialysis patients — despite reducing CV events generally"),
    ("K03", "cohort", "Should anticoagulation be avoided in elderly atrial fibrillation patients at high risk of falls?", "anticoagulation benefit OUTWEIGHS fall-related bleeding risk; should NOT be withheld for fall risk — counterintuitive"),
    # ── HOLDOUT subset (added 2026-06-15) — NOT used to design the prompt fix; tests generalization. ──
    # expected_direction documented in note (judge does NOT read it; it compares answer vs its own cited abstract).
    ("H1", "holdout", "What is the effect of class I antiarrhythmic drugs (e.g. flecainide, encainide) on mortality after myocardial infarction?", "CAST: class I antiarrhythmics INCREASE mortality post-MI despite suppressing arrhythmia — counterintuitive"),
    ("H2", "holdout", "Is cigarette smoking associated with the risk of developing Parkinson's disease?", "smoking INVERSELY associated with PD risk (LOWER risk among smokers)"),
    ("H3", "holdout", "What is the effect of beta-blockers on mortality in heart failure with reduced ejection fraction (HFrEF)?", "beta-blockers REDUCE mortality / improve survival in HFrEF despite negative inotropy"),
    ("H4", "holdout", "What is the effect of early dietary peanut introduction on the risk of peanut allergy in infants?", "early introduction (LEAP) REDUCES peanut allergy incidence vs avoidance"),
    ("H5", "holdout", "What is the relationship between long-term bisphosphonate use and atypical femoral fractures?", "long-term bisphosphonate use INCREASES atypical femoral fracture risk (paradox for an anti-fracture drug)"),
]

DIRECTION_JUDGE_SYSTEM = (
    "You are a strict medical citation auditor checking DIRECTION OF EFFECT. A claim from an "
    "AI-generated answer cites a source. Determine whether the answer states the effect / "
    "association in the SAME direction as the cited abstract, or REVERSES it. Base your verdict "
    "ONLY on the provided abstract — you see the ABSTRACT, not the full paper. Do NOT use outside "
    "medical knowledge. Output JSON only.\n\n"
    "Verdicts:\n"
    "- same: the claim states the effect in the same direction as the abstract.\n"
    "- reversed: the claim states the OPPOSITE direction to the abstract (e.g. claim says a factor "
    "increases mortality but the abstract reports it is associated with lower mortality). HIGHEST PRIORITY.\n"
    "- not_directional: the claim is not about a directional effect/association.\n"
    "- abstract_silent: the abstract reports no directional effect relevant to this claim."
)


def judge_direction(oai, query, claim, pmid, title, abstract):
    user = (f"QUERY: {query}\n\nCLAIM (cites this source): {claim}\n\n"
            f"CITED ABSTRACT (PMID {pmid}):\nTitle: {title}\nAbstract: {abstract[:3500]}\n\n"
            "Return JSON: {\"direction\": \"same|reversed|not_directional|abstract_silent\", "
            "\"effect_in_claim\": \"<the direction the claim asserts>\", "
            "\"effect_in_abstract\": \"<the direction the abstract reports>\", "
            "\"evidence_quote\": \"<short verbatim quote from the abstract, or 'none'>\", "
            "\"reasoning\": \"<1-2 sentences>\"}")
    try:
        resp = oai.chat.completions.create(
            model=CLAIM_MODEL, temperature=0, response_format={"type": "json_object"},
            messages=[{"role": "system", "content": DIRECTION_JUDGE_SYSTEM},
                      {"role": "user", "content": user}], max_tokens=400)
        return json.loads(resp.choices[0].message.content)
    except Exception as e:
        return {"direction": "error", "effect_in_claim": "", "effect_in_abstract": "",
                "evidence_quote": "", "reasoning": str(e)}


async def main_adversarial(throttle: float = 0.0):
    _guard_env()
    if throttle:
        print(f"[throttle] sleeping {throttle}s between answer generations")
    from api.data_sources.pubmed import PubMedClient
    oai = OpenAI()
    pubmed = PubMedClient()
    RESULTS_DIR.mkdir(exist_ok=True)

    rows = []
    print(f"\n=== Generating {len(ADVERSARIAL)} adversarial answers (dev backend) ===")
    async with httpx.AsyncClient() as client:
        for cid, tag, query, note in ADVERSARIAL:
            t0 = time.time()
            try:
                ans, cits = await gen_answer(client, query)
            except Exception as e:
                ans, cits = f"[ERROR] {type(e).__name__}", []
            cit_by_id = {int(c["id"]): c for c in cits if "id" in c}
            pmids = sorted({p for p in (extract_pmid(c) for c in cits) if p})
            print(f"  [{cid}/{tag}] {len(cits)} cit, {len(pmids)} PMID ({round(time.time()-t0)}s)")
            rows.append({"id": cid, "tag": tag, "query": query, "note": note,
                         "answer": ans, "citations": cits, "cit_by_id": cit_by_id, "pmids": pmids})
            if throttle:
                await asyncio.sleep(throttle)

    print("\n=== Direction-of-effect judging (gpt-4.1, abstract-only) ===")
    for r in rows:
        r["pairs"] = []
        if not r["pmids"]:
            print(f"  [{r['id']}] no citations — skipped")
            continue
        try:
            arts = {a.pmid: a for a in await pubmed.fetch_details(r["pmids"])}
        except Exception:
            arts = {}
        time.sleep(0.5)
        for pr in claim_pairs(r["answer"], r["cit_by_id"])[:MAX_PAIRS_PER_ANSWER]:
            art = arts.get(pr["pmid"])
            if not art:
                continue
            jd = judge_direction(oai, r["query"], pr["claim"], pr["pmid"], art.title, art.abstract)
            r["pairs"].append({**pr, **jd})
            time.sleep(0.2)
        r["reversed"] = any(p.get("direction") == "reversed" for p in r["pairs"])
        print(f"  [{r['id']}/{r['tag']}] pairs={len(r['pairs'])} reversed={r['reversed']}")

    def rate(tag):
        grp = [r for r in rows if r["tag"] == tag and r["pmids"]]
        rev = [r for r in grp if r.get("reversed")]
        return len(rev), len(grp), grp, rev

    fr, ft, _, _ = rate("famous")
    kr, kt, _, _ = rate("cohort")
    all_rev = [p for r in rows for p in r.get("pairs", []) if p.get("direction") == "reversed"]
    nocit = [r["id"] for r in rows if not r["pmids"]]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = RESULTS_DIR / f"adversarial_contradiction_{ts}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"timestamp": ts,
                   "famous_reversal": {"reversed": fr, "answers": ft},
                   "cohort_reversal": {"reversed": kr, "answers": kt},
                   "reversed_pairs": all_rev, "no_citation_answers": nocit,
                   "rows": [{k: v for k, v in r.items() if k != "cit_by_id"} for r in rows]},
                  f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 64)
    print("ADVERSARIAL CONTRADICTION REPORT — UPPER BOUND (loaded toward failure)")
    print("EVIDENCE for the founder + medical advisor — NOT a recommendation.")
    print("=" * 64)
    print(f"FAMOUS-set reversal rate:  {fr}/{ft} answers reverse a finding "
          f"({round(fr/ft*100,1) if ft else 0}%)")
    print(f"COHORT-set reversal rate:  {kr}/{kt} answers reverse a finding "
          f"({round(kr/kt*100,1) if kt else 0}%)  <- the more realistic risk signal")
    if nocit:
        print(f"(answers with no citations, excluded: {nocit})")
    print(f"\n🚩 EVERY REVERSED claim ({len(all_rev)}) — quoted:")
    for r in rows:
        for p in r.get("pairs", []):
            if p.get("direction") != "reversed":
                continue
            print(f"\n  [{r['id']}/{r['tag']}] PMID:{p['pmid']}")
            print(f"    QUERY:  {r['query']}")
            print(f"    CLAIM:  {p['claim'][:240]}")
            print(f"    CLAIM SAYS:    {p.get('effect_in_claim','')[:160]}")
            print(f"    ABSTRACT SAYS: {p.get('effect_in_abstract','')[:160]}")
            print(f"    EVIDENCE: {p.get('evidence_quote','')[:240]}")
            print(f"    WHY:    {p.get('reasoning','')[:240]}")
    print("\n⚠️ UPPER BOUND: set is deliberately loaded toward failure. The Stage-2 random rate")
    print("   (~0.6% contradicts) is the lower bound; true population rate is between. Abstract-only —")
    print("   a clear direction reversal (e.g. OR 0.78) is robust, but each flag needs human full-text review.")
    print(f"\nSaved → {out}")


def main_plan():
    print("=== Stage 2 citation-truth — PLAN (no generation) ===")
    print(f"Sample: {len(SAMPLE)} answers (10 narrow + 10 broad/population)")
    for cid, tag, q in SAMPLE:
        print(f"  {cid} [{tag}] {q}")
    print("\nClaim-support judge rubric (system prompt):\n")
    print(CLAIM_JUDGE_SYSTEM)
    print("\nRun for real:  python scripts/citation_truth_check.py --run [--throttle 3]")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="generate + check (default: --plan)")
    ap.add_argument("--adversarial", action="store_true",
                    help="run the adversarial contradiction set (direction-of-effect judge)")
    ap.add_argument("--throttle", type=float, nargs="?", const=3.0, default=0.0,
                    help="seconds to sleep between answer generations (gentler on API quota; "
                         "bare --throttle = 3s). The back-to-back Stage-1 + Stage-2 load is what "
                         "drained the quota — use this on the re-run.")
    args = ap.parse_args()
    if args.adversarial:
        asyncio.run(main_adversarial(throttle=args.throttle))
    elif args.run:
        asyncio.run(main_run(throttle=args.throttle))
    else:
        main_plan()
