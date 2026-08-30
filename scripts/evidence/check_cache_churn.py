"""Fail a change whose only edit to the execution cache is a timestamp (#294).

    python scripts/evidence/check_cache_churn.py BASE.db HEAD.db  # compare two versions
    python scripts/evidence/check_cache_churn.py --report BASE.db HEAD.db   # say it, exit 0
    python scripts/evidence/check_cache_churn.py --local          # restore a churned cache
    python scripts/evidence/check_cache_churn.py --local --report # ...say it, change nothing

## Why this exists

``docs/.jupyter_cache/global.db`` is tracked deliberately: Read the Docs renders
example outputs from it instead of executing them (``D20``), so an absent or stale
cache means RTD quietly starts executing on shared builders. It has to stay in git.

But **every** ``sphinx-build`` rewrites it, including builds that execute nothing.
jupyter-cache stamps ``nbcache.accessed`` on a cache *hit*, so reading the cache is
enough to dirty the file. Measured on 2026-08-30, on a build logging zero
``Executing notebook`` lines:

    settings:  0 rows | changed columns: none
    nbproject: 5 rows | changed columns: none
    nbcache:   5 rows | changed columns: {'accessed': 1}

One column, one row, and nothing else -- while git sees 28 KB of changed binary.

Two costs, and the second is the one that bites. It rides along on ``git add -A``
into pull requests that touched no notebook. And several agents work this
repository concurrently (``CLAUDE.md``), so **a binary file that every docs build
rewrites is a merge conflict whose only resolution is picking a side arbitrarily**.

## What this does not do

It does not stop the write. jupyter-cache owns that timestamp and patching it
would mean carrying a fork of somebody else's cache layer.

It also is not a ``.gitattributes`` clean filter, which was the other candidate in
#294. A filter has to be configured by every contributor and silently does nothing
for anyone who has not configured it -- the failure mode is a checkout that looks
fine and is not. This needs nothing installed: CI compares the two committed
versions, and ``--local`` is a convenience that uses only git and the standard
library.

## The rule

A delta confined to ``nbcache.accessed`` is churn and should not be committed.
Anything else -- a new or removed row, a changed ``data``, ``hashkey`` or
``created`` -- is a real cache update and must be committed, because that is the
cache doing its job.
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = Path("docs/.jupyter_cache/global.db")

# Tables jupyter-cache maintains. Read explicitly rather than globbing
# sqlite_master so that a schema change upstream surfaces as a mismatch here
# instead of being silently skipped.
TABLES = ("settings", "nbproject", "nbcache")

# The one column a mere cache *read* is allowed to move.
TIMESTAMP_COLUMNS = {("nbcache", "accessed")}

TIMESTAMP_ONLY, SUBSTANTIVE, IDENTICAL = "timestamp-only", "substantive", "identical"


def _read(path: Path) -> dict[str, list[dict[str, object]]]:
    """Every row of every known table, ordered by primary key."""
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        return {t: [dict(r) for r in con.execute(f"select * from {t} order by pk")] for t in TABLES}
    finally:
        con.close()


def compare(base: Path, head: Path) -> tuple[str, set[tuple[str, str]]]:
    """Classify the delta between two cache databases.

    Returns the verdict and the set of ``(table, column)`` pairs that differ. A
    structural difference -- a missing table, a differing row count, a changed
    primary key -- is reported as substantive with an empty column set, because
    the point of the check is to be conservative about what it calls churn.
    """
    try:
        a, b = _read(base), _read(head)
    except sqlite3.Error:
        # Unreadable or unexpected schema. Never the check's business to guess.
        return SUBSTANTIVE, set()

    changed: set[tuple[str, str]] = set()
    for table in TABLES:
        rows_a, rows_b = a[table], b[table]
        if len(rows_a) != len(rows_b):
            return SUBSTANTIVE, set()
        for ra, rb in zip(rows_a, rows_b, strict=True):
            if ra.keys() != rb.keys() or ra.get("pk") != rb.get("pk"):
                return SUBSTANTIVE, set()
            changed |= {(table, k) for k in ra if ra[k] != rb[k]}

    if not changed:
        return IDENTICAL, changed
    if changed <= TIMESTAMP_COLUMNS:
        return TIMESTAMP_ONLY, changed
    return SUBSTANTIVE, changed


def _git_show(ref: str, path: Path, into: Path) -> bool:
    """Write ``ref:path`` to ``into``. False when the ref has no such file."""
    proc = subprocess.run(
        ["git", "show", f"{ref}:{path.as_posix()}"],
        cwd=ROOT,
        capture_output=True,
    )
    if proc.returncode != 0:
        return False
    into.write_bytes(proc.stdout)
    return True


def _describe(changed: set[tuple[str, str]]) -> str:
    return ", ".join(f"{t}.{c}" for t, c in sorted(changed)) or "(structural)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="BASE.db HEAD.db")
    parser.add_argument(
        "--local",
        action="store_true",
        help="compare the working tree against HEAD and restore it if the delta is churn",
    )
    parser.add_argument(
        "--report", action="store_true", help="describe the delta and exit 0 regardless"
    )
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory() as tmp:
        if args.local:
            if args.paths:
                parser.error("--local takes no positional paths")
            head = ROOT / CACHE
            if not head.exists():
                print(f"{CACHE} does not exist; nothing to check")
                return 0
            base = Path(tmp) / "head.db"
            if not _git_show("HEAD", CACHE, base):
                print(f"{CACHE} is not committed at HEAD; nothing to compare against")
                return 0
        else:
            if len(args.paths) != 2:
                parser.error("give two database paths, or --local")
            base, head = args.paths

        verdict, changed = compare(base, head)

        if verdict == IDENTICAL:
            print("execution cache unchanged")
            return 0

        if verdict == SUBSTANTIVE:
            print(f"execution cache genuinely updated ({_describe(changed)}) -- commit it")
            return 0

        print(f"execution cache delta is timestamps only ({_describe(changed)})")

        if args.report:
            return 0

        if args.local:
            shutil.copyfile(base, head)
            print(f"restored {CACHE} -- a build read the cache without changing it")
            return 0

        print()
        print(f"::error::{CACHE} changed, but the only difference is the")
        print("::error::`accessed` timestamp jupyter-cache stamps on a cache *hit*. No notebook")
        print("::error::was executed and no output moved, so this is 28 KB of binary churn that")
        print("::error::will conflict with every other branch touching the docs (#294). Drop it:")
        print("::error::  git checkout origin/main -- docs/.jupyter_cache/global.db")
        print("::error::Locally, `python scripts/evidence/check_cache_churn.py --local` does that")
        print("::error::for you, and leaves a genuine cache update alone.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
