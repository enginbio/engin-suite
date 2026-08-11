"""Tests for the D11 convention over xarray and pandas.

Skipped wholesale where the optional ``io`` extra is not installed, so the light
path stays installable without xarray/pandas.
"""

from __future__ import annotations

import numpy as np
import pytest

xr = pytest.importorskip("xarray", reason="requires the [io] extra")
pd = pytest.importorskip("pandas", reason="requires the [io] extra")

from engin_core.convention import (  # noqa: E402
    CONVENTION_ATTR,
    CONVENTION_VERSION,
    ConventionReport,
    register_domain_units,
    stamp,
    validate_endpoints,
    validate_timeseries,
)


def _codes(report: ConventionReport) -> set[str]:
    return {f.code for f in report.findings}


def conforming_ds(n_run: int = 3, n_time: int = 12) -> xr.Dataset:
    rng = np.random.default_rng(0)
    return xr.Dataset(
        data_vars={
            "titer": (("run", "time"), rng.random((n_run, n_time)) * 40, {"units": "g/L"}),
            "biomass": (("run", "time"), rng.random((n_run, n_time)) * 20, {"units": "g/L"}),
            "mu": (("run", "time"), rng.random((n_run, n_time)) * 0.35, {"units": "1/h"}),
        },
        coords={
            "run": ("run", [f"R{i:02d}" for i in range(n_run)]),
            "time": ("time", np.arange(float(n_time)), {"units": "h"}),
        },
        attrs={CONVENTION_ATTR: CONVENTION_VERSION},
    )


# ------------------------------------------------------------------ time series


def test_conforming_dataset_reports_no_errors():
    report = validate_timeseries(conforming_ds())
    assert report.ok, report.summary()
    assert report.findings == []


def test_missing_units_is_an_error_and_names_the_expected_unit():
    ds = conforming_ds()
    del ds["titer"].attrs["units"]
    report = validate_timeseries(ds)
    assert not report.ok
    (finding,) = [f for f in report.findings if f.code == "missing-units"]
    assert finding.target == "titer"
    assert "g/L" in finding.suggestion


def test_unparseable_units_are_caught():
    ds = conforming_ds()
    ds["titer"].attrs["units"] = "grams per litre-ish"
    report = validate_timeseries(ds)
    assert not report.ok
    assert "unparseable-units" in _codes(report)


def test_wrong_but_valid_units_warn_rather_than_error():
    """mg/L parses fine and is a real unit -- it is simply not what we record in."""
    ds = conforming_ds()
    ds["titer"].attrs["units"] = "mg/L"
    report = validate_timeseries(ds)
    assert report.ok, "a convertible unit must not be an error"
    assert "unexpected-units" in _codes(report)


def test_missing_dims_are_errors():
    ds = conforming_ds().isel(run=0, drop=True)
    report = validate_timeseries(ds)
    assert not report.ok
    assert "missing-run-dim" in _codes(report)


def test_time_without_a_coordinate_is_an_error():
    ds = conforming_ds().drop_vars("time")
    report = validate_timeseries(ds)
    assert not report.ok
    assert "time-not-a-coordinate" in _codes(report)


def test_time_without_units_warns():
    ds = conforming_ds()
    del ds["time"].attrs["units"]
    report = validate_timeseries(ds)
    assert report.ok
    assert "time-missing-units" in _codes(report)


def test_unregistered_channel_is_carried_not_rejected():
    """The registry is a recommendation. An unknown channel must not fail validation."""
    ds = conforming_ds()
    ds["fluorescence"] = (("run", "time"), np.zeros((3, 12)), {"units": "1"})
    report = validate_timeseries(ds)
    assert report.ok
    assert "unregistered-channel" in _codes(report)


def test_missing_convention_attr_warns_and_stamp_fixes_it():
    ds = conforming_ds()
    del ds.attrs[CONVENTION_ATTR]
    assert "missing-convention-attr" in _codes(validate_timeseries(ds))

    stamped = stamp(ds)
    assert stamped.attrs[CONVENTION_ATTR] == CONVENTION_VERSION
    assert CONVENTION_ATTR not in ds.attrs, "stamp must not mutate its input"
    assert "missing-convention-attr" not in _codes(validate_timeseries(stamped))


def test_empty_dataset_is_an_error():
    report = validate_timeseries(xr.Dataset())
    assert not report.ok
    assert {"missing-run-dim", "missing-time-dim", "no-data-variables"} <= _codes(report)


def test_every_finding_carries_an_actionable_suggestion():
    ds = conforming_ds()
    del ds["titer"].attrs["units"]
    ds["mu"].attrs["units"] = "not-a-unit"
    report = validate_timeseries(ds)
    assert report.findings
    for f in report.findings:
        assert f.suggestion.strip(), f"{f.code} has no suggestion"


# ------------------------------------------------------------------- endpoints


def doe_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "run_id": ["R00", "R01", "R02"],
            "feed_rate": [0.1, 0.2, 0.3],
            "titer": [30.0, 35.0, 28.0],
        }
    )


def test_conforming_endpoint_table_reports_no_errors():
    report = validate_endpoints(doe_frame(), units={"titer": "g/L", "feed_rate": "L/h"})
    assert report.ok, report.summary()
    assert report.findings == []


def test_missing_run_column_is_an_error():
    df = doe_frame().drop(columns=["run_id"])
    report = validate_endpoints(df, units={"titer": "g/L"})
    assert not report.ok
    assert "missing-run-column" in _codes(report)


def test_duplicate_run_ids_warn():
    df = doe_frame()
    df.loc[2, "run_id"] = "R00"
    report = validate_endpoints(df, units={"titer": "g/L", "feed_rate": "L/h"})
    assert report.ok
    assert "duplicate-run-ids" in _codes(report)


def test_units_in_frame_attrs_warn_because_csv_drops_them():
    """Pinned because it is a property of pandas, not a choice: if this stops being
    true, the convention can simplify and this test should be updated, not deleted."""
    df = doe_frame()
    df.attrs["units"] = {"titer": "g/L", "feed_rate": "L/h"}
    report = validate_endpoints(df)
    assert "units-in-frame-attrs" in _codes(report)


def test_pandas_still_drops_attrs_on_csv_round_trip(tmp_path):
    df = doe_frame()
    df.attrs["units"] = {"titer": "g/L"}
    path = tmp_path / "doe.csv"
    df.to_csv(path, index=False)
    assert pd.read_csv(path).attrs == {}, (
        "pandas now preserves .attrs through CSV; the convention's sidecar rule and "
        "the units-in-frame-attrs finding should be revisited rather than this test relaxed"
    )


def test_units_for_absent_columns_warn():
    report = validate_endpoints(
        doe_frame(), units={"titer": "g/L", "feed_rate": "L/h", "tighter": "g/L"}
    )
    assert "units-for-absent-columns" in _codes(report)


# ----------------------------------------------------------------------- units


def test_vvm_is_registered_as_a_domain_unit():
    """pint does not ship vvm, and fermentation data is full of it."""
    pint = pytest.importorskip("pint")
    assert register_domain_units()
    reg = pint.get_application_registry()
    assert reg.Unit("vvm").dimensionality == reg.Unit("1/min").dimensionality


def test_airflow_in_vvm_validates():
    pytest.importorskip("pint")
    ds = conforming_ds()
    ds["airflow"] = (("run", "time"), np.ones((3, 12)), {"units": "vvm"})
    report = validate_timeseries(ds)
    assert report.ok, report.summary()


def test_report_summary_counts_by_level():
    ds = conforming_ds()
    del ds["titer"].attrs["units"]
    summary = validate_timeseries(ds).summary()
    assert "does not conform" in summary
    assert CONVENTION_VERSION in summary
