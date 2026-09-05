#!/usr/bin/env python3
"""Claim the ``engin-*`` distribution names on PyPI with honest placeholder releases.

Why this script exists
----------------------
PyPI has **no prefix or namespace reservation**. Publishing ``engin-core`` does nothing
for ``engin-protein``: each name is created by uploading a distribution under that exact
name, and until then anyone may take it. `PEP 752 <https://peps.python.org/pep-0752/>`_
specifies namespace grants and is accepted, but `PEP 755
<https://peps.python.org/pep-0755/>`_ — the PyPI policy that would govern them — is still
draft, and PyPI's Simple API is still at version 1.4 rather than the 1.5 the feature
requires. So: six names, six uploads.

Why placeholders rather than the real ``0.1.0``
-----------------------------------------------
The packages are real and their code is public, but the project is not ready to make the
promises a release makes: ``D24`` gates any visibility push, and the API-stability policy
(``D14``) attaches to a published version. A ``0.0.1.dev0`` marker claims the name without
claiming readiness.

**A ``.dev`` marker does not stop anyone getting the stub, and this docstring claimed it
did until 2026-08-29 (#315).** pip excludes pre-releases *only when some other candidate
matches*; with a lone ``0.0.1.dev0`` on the index there is nothing else, so the fallback
admits it and ``pip install engin-core`` succeeds. Measured with ``packaging``, which is
the filtering pip uses:

    >>> SpecifierSet("").filter([Version("0.0.1.dev0")])
    [<Version('0.0.1.dev0')>]
    >>> SpecifierSet("").filter([Version("0.0.1.dev0"), Version("1.0.0")])
    [<Version('1.0.0')>]

So a user gets an empty stub rather than "no matching distribution", which is the more
confusing outcome and is why ``docs/install.md``, ``docs/index.md`` and ``GOVERNANCE.md``
all warn about it. Those pages were right and this file was wrong -- including in the
README it uploads, so the false claim was published on PyPI.

This is deliberately not name-squatting, and the metadata is written so a reviewer can see
that: every placeholder points at the repository where the real code already lives, and
names the release that will replace it.

Usage
-----
    python scripts/pypi/reserve_names.py            # build + check, upload nothing
    python scripts/pypi/reserve_names.py --upload   # build + check + twine upload

``--upload`` shells out to ``twine``, which reads credentials from the environment or
``~/.pypirc``. This script never handles a token itself.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACKAGES = REPO / "packages"
PLACEHOLDER_VERSION = "0.0.1.dev0"
REPO_URL = "https://github.com/enginbio/engin-suite"

#: Documents that tell a reader whether Engin is installable. This prose has
#: disagreed with the index **five** times -- four where the index moved and the
#: prose did not (#269), and once the other way, where six documents said
#: ``pip install`` gave you nothing after ``0.1.1`` had shipped (#368). The second
#: direction is the more misleading one: a reader concludes the project is broken
#: rather than unpublished.
_CLAIM_ROOTS = ("README.md", "GOVERNANCE.md", "DECISIONS.md", "CONTRIBUTING.md")

#: Phrases that assert Engin is *not* installable. Deliberately a short, literal
#: list rather than anything clever: validated against `main` immediately before
#: #368, where it catches four of the six documents that correction had to fix, at
#: the exact lines, and produces no hits on the tree after it.
_NOT_RELEASED = re.compile(
    r"not (?:yet )?on PyPI"
    r"|not released on PyPI"
    r"|has not been released"
    r"|empty stub"
    r"|installs nothing"
    r"|fetches nothing",
    re.IGNORECASE,
)

#: A corrected page often *quotes* the claim it withdrew, and that quotation is
#: the opposite of the defect. Same line-scoped escape hatch the evidence checks
#: use, and using it is a visible act in the diff.
_CLAIM_OPT_OUT = re.compile(r"<!--\s*pypi-status-ok\b[^>]*-->")


def _documents_denying_release() -> list[tuple[str, int, str]]:
    """Published lines asserting Engin is not installable, with their locations."""
    paths = [p for p in (REPO / "docs").rglob("*.md") if "_build" not in p.parts]
    paths += [REPO / name for name in _CLAIM_ROOTS]
    found = []
    for path in sorted(paths):
        if not path.exists():
            continue
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if _NOT_RELEASED.search(line) and not _CLAIM_OPT_OUT.search(line):
                found.append((str(path.relative_to(REPO)), number, line.strip()))
    return found


PYPROJECT = """\
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{name}"
version = "{version}"
description = "Name reservation for {name} - the real package lives in the engin-suite repository."
readme = "README.md"
requires-python = ">=3.10"
license = "Apache-2.0"
authors = [{{ name = "EnginBio" }}]
keywords = ["bioprocess", "fermentation", "uncertainty", "techno-economic"]
classifiers = [
    "Development Status :: 1 - Planning",
    "Intended Audience :: Science/Research",
    "Programming Language :: Python :: 3",
    "Topic :: Scientific/Engineering :: Bio-Informatics",
]

[project.urls]
Homepage = "https://docs.engin.bio"
Repository = "{repo_url}"
Issues = "{repo_url}/issues"

[tool.setuptools]
packages = []
"""

README = """\
# {name}

**This is a name reservation, not a usable release.**

`{name}` is part of [engin-suite]({repo_url}), an Apache-2.0 toolkit for bioprocess
forecasting under calibrated uncertainty, coupled to cost. The code for this package is
real and public — it is in the repository — but no usable version has been published to
PyPI yet.

This `{version}` marker exists so the name is held by the project rather than by whoever
takes it first. It contains no modules and does nothing if installed.

**`pip install {name}` will select this stub.** A pre-release is normally skipped, but
only when some other release matches -- and there is no other release, so it is chosen
anyway. Expect an install that succeeds and gives you nothing.

## What to do instead

Install from the repository:

```bash
pip install "{name} @ git+{repo_url}#subdirectory=packages/{name}"
```

## When this gets replaced

By a real release, once the project has published real-data calibration coverage, its
out-of-distribution failure mode, and one non-synthetic worked example. Those gates are
tracked in the repository. Until then, treat anything on PyPI under this name as a
placeholder.
"""


def discover() -> list[str]:
    """Read distribution names from the monorepo, so this cannot drift from reality."""
    names = []
    for pyproject in sorted(PACKAGES.glob("*/pyproject.toml")):
        match = re.search(r'^name = "([^"]+)"', pyproject.read_text(), re.M)
        if match:
            names.append(match.group(1))
    return names


def build_one(name: str, outdir: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp) / name
        project.mkdir()
        (project / "pyproject.toml").write_text(
            PYPROJECT.format(name=name, version=PLACEHOLDER_VERSION, repo_url=REPO_URL)
        )
        (project / "README.md").write_text(
            README.format(name=name, version=PLACEHOLDER_VERSION, repo_url=REPO_URL)
        )
        subprocess.run(
            [sys.executable, "-m", "build", "--sdist", "--outdir", str(outdir), str(project)],
            check=True,
            capture_output=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--upload", action="store_true", help="twine upload after checking")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="check the live index against the names in this repo and exit; builds nothing",
    )
    parser.add_argument("--outdir", default=str(REPO / "dist-placeholders"))
    args = parser.parse_args()

    names = discover()
    if not names:
        print("No packages discovered under packages/ - refusing to guess.", file=sys.stderr)
        return 1

    if args.verify:
        # Read-only, unauthenticated, and deliberately reachable without building
        # anything. The point is that a document claiming an index state can be
        # checked against the index rather than re-read by a human for a fifth time.
        print(f"Verifying {len(names)} names against PyPI:")
        if not _report(names, verify_only=True):
            return 1

        # The index half passing is not the check. Every name being held while a
        # document still says otherwise is exactly the state #368 shipped, and
        # `_report` cannot see it -- it compares the index to `pyproject.toml` and
        # then tells a human the documents "may say so".
        denials = _documents_denying_release()
        if denials:
            print(
                f"\nAll names are held, but {len(denials)} published line(s) still say "
                "Engin is not installable:"
            )
            for path, number, text in denials:
                print(f"  {path}:{number}\n      {text[:96]}")
            print(
                "\nUpdate them, or mark a line that is quoting a withdrawn claim with"
                "\n  <!-- pypi-status-ok: why this line is correct -->"
            )
            return 1
        print("No published line contradicts that.")
        return 0

    outdir = Path(args.outdir)
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True)

    print(f"Claiming {len(names)} names at {PLACEHOLDER_VERSION}:")
    for name in names:
        print(f"  - {name}")
        build_one(name, outdir)

    artifacts = sorted(str(p) for p in outdir.glob("*.tar.gz"))
    subprocess.run([sys.executable, "-m", "twine", "check", *artifacts], check=True)

    if not args.upload:
        print("\nBuilt and checked. Nothing uploaded. To publish:")
        print(f"  python {Path(__file__).relative_to(REPO)} --upload")
        return 0

    print("\nUploading to PyPI. twine reads credentials from the environment or ~/.pypirc.")
    # --skip-existing makes this resumable. PyPI rate-limits *new project
    # creation*, and on 2026-08-13 the first real run got four of six names
    # before a 429; without this flag, re-running fails on the four that already
    # exist and the remaining two stay unclaimed. A partial upload is the
    # expected case here, not an edge one.
    #
    # Note the failure mode that run exposed: twine printed a 100% progress bar
    # for a fifth distribution that PyPI then rejected. **The progress bar is not
    # a receipt** -- verify against the index, which is what `--verify` does.
    subprocess.run(
        [sys.executable, "-m", "twine", "upload", "--skip-existing", *artifacts],
        check=True,
    )
    print()
    return 0 if _report(names) else 1


def _report(names: list[str], verify_only: bool = False) -> bool:
    """Check each name against PyPI itself and say which are actually claimed.

    **A 404 and an unreachable index are different answers**, and this used to
    conflate them: an `OSError` was appended to ``missing``, so a network blip
    read as "the name is unclaimed". That is tolerable when a human is watching
    an upload and fatal when the result gates CI, because the check would fail
    for a reason that has nothing to do with the thing it is checking. Only a
    definite HTTP error now counts as unclaimed; an unreachable index is reported
    as unknown and, under ``--verify``, does not fail the run.
    """
    import json
    import urllib.error
    import urllib.request

    held, missing, unknown = [], [], []
    for name in names:
        try:
            with urllib.request.urlopen(f"https://pypi.org/pypi/{name}/json", timeout=20) as r:
                held.append((name, json.load(r)["info"]["version"]))
        except urllib.error.HTTPError:  # the index answered: no such project
            missing.append(name)
        except OSError as exc:  # we never got an answer
            unknown.append((name, exc))

    for name, version in held:
        print(f"  claimed   {name} {version}")
    for name in missing:
        print(f"  MISSING   {name}")
    for name, exc in unknown:
        print(f"  unknown   {name} (could not reach the index: {exc})")

    if unknown and verify_only and not missing:
        print(
            f"\n{len(unknown)} name(s) could not be checked. Not failing: an "
            "unreachable index is not evidence that a name is unclaimed."
        )
        return True

    if missing:
        print(
            f"\n{len(missing)} name(s) not claimed. PyPI rate-limits new project "
            "creation, so wait and re-run:\n"
            f"  python {Path(__file__).relative_to(REPO)} --upload"
        )
        return False
    if verify_only:
        print(f"\nAll {len(held)} names held.")
    else:
        print("\nAll names held. Update GOVERNANCE.md 5.4 to say so.")
    return True


if __name__ == "__main__":
    raise SystemExit(main())
