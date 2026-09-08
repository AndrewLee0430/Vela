# -*- coding: utf-8 -*-
"""httpx request-line logging is suppressed below WARNING (HISTORY HONESTY car
segment 4a, item (d)).

THE BUSINESS RULE (CLAUDE.md Rule 17 — what breaks if this fails):
httpx logs every outbound request at INFO as `HTTP Request: GET <full URL>`,
and two clients pass credentials as QUERY PARAMS (openFDA `api_key`, NCBI
`api_key` + `email`). Behind `logging.basicConfig(level=logging.INFO)` those
lines — key included — landed in the dev console and the Fly log on every
Research request (measured 2026-09-04: 18 keyed lines per probe run; seen in
plain text in a pasted local log 2026-09-08 → key rotated by the founder).
If the `httpx` logger falls back to the root level again, the rotated key
starts leaking on the next request.

Rule 19 controls: Vela's own INFO lines (`[Verify]` / `[Research]` on the
`vela` logger) must still pass, and httpx WARNING+ must still surface — the
fix narrows ONE library logger, it does not silence anything else.

The request line is produced by the REAL httpx client through an in-process
MockTransport (no network), so the test observes the library's own log call,
not a hand-written stand-in.
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Env BEFORE importing api.server (same pattern as test_research_history_payload).
os.environ["TEST_MODE"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import httpx  # noqa: E402

import api.server  # noqa: E402,F401  — runs basicConfig + the logger configuration under test

SECRET = "ROTATED-KEY-MUST-NOT-APPEAR"
URL = f"https://api.fda.gov/drug/label.json?search=aspirin&api_key={SECRET}"


def _request_through_httpx() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json={"ok": True}))
    with httpx.Client(transport=transport) as client:
        client.get(URL)


def test_httpx_request_line_with_api_key_is_not_logged(caplog):
    """The library's INFO `HTTP Request:` line — which carries the full URL and
    therefore the query-param api_key — must not reach any handler."""
    caplog.set_level(logging.INFO)  # root at INFO, exactly as basicConfig leaves it
    _request_through_httpx()
    httpx_records = [r for r in caplog.records if r.name == "httpx"]
    assert httpx_records == [], (
        "httpx INFO request line reached the log handlers: "
        + " | ".join(r.getMessage() for r in httpx_records)
    )
    assert SECRET not in caplog.text, "the query-param api_key leaked into the log"


def test_vela_info_line_still_passes_control(caplog):
    """CONTROL (Rule 17 / Rule 19): the `[Verify]` / `[Research]` INFO lines on
    the `vela` logger — the prod-verification hooks — are untouched."""
    caplog.set_level(logging.INFO)
    logging.getLogger("vela").info("[Verify] control line for the httpx level test")
    assert any(
        r.name == "vela" and r.levelno == logging.INFO and "[Verify] control line" in r.getMessage()
        for r in caplog.records
    ), "a vela INFO line was filtered — the fix over-reached beyond the httpx logger"


def test_httpx_warning_still_passes_control(caplog):
    """CONTROL (Rule 17): httpx WARNING and above still surface — only the
    per-request INFO line is suppressed, not the library's error reporting."""
    caplog.set_level(logging.INFO)
    logging.getLogger("httpx").warning("httpx warning control line")
    assert any(
        r.name == "httpx" and r.levelno == logging.WARNING and "warning control" in r.getMessage()
        for r in caplog.records
    ), "httpx WARNING was filtered — the level was set too high"
