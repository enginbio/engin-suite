"""Ranking metrics — for reporting a model against the baseline it claims to beat.

Both metrics answer questions a *ranking* model is actually judged on, which is not
the same as regression error. A model can have a mediocre R² and still rank
perfectly, and only the ranking matters when the decision is "which K do we test."
"""
from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.stats import spearmanr


def spearman(a: NDArray[np.float64], b: NDArray[np.float64]) -> float:
    """Spearman rank correlation (scipy), NaN-safe -> 0.0 for degenerate input.

    Degenerate input (a constant score vector) yields NaN from scipy; 0.0 is the
    honest reading — a constant ranker carries no ordering information.
    """
    rho = spearmanr(a, b).statistic
    return float(rho) if np.isfinite(rho) else 0.0


def best_of_k_regret(
    scores: NDArray[np.float64],
    truth: NDArray[np.float64],
    k: int = 1,
) -> float:
    """Regret from picking the top-``k`` by ``scores``: ``truth.max() - best picked``.

    Zero means the ranker's top-k contained the true best. This is the metric that
    matches how the tool is used — you get K foundry slots, and what matters is
    whether the best candidate was in them, not the RMSE of the scores.
    """
    scores = np.asarray(scores, float)
    truth = np.asarray(truth, float)
    if scores.shape != truth.shape:
        raise ValueError(f"scores {scores.shape} and truth {truth.shape} must have equal shape")
    if not 1 <= k <= scores.size:
        raise ValueError(f"k={k} out of range for {scores.size} candidates")
    top = np.argsort(-scores)[:k]
    return float(truth.max() - truth[top].max())


def mean_regret(
    score_fn,
    groups: list[list],
    truth_fn,
    k: int = 1,
) -> float:
    """Mean :func:`best_of_k_regret` across candidate groups.

    ``score_fn(group) -> scores`` and ``truth_fn(group) -> truths``. Averaging over
    many independent groups is what makes a regret comparison meaningful — a single
    group is noise.
    """
    return float(np.mean([best_of_k_regret(score_fn(g), truth_fn(g), k=k) for g in groups]))
