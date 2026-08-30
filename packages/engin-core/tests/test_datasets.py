"""Tests for D12 dataset acquisition.

**No test here touches the network.** The fetch path is exercised against
``file://`` URLs over temporary files, which runs the real code — checksum,
manifest, refusal — without depending on a third party being up. A test suite
that downloads is a test suite that fails for reasons unrelated to the change
being tested.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from engin_core.datasets import (
    REGISTRY,
    Dataset,
    DatasetFile,
    License,
    available,
    cache_dir,
    describe,
    fetch,
    manifest_for,
    validate_registry,
)

PERMISSIVE = License(
    spdx="CC0-1.0",
    url="https://creativecommons.org/publicdomain/zero/1.0/",
    commercial_use=True,
    derivatives_allowed=True,
    redistributable=True,
)
RESTRICTIVE = License(
    spdx="CC-BY-NC-ND-4.0",
    url="https://creativecommons.org/licenses/by-nc-nd/4.0/",
    commercial_use=False,
    derivatives_allowed=False,
    redistributable=False,
)


@pytest.fixture
def local_dataset(tmp_path, monkeypatch):
    """Register a fetchable dataset served from a local file."""
    payload = tmp_path / "runs.csv"
    payload.write_text("run_id,titer\nR00,30.0\n")
    import hashlib

    digest = hashlib.sha256(payload.read_bytes()).hexdigest()

    ds = Dataset(
        name="local-fixture",
        description="A local file standing in for a real download.",
        homepage="https://example.invalid/fixture",
        citation="No citation; test fixture.",
        license=PERMISSIVE,
        tier=3,
        files=[DatasetFile(url=payload.as_uri(), sha256=digest, description="runs")],
    )
    monkeypatch.setitem(REGISTRY, "local-fixture", ds)
    return ds, digest


# ------------------------------------------------------------------ the licence gate


def test_noncommercial_dataset_is_refused_by_default():
    """The D12 rule, as a mechanism rather than a convention."""
    with pytest.raises(PermissionError) as excinfo:
        fetch("indpensim")
    message = str(excinfo.value)
    assert "CC-BY-NC-ND-4.0" in message
    assert "Apache-2.0" in message, "the refusal must say *why*, not just refuse"
    assert "accept_noncommercial=True" in message, "and name the deliberate override"


def test_refusal_precedes_the_missing_url_error():
    """Licence is checked before fetchability, so the reason reported is the real one."""
    with pytest.raises(PermissionError):
        fetch("indpensim", accept_noncommercial=False)


def test_override_reaches_the_next_failure_rather_than_downloading():
    """indpensim has no verified URLs, so consenting gets a different, honest error."""
    with pytest.raises(ValueError, match="no verified download URLs"):
        fetch("indpensim", accept_noncommercial=True)


def test_nothing_in_the_package_sets_the_override():
    """If Engin ever calls fetch() with accept_noncommercial=True, D12 has been lost."""
    src = Path(__file__).resolve().parents[1] / "src" / "engin_core"
    offenders = [
        p.name
        for p in src.rglob("*.py")
        if "accept_noncommercial=True" in p.read_text() and p.name != "datasets.py"
    ]
    assert not offenders, f"these modules bypass the D12 licence gate: {offenders}"


# ----------------------------------------------------------------------- fetching


def test_fetch_writes_the_file_and_a_provenance_manifest(local_dataset, tmp_path):
    ds, digest = local_dataset
    dest = tmp_path / "out"
    (path,) = fetch("local-fixture", dest=dest)

    assert path.exists()
    record = manifest_for(path)
    assert record.dataset == "local-fixture"
    assert record.sha256 == digest
    assert record.checksum_verified
    assert record.license_spdx == "CC0-1.0"
    assert record.fetched_utc.endswith("+00:00"), "timestamps are UTC and unambiguous"


def test_manifest_is_machine_readable_json(local_dataset, tmp_path):
    fetch("local-fixture", dest=tmp_path / "out")
    manifest = next((tmp_path / "out").glob("*.provenance.json"))
    loaded = json.loads(manifest.read_text())
    assert {"dataset", "url", "sha256", "fetched_utc", "license_spdx", "citation"} <= set(loaded)


def test_manifest_records_the_licence_that_governs_the_file(local_dataset, tmp_path):
    """The fetched file is not Apache-2.0, and the manifest has to say so."""
    (path,) = fetch("local-fixture", dest=tmp_path / "out")
    assert "Apache-2.0" in manifest_for(path).engin_note


def test_md5_mismatch_is_caught_too(tmp_path, monkeypatch):
    payload = tmp_path / "wrong.csv"
    payload.write_text("not what was promised")
    ds = Dataset(
        name="bad-md5",
        description="d",
        homepage="https://example.invalid",
        citation="c",
        license=PERMISSIVE,
        tier=3,
        files=[DatasetFile(url=payload.as_uri(), md5="0" * 32)],
    )
    monkeypatch.setitem(REGISTRY, "bad-md5", ds)
    dest = tmp_path / "out"
    with pytest.raises(OSError, match="md5 mismatch"):
        fetch("bad-md5", dest=dest)
    assert not (dest / "wrong.csv").exists()


def test_checksum_mismatch_removes_the_file_and_explains(tmp_path, monkeypatch):
    payload = tmp_path / "bad.csv"
    payload.write_text("not what was promised")
    ds = Dataset(
        name="bad-checksum",
        description="d",
        homepage="https://example.invalid",
        citation="c",
        license=PERMISSIVE,
        tier=3,
        files=[DatasetFile(url=payload.as_uri(), sha256="0" * 64)],
    )
    monkeypatch.setitem(REGISTRY, "bad-checksum", ds)

    dest = tmp_path / "out"
    with pytest.raises(OSError, match="sha256 mismatch"):
        fetch("bad-checksum", dest=dest)
    assert not (dest / "bad.csv").exists(), "a file that failed verification must not survive"


def test_second_fetch_is_a_no_op_unless_forced(local_dataset, tmp_path):
    dest = tmp_path / "out"
    (first,) = fetch("local-fixture", dest=dest)
    stamp = first.stat().st_mtime_ns
    (again,) = fetch("local-fixture", dest=dest)
    assert again.stat().st_mtime_ns == stamp


def test_a_corrupt_cached_file_is_not_returned_as_verified(local_dataset, tmp_path):
    """The cache-hit branch must check the digest, not just the path (#296).

    ``urlretrieve`` streamed into the destination path itself, so an interrupted
    download left a truncated file exactly where the next call short-circuits.
    """
    _ds, digest = local_dataset
    dest = tmp_path / "out"
    dest.mkdir()
    truncated = dest / "runs.csv"
    truncated.write_text("run_id,tit")  # a real prefix of the real payload

    (path,) = fetch("local-fixture", dest=dest)

    observed = hashlib.sha256(path.read_bytes()).hexdigest()
    assert observed == digest, "fetch returned a file that does not match the registry"


def test_a_stale_cache_is_replaced_rather_than_raising(local_dataset, tmp_path):
    """A bad cache is a miss, not a publisher error -- so re-download, do not raise."""
    _ds, digest = local_dataset
    dest = tmp_path / "out"
    dest.mkdir()
    (dest / "runs.csv").write_text("entirely different bytes")

    (path,) = fetch("local-fixture", dest=dest)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


def test_an_interrupted_download_leaves_nothing_at_the_destination(
    local_dataset, tmp_path, monkeypatch
):
    """A partial transfer must not be reachable under the real name (#296)."""
    import engin_core.datasets as datasets_module

    attempts = []

    def die(*_args, **_kwargs):
        attempts.append(1)
        raise TimeoutError("connection dropped mid-stream")

    monkeypatch.setattr(datasets_module.shutil, "copyfileobj", die)
    monkeypatch.setattr(datasets_module.time, "sleep", lambda _s: None)

    dest = tmp_path / "out"
    with pytest.raises(TimeoutError), pytest.warns(UserWarning, match="retrying in"):
        fetch("local-fixture", dest=dest)

    # A dropped stream is transient, so it is retried -- and still gives up (#296).
    assert len(attempts) == datasets_module._MAX_ATTEMPTS

    assert not (dest / "runs.csv").exists(), "a partial download must not survive"
    assert list(dest.glob("*")) == [], f"temp files left behind: {list(dest.glob('*'))}"


def test_verify_cache_can_be_switched_off(local_dataset, tmp_path):
    """The digest re-read is the default, not a mandate -- 227 MB is a real cost."""
    dest = tmp_path / "out"
    dest.mkdir()
    (dest / "runs.csv").write_text("wrong")

    (path,) = fetch("local-fixture", dest=dest, verify_cache=False)
    assert path.read_text() == "wrong", "verify_cache=False must skip the check"


def test_manifest_for_explains_an_unknown_file(tmp_path):
    stray = tmp_path / "mystery.csv"
    stray.write_text("x")
    with pytest.raises(FileNotFoundError, match="not fetched by"):
        manifest_for(stray)


# ----------------------------------------------------------------------- registry


def test_registry_is_internally_consistent():
    assert validate_registry() == []


def test_every_fetchable_file_has_a_checksum():
    """A download without a checksum cannot be verified, which defeats provenance."""
    for name, ds in REGISTRY.items():
        for spec in ds.files:
            assert spec.sha256 or spec.md5, f"{name}: {spec.url} has neither sha256 nor md5"


def test_every_registered_dataset_names_its_licence_and_source():
    """An entry that cannot say where it came from is worse than no entry."""
    for name, ds in REGISTRY.items():
        assert ds.license.spdx, f"{name}: no SPDX licence"
        assert ds.homepage.startswith("http"), f"{name}: no resolvable homepage"
        assert len(ds.citation) > 40, f"{name}: citation too thin to credit the authors"


def test_md5_only_entries_are_accepted():
    """Zenodo publishes md5. Demanding sha256 would force a full download to
    produce a digest nobody else can check against -- weaker provenance, not
    stronger. See DatasetFile's docstring."""
    md5_only = [n for n, ds in REGISTRY.items() if any(f.md5 and not f.sha256 for f in ds.files)]
    assert md5_only, "expected at least one entry relying on the publisher's md5"
    assert validate_registry() == []


def test_zenodo_style_urls_declare_a_filename():
    """Zenodo file endpoints end in /content, so the URL basename is not a name."""
    for name, ds in REGISTRY.items():
        for spec in ds.files:
            if spec.url.rstrip("/").endswith("/content"):
                assert spec.filename, f"{name}: {spec.url} would download as 'content'"


def test_unknown_dataset_names_the_alternatives():
    with pytest.raises(KeyError, match="available"):
        fetch("nope")


def test_describe_states_downstream_usability(capsys):
    text = describe("indpensim")
    assert "NOT usable by commercial downstream users" in text
    assert "CC-BY-NC-ND-4.0" in text


def test_available_is_sorted():
    assert available() == sorted(available())


def test_cache_dir_is_overridable_and_outside_the_repo(monkeypatch, tmp_path):
    monkeypatch.setenv("ENGIN_DATA_DIR", str(tmp_path / "elsewhere"))
    assert cache_dir() == tmp_path / "elsewhere"

    monkeypatch.delenv("ENGIN_DATA_DIR")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    resolved = cache_dir().resolve()
    repo = Path(__file__).resolve().parents[3]
    assert repo not in resolved.parents, "fetched data must never land inside the repository"


def test_the_registry_and_the_published_table_agree():
    """`docs/benchmarks.md` must list exactly the registered datasets (#280).

    The published table listed three of five for as long as five existed, and the
    two it omitted were the JBEI campaigns `docs/limitations.md` cites as narrowing
    the tier-4 absence claim -- so the page understated the project's own evidence.

    Nothing checked it. `render.py` regenerates `references.md` from the register,
    and `check_claims.py` verifies citations resolve, but this table is hand-written
    prose about code and had no equivalent. A page whose subject is what has and has
    not been measured is a bad place to keep a stale list.
    """
    docs = Path(__file__).resolve().parents[3] / "docs" / "benchmarks.md"
    if not docs.exists():  # pragma: no cover - the suite also runs from a wheel
        pytest.skip("docs/ not present in this checkout")

    section = docs.read_text().split("## What is registered", 1)
    assert len(section) == 2, "benchmarks.md lost its 'What is registered' section"
    # the table ends at the first blank line after the rows
    listed = set(re.findall(r"^\| `([a-z0-9-]+)` \|", section[1], re.M))

    assert listed == set(REGISTRY), (
        f"registry and published table disagree.\n"
        f"  in REGISTRY, not documented: {sorted(set(REGISTRY) - listed)}\n"
        f"  documented, not in REGISTRY: {sorted(listed - set(REGISTRY))}"
    )


def test_the_published_table_states_each_dataset_s_real_tier():
    """A wrong tier is worse than a missing row: D12 is graded on it."""
    docs = Path(__file__).resolve().parents[3] / "docs" / "benchmarks.md"
    if not docs.exists():  # pragma: no cover
        pytest.skip("docs/ not present in this checkout")

    section = docs.read_text().split("## What is registered", 1)[1]
    for name, tier in re.findall(r"^\| `([a-z0-9-]+)` \| [^|]+ \| (\d) \|", section, re.M):
        assert int(tier) == REGISTRY[name].tier, f"{name}: table says tier {tier}"


# ------------------------------------------------------------------ retry (#296)
#
# `pooch` was declined here on a measurement -- 8 net-new packages against a
# 12-package install, for retry alone -- so the policy is ours and has to be
# tested like it. The dangerous direction is retrying what should not be retried:
# a 404 behind three backoffs is a worse error than a 404.


def _flaky(datasets_module, monkeypatch, error, succeed_after):
    """Make the first ``succeed_after`` stream attempts raise ``error``."""
    attempts = []
    real = datasets_module.shutil.copyfileobj

    def maybe(*args, **kwargs):
        attempts.append(1)
        if len(attempts) <= succeed_after:
            raise error
        return real(*args, **kwargs)

    monkeypatch.setattr(datasets_module.shutil, "copyfileobj", maybe)
    monkeypatch.setattr(datasets_module.time, "sleep", lambda _s: None)
    return attempts


def test_a_transient_failure_is_retried_and_can_succeed(local_dataset, tmp_path, monkeypatch):
    """The case the retry exists for: one hiccup, then the file arrives."""
    import engin_core.datasets as datasets_module

    _ds, digest = local_dataset
    attempts = _flaky(datasets_module, monkeypatch, TimeoutError("dropped"), succeed_after=1)

    dest = tmp_path / "out"
    with pytest.warns(UserWarning, match="retrying in"):
        (path,) = fetch("local-fixture", dest=dest)

    assert len(attempts) == 2
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest


def test_a_404_is_not_retried(local_dataset, tmp_path, monkeypatch):
    """`HTTPError` subclasses `URLError`, so testing the parent first would retry this."""
    import urllib.error

    import engin_core.datasets as datasets_module

    not_found = urllib.error.HTTPError("u", 404, "Not Found", {}, None)
    attempts = _flaky(datasets_module, monkeypatch, not_found, succeed_after=99)

    with pytest.raises(urllib.error.HTTPError):
        fetch("local-fixture", dest=tmp_path / "out")

    assert len(attempts) == 1, "a 404 is an answer, not a hiccup"


def test_a_503_is_retried(local_dataset, tmp_path, monkeypatch):
    import urllib.error

    import engin_core.datasets as datasets_module

    unavailable = urllib.error.HTTPError("u", 503, "Unavailable", {}, None)
    attempts = _flaky(datasets_module, monkeypatch, unavailable, succeed_after=1)

    with pytest.warns(UserWarning, match="retrying in"):
        fetch("local-fixture", dest=tmp_path / "out")

    assert len(attempts) == 2


def test_no_attempt_leaves_a_temp_file_behind(local_dataset, tmp_path, monkeypatch):
    """Each retry must start clean, or a later attempt streams onto a partial one."""
    import engin_core.datasets as datasets_module

    _flaky(datasets_module, monkeypatch, TimeoutError("dropped"), succeed_after=99)

    dest = tmp_path / "out"
    with pytest.raises(TimeoutError), pytest.warns(UserWarning):
        fetch("local-fixture", dest=dest)

    assert list(dest.glob("*")) == [], f"temp files left behind: {list(dest.glob('*'))}"


def test_retry_after_is_honoured_but_capped(monkeypatch):
    """A rate-limited server may say when to return; a broken one must not hang us."""
    import urllib.error

    import engin_core.datasets as datasets_module

    def error(value):
        return urllib.error.HTTPError("u", 429, "Too Many", {"Retry-After": value}, None)

    assert datasets_module._retry_after(error("2")) == 2.0
    assert datasets_module._retry_after(error("99999")) == datasets_module._RETRY_AFTER_CAP_SECONDS
    assert datasets_module._retry_after(error("-1")) is None
    assert datasets_module._retry_after(error("Wed, 21 Oct 2026 07:28:00 GMT")) is None
    assert datasets_module._retry_after(urllib.error.HTTPError("u", 429, "x", {}, None)) is None
