"""The simpler approaches Engin says it beats, implemented so they can beat it.

`docs/benchmarks.md` promised five baselines and shipped one -- an
expected-improvement batch against a random batch -- until 2026-08-13, when the
D23 evidence pass found the table describing a plan in the present tense (#81).
The table now marks what is built. This module is how that column starts moving.

**Response surface methodology first**, because it is the one a process engineer
would actually reach for and the one the front page names. RSM is not a straw man:
on a smooth low-dimensional surface a fitted quadratic is a strong model, it is
cheap, and it has decades of practice behind it. If it wins here, that belongs in
the published table beside the losses -- a benchmark suite that always favours its
author is not evidence, and this project has said so in three documents.

## What is implemented

``fit_rsm`` fits the classical second-order model -- intercept, linear, pure
quadratic and two-factor interaction terms -- by least squares. For five knobs
that is 21 coefficients, which a 70-run training split supports comfortably.

``rsm_recommend`` optimizes the fitted surface over the unit cube from many random
starts and returns the ``k`` best distinct optima. That is the batch analogue of
what RSM is used for in practice: fit, find the stationary point, run there.

## What is deliberately not implemented

No sequential RSM (steepest ascent, then refit, then a central-composite design
around the new centre). That is how RSM is really run and it would be a stronger
baseline, but it is a *different experiment* -- an adaptive method against an
adaptive method, over multiple rounds. This module compares single-shot design
choice from one campaign, which is what ``benchmark.py`` measures. Making the
comparison multi-round is worth doing and is not this.
"""

from __future__ import annotations

import itertools

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.optimize import minimize


def quadratic_features(U: ArrayLike) -> NDArray[np.float64]:
    """Second-order design matrix: 1, x_i, x_i^2, x_i x_j."""
    U = np.atleast_2d(np.asarray(U, float))
    n, d = U.shape
    blocks = [np.ones((n, 1)), U, U**2]
    if d > 1:
        pairs = [U[:, i] * U[:, j] for i, j in itertools.combinations(range(d), 2)]
        blocks.append(np.column_stack(pairs))
    return np.hstack(blocks)


class RSM:
    """A fitted second-order response surface."""

    def __init__(self, coef: NDArray[np.float64], d: int) -> None:
        self.coef = coef
        self.d = d

    def predict(self, U: ArrayLike) -> NDArray[np.float64]:
        return quadratic_features(U) @ self.coef


def fit_rsm(U: ArrayLike, y: ArrayLike) -> RSM:
    """Least-squares fit of the classical second-order model.

    ``lstsq`` rather than a regularized fit on purpose: textbook RSM is ordinary
    least squares, and handicapping the baseline with a penalty it does not
    normally carry would make the comparison flattering rather than fair.
    """
    U = np.atleast_2d(np.asarray(U, float))
    coef, *_ = np.linalg.lstsq(quadratic_features(U), np.asarray(y, float), rcond=None)
    return RSM(coef, U.shape[1])


def rsm_recommend(
    model: RSM, k: int = 8, seed: int = 0, n_starts: int = 64, tol: float = 0.05
) -> NDArray[np.float64]:
    """The ``k`` best distinct maxima of the fitted surface on the unit cube.

    Multi-start L-BFGS-B, deduplicated by ``tol`` in design space so a batch is
    genuinely ``k`` different conditions rather than one optimum found ``k`` times.
    Falls back to filling from the ranked starts if the surface has fewer than
    ``k`` distinct optima, which a near-planar fit does.
    """
    rng = np.random.default_rng(seed)
    bounds = [(0.0, 1.0)] * model.d
    found: list[tuple[float, NDArray[np.float64]]] = []
    for x0 in rng.random((n_starts, model.d)):
        res = minimize(lambda x: -float(model.predict(x)[0]), x0, method="L-BFGS-B", bounds=bounds)
        found.append((-float(res.fun), np.clip(res.x, 0.0, 1.0)))

    found.sort(key=lambda t: -t[0])
    batch: list[NDArray[np.float64]] = []
    for _, x in found:
        if all(np.linalg.norm(x - chosen) > tol for chosen in batch):
            batch.append(x)
        if len(batch) == k:
            break
    while len(batch) < k:  # near-planar surface: pad with the best remaining starts
        batch.append(found[len(batch)][1])
    return np.array(batch)
