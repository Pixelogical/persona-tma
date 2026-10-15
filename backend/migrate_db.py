"""Safely migrate an older Persona database to the current schema.

Usage (from the backend dir / container /app):

    python migrate_db.py --dry-run   # only report what WOULD change
    python migrate_db.py             # backup -> migrate -> verify

Steps (idempotent, additive — rows are never deleted and lookups keep
working with or without this script, because the app auto-migrates on
startup too; this script just adds a verified backup + report):

  1. Backs up the sqlite file to data/persona.db.bak-YYYYmmdd-HHMMSS
  2. Creates missing tables and columns (current models.py schema) and
     rebuilds the legacy songs table if it still has UNIQUE(file_unique_id)
  3. Backfills songs.norm_key (duplicate detection key)
  4. Normalizes legacy songs.tags values to the current tag rules
     ("Pop, Synth-Pop" -> "pop,synth_pop"); tags that cannot be normalized
     (e.g. non-English) are LEFT UNTOUCHED and reported — nothing is lost
  5. Rewrites legacy short-form group ids (-3784999585) to the canonical
     -100 supergroup form (-1003784999585) the Bot API requires; both
     forms are treated as equal everywhere in the app, so either works
  6. Verifies every table's row count is unchanged afterwards; on any
     mismatch it prints the backup path to restore from

Run with the backend stopped (docker compose stop backend), then start it
again — e.g.:

    docker compose stop backend
    docker compose run --rm backend python migrate_db.py --dry-run
    docker compose run --rm backend python migrate_db.py
    docker compose up -d backend
"""
import argparse
import sqlite3
import sys
from datetime import datetime

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from config import settings  # noqa: F401  (loads .env / paths)
from database import SessionLocal, engine, init_db
from models import Base, chat_id_variants, normalize_tag, parse_tags


def table_counts() -> dict:
    counts = {}
    insp = inspect(engine)
    with engine.connect() as conn:
        for table in insp.get_table_names():
            counts[table] = conn.exec_driver_sql(
                f'select count(*) from "{table}"'
            ).scalar()
    return counts


def schema_gaps() -> tuple:
    """What the current models.py schema needs that the DB doesn't have."""
    insp = inspect(engine)
    have = set(insp.get_table_names())
    missing_tables = [t.name for t in Base.metadata.sorted_tables if t.name not in have]
    missing_columns = {}
    for table in Base.metadata.sorted_tables:
        if table.name not in have:
            continue
        present = {c["name"] for c in insp.get_columns(table.name)}
        missing = [c.name for c in table.columns if c.name not in present]
        if missing:
            missing_columns[table.name] = missing
    has_legacy_unique = False
    if "songs" in have and engine.name == "sqlite":
        with engine.connect() as conn:
            rows = conn.exec_driver_sql("PRAGMA index_list(songs)").fetchall()
        has_legacy_unique = any(int(r[2]) == 1 for r in rows)
    return missing_tables, missing_columns, has_legacy_unique


def plan_data_fixups(db) -> tuple:
    """Raw SQL so this also runs against old schemas missing newer columns.
    Returns (tags_updates, unnormalizable_tags, chat_id_updates)."""
    tags_updates, unnormalizable, chat_updates = [], [], []
    if "songs" not in inspect(engine).get_table_names():
        return tags_updates, unnormalizable, chat_updates
    cols = {c["name"] for c in inspect(engine).get_columns("songs")}
    if "chat_id" not in cols:
        return tags_updates, unnormalizable, chat_updates
    rows = db.execute(
        text(f"select id, chat_id{' , tags' if 'tags' in cols else ', NULL'} from songs")
    ).fetchall()
    for song_id, chat_id, tags in rows:
        if tags:
            normalized, bad = [], None
            for tag in parse_tags(tags):
                norm = normalize_tag(tag)
                if norm is None:
                    bad = tag
                    break
                if norm not in normalized:
                    normalized.append(norm)
            if bad is not None:
                unnormalizable.append((song_id, tags, bad))
            elif ",".join(normalized) != tags:
                tags_updates.append((song_id, tags, ",".join(normalized)))
        if chat_id and chat_id < 0:
            canonical = chat_id_variants(chat_id)[0]
            if canonical != chat_id:
                chat_updates.append((song_id, chat_id, canonical))
    return tags_updates, unnormalizable, chat_updates


def make_backup() -> str:
    path = engine.url.database
    dest = f"{path}.bak-{datetime.now():%Y%m%d-%H%M%S}"
    src = sqlite3.connect(path)
    try:
        dst = sqlite3.connect(dest)
        with dst:
            src.backup(dst)  # wal-safe, unlike a plain file copy
        dst.close()
    finally:
        src.close()
    return dest


def report(tags_updates, unnormalizable, chat_updates, dry_run: bool) -> None:
    verb = "would" if dry_run else "will"
    for song_id, old, new in tags_updates:
        print(f"  tags  song #{song_id}: {old!r} -> {new!r}")
    for song_id, tags, bad in unnormalizable:
        print(f"  tags  song #{song_id}: left as-is ({bad!r} is not an English tag)")
    for song_id, old, new in chat_updates:
        print(f"  chat  song #{song_id}: {old} -> {new} (same group, Bot API form)")
    if tags_updates or chat_updates:
        print(f"  ({verb} {len(tags_updates)} tag value(s) and "
              f"{len(chat_updates)} group id(s) updated)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="only show what would change; touch nothing")
    args = ap.parse_args()

    url = engine.url.render_as_string(hide_password=True)
    print(f"database: {url}")
    if not inspect(engine).get_table_names():
        print("empty database — nothing to migrate (the app creates the current schema on startup)")
        return 0

    before = table_counts()
    missing_tables, missing_columns, legacy_unique = schema_gaps()
    db = SessionLocal()
    try:
        tags_updates, unnormalizable, chat_updates = plan_data_fixups(db)
    finally:
        db.close()

    if not (missing_tables or missing_columns or legacy_unique
            or tags_updates or chat_updates):
        print("already up to date — nothing to do")
        return 0

    for table in missing_tables:
        print(f"  table {table}: missing (will be created)")
    for table, columns in missing_columns.items():
        print(f"  cols  {table}: missing {', '.join(columns)}")
    if legacy_unique:
        print("  songs: legacy UNIQUE(file_unique_id) found (table will be rebuilt to remove it)")
    report(tags_updates, unnormalizable, chat_updates, args.dry_run)

    if args.dry_run:
        print("\ndry run — no changes made")
        return 0

    backup = make_backup() if engine.name == "sqlite" else None
    if backup:
        print(f"backup written: {backup}")

    try:
        init_db()  # create tables/columns, drop legacy unique, backfill norm_key
        db = SessionLocal()
        try:
            for song_id, _, new_tags in tags_updates:
                db.execute(text("update songs set tags = :t where id = :i"),
                           {"t": new_tags, "i": song_id})
            for song_id, _, new_chat in chat_updates:
                db.execute(text("update songs set chat_id = :c where id = :i"),
                           {"c": new_chat, "i": song_id})
            db.commit()
        finally:
            db.close()
    except OperationalError as exc:
        print(f"\n!! migration failed: {exc}")
        print("Stop the backend first (docker compose stop backend), run this "
              "script again, then start it. Your data is untouched")
        if backup:
            print(f"(backup: {backup})")
        return 1

    after = table_counts()
    missing_tables, missing_columns, legacy_unique = schema_gaps()
    lost = {t: (n, after.get(t, 0)) for t, n in before.items() if after.get(t, 0) < n}
    if lost or missing_tables or missing_columns or legacy_unique:
        print("\n!! verification FAILED — schema gaps or row loss:")
        for table, (was, now) in lost.items():
            print(f"   {table}: {was} -> {now} rows")
        print(f"   schema still missing: {missing_tables} {missing_columns}"
              f" legacy_unique={legacy_unique}")
        if backup:
            print(f"restore with:  cp '{backup}' '{engine.url.database}'")
        return 1

    print("\nverification: every table intact, schema now matches models.py")
    for table in sorted(after):
        delta = f" (+{after[table] - before.get(table, 0)} new)" if table not in before else ""
        print(f"  {table:<18} {after[table]} rows{delta}")
    print("done. start the backend again: docker compose up -d backend")
    return 0


if __name__ == "__main__":
    sys.exit(main())
