"""Techno-economic head: mechanics, posterior propagation, and two pinned findings."""

from __future__ import annotations

import numpy as np
import pytest

from engin_core import fit_gp
from engin_core.simulator import simulate_unit
from engin_core.tea import (
    CostModel,
    CostParameters,
    ParametricCostModel,
    ProductionScale,
    PurityGrade,
    annual_capital_charge_usd,
    bioreactor_direct_cost_usd,
    break_even,
    capital_charge_factor,
    capital_cost_per_batch_usd,
    cost_samples,
    cost_summary,
    design_context,
    expected_cost_reduction,
    purity_dsp_multiplier,
    recommend_batch_by_cost,
)


def _fitted_gp(n: int = 60, seed: int = 0):
    rng = np.random.default_rng(seed)
    U = rng.random((n, 5))
    return fit_gp(U, simulate_unit(U), seed=seed), U


# ------------------------------------------------------------------ mechanics


def test_design_context_needs_no_simulation():
    ctx = design_context(np.full((3, 5), 0.5))
    assert set(ctx) == {"substrate_fed_g", "final_volume_L", "reactor_L_h"}
    assert np.all(ctx["substrate_fed_g"] > 0)
    assert np.all(ctx["final_volume_L"] >= 1.0)


def test_parametric_model_satisfies_the_cost_model_protocol():
    # The seam that lets a BioSTEAM flowsheet substitute without touching anything above.
    assert isinstance(ParametricCostModel(), CostModel)


def test_cost_is_positive_and_finite():
    rng = np.random.default_rng(0)
    U = rng.random((50, 5))
    cost = ParametricCostModel().cost_per_kg(simulate_unit(U), U)
    assert np.all(np.isfinite(cost)) and np.all(cost > 0)


def test_downstream_cost_falls_as_titer_rises():
    """The sign D13 originally had backwards. Higher titer is *cheaper* to recover."""
    m = ParametricCostModel()
    U = np.full((1, 5), 0.5)
    assert (
        m.cost_breakdown([80.0], U)["downstream"][0] < m.cost_breakdown([20.0], U)["downstream"][0]
    )


def test_raw_material_cost_rises_when_substrate_is_fed_without_converting():
    m = ParametricCostModel()
    U = np.full((1, 5), 0.5)
    lean = m.cost_breakdown([60.0], U)["raw_material"][0]
    wasteful = m.cost_breakdown([20.0], U)["raw_material"][0]
    assert wasteful > lean  # same substrate, less product


def test_breakdown_sums_to_total():
    rng = np.random.default_rng(1)
    U = rng.random((20, 5))
    m = ParametricCostModel()
    t = simulate_unit(U)
    assert np.allclose(sum(m.cost_breakdown(t, U).values()), m.cost_per_kg(t, U))


def test_cost_parameters_reject_nonsense():
    with pytest.raises(ValueError):
        CostParameters(substrate_usd_per_kg=-1.0)
    with pytest.raises(ValueError):
        CostParameters(target_usd_per_kg=0.0)


# ------------------------------------------------- uncertainty propagation


def test_titer_uncertainty_reaches_cost():
    gp, U = _fitted_gp()
    s = cost_samples(gp, U[:4], n_samples=256)
    assert s.shape == (4, 256)
    assert np.all(s > 0) and np.all(s.std(axis=1) > 0)


def test_cost_summary_is_a_forecast_not_a_point():
    gp, U = _fitted_gp()
    for s in cost_summary(gp, U[:5], n_samples=512):
        assert s.lower_usd_per_kg <= s.expected_usd_per_kg <= s.upper_usd_per_kg
        assert 0.0 <= s.prob_meets_target <= 1.0
        assert s.interval_width > 0


def test_probability_of_meeting_target_is_monotone_in_the_target():
    gp, U = _fitted_gp()
    lax = cost_summary(gp, U[:5], params=CostParameters(target_usd_per_kg=400.0), n_samples=512)
    strict = cost_summary(gp, U[:5], params=CostParameters(target_usd_per_kg=100.0), n_samples=512)
    for a, b in zip(lax, strict, strict=True):
        assert a.prob_meets_target >= b.prob_meets_target


def test_wider_level_gives_a_wider_interval():
    gp, U = _fitted_gp()
    narrow = cost_summary(gp, U[:3], level=0.50, n_samples=1024)
    wide = cost_summary(gp, U[:3], level=0.99, n_samples=1024)
    for a, b in zip(narrow, wide, strict=True):
        assert b.interval_width > a.interval_width


# ----------------------------------------------------------------- acquisition


def test_expected_cost_reduction_is_non_negative():
    gp, U = _fitted_gp()
    acq = expected_cost_reduction(gp, U[:20], best_cost=150.0, n_samples=256)
    assert acq.shape == (20,) and np.all(acq >= 0)


def test_a_lower_incumbent_cost_is_harder_to_improve_on():
    gp, U = _fitted_gp()
    easy = expected_cost_reduction(gp, U[:20], best_cost=400.0, n_samples=256)
    hard = expected_cost_reduction(gp, U[:20], best_cost=60.0, n_samples=256)
    assert easy.sum() > hard.sum()


def test_recommend_batch_by_cost_returns_diverse_designs():
    gp, _ = _fitted_gp()
    X, acq = recommend_batch_by_cost(gp, best_cost=200.0, k=6, pool=800)
    assert X.shape == (6, 5) and acq.shape == (6,)
    for i in range(len(X)):
        for j in range(i + 1, len(X)):
            assert np.linalg.norm(X[i] - X[j]) > 0.15


def test_cost_recommendation_never_repeats_a_design_already_run():
    """#224, the D13 recommender's half of it.

    **The training set is drawn from the recommender's own candidate pool, and the
    pool parameters are pinned to a case that actually fails without the fix.** Both
    halves are load-bearing. A GP fitted on unrelated random points passes against
    the unfixed code by luck -- in 5D with ``min_dist=0.15`` a fresh candidate rarely
    lands inside a training point's exclusion ball -- and so does the pool-seeded
    version at most ``(pool, seed)`` combinations, because an already-measured design
    usually carries low acquisition and sorts far down the order.

    At ``pool=400, seed=2`` it does not: the unfixed recommender returns a design at
    distance **0.0** from a training point, an exact repeat. Verified by reverting
    ``recommend.py`` and ``tea.py`` and re-running. If this test ever stops failing
    against the unfixed code, it has stopped testing anything.
    """
    pool, seed = 400, 2
    candidates = np.random.default_rng(seed).random((pool, 5))
    already_run = candidates[:40]
    gp = fit_gp(already_run, simulate_unit(already_run), seed=0)

    X, _ = recommend_batch_by_cost(gp, best_cost=200.0, k=6, pool=pool, seed=seed)
    for x in X:
        assert np.min(np.linalg.norm(gp.X - x, axis=1)) > 0.15


# ------------------------------------------------------- the pinned findings


def test_this_simulator_cannot_reproduce_industrial_cost_shares():
    """Raw material is ~2% here, where the literature has it as a dominant term.

    The comparison figure was corrected 2026-08-11 by the D23 evidence pass: an
    earlier version cited "35-50% of precision-fermentation COGS", which was not
    sourceable. Konzock & Nielsen (2024) support the direction -- yield directly
    defines substrate cost, "more than 50% of the total costs" for commodity
    chemicals -- but not that split. The finding this test pins is unaffected:
    ~2% is far below any of them.

    Not a bug in the cost model. With realistic media prices and this simulator's
    substrate-to-product ratio at 1–2 L scale, the yield lever is nearly invisible;
    reproducing the industrial share would need substrate priced around $28/kg,
    which is a fiction rather than a feedstock.

    **The consequence matters:** cost optimization on this simulator is driven by the
    facility and downstream terms, not by yield — so it cannot demonstrate the very
    argument D13 rests on. A representative process is needed for that.

    If this test starts failing, the simulator's economics have become more realistic
    and the claim above should be re-checked rather than the assertion relaxed.
    """
    rng = np.random.default_rng(0)
    U = rng.random((400, 5))
    m = ParametricCostModel()
    b = m.cost_breakdown(simulate_unit(U), U)
    total = sum(b.values())
    raw_share = float(np.median(b["raw_material"] / total))
    assert raw_share < 0.10, (
        f"raw-material share is {raw_share:.1%}; the module docstring says it is ~2% "
        "and that the yield lever is invisible here. Re-check that claim."
    )


def test_cost_and_titer_still_choose_the_same_design_here():
    """D13's practical effect remains undemonstrable on the bundled simulator.

    Two independent reasons, both established rather than assumed:

    1. Titer and yield are *positively* correlated in this simulator, so the
       titer-optimal design is also near the top of the yield distribution.
    2. Raw material is ~2% of modelled cost at this scale, so the yield term cannot
       move the optimum even where it differs.

    D13's decision stands on the TRY argument in ``DECISIONS.md``; what cannot be shown
    *here* is the specific claim that a cost objective picks a different design. Pinned
    so it is not quietly forgotten.
    """
    rng = np.random.default_rng(0)
    U = rng.random((400, 5))
    titer = simulate_unit(U)
    cost = ParametricCostModel().cost_per_kg(titer, U)
    assert int(np.argmin(cost)) == int(np.argmax(titer)), (
        "cost and titer optima diverged -- D13 may now be demonstrable on this "
        "simulator; update the docs rather than relaxing this test"
    )


# --- Production scale and capital recovery (#143 piece 1). ---


def test_equation_9_reproduces_humbirds_own_cost_table():
    # The published correlation against the table it was fitted to, 1-200 m3.
    # Agreement is ~10%, which is what the piecewise fit buys; asserting tighter
    # would be asserting something the source does not claim.
    published_installed_usd_k = {
        1: 774,
        2: 856,
        5: 966,
        10: 1200,
        20: 1500,
        50: 2600,
        100: 4000,
        200: 6800,
    }
    for volume_m3, table_usd_k in published_installed_usd_k.items():
        predicted = bioreactor_direct_cost_usd(volume_m3) / 1000.0
        assert predicted == pytest.approx(table_usd_k, rel=0.11)


def test_capital_charge_factor_matches_the_published_15_percent():
    # Humbird Eq 10 at i=7.5%, n=10 years.
    assert capital_charge_factor(0.075, 10) == pytest.approx(0.1457, abs=5e-4)
    # Monotone in both arguments, in the directions that must hold.
    assert capital_charge_factor(0.10, 10) > capital_charge_factor(0.075, 10)
    assert capital_charge_factor(0.075, 20) < capital_charge_factor(0.075, 10)


def test_capital_cost_per_kg_falls_with_scale():
    # The point of the whole exercise: cost per kilogram at bench scale and at
    # plant scale must differ in more than a linear volume factor.
    def per_kg(volume_m3):
        scale = ProductionScale(working_volume_m3=volume_m3, batches_per_year=20, n_vessels=1)
        return capital_cost_per_batch_usd(scale) / (30.0 * volume_m3)  # 30 g/L

    small, large = per_kg(1.0), per_kg(200.0)
    assert small > large
    # And the fall is faster than the vessel-cost ratio, because of the fixed term.
    assert small / large > 10.0


def test_scale_is_opt_in_and_changes_nothing_when_unset():
    U = np.array([[0.5, 0.5, 0.5, 0.5, 0.5]])
    titer = simulate_unit(U)
    baseline = ParametricCostModel(CostParameters())
    assert baseline.params.scale is None
    assert baseline.cost_breakdown(titer, U)["capital"] == pytest.approx(0.0)

    scaled = ParametricCostModel(
        CostParameters(scale=ProductionScale(working_volume_m3=20.0, batches_per_year=15))
    )
    assert scaled.cost_per_kg(titer, U) > baseline.cost_per_kg(titer, U)


def test_breakdown_still_sums_to_total_with_capital():
    U = np.array([[0.4, 0.3, 0.6, 0.5, 0.5]])
    titer = simulate_unit(U)
    model = ParametricCostModel(
        CostParameters(scale=ProductionScale(working_volume_m3=10.0, batches_per_year=12))
    )
    parts = model.cost_breakdown(titer, U)
    assert sum(parts.values()) == pytest.approx(model.cost_per_kg(titer, U))


def test_more_vessels_do_not_change_cost_per_kg_but_more_batches_do():
    # n_vessels scales capital and output together, so per-kg is flat in it.
    # batches_per_year is the utilisation lever and must move the number.
    base = ProductionScale(working_volume_m3=20.0, batches_per_year=15, n_vessels=1)
    more_vessels = base.model_copy(update={"n_vessels": 4})
    more_batches = base.model_copy(update={"batches_per_year": 30})
    assert capital_cost_per_batch_usd(more_vessels) == pytest.approx(
        capital_cost_per_batch_usd(base)
    )
    assert capital_cost_per_batch_usd(more_batches) == pytest.approx(
        capital_cost_per_batch_usd(base) / 2.0
    )


def test_production_scale_rejects_nonsense():
    with pytest.raises(ValueError):
        ProductionScale(working_volume_m3=0, batches_per_year=10)
    with pytest.raises(ValueError):
        ProductionScale(working_volume_m3=10, batches_per_year=-1)
    with pytest.raises(ValueError):
        bioreactor_direct_cost_usd(0)
    with pytest.raises(ValueError):
        capital_charge_factor(1.5, 10)


def test_capital_chain_follows_the_published_sequence():
    # TDC -> total plant cost (indirect) -> total capital investment (contingency)
    # -> annual charge (capital charge factor). Pinned explicitly because each
    # factor is a separate citation and a silent reordering would still "work".
    scale = ProductionScale(working_volume_m3=20.0, batches_per_year=15, n_vessels=2)
    direct = bioreactor_direct_cost_usd(20.0) * 2
    expected = (
        direct
        * (1 + scale.indirect_cost_factor)
        * (1 + scale.contingency_factor)
        * capital_charge_factor(scale.capital_charge_rate, scale.capital_lifetime_years)
    )
    assert annual_capital_charge_usd(scale) == pytest.approx(expected)
    # A 20 m3 vessel is $1.4M direct by Equation 9; sanity-check the magnitude.
    assert 1.3e6 < bioreactor_direct_cost_usd(20.0) < 1.5e6


# --- Purity as a cost axis (#17). ---


def test_purity_multiplier_derives_the_published_range():
    # Straathof: crude ~25% DSP share, purified/formulated 50-55%. Converting
    # shares to a multiplier on the DSP term, holding upstream cost fixed.
    assert purity_dsp_multiplier(PurityGrade.CRUDE) == 1.0
    assert purity_dsp_multiplier(PurityGrade.PURIFIED) == pytest.approx(3.316, abs=1e-3)
    # The published range endpoints bracket it.
    lo = purity_dsp_multiplier(PurityGrade.PURIFIED, purified_share=0.50)
    hi = purity_dsp_multiplier(PurityGrade.PURIFIED, purified_share=0.55)
    assert lo == pytest.approx(3.0, abs=1e-6)
    assert hi == pytest.approx(3.667, abs=1e-3)
    assert lo < purity_dsp_multiplier(PurityGrade.PURIFIED) < hi


def test_purity_multiplier_is_not_the_total_cost_ratio():
    # Guards the modelling choice, not the arithmetic. Holding *total* cost fixed
    # would give 0.525/0.25 = 2.1x, which assumes purification is free in
    # aggregate. If someone "simplifies" to that ratio, this fails.
    assert purity_dsp_multiplier(PurityGrade.PURIFIED) != pytest.approx(2.1, abs=0.05)


def test_purity_accepts_strings_and_rejects_nonsense():
    assert purity_dsp_multiplier("crude") == 1.0
    assert purity_dsp_multiplier("purified") > 1.0
    with pytest.raises(ValueError):
        purity_dsp_multiplier("pharmaceutical")  # not a grade the evidence supports
    with pytest.raises(ValueError):
        purity_dsp_multiplier(PurityGrade.PURIFIED, crude_share=0.0)
    with pytest.raises(ValueError):
        purity_dsp_multiplier(PurityGrade.PURIFIED, purified_share=1.0)


def test_purity_defaults_to_crude_and_changes_nothing():
    U = np.array([[0.5, 0.5, 0.5, 0.5, 0.5]])
    titer = simulate_unit(U)
    assert CostParameters().purity_grade is PurityGrade.CRUDE
    assert CostParameters().purity_multiplier == 1.0
    crude = ParametricCostModel(CostParameters())
    purified = ParametricCostModel(CostParameters(purity_grade=PurityGrade.PURIFIED))
    assert purified.cost_per_kg(titer, U) > crude.cost_per_kg(titer, U)


def test_purity_scales_only_the_downstream_term():
    # The whole claim is that specification moves DSP, not fermentation.
    U = np.array([[0.4, 0.3, 0.6, 0.5, 0.5]])
    titer = simulate_unit(U)
    crude = ParametricCostModel(CostParameters()).cost_breakdown(titer, U)
    pure = ParametricCostModel(CostParameters(purity_grade=PurityGrade.PURIFIED)).cost_breakdown(
        titer, U
    )
    assert pure["raw_material"] == pytest.approx(crude["raw_material"])
    assert pure["facility"] == pytest.approx(crude["facility"])
    assert pure["downstream"] == pytest.approx(
        crude["downstream"] * purity_dsp_multiplier(PurityGrade.PURIFIED)
    )


def test_override_covers_the_product_class_the_default_does_not():
    # Affinity-purified proteins sit an order of magnitude above the default;
    # the override exists so that case is expressible rather than mis-modelled.
    params = CostParameters(purity_grade=PurityGrade.PURIFIED, purity_multiplier_override=30.0)
    assert params.purity_multiplier == 30.0
    with pytest.raises(ValueError):
        CostParameters(purity_multiplier_override=0.0)


# --- Break-even inversion (#143 piece 2). ---


def _design():
    return np.array([[0.5, 0.5, 0.5, 0.5, 0.5]])


def test_break_even_titer_actually_hits_the_target():
    U = _design()
    r = break_even(U)
    assert r.reachable and r.value is not None
    # The root is a root: cost at the returned titer equals the target.
    assert r.cost_at_value == pytest.approx(r.target_usd_per_kg, rel=1e-6)
    model = ParametricCostModel()
    assert float(model.cost_per_kg(np.array([r.value]), U)[0]) == pytest.approx(
        r.target_usd_per_kg, rel=1e-6
    )


def test_break_even_agrees_with_the_forward_model_either_side():
    # Above the break-even titer the target is met; below it, not. This is the
    # property that makes the inversion worth trusting.
    U = _design()
    r = break_even(U)
    model = ParametricCostModel()
    assert float(model.cost_per_kg(np.array([r.value * 1.1]), U)[0]) < r.target_usd_per_kg
    assert float(model.cost_per_kg(np.array([r.value * 0.9]), U)[0]) > r.target_usd_per_kg


def test_a_harder_target_needs_a_higher_titer():
    U = _design()
    easy = break_even(U, params=CostParameters(target_usd_per_kg=300.0))
    hard = break_even(U, params=CostParameters(target_usd_per_kg=120.0))
    assert hard.value > easy.value


def test_an_unreachable_target_refuses_rather_than_returning_a_number():
    U = _design()
    r = break_even(U, params=CostParameters(target_usd_per_kg=5.0))
    assert r.reachable is False
    assert r.value is None  # not a float nobody should act on
    assert "does not close this gap" in r.note
    assert r.searched == (0.1, 500.0)  # "unreachable" is scoped to what was searched


def test_a_target_met_at_the_bracket_floor_says_so():
    U = _design()
    r = break_even(U, params=CostParameters(target_usd_per_kg=100_000.0))
    assert r.reachable and r.value == pytest.approx(0.1)
    assert "at or below" in r.note


def test_prob_reaching_is_the_inverse_of_prob_meets_target():
    # The two questions are the same question. If the GP says P(titer >= break-even)
    # is 0.4, then P(cost <= target) should be about 0.4 too -- and if these ever
    # disagree, one of the two paths has a bug.
    gp, U = _fitted_gp(n=60, seed=0)
    Uq = U[:1]
    params = CostParameters(target_usd_per_kg=150.0)
    r = break_even(Uq, params=params, gp=gp)
    assert r.prob_reaching is not None
    summary = cost_summary(gp, Uq, params=params, n_samples=20_000, seed=0)[0]
    assert r.prob_reaching == pytest.approx(summary.prob_meets_target, abs=0.02)


def test_break_even_refuses_the_axes_it_cannot_solve():
    U = _design()
    for axis in ("scale", "yield", "rate"):
        with pytest.raises(ValueError, match="not available"):
            break_even(U, solve_for=axis)


def test_break_even_rejects_a_bad_bracket_and_multiple_designs():
    with pytest.raises(ValueError, match="bracket"):
        break_even(_design(), bracket=(50.0, 10.0))
    with pytest.raises(ValueError, match="one design at a time"):
        break_even(np.repeat(_design(), 3, axis=0))


def test_non_monotone_cost_models_are_refused_not_silently_rooted():
    # CostModel is a protocol; a flowsheet-backed one carries no monotonicity
    # guarantee, and a root find over a non-monotone curve returns an arbitrary root.
    class Wobbly:
        def cost_per_kg(self, titer_g_L, U):
            t = np.asarray(titer_g_L, float)
            return 200.0 + np.sin(t)

    with pytest.raises(ValueError, match="not monotone"):
        break_even(_design(), model=Wobbly())


def test_break_even_sees_purity_and_scale():
    # Regression. `break_even` built its default ParametricCostModel from *no*
    # parameters while reading the target from the caller's, so purity_grade and
    # scale reached the target and never reached the cost curve -- every parameter
    # set returned the same break-even titer. Invisible until #143 piece 1 and #17
    # were stacked together, because before that there was nothing to vary.
    U = _design()
    base = break_even(U).value
    purer = break_even(U, params=CostParameters(purity_grade=PurityGrade.PURIFIED)).value
    scaled = break_even(
        U,
        params=CostParameters(scale=ProductionScale(working_volume_m3=20.0, batches_per_year=15)),
    ).value
    both = break_even(
        U,
        params=CostParameters(
            purity_grade=PurityGrade.PURIFIED,
            scale=ProductionScale(working_volume_m3=20.0, batches_per_year=15),
        ),
    ).value
    # Each added cost pushes the break-even titer up, and both together push furthest.
    assert purer > base
    assert scaled > base
    assert both > purer and both > scaled
