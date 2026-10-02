"""Build the DailyMed ROUTE sidecar — route-mismatch car, Segment 1 (KEY only; NO behaviour change).

For every distinct setid in data/dailymed/label_docs.json, fetch the SPL from the SAME endpoint the corpus builder uses
(`api.data_sources.dailymed.DailyMedClient._fetch_spl_xml` → `{BASE_URL}/spls/{setid}.xml`, BASE_URL =
https://dailymed.nlm.nih.gov/dailymed/services/v2) and extract, per manufactured product:
  - the product dosage form: the `formCode` that is a DIRECT child of `manufacturedProduct/manufacturedProduct`
    (packaging formCodes — CARTON, SYRINGE, VIAL … under asContent/containerPackagedProduct — are NOT read: the
    2026-08-04 E-B classifier counted container tokens as dosage forms; see TECH_DEBT instrument-blind row 10)
  - kit part forms: `…/manufacturedProduct/part/partProduct/formCode`
  - the route(s): `manufacturedProduct/consumedIn/substanceAdministration/routeCode`, and for KITS the parts' own
    `manufacturedProduct/manufacturedProduct/part/consumedIn/substanceAdministration/routeCode`
plus the SPL `versionNumber` and the document type (`document/code/@displayName`).

Writes data/dailymed/label_routes.json keyed by setid:
  {routes:[...], forms:[...], spl_version, corpus_spl_version, corpus_spl_version_match, document_type, products:[...]}
DOES NOT touch label_docs.json, label_emb.npy or api/. FAIL LOUD (Rule 18): every setid that failed to fetch / parse, or whose
SPL carries no routeCode, is listed in `_meta.failures` / `_meta.no_route` — a route is NEVER defaulted.

Fetch etiquette: CONCURRENCY workers (default 4), a per-request pause, retries with backoff on 429 / 5xx / network errors.
Resumable: each setid's parsed result is appended to tests/results/route_sidecar_cache.jsonl (gitignored); a re-run skips setids
already cached OK and retries failures. The raw XML is not cached (size).

Usage:
    python scripts/build_dailymed_route_sidecar.py                # fetch (resumable) + write the sidecar
    python scripts/build_dailymed_route_sidecar.py --limit 20     # smoke
    python scripts/build_dailymed_route_sidecar.py --from-cache   # write the sidecar from the cache only (no network)
"""
import argparse
import asyncio
import json
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "data/dailymed/label_docs.json"
OUT = ROOT / "data/dailymed/label_routes.json"
CACHE = ROOT / "tests/results/route_sidecar_cache.jsonl"
BASE_URL = "https://dailymed.nlm.nih.gov/dailymed/services/v2"   # = api/data_sources/dailymed.py DailyMedClient.BASE_URL
NS = "{urn:hl7-org:v3}"
CONCURRENCY = 4
PAUSE_S = 0.25
RETRIES = 4


def code_obj(el):
    return None if el is None else {"code": el.get("code"), "display": el.get("displayName"), "system": el.get("codeSystem")}


def parse_spl(xml: bytes) -> dict:
    root = ET.fromstring(xml)
    ver = root.find(f"{NS}versionNumber")
    dcode = root.find(f"{NS}code")
    products = []
    for outer in root.iter(f"{NS}manufacturedProduct"):
        inner = outer.find(f"{NS}manufacturedProduct")
        if inner is None:            # pre-2009 SPL schema names the inner product manufacturedMedicine
            inner = outer.find(f"{NS}manufacturedMedicine")
        if inner is None:            # `outer` is itself an inner product, or a non-product wrapper
            continue
        name = inner.find(f"{NS}name")
        form = code_obj(inner.find(f"{NS}formCode"))
        parts = [code_obj(p.find(f"{NS}formCode")) for p in inner.findall(f"{NS}part/{NS}partProduct")]
        routes = [code_obj(r) for r in outer.findall(f"{NS}consumedIn/{NS}substanceAdministration/{NS}routeCode")]
        # kits: each part carries its own route at …/manufacturedProduct/manufacturedProduct/part/consumedIn/…/routeCode
        routes += [code_obj(r) for r in inner.findall(f"{NS}part/{NS}consumedIn/{NS}substanceAdministration/{NS}routeCode")]
        products.append({"name": (name.text or "").strip() if name is not None else None, "form": form,
                         "part_forms": [p for p in parts if p], "routes": [r for r in routes if r]})
    routes = sorted({r["display"] for p in products for r in p["routes"] if r.get("display")})
    forms = sorted({p["form"]["display"] for p in products if p["form"] and p["form"].get("display")})
    part_forms = sorted({f["display"] for p in products for f in p["part_forms"] if f.get("display")})
    return {"spl_version": int(ver.get("value")) if ver is not None and (ver.get("value") or "").isdigit() else None,
            "document_type": dcode.get("displayName") if dcode is not None else None,
            "routes": routes, "forms": forms, "part_forms": part_forms, "products": products}


async def fetch_one(client, sem, setid):
    url = f"{BASE_URL}/spls/{setid}.xml"
    last = None
    for attempt in range(RETRIES + 1):
        async with sem:
            await asyncio.sleep(PAUSE_S)
            try:
                r = await client.get(url)
            except Exception as e:                      # network / timeout
                last = f"{type(e).__name__}: {e}"[:200]
                r = None
        if r is not None:
            if r.status_code == 200:
                try:
                    return {"setid": setid, "ok": True, **parse_spl(r.content)}
                except Exception as e:
                    return {"setid": setid, "ok": False, "reason": f"parse: {type(e).__name__}: {e}"[:200]}
            if r.status_code == 404:
                return {"setid": setid, "ok": False, "reason": "HTTP 404"}
            last = f"HTTP {r.status_code}"
            if r.status_code not in (429, 500, 502, 503, 504):
                return {"setid": setid, "ok": False, "reason": last}
        await asyncio.sleep(min(30, 2 ** attempt * 2))
    return {"setid": setid, "ok": False, "reason": f"retries exhausted ({last})"}


def load_cache():
    done = {}
    if CACHE.exists():
        for ln in CACHE.read_text(encoding="utf-8").splitlines():
            if ln.strip():
                rec = json.loads(ln)
                done[rec["setid"]] = rec               # last record wins
    return done


async def fetch_all(setids):
    cache = load_cache()
    todo = [s for s in setids if not (s in cache and cache[s].get("ok"))]
    print(f"setids {len(setids)} · cached OK {len(setids) - len(todo)} · to fetch {len(todo)}", flush=True)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(CONCURRENCY)
    t0 = time.time()
    async with httpx.AsyncClient(timeout=60.0, headers={"User-Agent": "vela-route-sidecar/1 (offline corpus key build)"}) as client:
        with open(CACHE, "a", encoding="utf-8") as fh:
            for i, coro in enumerate(asyncio.as_completed([fetch_one(client, sem, s) for s in todo]), 1):
                rec = await coro
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
                if i % 50 == 0 or i == len(todo):
                    print(f"  {i}/{len(todo)} fetched · {time.time() - t0:.0f}s", flush=True)
    return load_cache()


def corpus_setids():
    docs = json.load(open(DOCS, encoding="utf-8"))["documents"]
    ver = {}
    for d in docs:
        ver.setdefault(d["setid"], d.get("spl_version"))
    return ver


def write_sidecar(corpus_ver, cache):
    out, failures, no_route = {}, [], []
    for sid in sorted(corpus_ver):
        rec = cache.get(sid)
        if rec is None or not rec.get("ok"):
            failures.append({"setid": sid, "reason": (rec or {}).get("reason", "not fetched")})
            continue
        cv = corpus_ver[sid]
        try:
            cv_int = int(cv) if cv is not None else None
        except (TypeError, ValueError):
            cv_int = None
        out[sid] = {"routes": rec["routes"], "forms": rec["forms"], "part_forms": rec["part_forms"],
                    "spl_version": rec["spl_version"], "corpus_spl_version": cv_int,
                    "corpus_spl_version_match": (rec["spl_version"] == cv_int) if cv_int is not None else None,
                    "document_type": rec["document_type"], "products": rec["products"]}
        if not rec["routes"]:
            no_route.append(sid)
    meta = {"source": f"{BASE_URL}/spls/{{setid}}.xml (same endpoint as scripts/build_dailymed_label_corpus.py via DailyMedClient._fetch_spl_xml)",
            "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "corpus_setids": len(corpus_ver), "fetched_ok": len(out), "with_route": len(out) - len(no_route),
            "failures": failures, "no_route": no_route,
            "spl_version_mismatch": sum(1 for v in out.values() if v["corpus_spl_version_match"] is False),
            "extraction": "product form = formCode directly under manufacturedProduct/manufacturedProduct (packaging formCodes NOT read); "
                          "kit parts = part/partProduct/formCode; route = manufacturedProduct/consumedIn/substanceAdministration/routeCode; "
                          "no route is ever defaulted",
            "note": "the CURRENT SPL is fetched; where spl_version != corpus_spl_version the route key describes a newer revision of the same setid"}
    OUT.write_text(json.dumps({"_meta": meta, "labels": out}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in meta.items() if k not in ("source", "extraction", "note")}, indent=1))
    if failures or no_route:
        print(f"FAIL LOUD: {len(failures)} setid(s) failed, {len(no_route)} carry no routeCode — listed in _meta", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--from-cache", action="store_true")
    a = ap.parse_args()
    corpus_ver = corpus_setids()
    setids = sorted(corpus_ver)[: a.limit] if a.limit else sorted(corpus_ver)
    cache = load_cache() if a.from_cache else asyncio.run(fetch_all(setids))
    if a.limit:
        corpus_ver = {s: corpus_ver[s] for s in setids}
    write_sidecar(corpus_ver, cache)


if __name__ == "__main__":
    main()
