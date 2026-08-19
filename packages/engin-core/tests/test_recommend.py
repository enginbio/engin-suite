"""Recommender: EI math, diversity, and that a recommended batch beats the prior."""

from __future__ import annotations

import numpy as np

from engin_core import (
    expected_improvement,
    fit_gp,
    recommend_batch,
    simulate_unit,
)


def _dataset(seed=0, d=5, n=90):
    rng = np.random.default_rng(seed)
    U = rng.random((n, d))
    y_true = simulate_unit(U)
    y_obs = np.maximum(y_true + rng.normal(0, 0.05 * y_true + 0.4), 0.0)
    return U, y_obs, y_true


def test_expected_improvement_is_sane():
    ei = expected_improvement(np.array([10.0, 5.0, 1.0]), np.array([1.0, 1.0, 1.0]), best=5.0)
    assert np.all(ei >= 0.0)  # EI is non-negative
    assert ei[0] > ei[1] > ei[2]  # higher mean over incumbent -> more EI
    # more uncertainty at the incumbent mean -> more EI (exploration value)
    hi = expected_improvement(np.array([5.0]), np.array([3.0]), best=5.0)[0]
    lo = expected_improvement(np.array([5.0]), np.array([1.0]), best=5.0)[0]
    assert hi > lo


def test_recommend_batch_is_diverse_and_shaped():
    U, y, _ = _dataset(seed=0)
    gp = fit_gp(U, y, seed=0)
    X, mean, sd, ei = recommend_batch(gp, float(y.max()), k=8, seed=1, min_dist=0.15)
    assert X.shape == (8, U.shape[1])
    assert mean.shape == sd.shape == ei.shape == (8,)
    assert np.all(ei >= 0.0)
    # diversity filter respected: all pairwise distances exceed min_dist
    for i in range(len(X)):
        for j in range(i + 1, len(X)):
            assert np.linalg.norm(X[i] - X[j]) > 0.15


def test_recommended_batch_beats_prior_best():
    # Self-validating active learning: simulate the *true* titer of the runs the
    # model recommends and confirm the best of them reaches or exceeds the best
    # *true* titer in the initial DoE. We compare true-vs-true on purpose: the
    # best *observed* run can be a noise-inflated outlier above what is physically
    # achievable, an unfair bar the recommender should not be asked to clear.
    # A 1 g/L tolerance absorbs ties on the optimum plateau.
    TOL = 1.0
    trials = 6
    for seed in range(trials):
        U, y, y_true = _dataset(seed=seed)
        gp = fit_gp(U, y, seed=seed)
        best_true_prior = float(y_true.max())
        X, *_ = recommend_batch(gp, float(y.max()), k=8, seed=seed + 10)
        best_new_true = float(simulate_unit(X).max())
        assert best_new_true >= best_true_prior - TOL, (
            f"seed {seed}: recommended {best_new_true:.1f} < prior true {best_true_prior:.1f} g/L"
        )


# --- The candidate pool is fresh per call (ADR 0011, #224 part 2). ---


def _gp_for_seed_tests(n=40, seed=0):
    rng = np.random.default_rng(seed)
    U = rng.random((n, 5))
    return fit_gp(U, simulate_unit(U), seed=seed)


def test_default_seed_draws_a_fresh_pool_each_call():
    # The property, not a number. `seed=1` used to make the pool byte-identical on
    # every call, so a multi-round campaign searched one fixed lattice and converged
    # to the best point in it -- 110.770 g/L on every data seed, against 113.550 when
    # the pool varied. ADR 0011 accepted defaulting to None.
    gp = _gp_for_seed_tests()
    best = float(gp.predict(gp.X)[0].max())
    a, *_ = recommend_batch(gp, best, k=8)
    b, *_ = recommend_batch(gp, best, k=8)
    assert not np.array_equal(a, b), "default seed must not return an identical batch"


def test_an_explicit_seed_still_reproduces_exactly():
    # Reproducibility is not lost, it is opt-in. This is the half of ADR 0011 that
    # someone would otherwise assume was traded away.
    gp = _gp_for_seed_tests()
    best = float(gp.predict(gp.X)[0].max())
    a, *_ = recommend_batch(gp, best, k=8, seed=7)
    b, *_ = recommend_batch(gp, best, k=8, seed=7)
    assert np.array_equal(a, b)
    c, *_ = recommend_batch(gp, best, k=8, seed=8)
    assert not np.array_equal(a, c), "different seeds must give different pools"


def test_recommendation_never_repeats_a_design_already_run():
    """The filter's second memory (#224 part 1).

    This is the assertion whose absence let the defect survive: the diversity test
    above checks distances *within* the returned batch, which the filter always
    enforced, and says nothing about the designs already run.
    """
    U, y, _ = _dataset(seed=0)
    gp = fit_gp(U, y, seed=0)
    X, *_ = recommend_batch(gp, float(y.max()), k=8, seed=1, min_dist=0.15)
    for x in X:
        assert np.min(np.linalg.norm(gp.X - x, axis=1)) > 0.15


def test_multi_round_campaign_stops_re_running_measured_conditions():
    """The user-visible symptom, in the units that matter: reactor runs.

    Rounds are run with an explicit fixed ``seed`` so the candidate pool is
    identical every round -- the sharpest version of the trap, and the one where
    the unfixed filter returns the same high-EI points again and again.
    """
    U, y, _ = _dataset(seed=0)
    for _ in range(3):
        gp = fit_gp(U, y, seed=0)
        X, *_ = recommend_batch(gp, float(y.max()), k=8, seed=1, min_dist=0.15)
        for x in X:
            assert np.min(np.linalg.norm(U - x, axis=1)) > 0.15
        y_new = np.maximum(simulate_unit(X), 0.0)
        U = np.vstack([U, X])
        y = np.concatenate([y, y_new])
