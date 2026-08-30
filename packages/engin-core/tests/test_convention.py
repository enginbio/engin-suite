"""Tests for the D11 convention over xarray and pandas.

Skipped wholesale where the optional ``io`` extra is not installed, so the light
path stays installable without xarray/pandas.
"""

from __future__ import annotations

import numpy as np
import pytest

xr = pytest.importorskip("xarray", reason="requires the [io] extra")
pd = pytest.importorskip("pandas", reason="requires the [io] extra")

from engin_core import convention  # noqa: E402
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


# ------------------------------------------------------- MIFE/MIFD alignment (D11)


def test_every_channel_has_a_mife_verdict():
    """A channel with no entry is an unexamined one, which is what D11 forbids.

    The register carried `standard_impl: none exists` for this convention until
    2026-08-13, when MIFE/MIFD turned out to be published and this project's own
    D11 already named it. The mapping is what keeps that from being re-asserted:
    adding a channel now forces a decision about whether the standard covers it.
    """
    assert set(convention.MIFE_SLOTS) == set(convention.CHANNELS)


def test_every_unmapped_channel_states_why():
    """`None` must be a documented gap, never a shrug."""
    unmapped = {k for k, v in convention.MIFE_SLOTS.items() if v is None}
    assert unmapped == set(convention.MIFE_GAPS)
    assert all(len(reason) > 20 for reason in convention.MIFE_GAPS.values())


def test_controlled_conditions_defer_to_mife_naming():
    """Where MIFE has a slot, we map to it rather than inventing a name."""
    assert convention.mife_slot("feed_rate") == "feed_flow_rate"
    assert convention.mife_slot("agitation") == "agitation_rate"
    assert convention.mife_slot("do") == "pO2"


def test_the_gaps_are_the_derived_rates():
    """The boundary between the two layers, asserted rather than described.

    MIFE specifies controlled conditions; this convention adds measured and
    derived series. These four are exactly the channels a real industrial export
    forced into the registry and that a simulator never needed.
    """
    for derived in ("our", "cer", "rq", "kla"):
        assert convention.mife_slot(derived) is None


def test_an_unregistered_channel_is_an_error_not_a_gap():
    with pytest.raises(KeyError):
        convention.mife_slot("not_a_channel")


# ------------------------------------------------------------------------ roles
#
# Added with convention 0.2 (ADR 0009). The concrete failure these exist for: run
# against a real DASGIP export, the loader mapped `XCO2 1.Out` -- a controller
# output -- onto the measured `offgas_co2` channel. With no role concept that is a
# mapping the types permit and no evidence string can describe.


def test_role_defaults_to_measured():
    """Absent role means measured, which is what every 0.1 dataset already was."""
    assert convention.role_of(xr.DataArray([1.0])) == convention.DEFAULT_ROLE
    assert convention.DEFAULT_ROLE == "measured"


def test_a_dataset_written_before_roles_existed_still_conforms():
    """0.2 is additive: 0.1 data needs no migration."""
    report = validate_timeseries(conforming_ds())
    assert report.ok, report.summary()
    assert report.findings == []


def test_registered_channel_name_at_a_non_measured_role_is_an_error():
    """The XCO2 1.Out case. CHANNELS defines measured quantities, so a registered
    name at another role claims a meaning that does not apply."""
    ds = conforming_ds()
    ds["titer"].attrs["role"] = "output"
    report = validate_timeseries(ds)
    assert "channel-name-at-non-measured-role" in _codes(report)
    assert not report.ok


def test_the_same_variable_at_measured_role_is_clean():
    """The check must be about the role, not about the attribute being present."""
    ds = conforming_ds()
    ds["titer"].attrs["role"] = "measured"
    report = validate_timeseries(ds)
    assert "channel-name-at-non-measured-role" not in _codes(report)
    assert report.ok, report.summary()


def test_an_unregistered_name_may_hold_any_role():
    """A vendor column that is genuinely an actuator signal is representable --
    that is the point. It is only claiming a *channel* name that is refused."""
    ds = conforming_ds()
    ds["xco2_1_out"] = (("run", "time"), np.zeros_like(ds["titer"].values), {"units": "%"})
    ds["xco2_1_out"].attrs["role"] = "output"
    report = validate_timeseries(ds)
    assert "channel-name-at-non-measured-role" not in _codes(report)


def test_an_unknown_role_is_reported_not_swallowed():
    ds = conforming_ds()
    ds["titer"].attrs["role"] = "controller_output"  # plausible, not the vocabulary
    report = validate_timeseries(ds)
    assert "unknown-role" in _codes(report)


def test_every_role_carries_a_description():
    """The vocabulary is small enough that an undocumented member is an oversight."""
    assert set(convention.ROLES) == {"measured", "setpoint", "output"}
    assert all(v.strip() for v in convention.ROLES.values())


# ------------------------------------------------------- run groupings (0.3, #310)


def _grouped_dataset(n_runs: int = 6):
    import numpy as np
    import xarray as xr

    ds = xr.Dataset(
        {"titer": (("run", "time"), np.zeros((n_runs, 3)))},
        coords={
            "run": np.arange(n_runs),
            "time": np.arange(3),
            "run_day": ("run", [i // 2 for i in range(n_runs)]),
        },
    )
    ds["titer"].attrs["units"] = "g/L"
    return ds


def test_a_coordinate_can_say_what_runs_share():
    ds = _grouped_dataset()
    ds.coords["run_day"].attrs[convention.GROUPING_ATTR] = "run_day"
    codes = {f.code for f in convention.validate_timeseries(ds).findings}
    assert "groupings-declared" in codes
    assert "no-grouping-declared" not in codes


def test_an_unknown_grouping_is_an_error_and_not_also_a_silence():
    """A bad value must not simultaneously report as no value at all."""
    ds = _grouped_dataset()
    ds.coords["run_day"].attrs[convention.GROUPING_ATTR] = "whenever"
    findings = convention.validate_timeseries(ds).findings
    codes = [f.code for f in findings]
    assert "unknown-grouping" in codes
    assert "no-grouping-declared" not in codes, (
        "a declared-but-invalid grouping is a different fault from none declared"
    )
    assert any(f.level == "error" for f in findings if f.code == "unknown-grouping")


def test_absence_is_recorded_when_asked_and_silent_otherwise():
    """The point of #310, without breaking the convention's additive promise.

    An unconditional note would make every pre-0.3 dataset report a finding, which
    is exactly what ``test_a_dataset_written_before_roles_existed_still_conforms``
    asserts must not happen. So the note is opt-in.
    """
    ds = _grouped_dataset()
    default_codes = {f.code for f in convention.validate_timeseries(ds).findings}
    assert "no-grouping-declared" not in default_codes, "silent by default"
    findings = convention.validate_timeseries(ds, note_missing_grouping=True).findings
    note = next(f for f in findings if f.code == "no-grouping-declared")
    assert note.level == "info", "absence is a note, not a failure -- it is often true"
    assert "run-day" in note.message


def test_grouping_has_no_default_unlike_role():
    """``role`` defaults because every legacy column *was* measured. This cannot."""
    ds = _grouped_dataset()
    assert convention.grouping_of(ds.coords["run_day"]) is None
    assert convention.role_of(ds["titer"]) == convention.DEFAULT_ROLE


def test_the_convention_version_records_the_addition():
    assert convention.CONVENTION_VERSION == "0.3"
    assert set(convention.GROUPINGS) == {
        "run_day",
        "lot",
        "lineage",
        "operator",
        "position",
        "session",
    }
