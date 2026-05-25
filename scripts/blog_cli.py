"""Vela Blog Content CLI (PHASE B).

Manages content/blog/*.md → BlogPost DB workflow. Mirrors
scripts/explore_cli.py structure but narrowed to MVP scope:
ONLY `sync` and `list` commands (no publish/unpublish/archive/from-vela).

Commands:
    sync     UPSERT all content/blog/*.md to DB
    list     Print all BlogPost rows

Usage:
    python scripts/blog_cli.py sync
    python scripts/blog_cli.py list

DB target: whatever DATABASE_URL points to (Neon Postgres in prod, sqlite
in dev). Mirrors explore_cli's connection pattern — load_dotenv() then
import SessionLocal.

Theme keys re-declared here (not imported from blog_renderer) so the CLI
stays light — same pattern explore_cli uses for SLUG_PATTERN constants
(see explore_cli.py:47–48 comment).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

# Ensure project root is on sys.path so `from api...` works from any cwd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # PyYAML — pre-installed dep
from dotenv import load_dotenv

load_dotenv()

from api.database.sql_db import SessionLocal  # noqa: E402
from api.models.sql_models import BlogPost  # noqa: E402


CONTENT_DIR = Path(__file__).resolve().parent.parent / "content" / "blog"

# Mirror api/services/blog_renderer.py constants. Re-declared so the CLI
# doesn't import the renderer (which pulls Jinja2 + share_renderer —
# overkill for editorial tooling).
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_SLUG_LEN = 80
REQUIRED_FRONTMATTER = ("slug", "locale", "title", "status")
VALID_STATUS = {"draft", "published"}        # NOT archived — blog MVP narrower than explore
VALID_LOCALES = {"en", "zh-TW"}              # Blog MVP locales (spec)
VALID_THEMES = {                              # mirror blog_renderer.BLOG_THEME_COLORS keys
    "research", "verify", "explain", "asia",
    "privacy", "allied-health", "strategy",
}
DEFAULT_THEME = "strategy"


# ─────────────────────────────────────────────────────────────────
# Frontmatter parsing + validation
# ─────────────────────────────────────────────────────────────────

def _parse_markdown(filepath: Path) -> tuple[dict, str]:
    """Parse YAML frontmatter + markdown body. Returns (metadata, body)."""
    text = filepath.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter (must start with '---')")
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        raise ValueError("malformed frontmatter (missing closing '---')")
    try:
        metadata = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"YAML parse error: {e}")
    if not isinstance(metadata, dict):
        raise ValueError(f"frontmatter must be a YAML mapping, got {type(metadata).__name__}")
    body = parts[2].strip()
    return metadata, body


def _validate_faqs(faqs) -> None:
    """faqs must be list of {q: str, a: str} dicts (else FAQPage JSON-LD breaks)."""
    if faqs is None:
        return
    if not isinstance(faqs, list):
        raise ValueError(f"faqs must be a YAML list, got {type(faqs).__name__}")
    for i, item in enumerate(faqs):
        if not isinstance(item, dict):
            raise ValueError(f"faqs[{i}] must be a mapping with q/a keys, got {type(item).__name__}")
        if "q" not in item or "a" not in item:
            raise ValueError(f"faqs[{i}] missing required q/a keys: {item!r}")
        if not isinstance(item["q"], str) or not isinstance(item["a"], str):
            raise ValueError(f"faqs[{i}] q and a must be strings")


def _validate_tags(tags) -> None:
    """tags must be list of strings."""
    if tags is None:
        return
    if not isinstance(tags, list):
        raise ValueError(f"tags must be a YAML list, got {type(tags).__name__}")
    for i, item in enumerate(tags):
        if not isinstance(item, str):
            raise ValueError(f"tags[{i}] must be a string, got {type(item).__name__}")


def _validate_metadata(metadata: dict, filepath: Path) -> None:
    """Raise ValueError if metadata is invalid."""
    for field in REQUIRED_FRONTMATTER:
        if field not in metadata:
            raise ValueError(f"missing required frontmatter field: {field}")

    slug = metadata["slug"]
    if not isinstance(slug, str) or not SLUG_PATTERN.match(slug):
        raise ValueError(
            f"invalid slug {slug!r} (must match {SLUG_PATTERN.pattern}, "
            "lowercase ASCII alphanumeric + hyphens, no double-hyphens)"
        )
    if len(slug) > MAX_SLUG_LEN:
        raise ValueError(f"slug exceeds {MAX_SLUG_LEN} chars: {slug!r}")

    locale = metadata["locale"]
    if locale not in VALID_LOCALES:
        raise ValueError(f"invalid locale {locale!r} (must be one of {sorted(VALID_LOCALES)})")

    status = metadata.get("status")
    if status not in VALID_STATUS:
        raise ValueError(f"invalid status {status!r} (must be one of {sorted(VALID_STATUS)})")

    title = metadata.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title must be a non-empty string")

    # Loose theme validation: warn but accept; renderer falls back to strategy.
    theme = metadata.get("theme")
    if theme is not None and theme not in VALID_THEMES:
        print(
            f"  WARN: {filepath.name} theme {theme!r} not in {sorted(VALID_THEMES)}; "
            "renderer will fall back to 'strategy'",
            file=sys.stderr,
        )

    _validate_faqs(metadata.get("faqs"))
    _validate_tags(metadata.get("tags"))

    expected_name = f"{slug}.{locale}.md"
    if filepath.name != expected_name:
        raise ValueError(
            f"filename {filepath.name!r} doesn't match frontmatter slug+locale "
            f"(expected {expected_name!r})"
        )


def _parse_published_at(value) -> datetime | None:
    """Coerce a frontmatter `published_at` value to datetime.

    yaml.safe_load returns datetime.date for bare 'YYYY-MM-DD', datetime
    for 'YYYY-MM-DD HH:MM:SS', str for quoted values. Normalize all.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        # Try common ISO formats
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value.strip(), fmt)
            except ValueError:
                continue
        raise ValueError(f"published_at {value!r} not a recognized ISO date/datetime")
    raise ValueError(f"published_at must be date/datetime/str, got {type(value).__name__}")


def _content_hash(body: str, faqs, tags, theme: str | None, cover_image: str | None, summary: str | None) -> str:
    """md5 over normalized content + JSON-serialized metadata. Any meaningful
    field change triggers update on re-sync."""
    normalized = (
        body
        + json.dumps(faqs or [], sort_keys=True, ensure_ascii=False)
        + json.dumps(tags or [], sort_keys=True, ensure_ascii=False)
        + (theme or "")
        + (cover_image or "")
        + (summary or "")
    )
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

                if not body:
                    raise ValueError("body_markdown is empty (frontmatter without content)")

                slug = metadata["slug"]
                locale = metadata["locale"]
                file_keys.add((slug, locale))

                title = metadata["title"]
                summary = metadata.get("summary")
                theme = metadata.get("theme") or DEFAULT_THEME
                cover_image = metadata.get("cover_image") or None
                faqs = metadata.get("faqs")
                tags = metadata.get("tags")
                status = metadata["status"]
                published_at_fm = _parse_published_at(metadata.get("published_at"))

                existing = (
                    session.query(BlogPost)
                    .filter_by(slug=slug, locale=locale)
                    .first()
                )

                if existing:
                    new_hash = _content_hash(body, faqs, tags, theme, cover_image, summary)
                    old_hash = _content_hash(
                        existing.body_markdown or "",
                        existing.faqs,
                        existing.tags,
                        existing.theme,
                        existing.cover_image,
                        existing.summary,
                    )
                    # Metadata equality check separate from content hash so we
                    # detect title-only / status-only changes too.
                    metadata_unchanged = (
                        existing.title == title
                        and existing.status == status
                        and (existing.published_at == published_at_fm
                             if published_at_fm is not None
                             else True)
                    )
                    if new_hash == old_hash and metadata_unchanged:
                        unchanged += 1
                        continue

                    existing.title = title
                    existing.summary = summary
                    existing.body_markdown = body
                    existing.theme = theme
                    existing.cover_image = cover_image
                    existing.faqs = faqs
                    existing.tags = tags
                    existing.status = status
                    # published_at: respect frontmatter override; else auto-stamp on
                    # first publish; else leave alone.
                    if published_at_fm is not None:
                        existing.published_at = published_at_fm
                    elif status == "published" and not existing.published_at:
                        existing.published_at = datetime.utcnow()
                    # updated_at: SQLAlchemy onupdate=datetime.utcnow fires on the
                    # session.flush below; also bumped server-side on Postgres via
                    # explicit SET in PHASE A's migration default — both belt+suspenders.
                    updated += 1
                    print(f"  UPDATE {slug} ({locale}) [{status}]")
                else:
                    now_dt = datetime.utcnow()
                    pub_dt = published_at_fm
                    if pub_dt is None and status == "published":
                        pub_dt = now_dt
                    new_row = BlogPost(
                        slug=slug,
                        locale=locale,
                        title=title,
                        summary=summary,
                        body_markdown=body,
                        theme=theme,
                        cover_image=cover_image,
                        faqs=faqs,
                        tags=tags,
                        status=status,
                        published_at=pub_dt,
                    )
                    session.add(new_row)
                    inserted += 1
                    print(f"  INSERT {slug} ({locale}) [{status}]")
            except (ValueError, yaml.YAMLError) as e:
                print(f"  ERROR {filepath.name}: {e}", file=sys.stderr)
                errored += 1

        session.commit()

        # Orphan detection: rows in DB without a matching md file. NOT auto-deleted —
        # editor decides (matches explore_cli safety contract).
        all_db_rows = session.query(BlogPost).all()
        all_db_keys = {(r.slug, r.locale) for r in all_db_rows}
        orphans = all_db_keys - file_keys

        print(f"\nDone. Inserted={inserted}, Updated={updated}, Unchanged={unchanged}, Errored={errored}")
        if orphans:
            print(f"\nWARN: {len(orphans)} DB row(s) have no matching file (NOT deleted automatically):")
            for slug, locale in sorted(orphans):
                print(f"  {slug} ({locale})")
            print("Recreate the .md file or DELETE FROM blog_post WHERE ... manually to retire.")

        return 1 if errored > 0 else 0
    finally:
        session.close()


def cmd_list(args) -> int:
    session = SessionLocal()
    try:
        rows = (
            session.query(BlogPost)
            .order_by(BlogPost.status, BlogPost.updated_at.desc())
            .all()
        )
        if not rows:
            print("No entries in blog_post table.")
            return 0

        print(f"{'SLUG':<40} {'LOCALE':<8} {'STATUS':<10} {'TITLE':<50} {'UPDATED':<20}")
        print("-" * 130)
        for r in rows:
            updated = r.updated_at.strftime("%Y-%m-%d %H:%M") if r.updated_at else "—"
            title = (r.title[:47] + "...") if r.title and len(r.title) > 50 else (r.title or "")
            print(f"{r.slug:<40} {r.locale:<8} {r.status:<10} {title:<50} {updated:<20}")
        print(f"\nTotal: {len(rows)} row(s)")
        return 0
    finally:
        session.close()


# ─────────────────────────────────────────────────────────────────
# argparse wiring
# ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="blog_cli",
        description="Vela Blog Content CLI (PHASE B — sync + list only)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_sync = sub.add_parser("sync", help="UPSERT all content/blog/*.md to DB")
    p_sync.set_defaults(func=cmd_sync)

    p_list = sub.add_parser("list", help="Print all blog_post rows")
    p_list.set_defaults(func=cmd_list)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
