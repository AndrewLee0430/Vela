# -*- coding: utf-8 -*-
"""ARCHIVE UI car (founder rulings U1–U3, 2026-10-05) — what the EXPORTED HTML of each build
contains. Builds the static export twice (NEXT_PUBLIC_ARCHIVE_MODE=true, then unset) and reads
the files in out/.

THE BUSINESS RULES (CLAUDE.md Rule 17 — what breaks if each test fails):
  * The archive build shows ONLY the live surface: no link to /verify, /explain, /pricing or
    /refund anywhere a visitor lands (landing, an app page, the FAQ), no Verify / Explain band,
    no archive banner, no sign-up CTA — and it DOES carry one footer link to /about/ (U3), the
    archive FAQ (U4), and the archived notice on /refund (U1).
  * The flag-off build is unchanged: every one of those surfaces is still there. Without this
    half, a test that only looks for absences would pass on a build that broke the product.

WHY MARKUP, NOT i18n STRINGS: an i18n string ships in the JS bundle whether or not the flag is
on, so grepping the bundle for one cannot fail. These tests read the prerendered HTML and key on
markup the flag-gated components emit: hrefs, `data-band`, `data-archive-link`,
`data-archive-faq`, `data-archived-notice`, and the banner's `role="note"`. The same markers are
the prod readback (archive UI car baton).

COST: two `next build` runs (~4–5 min) and their memory. OPT-IN (founder ruling P3, 2026-10-05):
the whole module is skipped unless RUN_BUILD_TESTS=1 — a default full-suite run that included the
builds was reaped under memory pressure (archive UI car baton §2). Also skipped when node_modules
is absent.
Run: RUN_BUILD_TESTS=1 python -m pytest tests/test_archive_ui_build.py -q
"""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_BUILD_TESTS") != "1",
    reason="production-build tests are opt-in: set RUN_BUILD_TESTS=1 (two `next build` runs, ~4-5 min)",
)
HERO_CHIP2_EN = "Can elderly patients take BP meds with calcium?"


def _build(env_flag, dest):
    npm = shutil.which("npm.cmd") or shutil.which("npm")
    env = {k: v for k, v in os.environ.items() if k != "NEXT_PUBLIC_ARCHIVE_MODE"}
    if env_flag is not None:
        env["NEXT_PUBLIC_ARCHIVE_MODE"] = env_flag
    r = subprocess.run([npm, "run", "build"], cwd=ROOT, env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=900)
    assert r.returncode == 0, f"next build failed (flag={env_flag}):\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}"
    shutil.copytree(ROOT / "out", dest)
    return dest


@pytest.fixture(scope="module")
def builds(tmp_path_factory):
    if not (ROOT / "node_modules").is_dir():
        pytest.skip("node_modules absent — cannot run next build")
    base = tmp_path_factory.mktemp("archive_ui")
    default = _build(None, base / "default")          # order: archive last, so out/ ends as the
    archive = _build("true", base / "archive")         # archive build (what prod ships)
    return {"archive": archive, "default": default}


def _html(builds, which, page):
    return (builds[which] / page).read_text(encoding="utf-8")


RETIRED_HREFS = ['href="/verify"', 'href="/explain"', 'href="/pricing"', 'href="/refund"']


@pytest.mark.parametrize("page", ["index.html", "research.html", "faq.html"])
def test_archive_build_links_no_retired_surface(builds, page):
    html = _html(builds, "archive", page)
    found = [h for h in RETIRED_HREFS if h in html]
    assert found == [], f"{page}: the archive build still links {found}"
    assert 'href="/sign-up"' not in html, f"{page}: a sign-up CTA survived in the archive build"
    assert 'role="note"' not in html, f"{page}: the archive banner (U3: removed) is rendered"


def test_archive_landing_has_no_bands_no_chip2_and_one_about_link(builds):
    html = _html(builds, "archive", "index.html")
    assert 'data-band="verify"' not in html and 'data-band="explain"' not in html, \
        "U2: the Verify / Explain landing bands must be removed in the archive build"
    assert HERO_CHIP2_EN not in html, "hero chip 2 must stay hidden in the archive build"
    about = re.findall(r'<a[^>]*data-archive-link="about"[^>]*>', html)
    assert len(about) == 1 and 'href="/about/"' in about[0], \
        f"U3: exactly one footer link to /about/ expected, found {len(about)}"


def test_archive_faq_is_the_archive_variant(builds):
    html = _html(builds, "archive", "faq.html")
    assert "data-archive-faq" in html, "U4: the archive FAQ must replace the normal FAQ"
    assert 'data-archive-link="about"' in html, "U3: the FAQ footer carries the About link"


@pytest.mark.parametrize("page", ["refund.html", "verify.html", "explain.html", "pricing.html"])
def test_archive_retired_routes_render_the_notice(builds, page):
    assert "data-archived-notice" in _html(builds, "archive", page), \
        f"U1: {page} must render ArchivedFeatureNotice in the archive build"


def test_default_build_keeps_every_surface(builds):
    """CONTROL: the flag-off build still has what the archive build removes — so the absences
    above are the flag's effect, not a broken page."""
    index = _html(builds, "default", "index.html")
    for h in ['href="/verify"', 'href="/explain"', 'href="/pricing"', 'href="/refund"']:
        assert h in index, f"default landing lost {h}"
    assert 'data-band="verify"' in index and 'data-band="explain"' in index
    assert HERO_CHIP2_EN in index
    assert 'data-archive-link="about"' not in index and 'role="note"' not in index
    faq = _html(builds, "default", "faq.html")
    assert "data-archive-faq" not in faq and 'href="/sign-up"' in faq and 'href="/refund"' in faq
    assert 'href="/verify"' in _html(builds, "default", "research.html")
    for page in ("refund.html", "verify.html", "explain.html", "pricing.html"):
        assert "data-archived-notice" not in _html(builds, "default", page), page
