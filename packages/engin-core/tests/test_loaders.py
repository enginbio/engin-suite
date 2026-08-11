"""Tests for the D11 ingest layer.

The property under test throughout is that a messy table produces a *report*,
not an exception. Where a test asserts a confidence number it asserts an
ordering or a threshold, never an exact value -- the score is a heuristic and
pinning its arithmetic would make the tests an obstacle to improving it.
"""

from __future__ import annotations

import pytest

xr = pytest.importorskip("xarray", reason="requires the [io] extra")
pd = pytest.importorskip("pandas", reason="requires the [io] extra")

from engin_core.convention import CONVENTION_ATTR, validate_timeseries  # noqa: E402
from engin_core.loaders import (  # noqa: E402
    ALIASES,
    infer_columns,
    load_endpoints,
    load_timeseries,
    register_alias,
)


def _guess(report, source):
    return next(g for g in report.guesses if g.source == source)


# ------------------------------------------------------------------- inference


def test_canonical_headers_are_matched_with_full_confidence():
    df = pd.DataFrame({"run_id": ["R1"], "titer": [30.0], "biomass": [8.0]})
    report = infer_columns(df)
    assert report.run_column == "run_id"
    assert _guess(report, "titer").channel == "titer"
    assert _guess(report, "titer").confidence >= 0.95


def test_aliases_are_matched_and_scored_below_canonical():
    df = pd.DataFrame({"Batch": ["B1"], "OD600": [4.0], "Titre": [12.0]})
    report = infer_columns(df)
    assert report.run_column == "Batch"
    assert _guess(report, "OD600").channel == "biomass"
    assert _guess(report, "Titre").channel == "titer"

    canonical = infer_columns(pd.DataFrame({"biomass": [1.0]}))
    assert _guess(report, "OD600").confidence < _guess(canonical, "biomass").confidence


def test_units_are_extracted_from_several_header_styles():
    df = pd.DataFrame(
        {
            "Titer (g/L)": [30.0],
            "Biomass [g/L]": [8.0],
            "feed_rate_L_per_h": [0.2],
            "DO (%)": [60.0],
        }
    )
    report = infer_columns(df)
    assert _guess(report, "Titer (g/L)").units == "g/L"
    assert _guess(report, "Biomass [g/L]").units == "g/L"
    assert _guess(report, "feed_rate_L_per_h").units == "L/h"
    assert _guess(report, "DO (%)").units == "%"


def test_agreeing_units_raise_confidence_above_the_same_header_without_them():
    with_units = _guess(infer_columns(pd.DataFrame({"Titre (g/L)": [1.0]})), "Titre (g/L)")
    without = _guess(infer_columns(pd.DataFrame({"Titre": [1.0]})), "Titre")
    assert with_units.confidence > without.confidence
    assert "agree" in with_units.evidence


def test_absent_units_are_flagged_without_costing_channel_confidence():
    """Confidence is about *which channel this is*. A header spelled exactly like
    the canonical name is not a worse identification for omitting its units."""
    guess = _guess(infer_columns(pd.DataFrame({"titer": [1.0]})), "titer")
    assert guess.confidence == 1.0
    assert guess.units_assumed is True
    assert guess.units == "g/L"

    stated = _guess(infer_columns(pd.DataFrame({"titer (g/L)": [1.0]})), "titer (g/L)")
    assert stated.units_assumed is False


def test_disagreeing_units_are_reported_not_silently_converted():
    guess = _guess(infer_columns(pd.DataFrame({"Titer (mg/L)": [1.0]})), "Titer (mg/L)")
    assert guess.units == "mg/L", "the loader must not quietly rewrite the source units"
    assert "differ" in guess.evidence


def test_unknown_column_is_reported_and_carried_not_dropped():
    df = pd.DataFrame({"run_id": ["R1"], "AUX2_raw": [0.1], "titer": [30.0]})
    report = infer_columns(df)
    guess = _guess(report, "AUX2_raw")
    assert guess.channel is None
    assert guess in report.unmapped
    assert any(n.code == "unmapped-column" for n in report.notes)


def test_ambiguous_header_is_flagged_for_review_with_alternatives():
    """'o2' is a plausible spelling of two different channels."""
    report = infer_columns(pd.DataFrame({"run_id": ["R1"], "o2": [20.0]}))
    guess = _guess(report, "o2")
    assert guess.confidence < report.review_threshold
    assert guess in report.needs_review
    assert guess.alternatives, "an ambiguous match should name what else it could be"


def test_missing_run_column_is_a_note_not_an_exception():
    report = infer_columns(pd.DataFrame({"titer": [1.0]}))
    assert report.run_column is None
    assert any(n.code == "no-run-column-found" for n in report.notes)


def test_every_note_carries_a_suggestion():
    df = pd.DataFrame({"o2": [1.0], "AUX2_raw": [1.0]})
    report = infer_columns(df)
    assert report.notes
    for note in report.notes:
        assert note.suggestion.strip(), f"{note.code} has no suggestion"


def test_orientation_distinguishes_endpoint_from_long():
    endpoint = infer_columns(pd.DataFrame({"run_id": ["R1"], "titer": [1.0]}))
    long = infer_columns(pd.DataFrame({"run_id": ["R1"], "time (h)": [0.0], "titer": [1.0]}))
    assert endpoint.orientation == "endpoint"
    assert long.orientation == "long"
    assert long.time_column == "time (h)"


def test_register_alias_teaches_a_real_spelling():
    assert infer_columns(pd.DataFrame({"PROD_A": [1.0]})).unmapped
    try:
        register_alias("titer", "prod_a")
        guess = _guess(infer_columns(pd.DataFrame({"PROD_A": [1.0]})), "PROD_A")
        assert guess.channel == "titer"
    finally:
        ALIASES["titer"] = tuple(a for a in ALIASES["titer"] if a != "prod_a")


def test_register_alias_rejects_an_unknown_channel():
    """A typo here would produce a mapping that never fires."""
    with pytest.raises(KeyError):
        register_alias("tighter", "whatever")


# -------------------------------------------------------------------- endpoint


def test_load_endpoints_renames_to_channels_and_keeps_unknowns():
    df = pd.DataFrame({"Batch": ["B1", "B2"], "Titre (g/L)": [30.0, 31.0], "AUX2": [1, 2]})
    out, report = load_endpoints(df)
    assert "run_id" in out.columns
    assert "titer" in out.columns
    assert "AUX2" in out.columns, "unmapped columns must survive the load"
    assert report.units()["titer"] == "g/L"


def test_load_endpoints_can_report_without_touching_the_data():
    df = pd.DataFrame({"Batch": ["B1"], "Titre": [30.0]})
    out, _ = load_endpoints(df, rename=False)
    assert list(out.columns) == ["Batch", "Titre"]


def test_explicit_run_column_overrides_inference_and_clears_the_note():
    df = pd.DataFrame({"weird_name": ["A"], "titer": [1.0]})
    _, report = load_endpoints(df, run_column="weird_name")
    assert report.run_column == "weird_name"
    assert not any(n.code == "no-run-column-found" for n in report.notes)


# ------------------------------------------------------------------ time series


def long_frame() -> pd.DataFrame:
    rows = []
    for run in ("R00", "R01"):
        for t in range(4):
            rows.append(
                {
                    "Batch": run,
                    "Time (h)": float(t),
                    "Titer (g/L)": 10.0 + t,
                    "OD600": 2.0 + t,
                }
            )
    return pd.DataFrame(rows)


def test_long_table_becomes_a_conforming_dataset():
    ds, report = load_timeseries(long_frame())
    assert set(ds.dims) == {"run", "time"}
    assert set(ds.data_vars) == {"titer", "biomass"}
    assert ds["titer"].attrs["units"] == "g/L"
    assert ds["time"].attrs["units"] == "h"
    assert ds.attrs[CONVENTION_ATTR]

    convention_report = validate_timeseries(ds)
    assert convention_report.ok, convention_report.summary()
    assert report.orientation == "long"


def test_values_survive_the_reshape():
    ds, _ = load_timeseries(long_frame())
    assert float(ds["titer"].sel(run="R01", time=3.0)) == 13.0


def test_time_without_units_is_assumed_hours_and_said_so():
    df = long_frame().rename(columns={"Time (h)": "Time"})
    ds, report = load_timeseries(df)
    assert ds["time"].attrs["units"] == "h"
    assert any(n.code == "time-units-assumed" for n in report.notes)


def test_non_numeric_columns_are_dropped_with_a_warning():
    df = long_frame()
    df["operator"] = "alice"
    ds, report = load_timeseries(df)
    assert "operator" not in ds.data_vars
    assert any(n.code == "non-numeric-columns-dropped" for n in report.notes)


def test_duplicate_run_time_rows_are_reported():
    df = pd.concat([long_frame(), long_frame().head(1)], ignore_index=True)
    _, report = load_timeseries(df)
    assert any(n.code == "duplicate-run-time-rows" for n in report.notes)


def test_unreshapeable_table_raises_with_an_actionable_message():
    """The one place raising is right: there is no (run, time) to reshape onto."""
    with pytest.raises(ValueError, match="time_column="):
        load_timeseries(pd.DataFrame({"Batch": ["R1"], "titer": [1.0]}))


def test_summary_mentions_the_review_threshold():
    _, report = load_endpoints(pd.DataFrame({"Batch": ["B1"], "o2": [1.0]}))
    assert "review threshold" in report.summary()


# ------------------------------------------- regressions from the first real dataset


def test_short_headers_do_not_match_by_being_inside_a_longer_alias():
    """The first real dataset produced four confident-looking mappings, all wrong.

    ``our`` matched substrate via "carbonSOURce", ``ht`` matched biomass via
    "dryweigHT", ``fi`` matched mu via "speciFIc", and ``te`` matched titer via
    "tITEr". A short header appearing somewhere inside a long word is coincidence,
    not evidence about what a column means.
    """
    df = pd.DataFrame({"batch_id": ["B1"], "te": [31.1], "fi": [5286], "ht": [1.34]})
    report = infer_columns(df)
    for source in ("te", "fi", "ht"):
        guess = _guess(report, source)
        assert guess.channel is None, (
            f"{source!r} mapped to {guess.channel!r} on a substring coincidence; "
            "containment matching should not fire for headers this short"
        )


def test_gas_transfer_channels_from_the_first_real_dataset_map_exactly():
    """OUR, CER, RQ and kLa are standard in industrial records and were absent
    from a vocabulary built around a simulator."""
    df = pd.DataFrame(
        {"batch_id": ["B1"], "our": [1.08], "cer": [4.62], "rq": [4.26], "kla": [54.3]}
    )
    report = infer_columns(df)
    for source in ("our", "cer", "rq", "kla"):
        guess = _guess(report, source)
        assert guess.channel == source
        assert guess.confidence == 1.0


def test_hh_is_recognised_as_an_hour_axis():
    """The real dataset's time column. Without it the table reads as endpoint data."""
    df = pd.DataFrame({"batch_id": ["B1", "B1"], "hh": [30, 31], "our": [1.0, 1.1]})
    report = infer_columns(df)
    assert report.time_column == "hh"
    assert report.orientation == "long"


def test_unglossed_column_reports_that_no_default_exists():
    """Distinct from a known channel that merely omitted its units: the fix is to
    consult the source documentation, not to look up a default."""
    ds, _ = load_timeseries(long_frame())
    ds["aux2_raw"] = (("run", "time"), ds["titer"].values * 0.0)
    report = validate_timeseries(ds)
    codes = {f.code for f in report.findings}
    assert "missing-units-unknown-channel" in codes
    assert "missing-units" not in codes


def test_columns_claiming_the_same_channel_are_never_silently_merged():
    """A real dataset offered four aeration-rate columns -- total, air, O2 and CO2.

    All four matched `airflow`, all four were renamed to it, pandas produced
    duplicate column names without complaint, and every one was gone from the
    resulting Dataset. Silent loss is the worst available failure for a tool whose
    argument is honesty about what it knows.
    """
    df = pd.DataFrame(
        {
            "run_id": ["R1", "R1"],
            "time (h)": [0.0, 1.0],
            "Aeration rate total (L/h)": [1.0, 1.1],
            "Aeration rate air (L/h)": [0.8, 0.9],
            "Aeration rate O2 (L/h)": [0.2, 0.2],
        }
    )
    report = infer_columns(df)

    contested = [g for g in report.guesses if g.contested]
    assert len(contested) == 3, "all three claimants should be marked, not just the losers"
    assert all(g.channel == "airflow" for g in contested)
    assert "airflow" not in report.mapping().values(), "a contested channel must not be applied"

    note = next(n for n in report.notes if n.code == "contested-channel")
    assert note.level == "error"
    assert "Aeration rate air (L/h)" in note.message

    ds, _ = load_timeseries(df)
    assert len(ds.data_vars) == 3, "every source column must survive"
    assert all("Aeration" in name for name in ds.data_vars)


def test_an_uncontested_mapping_still_applies():
    """The collision check must not disable ordinary mapping."""
    df = pd.DataFrame({"run_id": ["R1"], "time (h)": [0.0], "Titre (g/L)": [30.0]})
    report = infer_columns(df)
    assert report.mapping() == {"Titre (g/L)": "titer"}
    assert not any(g.contested for g in report.guesses)
