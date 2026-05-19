"""Unit tests for OG image generation + StaticFiles mount routing.

Covers the [fix 4.5] OG image URL/path mismatch:
- generate_og_png writes static/og/<id>.png on disk
- repeated calls are idempotent (no rewrite of an existing file)
- a FastAPI app mounting StaticFiles at /static/og resolves
  GET /static/og/<id>.png to that file (the production fix in
  api/server.py — registered above the catch-all so the root mount's
  directory="static" does not double-prefix to static/static/og/<id>.png).
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from PIL import Image

from api.services.og_image import generate_og_png


_TEST_PREFIX = "test_og_"
_OG_DIR = Path("static") / "og"


@pytest.fixture(autouse=True)
def _cleanup_test_pngs():
    yield
    if _OG_DIR.exists():
        for p in _OG_DIR.glob(f"{_TEST_PREFIX}*.png"):
            try:
                p.unlink()
            except OSError:
                pass


def test_generate_writes_file():
    share_id = f"{_TEST_PREFIX}writes"
    out = generate_og_png(share_id, "Test query for OG card")

    assert out.exists(), f"expected {out} to exist after generate_og_png"
    assert out.name == f"{share_id}.png"
    assert out.parent == _OG_DIR

    with Image.open(out) as img:
        assert img.format == "PNG"
        assert img.size == (1200, 630)


def test_generate_idempotent():
    share_id = f"{_TEST_PREFIX}idempotent"
    first = generate_og_png(share_id, "First call")
    assert first.exists()
    first_mtime = first.stat().st_mtime

    time.sleep(0.05)
    second = generate_og_png(share_id, "Second call — should be ignored")

    assert second == first
    assert second.stat().st_mtime == first_mtime, (
        "og_image.py:160 should skip when target exists; mtime must not change"
    )


def test_static_mount_serves_og():
    share_id = f"{_TEST_PREFIX}mount"
    target = generate_og_png(share_id, "Mount routing test")
    assert target.exists()

    app = FastAPI()
    app.mount("/static/og", StaticFiles(directory=str(_OG_DIR)), name="og_images")

    with TestClient(app) as client:
        resp = client.get(f"/static/og/{share_id}.png")

    assert resp.status_code == 200, (
        f"expected 200 from /static/og/{share_id}.png; got {resp.status_code}. "
        "If 404, the dedicated mount in api/server.py is not resolving correctly."
    )
    assert resp.headers["content-type"] == "image/png"
    assert len(resp.content) > 0
