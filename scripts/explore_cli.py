"""Vela § 4.6 Explore Content CLI.

Manages content/explore/*.md → ExplorePage DB workflow.

Commands:
    sync                                    UPSERT all markdown files to DB
    list                                    Print all DB entries
    publish <slug> [--locale LOCALE]        Flip to status='published'
    unpublish <slug> [--locale LOCALE]      Flip to status='draft'
    archive <slug> [--locale LOCALE]        Flip to status='archived'
    from-vela "<query>" --locale LOCALE --slug SLUG
                                            Generate draft markdown from Vela research API

Usage:
    python scripts/explore_cli.py <command> [args]

DB target: whatever DATABASE_URL points to (Neon Postgres in dev). Mirrors
the connection pattern from scripts/seed_explore_dev.py — load_dotenv()
then import SessionLocal.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path so `from api...` works from any cwd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # PyYAML 6.0.3 — pre-installed dep
from dotenv import load_dotenv

load_dotenv()

from api.database.sql_db import SessionLocal  # noqa: E402
from api.models.sql_models import ExplorePage  # noqa: E402


CONTENT_DIR = Path(__file__).resolve().parent.parent / "content" / "explore"

# Mirror api/services/explore_renderer.py constants. Re-declared here so
# the CLI works without importing the renderer (which pulls Pillow,
# Jinja2, etc — overkill for editorial tooling).
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_SLUG_LEN = 80
REQUIRED_FRONTMATTER = ("slug", "locale", "query", "meta_title", "meta_description", "status")
VALID_STATUS = {"draft", "published", "archived"}


# ─────────────────────────────────────────────────────────────────
# Markdown frontmatter parsing
# ─────────────────────────────────────────────────────────────────

def _parse_markdown(filepath: Path) -> tuple[dict, str]:
    """Parse YAML frontmatter + markdown body. Returns (metadata, body)."""
    text = filepath.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"missing YAML frontmatter (must start with '---')")
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        raise ValueError(f"malformed frontmatter (missing closing '---')")
    try:
        metadata = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"YAML parse error: {e}")
    if not isinstance(metadata, dict):
        raise ValueError(f"frontmatter must be a YAML mapping, got {type(metadata).__name__}")
    body = parts[2].strip()
    return metadata, body


def _validate_metadata(metadata: dict, filepath: Path) -> None:
    """Raise ValueError if metadata is invalid."""
    for field in REQUIRED_FRONTMATTER:
        if field not in metadata:
            raise ValueError(f"missing required frontmatter field: {field}")

    slug = metadata["slug"]
    if not isinstance(slug, str) or not SLUG_PATTERN.match(slug):
        raise ValueError(
            f"invalid slug '{slug}' (must match {SLUG_PATTERN.pattern}, lowercase ASCII alphanumeric + hyphens, no double-hyphens)"
        )
    if len(slug) > MAX_SLUG_LEN:
        raise ValueError(f"slug exceeds {MAX_SLUG_LEN} chars: {slug!r}")

    status = metadata.get("status")
    if status not in VALID_STATUS:
        raise ValueError(f"invalid status '{status}' (must be one of {sorted(VALID_STATUS)})")

    expected_name = f"{slug}.{metadata['locale']}.md"
    if filepath.name != expected_name:
        raise ValueError(
            f"filename '{filepath.name}' doesn't match frontmatter slug+locale "
            f"(expected '{expected_name}')"
        )


def _content_hash(body: str, citations: list) -> str:
    """md5 of normalized content for idempotent sync."""
    normalized = body + json.dumps(citations or [], sort_keys=True, ensure_ascii=False)
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────────────────────────
# Commands
# ─────────────────────────────────────────────────────────────────

def cmd_sync(args) -> int:
    if not CONTENT_DIR.exists():
        print(f"WARN: {CONTENT_DIR} doesn't exist. Nothing to sync.")
        return 0

    md_files = sorted(p for p in CONTENT_DIR.glob("*.md") if p.name != "README.md")
    if not md_files:
        print(f"No markdown files in {CONTENT_DIR} (excluding README.md).")
        return 0

    print(f"Scanning {len(md_files)} markdown file(s)...")

    session = SessionLocal()
    inserted = updated = unchanged = errored = 0
    file_keys: set[tuple[str, str]] = set()
    try:
        for filepath in md_files:
            try:
                metadata, body = _parse_markdown(filepath)
                _validate_metadata(metadata, filepath)

                slug = metadata["slug"]
                locale = metadata["locale"]
                file_keys.add((slug, locale))

                citations = metadata.get("citations") or []
                if not isinstance(citations, list):
                    raise ValueError(f"citations must be a YAML list, got {type(citations).__name__}")

                existing = (
                    session.query(ExplorePage)
                    .filter_by(slug=slug, locale=locale)
                    .first()
                )

                if existing:
                    new_hash = _content_hash(body, citations)
                    old_hash = _content_hash(existing.answer_text or "", existing.citations or [])
                    metadata_unchanged = (
                        existing.query_text == metadata["query"]
                        and existing.meta_title == metadata["meta_title"]
                        and existing.meta_description == metadata["meta_description"]
                        and existing.category == metadata.get("category")
                        and existing.hreflang_group == metadata.get("hreflang_group")
                        and existing.status == metadata["status"]
                    )
                    if new_hash == old_hash and metadata_unchanged:
                        unchanged += 1
                        continue

                    existing.query_text = metadata["query"]
                    existing.answer_text = body
                    existing.citations = citations
                    existing.meta_title = metadata["meta_title"]
                    existing.meta_description = metadata["meta_description"]
                    existing.category = metadata.get("category")
                    existing.hreflang_group = metadata.get("hreflang_group")
                    existing.status = metadata["status"]
                    existing.last_updated_at = datetime.utcnow()
                    if metadata["status"] == "published" and not existing.published_at:
                        existing.published_at = datetime.utcnow()
                    updated += 1
                    print(f"  UPDATE {slug} ({locale}) [{metadata['status']}]")
                else:
                    now_dt = datetime.utcnow()
                    new_row = ExplorePage(
                        slug=slug,
                        locale=locale,
                        query_text=metadata["query"],
                        answer_text=body,
                        citations=citations,
                        meta_title=metadata["meta_title"],
                        meta_description=metadata["meta_description"],
                        category=metadata.get("category"),
                        hreflang_group=metadata.get("hreflang_group"),
                        status=metadata["status"],
                        published_at=now_dt if metadata["status"] == "published" else None,
                        last_updated_at=now_dt,
                    )
                    session.add(new_row)
                    inserted += 1
                    print(f"  INSERT {slug} ({locale}) [{metadata['status']}]")
            except (ValueError, yaml.YAMLError) as e:
                print(f"  ERROR {filepath.name}: {e}", file=sys.stderr)
                errored += 1

        session.commit()

        # Orphan detection: rows in DB without matching files
        all_db_rows = session.query(ExplorePage).all()
        all_db_keys = {(r.slug, r.locale) for r in all_db_rows}
        orphans = all_db_keys - file_keys

        print(f"\nDone. Inserted={inserted}, Updated={updated}, Unchanged={unchanged}, Errored={errored}")
        if orphans:
            print(f"\nWARN: {len(orphans)} DB row(s) have no matching file (NOT deleted automatically):")
            for slug, locale in sorted(orphans):
                print(f"  {slug} ({locale})")
            print("Use `archive <slug> --locale <locale>` to retire, or create the matching .md file.")

        return 1 if errored > 0 else 0
    finally:
        session.close()


def cmd_list(args) -> int:
    session = SessionLocal()
    try:
        rows = (
            session.query(ExplorePage)
            .order_by(ExplorePage.status, ExplorePage.last_updated_at.desc())
            .all()
        )
        if not rows:
            print("No entries in explore_page table.")
            return 0

        print(f"{'SLUG':<50} {'LOCALE':<8} {'STATUS':<12} {'UPDATED':<20}")
        print("-" * 90)
        for r in rows:
            updated = r.last_updated_at.strftime("%Y-%m-%d %H:%M") if r.last_updated_at else "—"
            print(f"{r.slug:<50} {r.locale:<8} {r.status:<12} {updated:<20}")
        print(f"\nTotal: {len(rows)} row(s)")
        return 0
    finally:
        session.close()


def _change_status(args, new_status: str) -> int:
    if new_status not in VALID_STATUS:
        print(f"ERROR: invalid status '{new_status}'", file=sys.stderr)
        return 1

    session = SessionLocal()
    try:
        row = (
            session.query(ExplorePage)
            .filter_by(slug=args.slug, locale=args.locale)
            .first()
        )
        if not row:
            print(
                f"ERROR: no row found for slug='{args.slug}', locale='{args.locale}'",
                file=sys.stderr,
            )
            return 1

        old_status = row.status
        row.status = new_status
        row.last_updated_at = datetime.utcnow()
        if new_status == "published" and not row.published_at:
            row.published_at = datetime.utcnow()

        session.commit()
        print(f"OK: {args.slug} ({args.locale}): {old_status} → {new_status}")
        return 0
    finally:
        session.close()


def cmd_publish(args) -> int:
    return _change_status(args, "published")


def cmd_unpublish(args) -> int:
    return _change_status(args, "draft")


def cmd_archive(args) -> int:
    return _change_status(args, "archived")


def cmd_from_vela(args) -> int:
    """Generate markdown draft by calling Vela research pipeline via in-process TestClient.

    TestClient runs FastAPI app in-process (no uvicorn dependency). TEST_MODE
    bypasses Clerk auth + credit checks, so editorial use doesn't burn user quota.
    The actual research pipeline (PHI guard, RAG retriever, LLM generator) runs
    end-to-end — same code paths as production.
    """
    # Slug validation upfront
    if not SLUG_PATTERN.match(args.slug):
        print(
            f"ERROR: invalid slug '{args.slug}' (must match {SLUG_PATTERN.pattern})",
            file=sys.stderr,
        )
        return 1

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CONTENT_DIR / f"{args.slug}.{args.locale}.md"
    if out_path.exists():
        print(f"WARN: {out_path} already exists. Overwriting will lose manual edits.")
        confirm = input("Overwrite? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return 1

    # Force TEST_MODE for the in-process invocation. This is set in the
    # current process's env so api.server's module-level guard sees it.
    os.environ["TEST_MODE"] = "true"

    print(f"Calling Vela research pipeline: query={args.query!r} locale={args.locale}...")
    print("(this loads vector store + LLM client; ~5-10s first call)")

    from fastapi.testclient import TestClient  # noqa: E402
    from api.server import app  # noqa: E402

    client = TestClient(app)
    response = client.post(
        "/api/research",
        json={"question": args.query, "max_results": 5},
    )

    if response.status_code != 200:
        print(f"ERROR: research API returned {response.status_code}: {response.text[:500]}", file=sys.stderr)
        return 1

    # Parse SSE stream
    answer_text = ""
    citations: list = []
    error_msg: str | None = None
    for line in response.text.split("\n"):
        if not line.startswith("data: "):
            continue
        try:
            evt = json.loads(line[6:])
        except json.JSONDecodeError:
            continue
        evt_type = evt.get("type")
        if evt_type == "answer":
            answer_text += evt.get("content", "")
        elif evt_type == "fallback":
            answer_text += evt.get("content", "")
        elif evt_type == "citations":
            citations = evt.get("content") or []
        elif evt_type == "error":
            error_msg = evt.get("content")

    if error_msg:
        print(f"ERROR: research pipeline reported: {error_msg}", file=sys.stderr)
        return 1
    if not answer_text.strip():
        print("ERROR: research pipeline returned empty answer.", file=sys.stderr)
        return 1

    # Massage citations into the frontmatter shape (already dict-shaped from
    # SSE; only need to remove non-serializable bits if any).
    safe_citations = []
    for c in citations:
        if not isinstance(c, dict):
            continue
        safe_citations.append({
            "source_type": c.get("source_type", "other"),
            "title": c.get("title", ""),
            "authors": c.get("authors", ""),
            "journal": c.get("journal", ""),
            "year": c.get("year", ""),
            "url": c.get("url", ""),
            "credibility": c.get("credibility", "peer-reviewed"),
            "snippet": c.get("snippet", ""),
        })

    # Truncate query for meta_title placeholder
    truncated_q = args.query[:55].rstrip()
    if len(args.query) > 55:
        truncated_q += "..."

    # meta_description placeholder: first ~150 chars of answer body (stripped)
    desc_source = re.sub(r"[#*_`>\-\n]+", " ", answer_text).strip()
    desc_source = re.sub(r"\s+", " ", desc_source)
    meta_desc = (desc_source[:152] + "...") if len(desc_source) > 155 else desc_source

    frontmatter = {
        "slug": args.slug,
        "locale": args.locale,
        "query": args.query,
        "meta_title": f"{truncated_q} | Vela",
        "meta_description": meta_desc,
        "category": "",
        "hreflang_group": "",
        "status": "draft",  # NEVER auto-publish — explicit editorial gate
        "citations": safe_citations,
    }

    yaml_block = yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False, default_flow_style=False)
    out_path.write_text(
        f"---\n{yaml_block}---\n\n{answer_text}\n",
        encoding="utf-8",
    )

    print(f"\nDraft saved to {out_path}")
    print(f"  query_text:       {args.query[:80]}{'...' if len(args.query) > 80 else ''}")
    print(f"  answer_text:      {len(answer_text)} chars")
    print(f"  citations:        {len(safe_citations)}")
    print()
    print("Next steps:")
    print(f"  1. Edit {out_path} — fill meta_title, meta_description, category, hreflang_group")
    print(f"  2. python scripts/explore_cli.py sync")
    print(f"  3. python scripts/explore_cli.py publish {args.slug} --locale {args.locale}")
    return 0


# ─────────────────────────────────────────────────────────────────
# argparse wiring
# ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="explore_cli",
        description="Vela § 4.6 Explore Content CLI",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_sync = sub.add_parser("sync", help="UPSERT all content/explore/*.md to DB")
    p_sync.set_defaults(func=cmd_sync)

    p_list = sub.add_parser("list", help="Print all DB entries")
    p_list.set_defaults(func=cmd_list)

    p_pub = sub.add_parser("publish", help="Flip to status='published'")
    p_pub.add_argument("slug")
    p_pub.add_argument("--locale", default="en")
    p_pub.set_defaults(func=cmd_publish)

    p_unpub = sub.add_parser("unpublish", help="Flip to status='draft'")
    p_unpub.add_argument("slug")
    p_unpub.add_argument("--locale", default="en")
    p_unpub.set_defaults(func=cmd_unpublish)

    p_arch = sub.add_parser("archive", help="Flip to status='archived'")
    p_arch.add_argument("slug")
    p_arch.add_argument("--locale", default="en")
    p_arch.set_defaults(func=cmd_archive)

    p_vela = sub.add_parser("from-vela", help="Generate draft markdown from Vela research API")
    p_vela.add_argument("query", help="The query to ask Vela")
    p_vela.add_argument("--locale", default="en")
    p_vela.add_argument("--slug", required=True, help="Slug for the generated file")
    p_vela.set_defaults(func=cmd_from_vela)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
