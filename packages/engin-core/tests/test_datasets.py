"""Tests for D12 dataset acquisition.

**No test here touches the network.** The fetch path is exercised against
``file://`` URLs over temporary files, which runs the real code — checksum,
manifest, refusal — without depending on a third party being up. A test suite
that downloads is a test suite that fails for reasons unrelated to the change
being tested.
"""

from __future__ import annotations

import json
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
    with pytest.raises(OSError, match="checksum mismatch"):
        fetch("bad-checksum", dest=dest)
    assert not (dest / "bad.csv").exists(), "a file that failed verification must not survive"


def test_second_fetch_is_a_no_op_unless_forced(local_dataset, tmp_path):
    dest = tmp_path / "out"
    (first,) = fetch("local-fixture", dest=dest)
    stamp = first.stat().st_mtime_ns
    (again,) = fetch("local-fixture", dest=dest)
    assert again.stat().st_mtime_ns == stamp


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
            assert spec.sha256 is not None, f"{name}: {spec.url} has no sha256"


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
