"""Stop/continue recommendation (#18).

The properties worth pinning are the ones that make this a *calibrated* rule
rather than a threshold with extra steps: the calibration widens rather than
narrows, the answer depends on the data rather than on how many candidate rows the
caller passed (#251), the incumbent is de-noised (#250), and the uncalibrated case
says so out loud.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.stats import norm

from engin_core import fit_gp, simulate_unit
from engin_core.stopping import (
    StopDecision,
    ei_below_threshold,
    headroom,
    posterior_incumbent,
    stop_decision,
)


def test_obvious_headroom_says_keep_going():
    d = stop_decision([10.0], [2.0], best=10.0, epsilon=0.0, delta=0.05)
    assert not d.stop
    assert d.p_worthwhile == pytest.approx(0.5, abs=1e-6)


def test_no_headroom_says_stop():
    """A candidate far below the incumbent with a tight posterior."""
    d = stop_decision([1.0], [0.05], best=10.0, epsilon=0.0, delta=0.05)
    assert d.stop
    assert d.p_worthwhile < 1e-6


def test_epsilon_is_in_objective_units_and_raises_the_bar():
    """Asking for a bigger gain can only make stopping more likely."""
    loose = stop_decision([11.0], [1.0], best=10.0, epsilon=0.0, delta=0.05)
    strict = stop_decision([11.0], [1.0], best=10.0, epsilon=5.0, delta=0.05)
    assert loose.p_worthwhile > strict.p_worthwhile


def test_calibration_widens_the_predictive_and_delays_stopping():
    """The point of the whole module.

    A conformal multiplier above the Gaussian one means the model was
    overconfident; the calibrated rule must then see *more* headroom, not less,
    and so must be less willing to stop.
    """
    mean, sd, best = [8.0], [1.0], 10.0
    raw = stop_decision(mean, sd, best, epsilon=0.0, delta=0.05)
    # q = 2.6 against a Gaussian 90% z of 1.645: the model was underestimating.
    calibrated = stop_decision(mean, sd, best, epsilon=0.0, delta=0.05, q=2.6, level=0.90)
    assert calibrated.p_worthwhile > raw.p_worthwhile


def test_a_conformal_multiplier_equal_to_the_gaussian_z_is_the_identity():
    """q = z means conformal agreed with the model, so nothing should move."""
    z = float(norm.ppf(0.95))
    mean, sd, best = [9.0], [1.5], 10.0
    raw = headroom(mean, sd, best)
    same = headroom(mean, sd, best, q=z, level=0.90)
    assert raw == pytest.approx(same, rel=1e-9)


def test_uncalibrated_decisions_are_flagged_and_say_why():
    d = stop_decision([1.0], [0.05], best=10.0, epsilon=0.0, delta=0.05)
    assert d.calibrated is False
    assert "overconfident" in d.rationale
    assert "stop early" in d.rationale


def test_calibrated_decisions_do_not_carry_the_warning():
    d = stop_decision([1.0], [0.05], best=10.0, epsilon=0.0, delta=0.05, q=2.0)
    assert d.calibrated is True
    assert "overconfident" not in d.rationale


def test_duplicating_a_candidate_does_not_change_the_decision():
    """Pool size carries no statistical content, so it must not move the answer.

    **This test replaces one that asserted the opposite** -- that adding candidates
    must strictly *raise* ``p_worthwhile``, on the grounds that independence is the
    conservative direction. That was the defect in #251 written down as a
    requirement, which is why it survived: the rule combined candidates as
    ``1 - prod(1 - p_i)``, so the same pool sub-sampled flipped stop from True at
    n=8 to False at n=4000 with nothing else changed.

    The direction of the old argument was fine. What was wrong is that the answer
    was controlled by ``len(candidates)``.
    """
    one = stop_decision([9.0], [1.0], best=10.0, epsilon=0.0, delta=0.05)
    many = stop_decision([9.0] * 5, [1.0] * 5, best=10.0, epsilon=0.0, delta=0.05)
    assert many.p_worthwhile == pytest.approx(one.p_worthwhile)
    assert many.stop == one.stop
    assert many.n_candidates == 5  # still reported, just not load-bearing


def test_a_more_promising_candidate_does_move_the_answer():
    """Invariance to duplicates must not become insensitivity to the data."""
    dull = stop_decision([9.0], [1.0], best=10.0, epsilon=0.0, delta=0.05)
    plus = stop_decision([9.0, 11.0], [1.0, 1.0], best=10.0, epsilon=0.0, delta=0.05)
    assert plus.p_worthwhile > dull.p_worthwhile


def test_p_worthwhile_is_the_largest_per_candidate_probability():
    mean = [9.0, 10.5, 8.0]
    sd = [1.0, 1.0, 1.0]
    d = stop_decision(mean, sd, best=10.0, epsilon=0.0, delta=0.05)
    assert d.p_worthwhile == pytest.approx(headroom(mean, sd, best=10.0).max())


def test_a_dense_grid_does_not_saturate_the_rule():
    """The refinement property: 1 - prod(1-p) diverged to 1 as the grid densified.

    Densifying a grid is a change with no statistical content -- neighbouring points
    have posterior correlation approaching 1 -- so a rule that saturates under it is
    reporting the grid, not the process.
    """
    coarse = stop_decision([9.0] * 8, [1.0] * 8, best=10.0, epsilon=0.0, delta=0.05)
    dense = stop_decision([9.0] * 4000, [1.0] * 4000, best=10.0, epsilon=0.0, delta=0.05)
    assert dense.p_worthwhile == pytest.approx(coarse.p_worthwhile)
    assert dense.p_worthwhile < 0.5  # the product reached ~1.0 here


def test_a_zero_variance_candidate_is_a_certainty_not_a_nan():
    below = headroom([5.0], [0.0], best=10.0)
    above = headroom([15.0], [0.0], best=10.0)
    assert np.isfinite(below).all() and np.isfinite(above).all()
    assert below[0] == pytest.approx(0.0, abs=1e-9)
    assert above[0] == pytest.approx(1.0, abs=1e-9)


def test_no_candidates_is_an_error_not_a_silent_stop():
    """Returning "stop" for an empty candidate set would be indistinguishable
    from a real recommendation."""
    with pytest.raises(ValueError, match="no candidates"):
        stop_decision([], [], best=10.0, epsilon=0.0, delta=0.05)


def test_the_ei_baseline_is_available_to_report_against():
    assert ei_below_threshold([0.001, 0.002], threshold=0.01) is True
    assert ei_below_threshold([0.001, 0.5], threshold=0.01) is False


def test_decision_is_serialisable():
    """It crosses a boundary into a memo or a CLI, so it must survive the trip."""
    d = stop_decision([9.0], [1.0], best=10.0, epsilon=0.0, delta=0.05, q=2.0)
    assert StopDecision.model_validate_json(d.model_dump_json()) == d


# ------------------------------------------- the incumbent must be de-noised (#250)


def _noisy_campaign(seed=3, n=24):
    """A DoE where at least one observation reads well above its own truth."""
    rng = np.random.default_rng(seed)
    U = rng.random((n, 5))
    y_true = simulate_unit(U)
    y_obs = np.maximum(y_true + rng.normal(0, 0.05 * y_true + 0.4), 0.0)
    return fit_gp(U, y_obs, seed=seed), y_true, y_obs


def test_posterior_incumbent_is_below_the_noisy_maximum():
    """The optimizer's curse, on this repo's own simulator.

    ``max(observed)`` is the maximum of noisy draws and is biased upward; the
    posterior mean at the same designs is not. If this ever inverts, the noise model
    ``fit_gp`` fits has stopped doing anything.
    """
    gp, _, y_obs = _noisy_campaign()
    assert posterior_incumbent(gp) < float(y_obs.max())


def test_a_lucky_assay_does_not_stop_the_campaign():
    """The failure the module was built to avoid, reached through the other argument.

    ``stopping.py`` widens the predictive so the rule does not stop early. An
    incumbent inflated by one high reading stops it early anyway, and by more than
    the conformal widening corrects. Here one observation is pushed 3 sigma up: the
    raw-observation incumbent stops, the de-noised one does not.
    """
    gp, _, y_obs = _noisy_campaign()
    mean, sd = gp.predict(gp.X, include_noise=False)

    lucky = float(y_obs.max()) + 3.0 * float(np.mean(sd)) + 5.0
    honest = posterior_incumbent(gp)

    assert stop_decision(mean, sd, lucky, epsilon=2.0, delta=0.05).stop
    assert not stop_decision(mean, sd, honest, epsilon=2.0, delta=0.05).stop


def test_the_incumbent_ignores_the_noise_it_was_told_about():
    """`include_noise=False` is the point, not an implementation detail."""
    gp, _, _ = _noisy_campaign()
    quiet, _ = gp.predict(gp.X, include_noise=False)
    assert posterior_incumbent(gp) == pytest.approx(float(quiet.max()))
