"""Real-data acquisition: fetch datasets, never ship them, record what you got.

Implements **D12**. Validation on Engin's own simulator demonstrates that the code
runs; it is not evidence the method works. Getting past that needs real
fermentation data, and this module is how a user obtains it — by **fetching**.

## The binding rule, and why it is enforced in code

`D12` states it plainly: **ship loaders that fetch, never data that ships.** The
reason is licensing rather than repository size. Several of the most useful public
fermentation datasets are NonCommercial or NoDerivatives, and this project is
Apache-2.0 — its users are commercial by assumption. Vendoring such a dataset, or
deriving a shipped default from one, would quietly hand every downstream user a
licence problem they never agreed to.

That is easy to state and easy to forget under deadline, so it is a mechanism
here rather than a convention: :func:`fetch` **refuses** a dataset whose licence
forbids commercial use unless the caller passes ``accept_noncommercial=True`` and
thereby takes the decision knowingly. Nothing in this package calls it that way.

## What "provenance manifest" means here

Not a catalogue entry — a record of what actually happened. :func:`fetch` writes a
JSON manifest beside each downloaded file recording the source URL, the SHA-256
observed at download time, whether it matched what the registry expected, the
licence, the citation, and a UTC timestamp. A result computed from that file can
then be traced to a specific byte sequence obtained on a specific day, which is
what makes a benchmark reproducible by someone else (`D15`).

## On the registry being small

It has one entry. That is not a stub: adding a dataset requires verifying its
licence and checksum, and an unverified entry is worse than an absent one because
it looks authoritative. :data:`REGISTRY` is easy to extend and
:func:`validate_registry` states what an entry must satisfy.
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

__all__ = [
    "REGISTRY",
    "Dataset",
    "DatasetFile",
    "License",
    "ProvenanceRecord",
    "available",
    "cache_dir",
    "describe",
    "fetch",
    "validate_registry",
]

Tier = Literal[1, 2, 3, 4, 5]
"""`D12` validation tiers: 1 own simulator, 2 independent simulator, 3 real but
out-of-domain, 4 in-domain literature DoE, 5 partner campaign."""


class License(BaseModel):
    """A dataset's licence, reduced to the three questions that decide usability.

    ``commercial_use`` is the one with teeth. Engin is Apache-2.0, so its users
    are commercial by assumption; a dataset that forbids commercial use cannot
    become part of a default path, however convenient it is.
    """

    spdx: str
    """SPDX identifier where one exists, e.g. ``CC-BY-NC-ND-4.0``."""

    url: str
    commercial_use: bool
    derivatives_allowed: bool
    redistributable: bool
    """Whether the data may be re-hosted. Even ``True`` does not mean this project
    will: `D12` says fetch, not ship, regardless."""

    @property
    def usable_by_downstream(self) -> bool:
        """Can an Apache-2.0 consumer of Engin use this without a licence problem?"""
        return self.commercial_use and self.derivatives_allowed


class DatasetFile(BaseModel):
    """One downloadable artefact, with the checksum that makes it verifiable."""

    url: str
    sha256: str | None = None
    """Expected digest. ``None`` means nobody has verified one yet — the download
    still records what it observed, and says the expectation was absent."""

    size_bytes: int | None = None
    description: str = ""


class Dataset(BaseModel):
    """A real dataset, described well enough to decide whether to fetch it."""

    name: str
    description: str
    homepage: str
    citation: str
    license: License
    tier: Tier
    files: list[DatasetFile] = Field(default_factory=list)
    notes: str = ""

    @property
    def fetchable(self) -> bool:
        return bool(self.files)


REGISTRY: dict[str, Dataset] = {
    "indpensim": Dataset(
        name="indpensim",
        description=(
            "Industrial-scale penicillin fermentation simulation (100,000 L), 100 batches "
            "with process and Raman spectroscopy measurements, validated against historical "
            "industrial data."
        ),
        homepage="http://www.industrialpenicillinsimulation.com/",
        citation=(
            "Goldrick et al., 'Modern day monitoring and control challenges outlined on an "
            "industrial-scale benchmark fermentation process', Computers & Chemical "
            "Engineering, 2019."
        ),
        license=License(
            spdx="CC-BY-NC-ND-4.0",
            url="https://creativecommons.org/licenses/by-nc-nd/4.0/",
            commercial_use=False,
            derivatives_allowed=False,
            redistributable=False,
        ),
        tier=2,
        files=[],
        notes=(
            "The canonical example of why D12's rule exists. It is the most cited public "
            "fermentation dataset and it is NonCommercial *and* NoDerivatives, so it cannot "
            "back any default path in an Apache-2.0 project: a downstream commercial user "
            "would inherit a restriction they never accepted. Also worth being precise about "
            "what it is -- a simulation validated against industrial data, not measurements "
            "from a real plant, which places it at D12 tier 2 rather than tier 3. No direct "
            "download URLs are recorded because none has been verified with a checksum, and "
            "an unverified URL in a registry is worse than an absent one."
        ),
    ),
}
"""Curated real datasets. One entry, deliberately -- see the module docstring."""


class ProvenanceRecord(BaseModel):
    """What was fetched, from where, and whether it was what we expected.

    Written beside every downloaded file. This is the artefact that lets a third
    party reproduce a benchmark rather than take its word for it.
    """

    dataset: str
    url: str
    path: str
    sha256: str
    sha256_expected: str | None = None
    size_bytes: int
    fetched_utc: str
    license_spdx: str
    citation: str
    engin_note: str = (
        "Fetched by engin_core.datasets, not redistributed with Engin (D12). "
        "The licence above governs this file; Engin's Apache-2.0 licence does not."
    )

    @property
    def checksum_verified(self) -> bool:
        return self.sha256_expected is not None and self.sha256 == self.sha256_expected


def cache_dir() -> Path:
    """Where fetched data lands.

    Honours ``ENGIN_DATA_DIR``, else an XDG-style cache. Deliberately outside the
    repository so a fetch can never become a commit.
    """
    override = os.environ.get("ENGIN_DATA_DIR")
    if override:
        return Path(override).expanduser()
    base = os.environ.get("XDG_CACHE_HOME") or (Path.home() / ".cache")
    return Path(base).expanduser() / "engin" / "datasets"


def available() -> list[str]:
    """Registry keys, sorted."""
    return sorted(REGISTRY)


def describe(name: str) -> str:
    """A human-readable summary, including whether it can be used downstream."""
    ds = _get(name)
    lic = ds.license
    verdict = (
        "usable by commercial downstream users"
        if lic.usable_by_downstream
        else "NOT usable by commercial downstream users"
    )
    lines = [
        f"{ds.name} -- {ds.description}",
        f"  homepage : {ds.homepage}",
        f"  licence  : {lic.spdx} ({verdict})",
        f"  D12 tier : {ds.tier}",
        f"  citation : {ds.citation}",
        f"  fetchable: {'yes' if ds.fetchable else 'no verified download URLs recorded'}",
    ]
    if ds.notes:
        lines.append(f"  notes    : {ds.notes}")
    return "\n".join(lines)


def _get(name: str) -> Dataset:
    try:
        return REGISTRY[name]
    except KeyError:
        raise KeyError(f"unknown dataset {name!r}; available: {available()}") from None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(
    name: str,
    dest: Path | None = None,
    *,
    accept_noncommercial: bool = False,
    force: bool = False,
) -> list[Path]:
    """Download a dataset and write a provenance manifest beside each file.

    Raises :class:`PermissionError` when the licence forbids commercial use and
    ``accept_noncommercial`` is not set. That is not paternalism about your own
    research — it is that a *default* path built on such a dataset would pass the
    restriction to every downstream user of an Apache-2.0 library. Setting the
    flag records that you decided knowingly; nothing in Engin sets it for you.

    Raises :class:`ValueError` when no verified download URL is recorded, rather
    than guessing one.
    """
    ds = _get(name)
    if not ds.license.usable_by_downstream and not accept_noncommercial:
        raise PermissionError(
            f"{name!r} is licensed {ds.license.spdx}, which does not permit commercial use "
            "and/or derivatives. Engin is Apache-2.0, so its users are commercial by "
            "assumption, and a default path built on this data would hand them a licence "
            "restriction they never accepted (D12).\n"
            "  You may still fetch it for your own evaluation by passing "
            "accept_noncommercial=True, which records that the decision was yours.\n"
            f"  Licence: {ds.license.url}"
        )

    if not ds.fetchable:
        raise ValueError(
            f"{name!r} has no verified download URLs recorded, so there is nothing to "
            "fetch. Add a DatasetFile with a sha256 you have checked yourself; an "
            f"unverified URL is worse than none. See {ds.homepage}"
        )

    target = Path(dest) if dest is not None else cache_dir() / name
    target.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    for spec in ds.files:
        filename = spec.url.rsplit("/", 1)[-1] or f"{name}.dat"
        path = target / filename
        if path.exists() and not force:
            written.append(path)
            continue
        urllib.request.urlretrieve(spec.url, path)  # noqa: S310 - registry URLs only
        digest = _sha256(path)
        record = ProvenanceRecord(
            dataset=ds.name,
            url=spec.url,
            path=str(path),
            sha256=digest,
            sha256_expected=spec.sha256,
            size_bytes=path.stat().st_size,
            fetched_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            license_spdx=ds.license.spdx,
            citation=ds.citation,
        )
        if spec.sha256 is not None and digest != spec.sha256:
            path.unlink(missing_ok=True)
            raise OSError(
                f"checksum mismatch for {spec.url}\n"
                f"  expected {spec.sha256}\n  observed {digest}\n"
                "The file was removed. Either the source changed or the download was "
                "corrupted; do not benchmark against it until this is resolved."
            )
        manifest = path.with_suffix(path.suffix + ".provenance.json")
        manifest.write_text(record.model_dump_json(indent=2) + "\n")
        written.append(path)
    return written


def validate_registry() -> list[str]:
    """Return the registry's integrity problems; empty means clean.

    Exists so the rules are executable rather than aspirational — see the test
    module, which fails the build on any finding.
    """
    problems: list[str] = []
    for key, ds in REGISTRY.items():
        if key != ds.name:
            problems.append(f"{key!r}: key does not match dataset name {ds.name!r}")
        for field in ("description", "homepage", "citation"):
            if not getattr(ds, field).strip():
                problems.append(f"{key!r}: empty {field}")
        if not ds.license.spdx.strip():
            problems.append(f"{key!r}: licence has no SPDX identifier")
        if not ds.license.url.startswith(("http://", "https://")):
            problems.append(f"{key!r}: licence url is not a URL")
        for spec in ds.files:
            if spec.sha256 is None:
                problems.append(
                    f"{key!r}: file {spec.url} has no sha256 -- a fetchable file without a "
                    "checksum cannot be verified, which defeats the provenance record"
                )
    return problems


def manifest_for(path: Path) -> ProvenanceRecord:
    """Read back the provenance record written beside a fetched file."""
    manifest = Path(str(path) + ".provenance.json")
    if not manifest.exists():
        raise FileNotFoundError(
            f"no provenance manifest beside {path}. It was not fetched by "
            "engin_core.datasets, so where it came from is unknown -- which is exactly "
            "what the manifest exists to prevent."
        )
    return ProvenanceRecord.model_validate(json.loads(manifest.read_text()))
