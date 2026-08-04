# -*- coding: utf-8 -*-
"""c2 Phase-1b — ONE network pass over the 1038 PINNED reference setids.

Serves Parts 2, 3 and 4 from a single fetch:
  - SPL document-type code (34391-3 Rx / 34390-5 OTC)  -> Part 2 Rx/OTC split
  - ALL section docs built by the BUILDER'S OWN `_section_docs_from_spl`, with the module
    constant SECTIONS monkeypatched to ADD 34071-1 -> faithful E-A documents (Part 3) and
    the text corpus for content stratification (Part 4)

⚠️ NO --resolve. NO selection change. Pinned setids only, read from the SHIPPED
data/dailymed/label_docs.json. The shipped corpus is NEVER written.
"""
import asyncio
import importlib.util
import io
import json
import sys
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

# ⚠️ Do NOT wrap sys.stdout here: the builder module wraps it again at import
# (build_dailymed_label_corpus.py:54), and the discarded wrapper closes the shared buffer
# -> "ValueError: I/O operation on closed file" before any work runs. Rely on
# PYTHONIOENCODING=utf-8 from the caller instead.
ROOT = Path(r"C:\Users\andre\projects\Vela")
sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location("bdm", ROOT / "scripts/build_dailymed_label_corpus.py")
bdm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bdm)   # this re-wraps sys.stdout with a utf-8 writer

from api.data_sources.dailymed import DailyMedClient  # noqa: E402

NS = "{urn:hl7-org:v3}"
LOINC_34071 = "34071-1"
DOCTYPE = {"34391-3": "Rx", "34390-5": "OTC"}

# ── THE E-A CHANGE, applied ONLY to this in-memory module copy ──────────────────
# Builder default (scripts/build_dailymed_label_corpus.py:77-84) + 34071-1.
bdm.SECTIONS = list(bdm.SECTIONS) + [("warnings_pre_plr", LOINC_34071, "Warnings")]
print("patched SECTIONS ->", [s[1] for s in bdm.SECTIONS], flush=True)

SHIPPED = ROOT / "data/dailymed/label_docs.json"
OUT = ROOT / "tests/results/c2_ea_fetch.json"
CONCURRENCY = 8


async def one(sem, dm, ref, out, fails):
    setid, moiety, mktg, ver = ref
    async with sem:
        xml = await dm._fetch_spl_xml(setid)
        if xml is None:
            fails.append({"setid": setid, "moiety": moiety, "error": "spl_fetch_failed"})
            return
        try:
            root = ET.fromstring(xml)
            dt = root.find(f"{NS}code")
            dtc = dt.get("code") if dt is not None else None
            docs = bdm._section_docs_from_spl(dm, xml, moiety, mktg, setid, ver)
        except Exception as e:
            fails.append({"setid": setid, "moiety": moiety,
                          "error": f"parse_failed: {type(e).__name__}: {e}"})
            return
        out.append({"setid": setid, "moiety": moiety, "marketing_category": mktg,
                    "spl_version": ver, "doctype_code": dtc,
                    "doctype": DOCTYPE.get(dtc, dtc or "?"),
                    "docs": docs})


async def main():
    shipped = json.loads(SHIPPED.read_text(encoding="utf-8"))["documents"]
    refs = {}
    for d in shipped:
        refs.setdefault(d["setid"], (d["setid"], d.get("moiety"),
                                     d.get("marketing_category"), d.get("spl_version")))
    refs = list(refs.values())
    print(f"pinned reference setids: {len(refs)}", flush=True)

    dm = DailyMedClient()
    sem = asyncio.Semaphore(CONCURRENCY)
    out, fails = [], []
    t0 = time.time()
    tasks = [one(sem, dm, r, out, fails) for r in refs]
    done = 0
    for chunk_start in range(0, len(tasks), 50):
        await asyncio.gather(*tasks[chunk_start:chunk_start + 50])
        done = min(chunk_start + 50, len(tasks))
        print(f"  {done}/{len(refs)}  ok={len(out)} fail={len(fails)}  "
              f"{time.time()-t0:.0f}s", flush=True)

    payload = {"fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
               "pinned_setids": len(refs), "ok": len(out), "failed": len(fails),
               "failures": fails,
               "sections_patched": [s[1] for s in bdm.SECTIONS],
               "labels": out}
    OUT.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"\nok={len(out)} failed={len(fails)}  elapsed={time.time()-t0:.0f}s", flush=True)
    if fails:
        print("FAILURES (first 10):", json.dumps(fails[:10], ensure_ascii=False), flush=True)
    print(f"-> {OUT}", flush=True)


asyncio.run(main())
