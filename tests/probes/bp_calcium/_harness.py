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


def l0_generation_override(gen):
    """The model the ANONYMOUS (L0) Research path generates with, READ from api/server.py — never hard-coded.

    Parses research_query's `if is_anonymous:` branch for its `model_override` assignment and maps it onto this
    process's AnswerGenerator. Segment 1d (2026-10-01) changed that line from `generator._fallback_model`
    (gpt-4.1-mini) to `None` (the L1 generator binding); a harness that hard-coded the old value would keep
    measuring a path production no longer runs (the instrument-blind shape). Unknown RHS → LOUD STOP.
    Returns (model_override_value, provenance_string).
    """
    import re as _re
    src = (ROOT / "api" / "server.py").read_text(encoding="utf-8")
    fn = src.index("async def research_query(")
    br = src.index("if is_anonymous:", fn)
    end = src.index("\n    else:", br)
    # CODE lines only: the Segment-1d comment above the assignment quotes the OLD line ("Was: `model_override =
    # generator._fallback_model`"), and a whole-block regex read that comment instead of the code (caught 2026-10-01).
    hits = [m.group(1) for ln in src[br:end].splitlines() if not ln.strip().startswith("#")
            for m in [_re.match(r"\s*model_override(?::\s*Optional\[str\])?\s*=\s*([A-Za-z_.]+)\s*$", ln)] if m]
    if len(hits) != 1:
        raise SystemExit(f"STOP: expected exactly one anon model_override code line in api/server.py, got {hits}")
    rhs = hits[0]
    table = {"None": None, "generator._fallback_model": gen._fallback_model, "generator.model": gen.model}
    if rhs not in table:
        raise SystemExit(f"STOP: unknown anon model_override RHS {rhs!r} in api/server.py")
    return table[rhs], f"api/server.py research_query is_anonymous: model_override = {rhs}"


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
