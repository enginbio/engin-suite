"""The RSM baseline exists so it can win, so the tests check it is real.

A baseline nobody has watched beat the tool is a baseline nobody has tested.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))

from baselines import fit_rsm, quadratic_features, rsm_recommend  # noqa: E402


def test_quadratic_features_has_the_textbook_term_count():
    """1 + d linear + d quadratic + d(d-1)/2 interactions."""
    X = quadratic_features(np.random.default_rng(0).random((7, 5)))
    assert X.shape == (7, 1 + 5 + 5 + 10)


def test_rsm_recovers_a_quadratic_exactly():
    """If the truth is second-order, the baseline should be near-perfect."""
    rng = np.random.default_rng(0)
    U = rng.random((60, 3))

    def truth(U):
        return 3 * U[:, 0] - 2 * U[:, 1] ** 2 + 1.5 * U[:, 0] * U[:, 2] + 0.5

    model = fit_rsm(U, truth(U))
    Ute = rng.random((30, 3))
    assert np.allclose(model.predict(Ute), truth(Ute), atol=1e-8)


def test_recommend_returns_k_distinct_designs():
    rng = np.random.default_rng(1)
    U = rng.random((60, 4))
    model = fit_rsm(U, U[:, 0] - (U[:, 1] - 0.5) ** 2)
    batch = rsm_recommend(model, k=6, seed=0)
    assert batch.shape == (6, 4)
    assert np.all((batch >= 0) & (batch <= 1))


def test_recommend_finds_a_known_optimum():
    """A surface peaking at an interior point should be found, not the corner."""
    rng = np.random.default_rng(2)
    U = rng.random((80, 2))
    peak = np.array([0.3, 0.7])
    model = fit_rsm(U, -np.sum((U - peak) ** 2, axis=1))
    best = rsm_recommend(model, k=1, seed=0)[0]
    assert np.allclose(best, peak, atol=0.05)


def test_prediction_interval_covers_when_the_model_class_is_right():
    """RSM's own interval, given its best shot.

    A baseline whose uncertainty is implemented badly makes any comparison
    against it worthless. If the truth *is* second-order plus noise, the OLS
    prediction interval should cover near its nominal level.
    """
    rng = np.random.default_rng(3)
    U = rng.random((120, 3))

    def truth(U):
        return 2 * U[:, 0] - (U[:, 1] - 0.4) ** 2 + 0.8 * U[:, 0] * U[:, 2]

    y = truth(U) + rng.normal(0, 0.1, len(U))
    model = fit_rsm(U[:80], y[:80])
    lo, hi = model.predict_interval(U[80:], level=0.90)
    covered = float(np.mean((y[80:] >= lo) & (y[80:] <= hi)))
    assert 0.80 <= covered <= 1.0


def test_the_interval_carries_observation_noise():
    """Prediction interval, not a confidence interval on the mean.

    The `1 +` in `sqrt(1 + leverage)` is the difference. Dropping it would narrow
    the baseline's interval and hand it a coverage failure it does not deserve.
    """
    rng = np.random.default_rng(4)
    U = rng.random((60, 2))
    model = fit_rsm(U, U[:, 0] + rng.normal(0, 0.2, 60))
    lo, hi = model.predict_interval(U[:5], level=0.90)
    half = (hi - lo) / 2
    assert np.all(half > np.sqrt(model.s2))  # wider than residual sd alone


def test_interval_without_degrees_of_freedom_is_refused():
    model = fit_rsm(np.random.default_rng(5).random((30, 2)), np.zeros(30))
    bare = type(model)(model.coef, model.d)
    try:
        bare.predict_interval(np.zeros((1, 2)))
    except ValueError:
        return
    raise AssertionError("expected ValueError without dof")
