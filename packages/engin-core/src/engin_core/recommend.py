"""Active-learning next-batch recommender (pure numpy).

Expected Improvement toward maximum titer, used to recommend the next DoE batch
with a diversity filter so the recommended runs are worth doing (high expected
titer *and* informative), not eight near-duplicates of the current best.

All quantities here are in **physical titer units (g/L)**: the GP predictive
mean/sd and the incumbent ``best_y`` share one unit system, so the improvement
term ``mean - best`` and the exploration term ``sd * phi(z)`` are dimensionally
consistent and EI genuinely balances exploitation against exploration.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .gp import GP, _Phi, _phi


def expected_improvement(
    mean: ArrayLike, sd: ArrayLike, best: float, xi: float = 0.01
) -> NDArray[np.float64]:
    """EI toward *maximizing* titer over the current best.

    ``mean``, ``sd`` and ``best`` must all be in the same units (g/L). ``xi``
    trades off exploitation vs exploration (larger -> more exploratory).
    """
    mean = np.asarray(mean, float)
    sd = np.maximum(np.asarray(sd, float), 1e-9)
    imp = mean - best - xi
    z = imp / sd
    return imp * _Phi(z) + sd * _phi(z)


def recommend_batch(
    gp: GP,
    best_y: float,
    k: int = 8,
    pool: int = 4000,
    seed: int = 1,
    min_dist: float = 0.15,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Rank a large candidate pool by EI; greedily pick ``k`` with a diversity filter.

    ``best_y`` is the best *observed* titer so far, in g/L (physical units) --
    the same units the GP predicts in. Returns ``(X, mean, sd, ei)`` for the
    picked points, where ``X`` are unit-cube design points and ``mean``/``sd``
    are the predictive titer (g/L).
    """
    rng = np.random.default_rng(seed)
    d = gp.X.shape[1]
    C = rng.random((pool, d))
    mean, sd = gp.predict(C, include_noise=False)
    ei = expected_improvement(mean, sd, best_y)
    order = np.argsort(-ei)
    picks: list[int] = []
    for idx in order:
        x = C[idx]
        if all(np.linalg.norm(x - C[p]) > min_dist for p in picks):
            picks.append(int(idx))
        if len(picks) == k:
            break
    picks_arr = np.array(picks)
    return C[picks_arr], mean[picks_arr], sd[picks_arr], ei[picks_arr]
