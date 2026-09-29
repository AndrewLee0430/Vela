"""Shared setup for the bp_calcium probe — production-parity retriever, no api/ change.

* Config is resolved by the canary gate's `load_production_config()` (parses the
  `retriever = HybridRetriever(...)` construction in api/server.py and cross-checks the
  constructor defaults; LOUD STOP on any mismatch) — never a bare HybridRetriever().
* load_dotenv() BEFORE any api import (instrument-blind #14), then SENTRY_DSN is blanked
  so a local probe cannot report to the real Sentry project.
* DATABASE_URL is asserted to point at the Dev Neon branch before anything runs.
"""
import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
# The TFDA / DailyMed stores open their indexes by RELATIVE path (data/...). Run from
# anywhere else and they load EMPTY with only a printed warning — the first step-2 run
# did exactly that (harmless there: the rewrite arm never searches a store).
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests" / "probes" / "canary"))
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env", override=True)

import canary_gate  # noqa: E402  (its own load_dotenv runs at import; SENTRY blanked AFTER)

os.environ["SENTRY_DSN"] = ""
os.environ["TEST_MODE"] = "true"

DEV_BRANCH_HOST = "ep-spring-voice-a127ye10"
QUERY = "Can elderly patients take BP meds with calcium?"


def assert_dev_db():
    url = os.environ.get("DATABASE_URL", "")
    if DEV_BRANCH_HOST not in url:
        raise SystemExit("STOP: DATABASE_URL does not point at the Dev branch")
    return DEV_BRANCH_HOST


def production_retriever():
    cfg = canary_gate.load_production_config()
    os.environ["SOURCE_WEIGHT_ACTIVE"] = "true" if cfg["source_weight_active"] else ""
    from api.rag.retriever import HybridRetriever
    r = HybridRetriever(
        local_threshold=cfg["local_threshold"],
        enable_local=cfg["enable_local"],
        enable_pubmed=cfg["enable_pubmed"],
        enable_fda=cfg["enable_fda"],
        enable_tfda=cfg["enable_tfda"],
        enable_dailymed=cfg["enable_dailymed"],
    )
    return r, cfg
