"""Fail when the committed execution cache no longer matches what the code produces.

``.github/workflows/docs.yml`` already greps a build log for ``Executing notebook``
and fails if it finds one. That catches a cache **miss** -- the cache not covering
a page it should. It cannot catch a cache **hit on stale content**, which is the
more dangerous case and the one that actually happened.

jupyter-cache keys on a content hash of the *notebook source*. A cell whose text
never changes keeps hitting forever, even after the code it imports has moved
underneath it. Nothing re-executes, nothing logs, and the site publishes output
the current code does not produce.

Both cases are on the record here:

- ``docs/guides/data-formats.md`` -- **stale hit**. The cell reads ``CHANNELS``
  and prints it. Its text has not changed since it was written;
  ``engin_core.convention`` gained four gas-transfer channels on 2026-08-11. The
  published page listed 13 of 17 for five days with every check green (#155).
- ``docs/methods/out-of-distribution.md`` -- **accurate hit**. A fresh run
  reproduced the cached output exactly, on every row of both tables (#169).

The check has to tell those apart, and the only way to do that is to run the
cells. So: build once from an empty cache, then compare the freshly executed
outputs against the committed ones, cell by cell.

Usage::

    # after a cold build has repopulated docs/.jupyter_cache
    python scripts/evidence/check_cache_fresh.py COMMITTED_CACHE_DIR FRESH_CACHE_DIR

Exit status is 0 when every commonly-keyed record matches, 1 otherwise.

**Why this is not a per-pull-request check.** A cold build executes every page and
takes minutes. The drift it detects is code moving away from a cached output over
time, which is a calendar problem rather than a per-change one, so it runs on a
schedule. Nothing here needs to block a merge; it needs to be noticed within days.
"""

from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path
from typing import Any

try:
    from jupyter_cache import get_cache
except ImportError:  # pragma: no cover - only hit outside the docs env
    print("jupyter-cache is not installed; run this in the docs environment", file=sys.stderr)
    raise SystemExit(2) from None


# A warning raised inside a notebook cell is reported against the kernel's
# throwaway source file, whose directory embeds the kernel PID:
#
#     /var/.../T/ipykernel_84079/815839376.py:10: UserWarning: ...
#
# That number changes on every execution, so a page whose cells emit any warning
# would differ from its own cache on every run. This check was written before any
# page did (#182); #195 added a small-calibration-set warning to
# conformal-calibration.md and made the difference real, so the next scheduled
# run would have failed on the PID rather than on drift. Found while adding the
# calibration figure in #230.
_KERNEL_TMP = re.compile(r"ipykernel_\d+[/\\]\d+\.py")


def _normalise(text: str) -> str:
    """Drop output that changes between identical executions.

    Only volatile *identifiers* are removed, never numbers a reader would act on.
    Widening this is how a freshness check quietly stops checking, so anything
    added here needs the same justification as the line above.
    """
    return _KERNEL_TMP.sub("ipykernel_<pid>/<cell>.py", text)


def _outputs(nb: Any) -> list[tuple[str, str]]:
    """(source, rendered-output) for every code cell that produced something.

    Outputs are flattened to text because that is what a reader sees. Comparing
    the raw output dicts would flag execution counts and metadata that carry no
    meaning for whether the published page is correct.
    """
    pairs = []
    for cell in nb.cells:
        if cell.get("cell_type") != "code":
            continue
        rendered = []
        for out in cell.get("outputs", []):
            if "text" in out:
                rendered.append("".join(out["text"]))
            elif "data" in out:
                data = out["data"]
                rendered.append("".join(data.get("text/plain", "")))
        pairs.append(("".join(cell.get("source", "")), _normalise("".join(rendered))))
    return pairs


def _records(path: Path) -> dict[str, Any]:
    """Cache records by hashkey.

    The hashkey is a content hash of the notebook source, so a record present in
    both caches under the same key is the *same cell text* -- which is exactly the
    comparison this check wants: same input, possibly different output.
    """
    cache = get_cache(str(path))
    return {rec.hashkey: cache.get_cache_bundle(rec.pk).nb for rec in cache.list_cache_records()}


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    committed, fresh = (Path(a) for a in args)
    for p in (committed, fresh):
        if not p.exists():
            print(f"no such cache directory: {p}", file=sys.stderr)
            return 2

    old, new = _records(committed), _records(fresh)
    shared = old.keys() & new.keys()

    stale: list[str] = []
    for key in sorted(shared):
        # strict=True on purpose: a shared hashkey means identical cell source, so
        # a length mismatch would mean the hash no longer identifies what we think.
        paired = zip(_outputs(old[key]), _outputs(new[key]), strict=True)
        for i, ((src, was), (_, now)) in enumerate(paired):
            if was.strip() == now.strip():
                continue
            first = next((line for line in src.splitlines() if line.strip()), "")
            # Show the actual differing lines. Printing the first line of each
            # side is useless when the outputs share a prefix, which is the
            # common case -- a cell that gained or lost rows part-way down.
            diff = difflib.unified_diff(
                was.strip().splitlines(),
                now.strip().splitlines(),
                fromfile="committed",
                tofile="fresh",
                lineterm="",
                n=1,
            )
            body = "\n".join(f"    {line}" for line in list(diff)[:14])
            stale.append(f"  {key[:10]} cell {i}  {first[:64]}\n{body}")

    # A key in one cache and not the other is not staleness. It means a page
    # gained or lost executed cells, which shows up as an ordinary diff in the
    # pull request that did it -- reported, not failed on.
    if only_committed := old.keys() - new.keys():
        print(f"note: {len(only_committed)} committed record(s) no longer produced by a build")
        print("      (a page stopped executing cells; evict them if that was deliberate)")
    if only_fresh := new.keys() - old.keys():
        print(f"note: {len(only_fresh)} record(s) produced by the build but not committed")
        print("      (rebuild the docs and commit docs/.jupyter_cache)")

    if stale:
        print(f"\n{len(stale)} cached cell output(s) do not match a fresh run:\n")
        print("\n".join(stale))
        print(
            "\nThe committed cache is serving output the current code does not produce.\n"
            "Rebuild the docs and commit the refreshed docs/.jupyter_cache. See #166."
        )
        return 1

    print(f"execution cache is current: {len(shared)} record(s) reproduce exactly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
