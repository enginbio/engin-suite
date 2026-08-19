"""Model core: calibration (the suite-wide requirement), errors, and attribution."""

from __future__ import annotations

import numpy as np
import pytest
from engin_core import highest_attainable_level

from engin_protein import CalibratedFitnessModel, OneHotPhysicochemical, make_landscape


def _split(epistasis: float = 0.5, n: int = 90, seed: int = 1):
    ls = make_landscape(epistasis=epistasis, seed=0)
    vs = ls.sample_campaign(n, seed=seed).measured()
    return ls, vs[: int(0.6 * n)], vs[int(0.6 * n) :]


def test_intervals_are_calibrated():
    # The suite-wide rule: coverage is asserted in a test, not quoted in a README.
    ls, train, cal = _split()
    model = CalibratedFitnessModel().fit(train).calibrate(cal, level=0.90)
    lib = ls.library(400, seed=7)
    truth = ls.true_fitness(lib)
    scored = model.score(lib)
    lo = np.array([s.lower for s in scored])
    hi = np.array([s.upper for s in scored])
    cover = float(np.mean((truth >= lo) & (truth <= hi)))
    # Conservative side is expected: with a small calibration split, split-conformal
    # takes close to the max residual ratio. Too-wide is the safe failure direction.
    assert 0.85 <= cover <= 1.0


def test_calibration_widens_with_a_higher_level():
    # 0.80 and 0.90 on purpose. This used to compare 0.80 against 0.99, which the
    # 36-variant calibration split cannot support at all (#197): the 0.99 branch
    # fell back to the largest observed score, so the assertion passed by
    # exercising the fallback path while reading as a test of the conformal one.
    # These two map to distinct conformal ranks -- the 30th and 34th smallest
    # score -- so the comparison is between two real quantiles.
    _, train, cal = _split()
    m80 = CalibratedFitnessModel().fit(train).calibrate(cal, level=0.80, warn_below_slack=None)
    m90 = CalibratedFitnessModel().fit(train).calibrate(cal, level=0.90, warn_below_slack=None)
    assert m90.q > m80.q
    assert (m80.level, m90.level) == (0.80, 0.90)
    assert m80.n_calibration == m90.n_calibration == len(cal)


def test_calibrate_refuses_a_level_the_split_cannot_support():
    # The bug this issue is about, now an exception rather than a mislabelled
    # interval. engin-core warns here; this package raises, because the multiplier
    # becomes a ScoredDesign bound the user reads as *the* interval at `level`.
    _, train, cal = _split()
    model = CalibratedFitnessModel().fit(train)
    with pytest.raises(ValueError, match=r"above what \d+ calibration variants can support"):
        model.calibrate(cal, level=0.99)
    # The message carries the fix, not just the complaint.
    with pytest.raises(ValueError, match=r"ceiling is n/\(n\+1\) = 0\.9730"):
        model.calibrate(cal, level=0.99)
    # And the ceiling itself is attainable.
    model.calibrate(cal, level=highest_attainable_level(len(cal)), warn_below_slack=None)
    assert model.q is not None


def test_the_top_of_the_level_range_is_a_plateau():
    # Worth pinning because it makes "higher level always widens" false, and a
    # future edit picking two levels from inside the plateau would look like a
    # regression in the test above rather than a property of small n.
    # At n=36 any level above 35/37 takes the 36th smallest score -- the maximum --
    # so 0.95 and 0.97 are the same interval.
    _, train, cal = _split()
    assert len(cal) == 36
    fitted = CalibratedFitnessModel().fit(train)
    q95 = CalibratedFitnessModel().fit(train).calibrate(cal, level=0.95, warn_below_slack=None).q
    q97 = CalibratedFitnessModel().fit(train).calibrate(cal, level=0.97, warn_below_slack=None).q
    assert q95 == pytest.approx(q97)
    # ...and both sit at the largest calibration score, which is the ceiling of
    # what 36 points can express however high the level goes.
    below = fitted.calibrate(cal, level=0.90, warn_below_slack=None).q
    assert q95 > below


def test_score_requires_calibration():
    _, train, _ = _split()
    model = CalibratedFitnessModel().fit(train)
    with pytest.raises(RuntimeError, match="calibrate"):
        model.score(train[:3])


def test_predict_requires_fit():
    with pytest.raises(RuntimeError, match="fit"):
        CalibratedFitnessModel().predict_raw(["AGSD"])


def test_calibrate_requires_fit():
    _, _, cal = _split()
    with pytest.raises(RuntimeError, match="fit"):
        CalibratedFitnessModel().calibrate(cal)


def test_unmeasured_variants_are_rejected_for_fitting():
    ls = make_landscape(seed=0)
    with pytest.raises(ValueError, match="no fitness"):
        CalibratedFitnessModel().fit(ls.library(10, seed=1))


def test_threshold_probability_is_monotone():
    # A higher bar can never be more likely to clear.
    ls, train, cal = _split()
    model = CalibratedFitnessModel().fit(train).calibrate(cal)
    lib = ls.library(50, seed=8)
    lowbar = np.array([s.prob_above_threshold for s in model.score(lib, threshold=0.3)])
    highbar = np.array([s.prob_above_threshold for s in model.score(lib, threshold=0.8)])
    assert np.all(highbar <= lowbar + 1e-9)


def test_ensemble_sd_is_positive():
    # A zero sd would make EI degenerate and the conformal multiplier infinite.
    _, train, _ = _split()
    model = CalibratedFitnessModel().fit(train)
    _, sd = model.predict(train[:20])
    assert np.all(sd > 0)


def test_position_importance_is_a_distribution_over_positions():
    ls, train, _ = _split()
    imp = CalibratedFitnessModel().fit(train).position_importance()
    assert imp.shape == (ls.length,)
    assert imp.sum() == pytest.approx(1.0)
    assert np.all(imp >= 0)


def test_importance_requires_fit():
    with pytest.raises(RuntimeError, match="fit"):
        CalibratedFitnessModel().position_importance()


def test_interaction_features_change_the_fit():
    _, train, cal = _split(epistasis=0.9)
    plain = CalibratedFitnessModel(interactions=False).fit(train).predict(cal)[0]
    inter = CalibratedFitnessModel(interactions=True).fit(train).predict(cal)[0]
    assert not np.allclose(plain, inter)


def test_descriptor_featurizer_runs():
    _, train, cal = _split()
    model = CalibratedFitnessModel(featurizer=OneHotPhysicochemical(use_descriptors=True))
    model.fit(train).calibrate(cal)
    assert model.q is not None
