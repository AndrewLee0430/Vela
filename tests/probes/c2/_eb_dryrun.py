# -*- coding: utf-8 -*-
"""E-B blast-radius DRY RUN. Resolve, capture, DISCARD. Writes NOTHING to data/. No embedding.

RULE A (shipped)  : TIERS in order; first tier with any candidate wins; within it
                    max(_pick_reference). == the pinned setids already in the corpus.
RULE B (proposed) : same tier order, same scorer, but consider ONLY candidates whose SPL
                    doctype is 34391-3 (Rx). If a tier has no Rx candidate, continue. If no
                    tier has one, fall back to rule A's pick.

⚠️ SEARCH-SPACE BOUND — stated because it is load-bearing:
   Under THIS rule-B definition, if rule A's winner is already Rx then it is also the
   top-scored Rx candidate in that same tier, so rule B picks THE SAME label. Therefore only
   the 128 moieties whose CURRENT pick is non-Rx can change. A different rule-B definition
   (e.g. ignoring tier order) would give a different number.
"""
import asyncio, importlib.util, io, json, sys, time
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(r"C:\Users\andre\projects\Vela")
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("bdm", ROOT / "scripts/build_dailymed_label_corpus.py")
bdm = importlib.util.module_from_spec(spec); spec.loader.exec_module(bdm)   # wraps stdout utf-8
from api.data_sources.dailymed import DailyMedClient        # noqa: E402

NS = "{urn:hl7-org:v3}"
RX, OTC = "34391-3", "34390-5"
WHITELIST = {"34073-7", "34070-3", "43685-7", "34066-1"}
FETCH = ROOT / "tests/results/c2_ea_fetch.json"
OUT = ROOT / "tests/results/eb_dryrun.json"
PER_TIER = 6
CONC = 6

STATS = {"spls_json": 0, "spl_xml": 0}


def analyse(xml):
    root = ET.fromstring(xml)
    dt = root.find(f"{NS}code")
    dtc = dt.get("code") if dt is not None else None
    forms = set()
    for fc in root.iter(f"{NS}formCode"):
        dn = fc.get("displayName")
        if dn:
            forms.add(dn.strip().upper())
    act = set()
    for am in root.iter(f"{NS}activeMoiety"):
        n = am.find(f"{NS}name")
        if n is not None and (n.text or "").strip():
            act.add(n.text.strip().upper())
    secs = set()
    for s in root.iter(f"{NS}section"):
        c = s.find(f"{NS}code")
        if c is not None and c.get("code"):
            secs.add(c.get("code"))
    title = root.find(f"{NS}title")
    return dtc, sorted(forms), len(act), secs, ("".join(title.itertext()).strip()[:90] if title is not None else "")


async def cands(http, q, code):
    p = {"drug_name": q, "pagesize": "50"}
    if code:
        p["marketing_category_code"] = code
    try:
        STATS["spls_json"] += 1
        r = await http.get(f"{bdm.V2}/spls.json", params=p)
        if r.status_code == 404:
            return []
        r.raise_for_status()
        return [(x["setid"], x.get("title", ""), int(x.get("spl_version") or 0))
                for x in r.json().get("data", []) if x.get("setid")]
    except Exception:
        return []


async def one(sem, http, dm, rec, out, fails):
    moiety, cur_setid, cur_doctype = rec
    async with sem:
        # current pick's dosage form (for the route/form comparison)
        cur = {"setid": cur_setid, "doctype": cur_doctype}
        STATS["spl_xml"] += 1
        x = await dm._fetch_spl_xml(cur_setid)
        if x is not None:
            try:
                _d, f, a, s, t = analyse(x)
                cur.update({"forms": f, "n_active": a, "safety": sorted(s & WHITELIST), "title": t})
            except Exception:
                pass
        winner, examined = None, 0
        for code, tier in bdm.TIERS:
            cs = await cands(http, moiety, code)
            if not cs:
                continue
            ranked = sorted(cs, key=lambda c: (1 if (moiety.split()[0].lower() if moiety.split() else moiety.lower()) in c[1].lower() else 0,
                                               -c[1].lower().count(" and "), c[2]), reverse=True)
            for setid, title, ver in ranked[:PER_TIER]:
                examined += 1
                STATS["spl_xml"] += 1
                xml = await dm._fetch_spl_xml(setid)
                if xml is None:
                    continue
                try:
                    dtc, forms, nact, secs, t = analyse(xml)
                except Exception:
                    continue
                if dtc == RX:
                    winner = {"setid": setid, "title": title[:90], "spl_version": ver,
                              "tier": tier, "doctype": "Rx", "forms": forms,
                              "n_active": nact, "safety": sorted(secs & WHITELIST)}
                    break
            if winner:
                break
        out.append({"moiety": moiety, "current": cur, "ruleB": winner,
                    "changed": bool(winner and winner["setid"] != cur_setid),
                    "candidates_examined": examined})


async def main():
    f = json.loads(FETCH.read_text(encoding="utf-8"))
    targets = [(l["moiety"], l["setid"], l["doctype"]) for l in f["labels"] if l["doctype_code"] != RX]
    print(f"DRY RUN — rule B over {len(targets)} non-Rx-pick moieties "
          f"(the only ones that can change; see header)", flush=True)
    dm = DailyMedClient()
    import httpx
    out, fails = [], []
    t0 = time.time()
    async with httpx.AsyncClient(timeout=40.0, headers={"User-Agent": "vela-eb-dryrun"}) as http:
        sem = asyncio.Semaphore(CONC)
        tasks = [one(sem, http, dm, r, out, fails) for r in targets]
        for i in range(0, len(tasks), 20):
            await asyncio.gather(*tasks[i:i + 20])
            print(f"  {min(i+20,len(tasks))}/{len(targets)}  "
                  f"json={STATS['spls_json']} xml={STATS['spl_xml']}  {time.time()-t0:.0f}s", flush=True)
    payload = {"ran_at": time.strftime("%Y-%m-%d %H:%M:%S"), "targets": len(targets),
               "requests": dict(STATS), "elapsed_s": round(time.time() - t0),
               "rule_b_definition": "tier order + _pick_reference, Rx-doctype only, fallback to rule A",
               "results": out}
    OUT.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    ch = [r for r in out if r["changed"]]
    print(f"\nmoieties examined {len(out)} | WOULD CHANGE {len(ch)} | no Rx found {sum(1 for r in out if not r['ruleB'])}")
    print(f"requests: {STATS}  elapsed {time.time()-t0:.0f}s")
    print(f"-> {OUT}")


asyncio.run(main())
