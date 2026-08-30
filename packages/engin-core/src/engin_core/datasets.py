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
JSON manifest beside each downloaded file recording the source URL, both digests
observed at download time, whether they matched what the registry expected, the
licence, the citation, and a UTC timestamp. A result computed from that file can
then be traced to a specific byte sequence obtained on a specific day, which is
what makes a benchmark reproducible by someone else (`D15`).

## The bar for an entry

Every dataset here has had its licence checked against the publisher, and carries
a checksum that is either the publisher's own or was verified against it. An
unverified entry is worse than an absent one, because it looks authoritative;
:func:`validate_registry` states the rules and the test suite fails the build on
any violation.

Note that **md5 is often the right checksum to record**, which is not the usual
advice — see :class:`DatasetFile` for why publisher-published beats
locally-stronger.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
import urllib.error
import urllib.request
import warnings
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
    """One downloadable artefact, with the checksum that makes it verifiable.

    **Either digest satisfies the registry, and md5 is not the weaker choice
    here.** What provenance needs is a match against the value *the publisher
    published*: that detects a file being swapped, truncated or silently revised.
    A digest computed by whoever added the registry entry proves only that the
    bytes have not changed since *they* downloaded it, which is a weaker claim
    dressed as a stronger algorithm. Zenodo publishes md5, so md5 is often the
    checkable one — and demanding sha256 would force every registrant to
    download the whole artefact (227 MB, for the largest here) to record a digest
    nobody else can check them against.

    Record both where both are known.
    """

    url: str
    sha256: str | None = None
    md5: str | None = None
    """At least one digest is required for a fetchable file — see
    :func:`validate_registry`. Say in ``description`` where the value came from if
    it is not the publisher's."""

    filename: str | None = None
    """What to call the download. Needed more often than it looks — Zenodo's file
    endpoints end in ``/content``, so the URL's last segment is not a name."""

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
    "erythromycin-efp": Dataset(
        name="erythromycin-efp",
        description=(
            "Erythromycin fed-batch fermentation, 406 industrial production batches sampled "
            "hourly (median 126 h per batch, 50,536 rows). 23 process variables: 5 process "
            "conditions, 6 cumulative feeds, 5 physicochemical and 7 biochemical indicators, "
            "including OUR, CER, respiratory quotient and kLa. The documented target is "
            "chemical potency during fermentation."
        ),
        homepage="https://doi.org/10.5281/zenodo.14619074",
        citation=(
            "Erythromycin fermentation process dataset (2025). Zenodo. "
            "doi:10.5281/zenodo.14619074. Historical production data from Yichang HEC "
            "Changjiang Pharmaceutical Co., Ltd, 2022."
        ),
        license=License(
            spdx="CC-BY-4.0",
            url="https://creativecommons.org/licenses/by/4.0/",
            commercial_use=True,
            derivatives_allowed=True,
            redistributable=True,
        ),
        tier=3,
        files=[
            DatasetFile(
                url="https://zenodo.org/api/records/14619074/files/EFP_long.csv/content",
                filename="EFP_long.csv",
                sha256="e432d23998c61db6d35b6f95d54b4c94c17b3d7b85a0117b8526665e5d91cf3e",
                md5="6f65e6af4bc8f5e750414372b8cf81ca",
                size_bytes=8025512,
                description=(
                    "Long format: one row per (batch_id, hour). md5 is Zenodo's published "
                    "value; sha256 was computed locally from a download that matched it."
                ),
            )
        ],
        notes=(
            "The closest public data to Engin's own domain: real, industrial, microbial, "
            "fed-batch, with a product-potency target and a run/time structure that maps "
            "onto the D11 convention almost directly (batch_id -> run, hh -> time in hours). "
            "Two honest caveats. It is *production* data, not designed experiments, so the "
            "process conditions were not varied to explore a design space -- which is why "
            "this is tier 3 and not tier 4.\n\n"
            "COLUMNS: 27 in the CSV -- date, batch_id, hh, then 23 process variables and the "
            "target 'hx'. Only three things about them are sourced, and the rest is not:\n"
            "  * 'hx' is the target, chemical potency during fermentation. The depositors' own "
            "    data_loader.py hard-codes target='hx' in every EFP Dataset class.\n"
            "  * The 23 split into 5 process conditions, 6 cumulative feeds, 5 physicochemical "
            "    indicators and 7 biochemical indicators -- the Zenodo record says so, by count "
            "    and category but NOT by name.\n"
            "  * 'our', 'cer', 'rq' and 'kla' are standard bioprocess abbreviations (oxygen "
            "    uptake rate, carbon evolution rate, respiratory quotient, volumetric mass "
            "    transfer coefficient) and are the only codes readable without a key.\n\n"
            "THE REST ARE STILL UNGLOSSED, and the 2026-08-17 attempt to gloss them failed for "
            "reasons worth recording so nobody repeats it: the source paper (Neurocomputing 657) "
            "is paywalled and no accessible version carries a variable table; the depositors' "
            "data_loader.py defines only the target; and the Zenodo description gives counts "
            "without names. Settling this needs the authors, not another search -- the same "
            "shape of founder task as the ABPDU licence question on #10.\n\n"
            "DO NOT infer them from the codes. They appear to be pinyin initialisms ('phzx' and "
            "'phlx' plausibly online and offline pH, 'mt' plausibly a cumulative-total suffix), "
            "and that reading is unverified. This dataset has already produced four confident "
            "false mappings in engin_core.loaders -- 'our' matched substrate via the substring "
            "'carbonsource' -- so a plausible-looking gloss here would be the same failure with "
            "better handwriting. Exactly the situation engin_core.loaders reports confidence for."
        ),
    ),
    "cho-k1-cultivations": Dataset(
        name="cho-k1-cultivations",
        description=(
            "24 Chinese Hamster Ovary (CHO)-K1 cultivations, 161.5-328.5 h each, in parallel "
            "bioreactors at 0.55-0.8 L working volume: 12 experiments x 2 reactors, nine "
            "batch and three fed-batch. 48 variables -- 38 continuous inline and 10 offline "
            "sampled up to twice daily -- with time-axis-aligned CSVs alongside the raw "
            "tables."
        ),
        homepage="https://doi.org/10.5281/zenodo.20829178",
        citation=(
            "Uhlendorff, S., Fulek, R., Eimler, J., Pein-Hackelbusch, M. and Frahm, B. "
            "Dataset Based on Chinese Hamster Ovary (CHO) Cultivations including Turbidity, "
            "Permittivity, O2 and CO2 Measurements (2026). Zenodo. "
            "doi:10.5281/zenodo.20829178."
        ),
        license=License(
            spdx="CC-BY-4.0",
            url="https://creativecommons.org/licenses/by/4.0/",
            commercial_use=True,
            derivatives_allowed=True,
            redistributable=True,
        ),
        tier=3,
        files=[
            DatasetFile(
                url="https://zenodo.org/api/records/20829178/files/Dataset.zip/content",
                filename="Dataset.zip",
                md5="71b2a35b7df2ed11644ec9f177453772",
                size_bytes=227627771,
                description=(
                    "Zenodo's published md5. No sha256 recorded: computing one would mean "
                    "downloading 227 MB to produce a digest nobody else can check against, "
                    "which is not what verification is for."
                ),
            )
        ],
        notes=(
            "Mammalian rather than microbial, so this is D12 tier 3 in the textbook sense -- "
            "real data, out of domain. That is the point of the tier: it tests whether the "
            "machinery survives real noise, missingness and scale change without pretending "
            "to be evidence about fermentation. The authors state it is intended for "
            "data-driven, mechanistic and hybrid modelling, and the fed-batch subset is the "
            "closest in structure to Engin's simulator."
        ),
    ),
    "jbei-isoprenol-dbtl6": Dataset(
        name="jbei-isoprenol-dbtl6",
        description=(
            "Final cycle (DBTL-6) of a six-round machine-learning-guided campaign raising "
            "isoprenol titer in Pseudomonas putida via multiplexed CRISPRi. Each row is one "
            "assay of one strain: the sgRNA combination is encoded in the line name, and the "
            "response is absolute isoprenol titer in mg/L by GC-FID at 48 h."
        ),
        homepage="https://github.com/JBEI/Isoprenol_CRISPRi",
        citation=(
            "Carruthers, D.N. et al. Automation and machine learning drive rapid optimization "
            "of isoprenol production in Pseudomonas putida. Nature Communications 16 (2025). "
            "doi:10.1038/s41467-025-66304-8. Archived at doi:10.5281/zenodo.17178684."
        ),
        license=License(
            spdx="BSD-3-Clause-LBNL",
            url="https://raw.githubusercontent.com/JBEI/Isoprenol_CRISPRi/main/license.txt",
            commercial_use=True,
            derivatives_allowed=True,
            redistributable=True,
        ),
        tier=3,
        files=[
            DatasetFile(
                url=(
                    "https://raw.githubusercontent.com/JBEI/Isoprenol_CRISPRi/"
                    "6437736ec0eab3eeb00a70ef474f34ea828ad116/"
                    "DBTL%20ART/isoprenol_data/dbtl6_isoprenol.csv"
                ),
                filename="dbtl6_isoprenol.csv",
                sha256="1353e8651c2fbb4728d9ae7bd5f3178cfc6aba685fb0578ddd4917c5fd4f6c45",
                size_bytes=46876,
                description=(
                    "Pinned to commit 6437736 rather than a branch, so the URL cannot move "
                    "under the digest. The publisher does not publish a per-file checksum -- "
                    "the DOI archive is a 660 MB repository zip -- so this sha256 was computed "
                    "locally and proves only that the bytes have not changed since download."
                ),
            )
        ],
        notes=(
            "**Not tier 4, and the reason is the whole point of the distinction.** The designed "
            "variation here is genetic -- sgRNA combinations over gene targets, an ~800,000 "
            "combination space -- not the process conditions Engin takes (feed_rate, "
            "feed_start, Sf, induction_time, S0). It is real, designed, multi-cycle and "
            "reports absolute titers, which is why it is registered; it is not evidence about "
            "the design space this project forecasts over. See #174, where it is the near-miss "
            "that falsifies the absolute-titer half of the tier-4 absence claim.\n\n"
            "**Licence discrepancy worth knowing about**: the Zenodo record states CC-BY-4.0 "
            "while the repository ships a 3-clause BSD (LBNL variant). Both permit commercial "
            "use and derivatives, so the practical answer is the same, but they are not the "
            "same licence and the repository's is the one recorded here."
        ),
    ),
    "jbei-flaviolin-media": Dataset(
        name="jbei-flaviolin-media",
        description=(
            "Five DBTL cycles of medium optimization for flaviolin production in Pseudomonas "
            "putida KT2440: Latin hypercube sampling for the first two cycles, then ART "
            "recommendations. Sixteen media components varied in mM -- including the NaCl term "
            "the study identifies as dominant -- against an OD340 response."
        ),
        homepage="https://github.com/JBEI/Flaviolin_media_opt_C3",
        citation=(
            "Machine learning-led semi-automated medium optimization reveals salt as key for "
            "flaviolin production in Pseudomonas putida. Communications Biology 8 (2025). "
            "doi:10.1038/s42003-025-08039-2."
        ),
        license=License(
            spdx="BSD-3-Clause-LBNL",
            url="https://raw.githubusercontent.com/JBEI/Flaviolin_media_opt_C3/main/license.txt",
            commercial_use=True,
            derivatives_allowed=True,
            redistributable=True,
        ),
        tier=3,
        files=[
            DatasetFile(
                url=(
                    "https://raw.githubusercontent.com/JBEI/Flaviolin_media_opt_C3/"
                    "82f23ffa3dd0dfbe09b7bea1fab8087310fba2b5/"
                    "flaviolin%20yield%20data/DBTL1-5_data.csv"
                ),
                filename="DBTL1-5_data.csv",
                sha256="794a2e4d516c67648ea23ed85576e2e4479e4212fc3bd42d5a9336afbccdb256",
                size_bytes=41936,
                description=(
                    "Pinned to commit 82f23ff. No publisher checksum exists for this file, so "
                    "the sha256 is locally computed and carries the weaker guarantee."
                ),
            )
        ],
        notes=(
            "**The closest thing to tier 4 currently registered, and it misses on one axis.** "
            "The designed variation is media composition, which *is* a process input, across "
            "genuinely multi-cycle campaigns. What it lacks is the response: OD340 is an "
            "absorbance proxy the source itself describes as such, not an absolute titer. So "
            "the tier-4 absence claim in docs/limitations.md survives on the assay alone -- if "
            "a comparable campaign reported g/L, that claim would be false. Registered so the "
            "near-miss is fetchable rather than only described (#174)."
        ),
    ),
}
"""Curated real datasets.

Every entry's licence was checked against the publisher and every checksum is
either the publisher's own or was verified against it. An entry that cannot meet
that bar does not belong here -- see :func:`validate_registry`.
"""


class ProvenanceRecord(BaseModel):
    """What was fetched, from where, and whether it was what we expected.

    Written beside every downloaded file. This is the artefact that lets a third
    party reproduce a benchmark rather than take its word for it.
    """

    dataset: str
    url: str
    path: str
    sha256: str
    md5: str
    sha256_expected: str | None = None
    md5_expected: str | None = None
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
        """True when every declared expectation matched. False if none was declared."""
        checks = [
            (self.sha256_expected, self.sha256),
            (self.md5_expected, self.md5),
        ]
        declared = [(e, o) for e, o in checks if e is not None]
        return bool(declared) and all(e == o for e, o in declared)


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


def _digests(path: Path) -> tuple[str, str]:
    """``(sha256, md5)``, computed in one pass so a large file is read once."""
    sha, md5 = hashlib.sha256(), hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
            md5.update(chunk)
    return sha.hexdigest(), md5.hexdigest()


#: Matching ``engin_pathway.rhea``: a third party is entitled to know who is calling,
#: and a stalled server must not hang the caller forever. ``urlretrieve`` supplied
#: neither -- it takes no timeout at all, so it inherited ``socket.getdefaulttimeout()``,
#: which is ``None``.
_TIMEOUT_SECONDS = 30.0
_USER_AGENT = "engin-core (https://github.com/enginbio/engin-suite)"

#: Retry policy (#296). The alternative considered was adopting ``pooch``, and it
#: was declined on a measurement: into a bare environment ``pooch`` pulls **8**
#: packages -- requests, urllib3, certifi, charset-normalizer, idna, platformdirs,
#: packaging and itself -- none of which any current dependency already provides,
#: against an ``engin-core`` install of 12. A 67% increase in install footprint,
#: for a module whose whole job is getting people to real data, is the exact trade
#: ADR 0002 refuses: "installs in seconds and runs anywhere. That is the adoption
#: path."
#:
#: And it would not have bought much. #299 already took the temp-file-then-verify,
#: the cache re-verification and the timeout; the only remaining gap was retry.
#: ``pooch`` does not do ``Range`` resume either, so resume stays unsolved on both
#: paths. Eight packages against the code below was not a close call.
_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = 1.0

#: Codes worth a second try: request timeout, too-early, rate limit, and the 5xx
#: family a server returns when it is briefly unable. A 404 or a 403 is an answer
#: rather than a hiccup -- retrying it only delays the error the caller needs.
_RETRY_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})

#: A rate-limited server may say when to come back. Honour it, but never sleep
#: longer than the whole retry budget would have taken -- a hostile or broken
#: ``Retry-After`` must not hang the caller, which is the same argument as the
#: timeout above.
_RETRY_AFTER_CAP_SECONDS = 30.0


def _mismatch(spec: DatasetFile, sha: str, md5: str) -> str | None:
    """Describe how ``sha``/``md5`` disagree with ``spec``, or ``None`` if they do not."""
    for algorithm, expected, observed in (
        ("sha256", spec.sha256, sha),
        ("md5", spec.md5, md5),
    ):
        if expected is not None and expected != observed:
            return f"{algorithm} mismatch\n  expected {expected}\n  observed {observed}"
    return None


def _retry_after(error: urllib.error.HTTPError) -> float | None:
    """Seconds a ``Retry-After`` header asks for, when it carries a usable one."""
    raw = error.headers.get("Retry-After") if error.headers is not None else None
    if raw is None:
        return None
    try:
        seconds = float(raw)  # the delta-seconds form; HTTP-date is not honoured
    except ValueError:
        return None
    if seconds < 0:
        return None
    return min(seconds, _RETRY_AFTER_CAP_SECONDS)


def _is_transient(error: BaseException) -> bool:
    """Whether ``error`` is worth trying again.

    ``HTTPError`` is checked first because it *subclasses* ``URLError``: testing the
    parent first would make every 404 look retryable.
    """
    if isinstance(error, urllib.error.HTTPError):
        return error.code in _RETRY_STATUS
    return isinstance(error, urllib.error.URLError | TimeoutError | ConnectionError)


def _download_once(url: str, path: Path) -> Path:
    """Stream ``url`` to a sibling temp file and return it, *unmoved*.

    This used to be :func:`urllib.request.urlretrieve`, which opens the final
    destination directly and streams into it. An interrupted transfer therefore
    left a truncated file at exactly the path :func:`fetch` short-circuits on --
    and nothing removed it, because the cleanup sat on the digest-mismatch branch
    downstream of the exception (#296).

    Returning the temp path unmoved lets the caller verify before publishing the
    name, so a file that fails its checksum never exists under the real name at
    all rather than being deleted after the fact.
    """
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    tmp = path.with_name(f"{path.name}.part-{os.getpid()}")
    try:
        with (
            urllib.request.urlopen(  # noqa: S310 - registry URLs only
                request, timeout=_TIMEOUT_SECONDS
            ) as response,
            tmp.open("wb") as handle,
        ):
            shutil.copyfileobj(response, handle)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return tmp


def _download(url: str, path: Path) -> Path:
    """:func:`_download_once`, retried on a transient failure with backoff.

    Each attempt cleans up its own temp file before the next begins, so a retry
    never streams on top of a partial one. A non-transient error -- a 404, a bad
    digest, anything the caller has to see -- is raised on the first attempt
    rather than delayed behind the backoff.
    """
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return _download_once(url, path)
        except BaseException as error:  # noqa: BLE001 - re-raised below unless transient
            if attempt == _MAX_ATTEMPTS or not _is_transient(error):
                raise
            delay = _BACKOFF_SECONDS * 2 ** (attempt - 1)
            if isinstance(error, urllib.error.HTTPError):
                delay = _retry_after(error) or delay
            warnings.warn(
                f"{url} failed ({type(error).__name__}: {error}); "
                f"retrying in {delay:.1f}s -- attempt {attempt + 1} of {_MAX_ATTEMPTS}",
                stacklevel=2,
            )
            time.sleep(delay)
    raise AssertionError("unreachable: the loop either returns or raises")


def fetch(
    name: str,
    dest: Path | None = None,
    *,
    accept_noncommercial: bool = False,
    verify_cache: bool = True,
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

    **A cached file is checked against the registry before it is returned**, and
    a download is verified before it is given its real name. Until #296 neither
    was true: verification ran only on the download branch, and it ran *after*
    :func:`urllib.request.urlretrieve` had already streamed into the destination
    path — so an interrupted transfer left a truncated file exactly where the
    next call short-circuits, and every later call returned it unchecked.

    Set ``verify_cache=False`` to skip the re-read when you know the cache is
    good and the file is large enough for the hash to cost real time; the
    registry's largest artefact is 227 MB. The default is to check, because the
    failure it prevents is silent — a CSV truncated mid-file parses cleanly and
    simply yields fewer rows.
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
        filename = spec.filename or spec.url.rsplit("/", 1)[-1] or f"{name}.dat"
        path = target / filename
        if path.exists() and not force:
            if not verify_cache:
                written.append(path)
                continue
            problem = _mismatch(spec, *_digests(path))
            if problem is None:
                written.append(path)
                continue
            # A bad cache is a miss, not a publisher error: the usual causes are an
            # interrupted download and a revised registry digest, and both are fixed
            # by fetching again. Say so rather than failing the caller's run.
            warnings.warn(
                f"cached {path} does not match the registry and is being re-downloaded"
                f" -- {problem}",
                UserWarning,
                stacklevel=2,
            )

        staged = _download(spec.url, path)
        sha, md5 = _digests(staged)
        problem = _mismatch(spec, sha, md5)
        if problem is not None:
            staged.unlink(missing_ok=True)
            raise OSError(
                f"{problem.splitlines()[0]} for {spec.url}\n"
                + "\n".join(problem.splitlines()[1:])
                + "\nThe download was discarded and nothing was written. Either the "
                "source changed or the transfer was corrupted; do not benchmark "
                "against it until this is resolved."
            )
        staged.replace(path)
        record = ProvenanceRecord(
            dataset=ds.name,
            url=spec.url,
            path=str(path),
            sha256=sha,
            md5=md5,
            sha256_expected=spec.sha256,
            md5_expected=spec.md5,
            size_bytes=path.stat().st_size,
            fetched_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            license_spdx=ds.license.spdx,
            citation=ds.citation,
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
            if spec.sha256 is None and spec.md5 is None:
                problems.append(
                    f"{key!r}: file {spec.url} has neither sha256 nor md5 -- a fetchable "
                    "file without a checksum cannot be verified, which defeats the "
                    "provenance record"
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
