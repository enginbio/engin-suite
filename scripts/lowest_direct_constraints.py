"""Emit a pip constraints file pinning every declared dependency to its floor.

The packages declare minimum versions (`numpy>=1.24`) rather than pins, which is
correct for libraries -- an application pins, a library states what it needs. But
CI always resolves the *latest* compatible set, so the floors are never exercised
and are effectively untested claims. A user who installs into an older environment
is the one who finds out.

This turns `>=X` into `==X` so a CI job can install the oldest supported set and
run the suites against it.

    python scripts/lowest_direct_constraints.py > constraints-lowest.txt
"""

from __future__ import annotations

import pathlib
import re
import sys

try:  # tomllib is stdlib from 3.11; this runs on the lowest supported Python
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 only
    import tomli as tomllib

# Packages in this repo resolve from the working tree, never from an index.
LOCAL = {
    "engin-core",
    "engin-graph",
    "engin-host",
    "engin-pathway",
    "engin-protein",
    "engin-materials",
    "engin-cultivate",
    "engin-compliance",
}

SPEC = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*>=\s*([0-9][0-9A-Za-z.*+!-]*)\s*$")


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    floors: dict[str, str] = {}
    for pyproject in sorted(root.glob("packages/*/pyproject.toml")):
        data = tomllib.loads(pyproject.read_text())
        project = data.get("project", {})
        deps = list(project.get("dependencies", []))
        for extra in project.get("optional-dependencies", {}).values():
            deps.extend(extra)
        for dep in deps:
            dep = dep.split(";")[0].split("#")[0]
            m = SPEC.match(dep)
            if not m:
                continue
            name, floor = m.group(1), m.group(2)
            if name.lower() in LOCAL:
                continue
            # Keep the highest declared floor: if one package needs a newer
            # minimum than another, that newer one is the real floor.
            prev = floors.get(name)
            if prev is None or _version_key(floor) > _version_key(prev):
                floors[name] = floor

    if not floors:
        print("no floors discovered -- dependency declarations changed shape", file=sys.stderr)
        return 1
    for name in sorted(floors):
        print(f"{name}=={floors[name]}")
    return 0


def _version_key(v: str) -> tuple[int, ...]:
    return tuple(int(p) if p.isdigit() else 0 for p in v.split("."))


if __name__ == "__main__":
    raise SystemExit(main())
