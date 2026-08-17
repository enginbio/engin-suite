"""Stop/continue recommendation (#18).

The properties worth pinning are the ones that make this a *calibrated* rule
rather than a threshold with extra steps: the calibration widens rather than
narrows, the combination across candidates errs toward continuing, and the
uncalibrated case says so out loud.
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.stats import norm

from engin_core.stopping import StopDecision, ei_below_threshold, headroom, stop_decision


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


def test_more_candidates_can_only_increase_the_chance_something_is_left():
    """Independence across candidates is the conservative direction: adding a
    candidate must not make the rule keener to stop."""
    one = stop_decision([9.0], [1.0], best=10.0, epsilon=0.0, delta=0.05)
    many = stop_decision([9.0] * 5, [1.0] * 5, best=10.0, epsilon=0.0, delta=0.05)
    assert many.p_worthwhile > one.p_worthwhile
    assert many.n_candidates == 5


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
