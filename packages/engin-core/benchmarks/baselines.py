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

## What this module deliberately does not implement -- and where it now lives

~~No sequential RSM (steepest ascent, then refit, then a central-composite design
around the new centre). That is how RSM is really run and it would be a stronger
baseline, but it is a *different experiment* -- an adaptive method against an
adaptive method, over multiple rounds. This module compares single-shot design
choice from one campaign, which is what ``benchmark.py`` measures. Making the
comparison multi-round is worth doing and is not this.~~

Superseded 2026-08-14: that different experiment is built, in
``sequential_rsm.py``, and reported by ``benchmark.py --multi-round``. The
reasoning above still describes *this* module correctly -- it remains the
single-shot baseline, and the single-round numbers it produced stay in
``docs/benchmarks.md`` unchanged -- but the note is no longer a statement about
what the repository contains.
"""

from __future__ import annotations

import itertools

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.optimize import minimize
from scipy.stats import t as student_t


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
    """A fitted second-order response surface, with its textbook interval."""

    def __init__(
        self,
        coef: NDArray[np.float64],
        d: int,
        s2: float = float("nan"),
        xtx_inv: NDArray[np.float64] | None = None,
        dof: int = 0,
    ) -> None:
        self.coef = coef
        self.d = d
        self.s2 = s2  # residual variance, RSS / dof
        self.xtx_inv = xtx_inv
        self.dof = dof

    def predict(self, U: ArrayLike) -> NDArray[np.float64]:
        return quadratic_features(U) @ self.coef

    def predict_interval(
        self, U: ArrayLike, level: float = 0.90
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """The OLS **prediction** interval -- the fair comparison for a forecast.

        ``yhat +/- t * s * sqrt(1 + x' (X'X)^-1 x)``. The ``1 +`` is what makes
        this a prediction interval rather than a confidence interval on the mean:
        it carries observation noise, which is what a forecast has to cover. Using
        the narrower confidence interval here would hand RSM a coverage failure it
        does not deserve, and the point of a baseline is that it gets its best
        shot.

        **This interval is model-based.** It assumes the second-order model is
        correct and reports what the residual variance implies given that. Where
        the quadratic is wrong, the residuals absorb the bias into ``s2`` rather
        than widening for the right reason -- which is precisely the assumption
        split conformal declines to make, and precisely what this measurement is
        for.
        """
        if self.xtx_inv is None or self.dof <= 0:
            raise ValueError("interval needs a fit with residual degrees of freedom")
        X = quadratic_features(U)
        leverage = np.einsum("ij,jk,ik->i", X, self.xtx_inv, X)
        half = student_t.ppf(0.5 + level / 2, self.dof) * np.sqrt(self.s2 * (1.0 + leverage))
        mean = X @ self.coef
        return mean - half, mean + half


def fit_rsm(U: ArrayLike, y: ArrayLike) -> RSM:
    """Least-squares fit of the classical second-order model.

    ``lstsq`` rather than a regularized fit on purpose: textbook RSM is ordinary
    least squares, and handicapping the baseline with a penalty it does not
    normally carry would make the comparison flattering rather than fair.
    """
    U = np.atleast_2d(np.asarray(U, float))
    y = np.asarray(y, float)
    X = quadratic_features(U)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    n, p = X.shape
    dof = n - p
    resid = y - X @ coef
    s2 = float(resid @ resid / dof) if dof > 0 else float("nan")
    xtx_inv = np.linalg.pinv(X.T @ X)  # pinv: the design can be rank-deficient
    return RSM(coef, U.shape[1], s2=s2, xtx_inv=xtx_inv, dof=dof)


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
