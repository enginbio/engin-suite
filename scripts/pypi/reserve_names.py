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

**That reasoning was correct and its premise expired the week it was written.**
``0.1.1`` was published to all six names on **2026-08-22**, seven days before #315 --
so by then a real release *did* match, the fallback no longer applied, and
``pip install engin-core`` resolved to 0.1.1 rather than to a stub. The specifier
semantics above are still right; the "there is no other release" they rested on is
not. Corrected 2026-09-05 (#368).

**Both halves of that are worth keeping in view**, because this file has now been
wrong in each direction: first about pre-release selection, then about whether
anything had been released at all. The mechanism was verified and the premise was
not, which is the cheaper mistake to make and the harder one to notice.

The historical note below is why ``docs/install.md``, ``docs/index.md`` and
``GOVERNANCE.md`` used to warn about the stub -- they were right at the time and are
now corrected too. It is kept because it explains what a reader will still find if
they look at the ``0.0.1.dev0`` artifacts, which remain on the index beneath the real
releases. Including in the
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
real and public — it is in the repository — and a usable version **is** published: see
the project's latest release rather than this `{version}` placeholder.

This `{version}` marker exists so the name is held by the project rather than by whoever
takes it first. It contains no modules and does nothing if installed.

**It is no longer what `pip install {name}` gives you.** A real release is published,
so pip resolves to that and skips this pre-release marker. This stub remains on the
index beneath it, and this description is what you are reading if you navigated to
the `{version}` artifact directly.

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
        return 0 if _report(names, verify_only=True) else 1

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
        print(f"\nAll {len(held)} names held. The documents may say so.")
    else:
        print("\nAll names held. Update GOVERNANCE.md 5.4 to say so.")
    return True


if __name__ == "__main__":
    raise SystemExit(main())
