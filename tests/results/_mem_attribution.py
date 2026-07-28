# -*- coding: utf-8 -*-
"""Memory attribution for the §2.7 gate transport blocker (READ-ONLY diagnosis).

Loads each corpus store ONE AT A TIME and samples process RSS between loads, so the
resident cost is attributed per corpus rather than inferred from disk sizes.
Also reports numpy array nbytes, which is the honest floor for the embedding matrices.

READ-ONLY: imports product code, mutates nothing.
"""
import io, os, sys, gc, json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
ROOT = Path(r"C:\Users\andre\projects\Vela")
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TEST_MODE", "true")
from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

import psutil  # noqa: E402
P = psutil.Process()


def rss_mb():
    gc.collect()
    return P.memory_info().rss / 1048576


def arr_mb(store):
    e = getattr(store, "embeddings", None)
    if e is None:
        return None, None
    return e.nbytes / 1048576, f"{e.shape} {e.dtype}"


rows = []
base = rss_mb()
print(f"{'stage':44} {'RSS MB':>9} {'delta':>9} {'emb nbytes':>11}  shape/dtype")
print("-" * 100)
print(f"{'baseline (interpreter + deps)':44} {base:9.1f} {'—':>9} {'—':>11}")

from api.database import vector_store as vs  # noqa: E402
after_import = rss_mb()
print(f"{'import api.database.vector_store':44} {after_import:9.1f} {after_import-base:9.1f} {'—':>11}")
rows.append(("import vector_store module", after_import - base, None, None))

prev = after_import
for label, getter in (("VectorStore (local drug index.json)", vs.get_vector_store),
                      ("TFDACorpusStore (indication corpus)", vs.get_tfda_store),
                      ("DailyMedCorpusStore (label corpus)", vs.get_dailymed_store)):
    store = getter()
    now = rss_mb()
    nb, shape = arr_mb(store)
    ndocs = len(getattr(store, "documents", []) or [])
    print(f"{label:44} {now:9.1f} {now-prev:9.1f} {(f'{nb:.1f}' if nb else '—'):>11}  {shape or ''}  docs={ndocs}")
    rows.append((label, now - prev, nb, f"{shape} docs={ndocs}"))
    prev = now

total = rss_mb()
print("-" * 100)
print(f"{'TOTAL RSS with all three corpora resident':44} {total:9.1f} {total-base:9.1f}")

os_free = psutil.virtual_memory()
print()
print(f"machine: total {os_free.total/1048576:,.0f} MB · available {os_free.available/1048576:,.0f} MB "
      f"· percent used {os_free.percent}%")
print()
print("NOTE: .npy embeddings are float16 ON DISK and expanded to float32 in RAM at "
      "vector_store.py:175 and :230 (`.astype(np.float32)`) → 2x the disk size resident.")

out = ROOT / "tests" / "results" / "mem_attribution.json"
out.write_text(json.dumps({
    "baseline_mb": round(base, 1), "total_mb": round(total, 1),
    "machine_total_mb": round(os_free.total / 1048576),
    "machine_available_mb": round(os_free.available / 1048576),
    "rows": [{"stage": r[0], "delta_mb": round(r[1], 1),
              "emb_nbytes_mb": round(r[2], 1) if r[2] else None, "detail": r[3]} for r in rows],
}, indent=1), encoding="utf-8")
print(f"-> {out}")
