"""
archive_snapshots.py — DTR Snapshot Quarterly Archiver
=======================================================

Strategy
--------
  - Supabase (hot)  : last 30 days only
  - Local archive   : organized by  archives/dtr-snapshots/YYYY-Q{N}/
  - Retrieval       : client asks IT → IT asks GenXcript → locate file in archive

What this script does
---------------------
  1. Lists every file in the dtr-snapshots bucket.
  2. Parses the work_date from the file path
     (format: {company_id}/{employee_id}/{YYYY-MM-DD}_{suffix}.jpg).
  3. Any file whose work_date is older than RETAIN_DAYS (default 30)
     is downloaded to the local archive folder, then deleted from Supabase.
  4. Prints a summary report.

Run
---
  python scripts/archive_snapshots.py            # default 30-day retention
  python scripts/archive_snapshots.py --days 60  # keep 60 days in Supabase
  python scripts/archive_snapshots.py --dry-run  # list without downloading/deleting

Schedule: run once per quarter (Windows Task Scheduler or manually).

Archive layout
--------------
  archives/
  └── dtr-snapshots/
      ├── 2026-Q1/
      │   ├── COMPANY_UUID/
      │   │   └── EMP_UUID/
      │   │       ├── 2026-01-06_in.jpg
      │   │       └── 2026-01-06_out.jpg
      │   └── ...
      └── 2026-Q2/
          └── ...
"""

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# ── Project root on path ──────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from db.connection import get_supabase_admin_client

BUCKET          = "dtr-snapshots"
ARCHIVE_ROOT    = ROOT / "archives" / "dtr-snapshots"
DEFAULT_RETAIN  = 30   # days


# ── Helpers ───────────────────────────────────────────────────────────────────

def _quarter(d: date) -> str:
    """Return  '2026-Q1' … '2026-Q4'  for a given date."""
    return f"{d.year}-Q{(d.month - 1) // 3 + 1}"


def _parse_date_from_path(path: str) -> date | None:
    """
    Extract the work_date from a storage path.
    Expected format:  {company_id}/{employee_id}/{YYYY-MM-DD}_{suffix}.jpg
    """
    try:
        filename = path.rsplit("/", 1)[-1]          # '2026-01-06_in.jpg'
        date_part = filename.split("_")[0]           # '2026-01-06'
        return date.fromisoformat(date_part)
    except Exception:
        return None


def _list_all_files(db) -> list[str]:
    """
    Return all file paths in the bucket (handles Supabase pagination — each
    list() call returns at most 100 items by default; we page until done).
    """
    paths: list[str] = []

    def _list_folder(prefix: str) -> None:
        offset = 0
        while True:
            items = db.storage.from_(BUCKET).list(
                prefix,
                options={"limit": 200, "offset": offset},
            )
            if not items:
                break
            for item in items:
                item_name = item.get("name", "")
                if not item_name:
                    continue
                full_path = f"{prefix}/{item_name}" if prefix else item_name
                # Supabase returns "folders" as items with id=None
                if item.get("id") is None:
                    _list_folder(full_path)
                else:
                    paths.append(full_path)
            if len(items) < 200:
                break
            offset += 200

    _list_folder("")
    return paths


# ── Main ──────────────────────────────────────────────────────────────────────

def run(retain_days: int = DEFAULT_RETAIN, dry_run: bool = False) -> None:
    cutoff = date.today() - timedelta(days=retain_days)

    print(f"\n{'[DRY RUN] ' if dry_run else ''}DTR Snapshot Archiver")
    print(f"  Bucket       : {BUCKET}")
    print(f"  Retain in DB : last {retain_days} days  (cutoff: {cutoff})")
    print(f"  Archive root : {ARCHIVE_ROOT}")
    print()

    db = get_supabase_admin_client()

    # 1 — List all files
    print("Listing bucket contents …", end=" ", flush=True)
    all_paths = _list_all_files(db)
    print(f"{len(all_paths)} file(s) found.")

    if not all_paths:
        print("Nothing to archive. Exiting.")
        return

    # 2 — Classify
    to_archive:  list[tuple[str, date]] = []   # (path, work_date)
    unrecognised: list[str]              = []

    for path in all_paths:
        d = _parse_date_from_path(path)
        if d is None:
            unrecognised.append(path)
        elif d < cutoff:
            to_archive.append((path, d))

    print(f"  → {len(to_archive)} file(s) to archive  "
          f"(older than {retain_days} days)")
    print(f"  → {len(all_paths) - len(to_archive) - len(unrecognised)} file(s) retained")
    if unrecognised:
        print(f"  → {len(unrecognised)} file(s) skipped (unrecognised name format):")
        for p in unrecognised[:5]:
            print(f"       {p}")
        if len(unrecognised) > 5:
            print(f"       … and {len(unrecognised) - 5} more")

    if not to_archive:
        print("\nNothing to archive. Exiting.")
        return

    if dry_run:
        print("\n[DRY RUN] Would archive:")
        for path, d in sorted(to_archive):
            dest = ARCHIVE_ROOT / _quarter(d) / path
            print(f"  {path}  →  {dest.relative_to(ROOT)}")
        return

    # 3 — Download + save locally
    print("\nDownloading …")
    downloaded: list[str] = []
    failed_dl:  list[str] = []

    for path, d in sorted(to_archive):
        dest = ARCHIVE_ROOT / _quarter(d) / path
        dest.parent.mkdir(parents=True, exist_ok=True)

        if dest.exists():
            # Already archived previously (re-run safety)
            downloaded.append(path)
            continue

        try:
            raw = db.storage.from_(BUCKET).download(path)
            dest.write_bytes(raw)
            downloaded.append(path)
            print(f"  ✓  {path}")
        except Exception as exc:
            failed_dl.append(path)
            print(f"  ✗  {path}  [{exc}]")

    # 4 — Delete successfully-downloaded files from Supabase
    if downloaded:
        print(f"\nDeleting {len(downloaded)} archived file(s) from Supabase …")
        deleted:      list[str] = []
        failed_del:   list[str] = []

        # Supabase storage delete accepts a list of paths
        CHUNK = 50   # stay under payload size limits
        for i in range(0, len(downloaded), CHUNK):
            chunk = downloaded[i : i + CHUNK]
            try:
                db.storage.from_(BUCKET).remove(chunk)
                deleted.extend(chunk)
            except Exception as exc:
                # Try one-by-one to isolate failures
                for p in chunk:
                    try:
                        db.storage.from_(BUCKET).remove([p])
                        deleted.append(p)
                    except Exception as exc2:
                        failed_del.append(p)
                        print(f"  ✗ delete failed: {p}  [{exc2}]")

        print(f"  Deleted : {len(deleted)}")
        if failed_del:
            print(f"  Failed  : {len(failed_del)}  (files kept in Supabase for safety)")

    # 5 — Summary
    print("\n" + "─" * 56)
    print("Archive complete.")
    print(f"  Archived & removed : {len(downloaded)}")
    print(f"  Download failures  : {len(failed_dl)}")
    print(f"  Archive location   : {ARCHIVE_ROOT}")
    print("─" * 56)

    if failed_dl:
        print("\n⚠  Some downloads failed — those files were NOT deleted from Supabase.")
        sys.exit(1)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Archive DTR snapshots older than N days from Supabase to local storage."
    )
    parser.add_argument(
        "--days", type=int, default=DEFAULT_RETAIN,
        help=f"Retain files this many days in Supabase (default: {DEFAULT_RETAIN})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="List files that would be archived without downloading or deleting.",
    )
    args = parser.parse_args()
    run(retain_days=args.days, dry_run=args.dry_run)
