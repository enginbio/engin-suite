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


def _is_far_enough(
    x: NDArray[np.float64],
    candidates: NDArray[np.float64],
    picks: list[int],
    already_run: NDArray[np.float64],
    min_dist: float,
) -> bool:
    """Is ``x`` further than ``min_dist`` from this batch's picks *and* from run designs?

    Shared by both recommenders (#224) so the two cannot drift apart again -- they
    previously differed on the boundary (``>`` here, ``>=`` in the cost recommender)
    as well as on whether ``already_run`` was consulted at all, which it was not.

    ``already_run`` is ``gp.X``: the designs the user has data for. Excluding their
    neighbourhood is what stops a multi-round campaign spending reactor time
    re-running conditions it has already measured.
    """
    if any(np.linalg.norm(x - candidates[p]) <= min_dist for p in picks):
        return False
    if len(already_run) and np.min(np.linalg.norm(already_run - x, axis=1)) <= min_dist:
        return False
    return True


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

    **The diversity filter has two memories, and it used to have one.** A candidate
    must sit further than ``min_dist`` from the other picks in this batch *and* from
    every design already in ``gp.X``. Only the first was checked until 2026-08-19
    (#224), so a multi-round campaign re-proposed conditions it already had data
    for -- up to 39 of 64 runs by round 3 on the bundled simulator.

    That is a waste measured in reactor-days rather than in titer: adding the check
    removes the repeats and recovers no titer at all, because the repeated designs
    carried EI that had already collapsed toward zero.

    **This is not a "never repeat" rule**, and it should not become one. Replication
    is a legitimate policy under observation noise, and ``fit_gp`` does fit a real
    ``WhiteKernel``. What is excluded is *silent, unintended* repetition produced by
    a filter with no memory; deliberate replication belongs behind an explicit
    option, not behind the absence of a distance check.

    ``min_dist`` is applied with the same strict ``>`` here and in
    :func:`engin_core.tea.recommend_batch_by_cost`, which previously disagreed on
    the boundary.

    Note ``seed`` defaults to a fixed value, so the candidate pool is identical on
    every call. That is deliberate for reproducibility of a *single* call and is a
    trap across a campaign -- vary it per round, as
    ``benchmarks/benchmark.py`` does. Tracked separately in #224.
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
        if _is_far_enough(x, C, picks, gp.X, min_dist):
            picks.append(int(idx))
        if len(picks) == k:
            break
    picks_arr = np.array(picks)
    return C[picks_arr], mean[picks_arr], sd[picks_arr], ei[picks_arr]
