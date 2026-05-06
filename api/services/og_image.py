"""PRD § 4.5 — Pillow OG image generator (1200×630 PNG).

Idempotent: if static/og/{share_id}.png exists, skip and return its
path. Generated synchronously at share-creation time (PHASE B) and
served via the existing FastAPI static mount.

Font handling: tries Noto Sans CJK first (Dockerfile installs
fonts-noto-cjk in stage 2). If neither CJK nor a usable Latin font is
locatable, generates a placeholder image rather than silently rendering
Chinese as tofu boxes — see PHASE A spec.
"""

from __future__ import annotations

import logging
import os
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

_OG_DIR = Path("static") / "og"
_PLACEHOLDER_NAME = "default.png"

_WIDTH = 1200
_HEIGHT = 630

# Search order: prefer CJK-aware fonts so Chinese share titles render
# correctly. Latin fallback is only used when the title is pure ASCII.
_CJK_CANDIDATES = (
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "C:/Windows/Fonts/msyh.ttc",       # Microsoft YaHei (zh-Hans/zh-Hant)
    "C:/Windows/Fonts/msjh.ttc",       # Microsoft JhengHei (zh-Hant)
)

_LATIN_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
)


def _find_font(candidates: tuple[str, ...]) -> str | None:
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


def _load_font(size: int, prefer_cjk: bool) -> ImageFont.FreeTypeFont | None:
    if prefer_cjk:
        path = _find_font(_CJK_CANDIDATES) or _find_font(_LATIN_CANDIDATES)
    else:
        path = _find_font(_LATIN_CANDIDATES) or _find_font(_CJK_CANDIDATES)
    if not path:
        return None
    try:
        return ImageFont.truetype(path, size)
    except OSError as e:
        logger.warning("[og] failed to load %s: %s", path, e)
        return None


def _has_cjk(text: str) -> bool:
    for ch in text:
        cp = ord(ch)
        # CJK Unified Ideographs + Hiragana/Katakana + Hangul
        if (
            0x3040 <= cp <= 0x30FF
            or 0x3400 <= cp <= 0x4DBF
            or 0x4E00 <= cp <= 0x9FFF
            or 0xAC00 <= cp <= 0xD7AF
            or 0xF900 <= cp <= 0xFAFF
        ):
            return True
    return False


def _wrap_text(text: str, max_chars: int, max_lines: int) -> list[str]:
    text = (text or "").strip().replace("\r", "")
    # CJK has no word boundaries; fall back to char-level wrapping
    if _has_cjk(text):
        lines: list[str] = []
        for paragraph in text.split("\n"):
            for i in range(0, len(paragraph), max_chars):
                lines.append(paragraph[i : i + max_chars])
                if len(lines) >= max_lines:
                    break
            if len(lines) >= max_lines:
                break
    else:
        lines = []
        for paragraph in text.split("\n"):
            wrapped = textwrap.wrap(paragraph, width=max_chars) or [""]
            for w in wrapped:
                lines.append(w)
                if len(lines) >= max_lines:
                    break
            if len(lines) >= max_lines:
                break

    if len(lines) > max_lines:
        lines = lines[:max_lines]
    if lines and len(text) > sum(len(l) for l in lines):
        last = lines[-1]
        if len(last) >= max_chars - 1:
            lines[-1] = last[:-1] + "…"
        else:
            lines[-1] = last + "…"
    return lines


def _draw_card(query_text: str, query_is_cjk: bool) -> Image.Image:
    img = Image.new("RGB", (_WIDTH, _HEIGHT), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Top accent bar
    draw.rectangle([(0, 0), (_WIDTH, 8)], fill=(37, 99, 235))

    # "Vela" wordmark top-left
    brand_font = _load_font(48, prefer_cjk=False)
    if brand_font:
        draw.text((60, 56), "Vela", font=brand_font, fill=(17, 24, 39))

    # Query body
    title_font = _load_font(56, prefer_cjk=query_is_cjk)
    max_chars = 22 if query_is_cjk else 42
    lines = _wrap_text(query_text or "Shared on Vela", max_chars=max_chars, max_lines=4)

    if title_font is None:
        # Last-resort placeholder — do NOT silently render the wrong font
        logger.warning("[og] no usable font found; emitting placeholder card")
        fallback = ImageFont.load_default()
        draw.text((60, 200), "Shared on Vela", font=fallback, fill=(17, 24, 39))
        return img

    line_height = 72
    y = 200
    for ln in lines:
        draw.text((60, y), ln, font=title_font, fill=(17, 24, 39))
        y += line_height

    # Footer accent
    foot_font = _load_font(28, prefer_cjk=False)
    if foot_font:
        draw.text((60, _HEIGHT - 70), "vela.an-tho.com", font=foot_font, fill=(107, 114, 128))

    return img


def generate_og_png(share_id: str, query_text: str) -> Path:
    """Idempotent. Returns path to PNG. Caller serves via /static/og/{id}.png."""
    _OG_DIR.mkdir(parents=True, exist_ok=True)
    target = _OG_DIR / f"{share_id}.png"
    if target.exists():
        return target

    cjk = _has_cjk(query_text or "")
    title_font_present = _find_font(_CJK_CANDIDATES if cjk else _LATIN_CANDIDATES) is not None
    if cjk and not _find_font(_CJK_CANDIDATES):
        # Bilingual CJK title with no CJK font on disk would tofu.
        # Emit a placeholder pointing to the default image and warn.
        logger.warning(
            "[og] CJK query but no Noto CJK font installed; using default placeholder. "
            "Install fonts-noto-cjk in Dockerfile stage 2."
        )
        placeholder = _OG_DIR / _PLACEHOLDER_NAME
        if not placeholder.exists():
            img = _draw_card("Shared on Vela", query_is_cjk=False)
            img.save(placeholder, format="PNG", optimize=True)
        return placeholder

    if not title_font_present:
        logger.warning("[og] no font found at all; emitting minimal placeholder")

    img = _draw_card(query_text, query_is_cjk=cjk)
    img.save(target, format="PNG", optimize=True)
    return target
