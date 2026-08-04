# -*- coding: utf-8 -*-
"""c2 Phase-1 READ-ONLY probe — Tasks B + C.

Queries DailyMed LIVE (v2 API) for the c2-i candidate moieties, enumerates candidate
labels per marketing-category tier, fetches each SPL, and reports:
  - the SPL DOCUMENT TYPE code (the Rx-vs-OTC discriminator candidate)
  - the marketing category recorded IN the SPL (<approval><code>)
  - which LOINC sections exist and their char counts

READ-ONLY: no corpus write, no product code touched. Network reads only.
"""
import asyncio
import io
import json
import sys
import time
import xml.etree.ElementTree as ET
from collections import OrderedDict

import httpx

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

V2 = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
NS = "{urn:hl7-org:v3}"

# Builder tiers, verbatim from scripts/build_dailymed_label_corpus.py:73
TIERS = [("C73594", "NDA"), ("C73607", "NDA_AG"), ("C73584", "ANDA"), (None, "other")]

# LOINC sections of interest. 43685-7 is what the corpus whitelists; 34071-1 is the
# older/OTC-style "WARNINGS" section the baton named — probing BOTH deliberately.
SECTIONS = OrderedDict([
    ("34070-3", "contraindications"),
    ("43685-7", "warnings_precautions"),
    ("34071-1", "warnings_OTC_style"),
    ("34073-7", "drug_interactions"),
    ("34066-1", "boxed_warning"),
    ("34067-9", "indications(control)"),
    ("34068-7", "dosage(control)"),
])
SAFETY = {"34070-3", "43685-7", "34071-1", "34073-7", "34066-1"}

# SPL document-type LOINC codes
DOCTYPE = {
    "34391-3": "HUMAN PRESCRIPTION DRUG LABEL",
    "34390-5": "HUMAN OTC DRUG LABEL",
}

MOIETIES = ["NAPROXEN", "OMEPRAZOLE", "IBUPROFEN", "CIMETIDINE", "TERBINAFINE", "FAMOTIDINE"]
PER_TIER = 4          # bounded: candidates fetched per tier
TIMEOUT = 40.0


async def candidates(http, drug, code):
    p = {"drug_name": drug, "pagesize": "50"}
    if code:
        p["marketing_category_code"] = code
    try:
        r = await http.get(f"{V2}/spls.json", params=p)
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return [(x["setid"], x.get("title", ""), int(x.get("spl_version") or 0))
                for x in r.json().get("data", []) if x.get("setid")]
    except Exception as e:
        return [("__ERROR__", f"{type(e).__name__}: {e}", 0)]


async def spl(http, setid):
    try:
        r = await http.get(f"{V2}/spls/{setid}.xml")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.content
    except Exception:
        return None


def analyse(xml):
    """Return (doctype_code, doctype_name, marketing_categories, {loinc: chars}, n_active)."""
    root = ET.fromstring(xml)
    dt = root.find(f"{NS}code")
    dtc = dt.get("code") if dt is not None else None

    mktg = set()
    for c in root.iter(f"{NS}approval"):
        cc = c.find(f"{NS}code")
        if cc is not None and cc.get("displayName"):
            mktg.add(cc.get("displayName"))

    active = set()
    for am in root.iter(f"{NS}activeMoiety"):
        n = am.find(f"{NS}name")
        if n is not None and (n.text or "").strip():
            active.add(n.text.strip().upper())

    secs = {}
    for sec in root.iter(f"{NS}section"):
        c = sec.find(f"{NS}code")
        if c is None:
            continue
        loinc = c.get("code")
        if loinc in SECTIONS:
            txt = "".join(sec.itertext())
            txt = " ".join(txt.split())
            if txt:
                secs[loinc] = max(secs.get(loinc, 0), len(txt))
    return dtc, DOCTYPE.get(dtc, dtc or "?"), sorted(mktg), secs, len(active)


async def main():
    out = {"probed_at": time.strftime("%Y-%m-%d %H:%M:%S"), "api": V2, "moieties": {}}
    async with httpx.AsyncClient(timeout=TIMEOUT, headers={"User-Agent": "vela-c2-probe"}) as http:
        for m in MOIETIES:
            print("=" * 100, flush=True)
            print(f"MOIETY: {m}", flush=True)
            print("=" * 100, flush=True)
            rows = []
            for code, tier in TIERS:
                cands = await candidates(http, m, code)
                if cands and cands[0][0] == "__ERROR__":
                    print(f"  [{tier}] QUERY ERROR: {cands[0][1]}", flush=True)
                    rows.append({"tier": tier, "error": cands[0][1]})
                    continue
                print(f"  [{tier}] {len(cands)} candidates"
                      + ("" if cands else "  (none)"), flush=True)
                for setid, title, ver in cands[:PER_TIER]:
                    xml = await spl(http, setid)
                    if xml is None:
                        print(f"      {setid[:8]}… SPL FETCH FAILED — {title[:60]}", flush=True)
                        rows.append({"tier": tier, "setid": setid, "title": title,
                                     "error": "spl_fetch_failed"})
                        continue
                    try:
                        dtc, dtn, mktg, secs, nact = analyse(xml)
                    except Exception as e:
                        print(f"      {setid[:8]}… PARSE FAILED {type(e).__name__}", flush=True)
                        rows.append({"tier": tier, "setid": setid, "title": title,
                                     "error": f"parse_failed: {type(e).__name__}"})
                        continue
                    saf = {k: v for k, v in secs.items() if k in SAFETY}
                    rows.append({"tier": tier, "setid": setid, "title": title, "spl_version": ver,
                                 "doctype_code": dtc, "doctype": dtn, "mktg_in_spl": mktg,
                                 "n_active_moieties": nact, "sections": secs,
                                 "safety_sections": saf})
                    flag = "🟢Rx" if dtc == "34391-3" else ("🟠OTC" if dtc == "34390-5" else "?")
                    print(f"      {flag} v{ver} {setid[:8]}… | {title[:58]}", flush=True)
                    print(f"           mktg_in_spl={mktg} active={nact} "
                          f"safety={ {SECTIONS[k]: v for k, v in saf.items()} }", flush=True)
                await asyncio.sleep(0.25)
            out["moieties"][m] = rows
            print(flush=True)
    p = "tests/results/c2_dailymed_probe.json"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"-> {p}", flush=True)


asyncio.run(main())
