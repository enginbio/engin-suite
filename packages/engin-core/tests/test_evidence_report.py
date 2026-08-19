"""Per-run evidence report (#145).

The tests that matter here are the ones asserting a report *refuses to omit* the
awkward parts: the tier's "does not establish" text, the absence of a baseline, and
the distinction between a conformal interval and a propagated one. A report that
quietly drops those is worse than no report, because it looks like diligence.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from engin_core import (
    Baseline,
    CostParameters,
    CostSummary,
    IntervalKind,
    RankedRoute,
    RouteRanking,
    ValidationTier,
    process_brief,
    report,
)
from engin_core.evidence import assumptions_from


def _cost() -> CostSummary:
    return CostSummary(
        expected_usd_per_kg=180.0,
        lower_usd_per_kg=140.0,
        upper_usd_per_kg=240.0,
        prob_meets_target=0.62,
        target_usd_per_kg=200.0,
    )


def _brief():
    ranking = RouteRanking(
        routes=[
            RankedRoute(route_id="r1", manufacturability=0.8, lo=0.72, hi=0.88),
            RankedRoute(route_id="r2", manufacturability=0.6, lo=0.55, hi=0.65),
        ],
        conditioned_on_host="E. coli",
        host_confidence=0.5,
    )
    return process_brief(ranking)


# ------------------------------------------------------- defaults are flagged


def test_untouched_parameters_are_all_flagged_default():
    rows = assumptions_from(CostParameters())
    assert rows, "CostParameters has fields; none were reported"
    assert all(a.is_default for a in rows if not a.name.startswith("scale"))


def test_caller_set_fields_are_flagged_even_when_equal_to_the_default():
    # The question is "did anybody think about this number", not "does it differ".
    params = CostParameters(target_usd_per_kg=200.0)  # 200.0 *is* the default
    by_name = {a.name: a for a in assumptions_from(params)}
    assert by_name["target_usd_per_kg"].is_default is False
    assert by_name["substrate_usd_per_kg"].is_default is True


def test_absent_scale_is_reported_rather_than_skipped():
    by_name = {a.name: a for a in assumptions_from(CostParameters())}
    assert by_name["scale"].value is None
    assert "bench vessel" in by_name["scale"].note


def test_present_scale_is_flattened_with_its_own_flags():
    params = CostParameters(
        scale={"working_volume_m3": 10.0, "n_vessels": 2, "batches_per_year": 12}
    )
    by_name = {a.name: a for a in assumptions_from(params)}
    assert by_name["scale.working_volume_m3"].value == 10.0
    assert by_name["scale.working_volume_m3"].is_default is False
    # untouched nested field still declares itself a default
    assert by_name["scale.capital_charge_rate"].is_default is True


# ------------------------------------------------- interval kinds stay distinct


def test_cost_interval_is_propagated_not_conformal():
    rep = report(tier=ValidationTier.OWN_SIMULATOR, cost=_cost())
    (iv,) = [i for i in rep.intervals if i.quantity.startswith("cost")]
    assert iv.kind is IntervalKind.PROPAGATED
    assert "not a conformal one" in iv.basis
    assert iv.width == pytest.approx(100.0)


def test_manufacturability_interval_is_heuristic():
    rep = report(tier=ValidationTier.OWN_SIMULATOR, brief=_brief())
    (iv,) = [i for i in rep.intervals if i.quantity.startswith("manufacturability")]
    assert iv.kind is IntervalKind.HEURISTIC
    # 0.5 confidence -> x1.5 on the 0.08 conformal half-width
    assert iv.upper - iv.lower == pytest.approx(2 * 1.5 * 0.08)


def test_no_interval_is_ever_labelled_calibrated():
    md = report(tier=ValidationTier.REAL_INDUSTRIAL, cost=_cost(), brief=_brief()).to_markdown()
    assert "calibrated interval by construction" in md  # the one licensed use
    assert not re.search(r"\|\s*\*\*calibrated\*\*\s*\|", md)


# ---------------------------------------------- section 4 is not droppable


@pytest.mark.parametrize("tier", list(ValidationTier))
def test_every_tier_carries_a_does_not_establish_line(tier):
    md = report(tier=tier).to_markdown()
    assert "## 4. What this does not establish" in md
    assert tier.does_not_establish in md


def test_tier_text_matches_the_published_table():
    """Guards drift between this module and ``docs/limitations.md``."""
    repo = Path(__file__).resolve().parents[3]
    limitations = repo / "docs" / "limitations.md"
    if not limitations.exists():  # pragma: no cover - suite also runs from a wheel
        pytest.skip("docs/ not present in this checkout")
    text = limitations.read_text()
    for tier in ValidationTier:
        row = next(
            (ln for ln in text.splitlines() if ln.strip().startswith(f"| {int(tier)} |")),
            None,
        )
        assert row is not None, f"tier {int(tier)} missing from the published table"
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        published_source, published_not = cells[1], cells[3]
        assert published_source == tier.source
        # the table bolds one phrase; compare on the text, not the emphasis
        assert published_not.replace("**", "") == tier.does_not_establish


# ------------------------------------------------ a missing baseline is loud


def test_absent_baseline_says_so_rather_than_omitting_the_section():
    md = report(tier=ValidationTier.OWN_SIMULATOR).to_markdown()
    assert "## 5. Baseline comparison" in md
    assert "No baseline supplied" in md
    assert "has not met that bar" in md


def test_baseline_that_beats_engin_is_reported_as_such():
    b = Baseline(
        name="response surface methodology",
        metric="best-true-titer lift",
        baseline_value=21.3,
        engin_value=15.9,
        source="docs/benchmarks.md",
    )
    assert b.engin_wins is False
    md = report(tier=ValidationTier.OWN_SIMULATOR, baselines=[b]).to_markdown()
    assert "**baseline**" in md


def test_uncompared_baseline_is_not_silently_a_loss():
    b = Baseline(name="BioSTEAM", metric="USD/kg", baseline_value=None, engin_value=None)
    assert b.engin_wins is None
    assert "not compared" in report(tier=ValidationTier.OWN_SIMULATOR, baselines=[b]).to_markdown()


# ------------------------------------------------------ provenance and repro


def test_provenance_chain_reaches_the_report():
    rep = report(tier=ValidationTier.OWN_SIMULATOR, brief=_brief())
    assert rep.provenance == "host=E. coli(conf=0.50) -> pathway -> process"
    assert rep.provenance in rep.to_markdown()


def test_repro_stamp_records_versions_and_seeds():
    rep = report(tier=ValidationTier.OWN_SIMULATOR, seeds={"cost_samples": 0})
    assert rep.repro.python
    assert "engin-core" in rep.repro.packages
    assert rep.repro.seeds == {"cost_samples": 0}
    assert "seed `cost_samples`: 0" in rep.to_markdown()


def test_dataset_manifest_digest_is_carried():
    rep = report(
        tier=ValidationTier.REAL_INDUSTRIAL,
        dataset_manifests={"indpensim": "abc123"},
    )
    assert "sha256 `abc123`" in rep.to_markdown()


# ------------------------------------------------------------------ machine


def test_json_round_trips_and_is_machine_readable():
    rep = report(
        tier=ValidationTier.REAL_INDUSTRIAL,
        params=CostParameters(target_usd_per_kg=150.0),
        brief=_brief(),
        cost=_cost(),
        seeds={"cost_samples": 7},
    )
    payload = json.loads(rep.to_json())
    assert payload["tier"] == 3
    assert payload["intervals"][0]["kind"] == "propagated"
    assert payload["repro"]["seeds"]["cost_samples"] == 7
    assert any(
        a["name"] == "target_usd_per_kg" and not a["is_default"] for a in payload["assumptions"]
    )


def test_all_six_sections_render_even_when_empty():
    md = report(tier=ValidationTier.OWN_SIMULATOR).to_markdown()
    for heading in (
        "## 1. Inputs and assumptions",
        "## 2. Provenance",
        "## 3. Uncertainty",
        "## 4. What this does not establish",
        "## 5. Baseline comparison",
        "## 6. Reproducibility",
    ):
        assert heading in md
