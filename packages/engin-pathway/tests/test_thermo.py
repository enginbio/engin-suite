"""The ΔG -> g_thermo transform (#140 item 1).

What is worth pinning is not the arithmetic but the *properties that make the
number mean something*: bounded without clipping, neutral at zero, monotone the
right way, and an interval that does not come back inverted.
"""

from __future__ import annotations

import numpy as np
import pytest

from engin_pathway.thermo import RT_KJ_PER_MOL, g_thermo, g_thermo_interval


def test_zero_energy_is_exactly_neutral():
    """A reaction with no thermodynamic preference scores 0.5.

    This is the property that makes the transform interpretable rather than
    tuned: it falls out of the equilibrium expression instead of being placed.
    """
    assert g_thermo(0.0) == pytest.approx(0.5)


def test_favourable_scores_above_neutral_and_unfavourable_below():
    assert g_thermo(-30.0) > 0.5
    assert g_thermo(30.0) < 0.5


def test_never_increases_with_energy():
    """Non-increasing everywhere, including the saturated tails."""
    dg = np.linspace(-200.0, 200.0, 401)
    assert np.all(np.diff(g_thermo(dg)) <= 0)


def test_strictly_decreasing_across_the_range_that_discriminates():
    """Strict monotonicity holds where the score is not saturated."""
    dg = np.linspace(-35.0, 60.0, 200)
    assert np.all(np.diff(g_thermo(dg)) < 0)


def test_it_saturates_on_the_favourable_side():
    """Exactly 1.0 below about -91 kJ/mol -- bisected, not eyeballed.

    An earlier version of this test said -40, read off a `%g`-formatted print that
    rendered 0.9999999 as "1". Asserting the float directly is what caught it.
    """
    assert g_thermo(-95.0) == 1.0
    assert g_thermo(-200.0) == 1.0
    assert g_thermo(-85.0) < 1.0


def test_discrimination_is_gone_well_before_the_float_saturates():
    """The limit that actually bites a ranking: by -30 kJ/mol the score is already
    0.99999, so favourable steps are practically tied long before -91."""
    assert g_thermo(-30.0) == pytest.approx(0.99999, abs=1e-5)
    assert g_thermo(-40.0) - g_thermo(-80.0) < 1e-6


def test_the_unfavourable_tail_stays_ordered():
    """It does not saturate the way the favourable side does, so strongly
    unfavourable steps remain distinguishable."""
    assert 0.0 < g_thermo(200.0) < 1e-30
    assert g_thermo(100.0) > g_thermo(200.0)


def test_bounded_without_clipping():
    """[0, 1] by construction. Clipping would hide a broken transform."""
    extreme = g_thermo([-1e4, -200.0, 0.0, 200.0, 1e4])
    assert np.all(extreme >= 0.0) and np.all(extreme <= 1.0)


def test_does_not_overflow_on_strongly_unfavourable_reactions():
    """The naive 1/(1+exp(dg/RT)) overflows here; expit does not."""
    with np.errstate(over="raise", invalid="raise"):
        g = g_thermo([500.0, 1e6])
    assert np.all(np.isfinite(g))
    assert g[0] == pytest.approx(0.0, abs=1e-12)


def test_rt_is_the_documented_constant():
    """About 2.479 kJ/mol at 298.15 K. A wrong RT would silently rescale every
    score while leaving every other property in this file passing."""
    assert RT_KJ_PER_MOL == pytest.approx(2.479, abs=0.001)


def test_one_rt_of_energy_moves_the_score_by_the_logistic_amount():
    """Anchors the scale: at ΔG = -RT the score is 1/(1+e^-1) ≈ 0.731."""
    assert g_thermo(-RT_KJ_PER_MOL) == pytest.approx(1.0 / (1.0 + np.exp(-1.0)))


def test_the_interval_is_not_inverted():
    """g_thermo decreases in ΔG, so the upper score bound comes from the lower
    energy bound. Mapping the endpoints in order would return low > high."""
    low, high = g_thermo_interval(-20.0, 5.0)
    assert low < high


def test_the_interval_brackets_the_point_estimate():
    dg, sd = -20.0, 5.0
    low, high = g_thermo_interval(dg, sd)
    assert low < g_thermo(dg) < high


def test_zero_uncertainty_collapses_to_the_point_estimate():
    low, high = g_thermo_interval(-44.8, 0.0)
    point = g_thermo(-44.8)
    assert low == pytest.approx(point)
    assert high == pytest.approx(point)


def test_a_negative_sd_is_treated_as_a_magnitude():
    """Defensive: a sign error upstream should not silently invert the interval."""
    assert g_thermo_interval(-20.0, -5.0) == pytest.approx(g_thermo_interval(-20.0, 5.0))


def test_the_tutorial_value_maps_sensibly():
    """eQuilibrator's own example, -44.8 ± 0.6 kJ/mol, is strongly favourable and
    its uncertainty is narrow -- so the score should sit near 1 with a tight band."""
    low, high = g_thermo_interval(-44.8, 0.6)
    assert g_thermo(-44.8) > 0.999
    assert high - low < 0.01


def test_vectorises_over_a_route():
    """Steps arrive as a sequence, not one at a time."""
    g = g_thermo([-44.8, 0.0, 12.0])
    assert g.shape == (3,)
    assert g[0] > g[1] > g[2]
