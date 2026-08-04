# -*- coding: utf-8 -*-
"""c2 Phase-1b Part 3a — build the E-A TREATMENT index into a SCRATCH path.

⚠️ The shipped index (data/dailymed/label_docs.json + label_emb.npy) is NEVER written.

Construction, deliberately minimal so the arms differ by EXACTLY ONE THING:
    TREATMENT docs = shipped docs (byte-identical, embeddings reused verbatim)
                   + the NEW 34071-1 docs only (embedded here)
No re-selection, no --resolve, no re-embedding of existing rows. Any drift in the
re-parsed non-34071-1 docs is reported by Part 2 but deliberately EXCLUDED from the arm,
so it cannot contaminate the comparison.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(r"C:\Users\andre\projects\Vela")
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv                    # noqa: E402
load_dotenv(ROOT / ".env", override=True)

FETCH = ROOT / "tests/results/c2_ea_fetch.json"
SHIP_DOCS = ROOT / "data/dailymed/label_docs.json"
SHIP_EMB = ROOT / "data/dailymed/label_emb.npy"
OUT_DIR = ROOT / "tests/results/c2_ea_index"      # SCRATCH — gitignored
OUT_DOCS = OUT_DIR / "label_docs.json"
OUT_EMB = OUT_DIR / "label_emb.npy"
L = "34071-1"
BATCH = 256

OUT_DIR.mkdir(parents=True, exist_ok=True)

ship = json.loads(SHIP_DOCS.read_text(encoding="utf-8"))
ship_docs = ship["documents"]
ship_emb = np.load(SHIP_EMB)
assert len(ship_docs) == ship_emb.shape[0], "shipped docs/emb row mismatch — ABORT"
print(f"shipped: {len(ship_docs)} docs, emb {ship_emb.shape} {ship_emb.dtype}")

fetch = json.loads(FETCH.read_text(encoding="utf-8"))
new_docs = [d for lab in fetch["labels"] for d in lab["docs"] if d["loinc"] == L]
# guard: none of these may already exist in the shipped corpus
existing = {d["source_id"] for d in ship_docs}
dupes = [d for d in new_docs if d["source_id"] in existing]
assert not dupes, f"ABORT: {len(dupes)} new source_ids already in the shipped corpus"
print(f"NEW {L} docs to embed: {len(new_docs)}  "
      f"({sum(len(d['content']) for d in new_docs):,} chars)")

# Reuse the BUILDER'S OWN embedding function so the new rows are produced exactly as the
# shipped ones were (same model constant, same batching, same 429 backoff) — parity matters
# because these vectors are concatenated onto the shipped matrix.
import importlib.util                                       # noqa: E402
_spec = importlib.util.spec_from_file_location("bdm", ROOT / "scripts/build_dailymed_label_corpus.py")
bdm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bdm)
print(f"embedder: {bdm.EMBEDDING_MODEL} (builder constant)")

t0 = time.time()
vecs = bdm.embed_documents(new_docs, batch_size=100)
print(f"  embedded {len(vecs)} rows in {time.time()-t0:.0f}s")

new_emb = np.asarray(vecs, dtype=np.float16)
assert new_emb.shape[0] == len(new_docs), "embed row mismatch — ABORT"
assert new_emb.shape[1] == ship_emb.shape[1], (
    f"dim mismatch: new {new_emb.shape[1]} vs shipped {ship_emb.shape[1]} — ABORT")

all_docs = ship_docs + new_docs
all_emb = np.concatenate([ship_emb.astype(np.float16), new_emb], axis=0)
assert len(all_docs) == all_emb.shape[0]

meta = dict(ship.get("_meta", {}))
meta["c2_EA_SCRATCH"] = {
    "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "basis": "shipped docs verbatim + 34071-1 docs only; NO re-selection, NO --resolve",
    "added_docs": len(new_docs),
    "added_chars": sum(len(d["content"]) for d in new_docs),
}
OUT_DOCS.write_text(json.dumps({"_meta": meta, "documents": all_docs}, ensure_ascii=False),
                    encoding="utf-8")
np.save(OUT_EMB, all_emb)
print(f"\nTREATMENT index: {len(all_docs)} docs, emb {all_emb.shape}")
print(f"-> {OUT_DOCS}\n-> {OUT_EMB}")
print(f"embedding tokens (approx chars/4): {sum(len(d['content']) for d in new_docs)//4:,}")
