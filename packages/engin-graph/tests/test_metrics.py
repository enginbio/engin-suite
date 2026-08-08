"""Ranking metrics: correctness and the degenerate cases that bite."""

from __future__ import annotations

import numpy as np
import pytest

from engin_graph import best_of_k_regret, mean_regret, spearman


def test_spearman_perfect_and_inverted():
    a = np.array([1.0, 2.0, 3.0, 4.0])
    assert spearman(a, a) == pytest.approx(1.0)
    assert spearman(a, -a) == pytest.approx(-1.0)


@pytest.mark.filterwarnings("ignore")  # scipy warns on constant input; that's the case under test
def test_spearman_is_nan_safe_for_constant_input():
    # scipy returns NaN for a constant vector; 0.0 is the honest reading, since a
    # constant ranker carries no ordering information. Propagating NaN would poison
    # any downstream comparison silently.
    assert spearman(np.ones(5), np.arange(5.0)) == 0.0


def test_regret_is_zero_when_top_pick_is_best():
    scores = np.array([0.1, 0.9, 0.3])
    truth = np.array([0.2, 0.8, 0.5])
    assert best_of_k_regret(scores, truth, k=1) == pytest.approx(0.0)


def test_regret_measures_the_gap_to_the_oracle():
    scores = np.array([0.9, 0.1])
    truth = np.array([0.2, 0.8])
    assert best_of_k_regret(scores, truth, k=1) == pytest.approx(0.6)


def test_regret_is_monotone_in_k():
    rng = np.random.default_rng(0)
    scores, truth = rng.normal(size=20), rng.normal(size=20)
    regrets = [best_of_k_regret(scores, truth, k=k) for k in (1, 3, 5, 20)]
    # pairwise: deliberately one shorter, so strict=False is correct here
    assert all(a >= b for a, b in zip(regrets, regrets[1:], strict=False))
    assert regrets[-1] == pytest.approx(0.0)  # k = n always contains the best


def test_regret_rejects_bad_shapes_and_k():
    with pytest.raises(ValueError, match="equal shape"):
        best_of_k_regret(np.zeros(3), np.zeros(4))
    with pytest.raises(ValueError, match="out of range"):
        best_of_k_regret(np.zeros(3), np.zeros(3), k=0)
    with pytest.raises(ValueError, match="out of range"):
        best_of_k_regret(np.zeros(3), np.zeros(3), k=4)


def test_mean_regret_averages_across_groups():
    groups = [[0, 1], [2, 3]]
    scores = {0: 1.0, 1: 0.0, 2: 0.0, 3: 1.0}
    truth = {0: 1.0, 1: 0.0, 2: 1.0, 3: 0.0}
    # group 1: picks the best (regret 0). group 2: picks the worst (regret 1).
    got = mean_regret(
        lambda g: np.array([scores[i] for i in g]),
        groups,
        lambda g: np.array([truth[i] for i in g]),
    )
    assert got == pytest.approx(0.5)
