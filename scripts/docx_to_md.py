"""Minimal docx -> markdown converter (no rewriting, just format conversion).

Handles: headings, paragraphs, bullet/numbered lists, tables, bold/italic,
inline code (monospace fonts), hyperlinks. Unknown content stays as plain text.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph


def _bool_attr(el, tag: str) -> bool:
    node = el.find(qn(tag))
    if node is None:
        return False
    val = node.get(qn("w:val"))
    return val not in ("false", "0")


def _run_to_md(r) -> str:
    text_parts = []
    for child in r:
        tag = child.tag
        if tag == qn("w:t"):
            text_parts.append(child.text or "")
        elif tag == qn("w:tab"):
            text_parts.append("\t")
        elif tag == qn("w:br"):
            text_parts.append("  \n")
    text = "".join(text_parts)
    if not text:
        return ""

    rPr = r.find(qn("w:rPr"))
    bold = italic = code = False
    if rPr is not None:
        bold = _bool_attr(rPr, "w:b")
        italic = _bool_attr(rPr, "w:i")
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is not None:
            font = (rFonts.get(qn("w:ascii")) or "") + (rFonts.get(qn("w:hAnsi")) or "")
            if any(k in font for k in ("Consolas", "Courier", "Mono", "Code")):
                code = True

    if code:
        return f"`{text}`"
    if bold and italic:
        return f"***{text}***"
    if bold:
        return f"**{text}**"
    if italic:
        return f"*{text}*"
    return text


def _paragraph_text(p_element, rels: dict) -> str:
    parts = []
    for child in p_element:
        tag = child.tag
        if tag == qn("w:r"):
            parts.append(_run_to_md(child))
        elif tag == qn("w:hyperlink"):
            inner = "".join(_run_to_md(r) for r in child.findall(qn("w:r")))
            rid = child.get(qn("r:id"))
            url = rels.get(rid, "") if rid else ""
            if url and inner:
                parts.append(f"[{inner}]({url})")
            else:
                parts.append(inner)
    return "".join(parts)


def _heading_level(style_name: str) -> int:
    if not style_name:
        return 0
    m = re.match(r"Heading (\d+)", style_name)
    if m:
        return min(int(m.group(1)), 6)
    if style_name == "Title":
        return 1
    return 0


def _list_info(p: Paragraph):
    pPr = p._element.find(qn("w:pPr"))
    if pPr is None:
        return None
    numPr = pPr.find(qn("w:numPr"))
    if numPr is None:
        return None
    ilvl = numPr.find(qn("w:ilvl"))
    level = int(ilvl.get(qn("w:val"))) if ilvl is not None else 0
    return level


def _table_to_md(table: Table, rels: dict) -> str:
    rows_out = []
    for row in table.rows:
        cells = []
        for cell in row.cells:
            lines = []
            for p in cell.paragraphs:
                t = _paragraph_text(p._element, rels).strip()
                if t:
                    lines.append(t)
            joined = "<br>".join(lines)
            joined = joined.replace("|", "\\|")
            cells.append(joined)
        rows_out.append(cells)

    if not rows_out:
        return ""
    ncols = max(len(r) for r in rows_out)
    for r in rows_out:
        while len(r) < ncols:
            r.append("")

    out = []
    out.append("| " + " | ".join(rows_out[0]) + " |")
    out.append("| " + " | ".join(["---"] * ncols) + " |")
    for r in rows_out[1:]:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def convert(src: Path, dst: Path) -> None:
    doc = Document(str(src))
    rels = {}
    for rid, rel in doc.part.rels.items():
        if rel.reltype.endswith("/hyperlink"):
            rels[rid] = rel.target_ref

    out: list[str] = []
    for block in doc.iter_inner_content():
        try:
            if isinstance(block, Paragraph):
                text = _paragraph_text(block._element, rels)
                style = block.style.name if block.style is not None else ""
                lvl = _heading_level(style)
                if lvl > 0:
                    out.append(f"{'#' * lvl} {text.strip()}")
                    out.append("")
                    continue
                li_level = _list_info(block)
                if li_level is not None:
                    indent = "  " * li_level
                    out.append(f"{indent}- {text.strip()}")
                    continue
                if text.strip():
                    out.append(text)
                    out.append("")
                else:
                    out.append("")
            elif isinstance(block, Table):
                out.append(_table_to_md(block, rels))
                out.append("")
            else:
                out.append("<!-- TODO: 轉換失敗,請人工檢查 -->")
                out.append("")
        except Exception as e:
            out.append(f"<!-- TODO: 轉換失敗,請人工檢查 ({type(e).__name__}: {e}) -->")
            out.append("")

    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    dst.write_text(text, encoding="utf-8")
    print(f"{src.name} -> {dst.name}  ({len(text)} chars, {text.count(chr(10))} lines)")


if __name__ == "__main__":
    convert(Path(sys.argv[1]), Path(sys.argv[2]))
