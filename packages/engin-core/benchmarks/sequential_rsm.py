"""Sequential response surface methodology -- Box--Wilson, as it is actually run.

``baselines.py`` fits one quadratic to one training split and goes to its optimum.
That is a real method, and on this simulator it beats Engin by 5.4 percentage
points of best-true-titer lift (PR #113, published at the top of
``docs/benchmarks.md``). It is also a *single-round* comparison, and single-round
scoring systematically favours pure exploitation: expected improvement spends part
of every batch on uncertainty it expects to repay in later rounds, and a
one-round benchmark collects the cost while cancelling the repayment.

This module removes that excuse by making the baseline adaptive too. It is the
follow-up ``baselines.py`` said was "worth doing and is not this".

**It did not rescue us.** Over 20 seeds on an identical 120-run budget, RSM leads
the mean at every one of ten rounds and wins 20 of 20 seeds at every round; the
gap narrows from 7.7 percentage points to 3.5 and stops there. So the repayment
mechanism the caveat named is visibly real and the conclusion it was offered to
support is not. That is published in ``docs/benchmarks.md`` rather than tuned
away, which is the same trade the single-round result already made.

## The method, and where it comes from

The method is Box & Wilson (1951). What is followed here is the treatment in the
NIST/SEMATECH e-Handbook of Statistical Methods -- §5.5.3 for the path of
steepest ascent, §5.3.3.6.1 for central composite designs, and the fractional
factorial catalogue in §5.3.3.4.7 for the block itself -- because that is the
account that was actually read while writing this, rather than one recalled.
Four block types cycle:

1. ``factorial`` -- a two-level orthogonal design in a small region of interest
   around the current operating point. For five knobs in eight runs that is the
   catalogued :math:`2^{5-2}_{III}` fraction, generators ``D = AB``, ``E = AC``,
   defining relation ``I = ABD = ACE = BCDE``. A **first-order** model fitted to
   this block gives the local gradient. Resolution III aliases two-factor
   interactions with main effects; that is the standard, accepted trade for a
   screening-and-ascent phase, where only the direction is wanted.
2. ``ascent`` -- runs along the path of steepest ascent,
   :math:`x_i = \\rho\\, b_i / \\lVert b \\rVert` for increasing :math:`\\rho`,
   until the response stops improving. The best point becomes the new centre and
   the cycle restarts, which is how the search travels.
3. ``axial`` -- when the ascent stalls, the two-level block is augmented with
   star points into a **central composite design**, which is what makes the pure
   quadratic terms estimable. :math:`\\alpha = 1` (face-centred, NIST's CCF)
   because the knobs have hard operating limits and the design must stay inside
   them.
4. ``canonical`` -- fit the full second-order model over the region of interest,
   locate the stationary point :math:`x_s = -\\tfrac12 B^{-1} b`, and classify it
   by the eigenvalues of :math:`B`. All-negative eigenvalues mean a maximum and
   that point is the answer. A saddle, a minimum, or a stationary point outside
   the region is not, and extrapolating a fitted surface past the runs that
   support it is the one thing this method warns against -- so the fallback is to
   maximize the surface *subject to staying inside the region*. Both cases fall
   out of seeding a bounded multi-start optimizer with the stationary point.

Then the centre moves to the best run so far, the region shrinks, and the cycle
begins again -- fit, ascend, re-centre, refit.

## Choices made so the baseline is not quietly weakened

- **The second-order fit uses every run inside the region of interest**, not just
  the current block. A practitioner does not discard data. Early in a campaign
  the region grows until it holds enough runs to support 21 coefficients, so the
  first quadratic fit is effectively the global fit ``baselines.py`` already
  does -- this method starts at least as strong as the single-shot one.
- **Steepest ascent is projected onto the feasible directions** when the path
  would immediately leave the cube. Turning the knobs that can still move,
  instead of stalling against a limit, is what anyone running the method does.
- **The region half-width is not tuned to a value that loses.** ``benchmark.py``
  sweeps it and publishes every setting, then reports the *best* one as the
  baseline's headline. Tuning the opponent up is the only safe direction.

Every block is exactly ``k`` runs, so a campaign of ``R`` rounds consumes
``R * k`` runs whichever phase it is in. That is what makes the comparison with a
``k``-point EI batch a comparison of methods rather than of budgets.
"""

from __future__ import annotations

import itertools

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.optimize import minimize

from baselines import RSM, fit_rsm

# Generators for the saturated eight-run resolution III series: three base
# factors at all sign combinations, further factors as products of them
# (NIST/SEMATECH e-Handbook table 3.17). d=5 takes D=AB, E=AC.
_EXTRA_COLUMNS = ((0, 1), (0, 2), (1, 2), (0, 1, 2))


def two_level_design(d: int, runs: int = 8) -> NDArray[np.float64]:
    """A catalogued two-level orthogonal design in coded units, ``(runs, d)`` of +-1.

    ``runs=8`` gives the full :math:`2^3` factorial for ``d <= 3`` and the
    standard fractions for ``d = 4..7`` (:math:`2^{4-1}_{IV}`,
    :math:`2^{5-2}_{III}`, :math:`2^{6-3}_{III}`, :math:`2^{7-4}_{III}`).
    Replicated when ``d`` is smaller than the base, which is a feature: repeated
    points estimate pure error.
    """
    if runs != 8:
        raise ValueError("only the eight-run series is catalogued here")
    if not 1 <= d <= 7:
        raise ValueError(f"no eight-run two-level design for d={d}")
    base = np.array(list(itertools.product((-1.0, 1.0), repeat=3)))
    cols = [base[:, i] for i in range(min(d, 3))]
    for gen in _EXTRA_COLUMNS[: max(0, d - 3)]:
        cols.append(np.prod(base[:, gen], axis=1))
    return np.column_stack(cols)


def stationary_point(model: RSM) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Canonical analysis: the stationary point and the eigenvalues of ``B``.

    Writing the fitted surface as :math:`b_0 + b^T x + x^T B x`, the stationary
    point solves :math:`b + 2Bx = 0`. All eigenvalues negative means a maximum;
    mixed signs a saddle; a near-zero one a ridge. A singular ``B`` (a fit with
    no curvature at all) has no stationary point, reported as ``nan``.
    """
    d = model.d
    b = model.coef[1 : 1 + d]
    B = np.diag(model.coef[1 + d : 1 + 2 * d]).astype(float)
    for (i, j), c in zip(itertools.combinations(range(d), 2), model.coef[1 + 2 * d :], strict=True):
        B[i, j] = B[j, i] = c / 2.0
    eig = np.linalg.eigvalsh(B)
    try:
        xs = np.linalg.solve(2.0 * B, -b)
    except np.linalg.LinAlgError:
        xs = np.full(d, np.nan)
    return xs, eig


def maximize_in_box(
    model: RSM,
    lo: NDArray[np.float64],
    hi: NDArray[np.float64],
    k: int = 8,
    seed: int = 0,
    n_starts: int = 48,
    tol: float = 0.05,
    extra_starts: NDArray[np.float64] | None = None,
) -> NDArray[np.float64]:
    """The ``k`` best distinct maxima of ``model`` inside ``[lo, hi]``.

    The bounded twin of ``baselines.rsm_recommend``: a response surface is only
    trusted inside the region it was fitted over, so the second-order phase
    optimizes there rather than across the whole cube. ``extra_starts`` is how
    the canonical stationary point is offered to the optimizer -- if it is an
    interior maximum, the search lands exactly on it.
    """
    rng = np.random.default_rng(seed)
    bounds = list(zip(lo, hi, strict=True))
    starts = lo + rng.random((n_starts, model.d)) * (hi - lo)
    if extra_starts is not None:
        extra = np.atleast_2d(extra_starts)
        extra = extra[np.all(np.isfinite(extra), axis=1)]
        if len(extra):
            starts = np.vstack([np.clip(extra, lo, hi), starts])

    found: list[tuple[float, NDArray[np.float64]]] = []
    for x0 in starts:
        res = minimize(lambda x: -float(model.predict(x)[0]), x0, method="L-BFGS-B", bounds=bounds)
        found.append((-float(res.fun), np.clip(res.x, lo, hi)))
    found.sort(key=lambda t: -t[0])

    batch: list[NDArray[np.float64]] = []
    for _, x in found:
        if all(np.linalg.norm(x - chosen) > tol for chosen in batch):
            batch.append(x)
        if len(batch) == k:
            break
    if len(batch) < k:
        batch = _fill_around(batch, lo, hi, k, tol)
    return np.array(batch[:k])


def _fill_around(
    batch: list[NDArray[np.float64]],
    lo: NDArray[np.float64],
    hi: NDArray[np.float64],
    k: int,
    tol: float,
) -> list[NDArray[np.float64]]:
    """Complete a short batch with a face-centred star around its best point.

    A fitted surface with one dominant optimum -- a near-planar fit, or a
    converged campaign sitting in a corner -- gives every multi-start the same
    answer, and ``baselines.rsm_recommend`` then pads the batch with copies of
    it. On a deterministic simulator those copies buy nothing at all: eight
    identical runs return one number. Replication is a real technique against
    observation noise, but scoring is on *true* titer here, so this spends the
    spare runs on a small design around the optimum instead. That is the
    confirmation-and-local-exploration step of the method, and it makes the
    baseline stronger; ``baselines.py`` is left as it is, so the published
    single-round number stays reproducible from the code that produced it.
    """
    if not batch:  # nothing to centre on: cannot happen via maximize_in_box
        return batch
    centre = batch[0]
    span = np.maximum(hi - lo, 1e-9)
    for scale in (1.0, 2.0, 4.0):
        for i in range(len(centre)):
            for sign in (-1.0, 1.0):
                if len(batch) >= k:
                    return batch
                x = centre.copy()
                x[i] = np.clip(x[i] + sign * scale * tol * span[i], lo[i], hi[i])
                if all(np.linalg.norm(x - chosen) > 1e-9 for chosen in batch):
                    batch.append(x)
    while len(batch) < k:  # a degenerate box with no room at all
        batch.append(centre.copy())
    return batch


class SequentialRSM:
    """A Box--Wilson campaign: ask for a block of ``k`` runs, tell it the results.

    ``radius`` is the half-width of the region of interest in unit-cube units --
    the "relatively small region" in which a first-order approximation is
    expected to hold. It shrinks by ``shrink`` each time a second-order phase
    completes, which is how the search converges, with ``min_radius`` as the
    floor so the design never collapses below what the observation noise can
    resolve.
    """

    def __init__(
        self,
        U: ArrayLike,
        y: ArrayLike,
        radius: float = 0.20,
        shrink: float = 0.6,
        min_radius: float = 0.05,
        seed: int = 0,
    ) -> None:
        self.U = np.atleast_2d(np.asarray(U, float)).copy()
        self.y = np.asarray(y, float).copy()
        self.d = self.U.shape[1]
        self.radius = float(radius)
        self.shrink = float(shrink)
        self.min_radius = float(min_radius)
        self.seed = int(seed)
        self.round = 0
        self.phase = "factorial"
        self.centre = self.U[int(np.argmax(self.y))].copy()  # current operating point
        self.gradient: NDArray[np.float64] | None = None
        self.history: list[str] = []

    # -- geometry -------------------------------------------------------------

    def _box(self, half_width: float) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """The region of interest, clipped to the cube."""
        return (
            np.clip(self.centre - half_width, 0.0, 1.0),
            np.clip(self.centre + half_width, 0.0, 1.0),
        )

    def _design_centre(self) -> NDArray[np.float64]:
        """A centre the two-level box fits around without any point being clipped.

        Clipping design points destroys the orthogonality the block exists for,
        so the box moves inside the operating limits instead -- which is also
        what happens in a real plant, where a knob simply cannot go past its stop.
        """
        r = min(self.radius, 0.5)
        return np.clip(self.centre, r, 1.0 - r)

    # -- the four block types -------------------------------------------------

    def _factorial_block(self, k: int) -> NDArray[np.float64]:
        r = min(self.radius, 0.5)
        return np.clip(self._design_centre() + r * two_level_design(self.d, k), 0.0, 1.0)

    def _ascent_block(self, k: int) -> NDArray[np.float64]:
        """Points at increasing ``rho`` along the path of steepest ascent."""
        g = self.gradient
        if g is None or not np.any(np.isfinite(g)) or np.allclose(g, 0.0):
            g = np.zeros(self.d)
        g = self._feasible_direction(g)
        if np.allclose(g, 0.0):  # cornered: fall back to a fresh local design
            return self._factorial_block(k)

        rho_max = self._max_step(g)
        rhos = np.linspace(rho_max / k, rho_max, k)
        return np.clip(self.centre + self.radius * rhos[:, None] * g[None, :], 0.0, 1.0)

    def _axial_block(self, k: int) -> NDArray[np.float64]:
        """Face-centred star points, completing the central composite design.

        ``alpha = 1``: NIST's CCF, the variant for factors that cannot be run
        outside their stated range. When ``2d`` star points do not fit the block,
        the least influential factors are dropped -- screening exists to say
        which those are -- and any spare runs replicate the centre, which is what
        gives the design a pure-error estimate and a curvature check.
        """
        r = min(self.radius, 0.5)
        c = self._design_centre()
        order = self._factor_ranking()
        pts = [c + r * s * np.eye(self.d)[i] for i in order for s in (1.0, -1.0)][:k]
        while len(pts) < k:
            pts.append(c.copy())
        return np.clip(np.array(pts), 0.0, 1.0)

    def _canonical_block(self, k: int) -> NDArray[np.float64]:
        """Fit the quadratic over the region of interest and go to its optimum."""
        lo, hi, model = self._region_fit()
        xs, _ = stationary_point(model)
        return maximize_in_box(
            model, lo, hi, k=k, seed=self.seed + 17 * self.round, extra_starts=xs[None, :]
        )

    # -- the pieces those blocks lean on --------------------------------------

    def _feasible_direction(self, g: NDArray[np.float64]) -> NDArray[np.float64]:
        """Zero out gradient components that only push against an operating limit.

        Without this the ascent stalls whenever the current best sits on a face
        of the cube, which on a bounded design space is most of the time. Turning
        the knobs that can still move is what a practitioner does, and it makes
        the baseline stronger, not weaker.
        """
        g = np.asarray(g, float).copy()
        at_hi = (self.centre >= 1.0 - 1e-9) & (g > 0)
        at_lo = (self.centre <= 1e-9) & (g < 0)
        g[at_hi | at_lo] = 0.0
        n = float(np.linalg.norm(g))
        return g / n if n > 1e-12 else np.zeros_like(g)

    def _max_step(self, g: NDArray[np.float64], cap: float = 8.0) -> float:
        """Largest ``rho <= cap`` keeping ``centre + radius*rho*g`` inside the cube.

        Walking off the edge and clipping would spend several runs on the same
        boundary point; spreading the same block over the segment that is
        actually reachable spends the budget on distinct conditions instead.
        """
        limits = [cap]
        for i in range(self.d):
            if g[i] > 1e-12:
                limits.append((1.0 - self.centre[i]) / (self.radius * g[i]))
            elif g[i] < -1e-12:
                limits.append(-self.centre[i] / (self.radius * g[i]))
        return float(max(min(limits), 1e-3))

    def _factor_ranking(self) -> list[int]:
        """Factors ordered by the magnitude of the last first-order effect."""
        if self.gradient is None:
            return list(range(self.d))
        return list(np.argsort(-np.abs(self.gradient)))

    def _region_fit(self) -> tuple[NDArray[np.float64], NDArray[np.float64], RSM]:
        """The region of interest, grown until it supports a second-order fit.

        A quadratic in ``d`` knobs has ``1 + 2d + d(d-1)/2`` coefficients -- 21
        for five -- so the region has to hold comfortably more runs than that or
        the fit interpolates noise. Growing rather than refusing is what keeps
        this method at least as strong as the single-shot baseline: on the first
        pass the region opens out to the whole cube and the fit is exactly the
        global one ``baselines.fit_rsm`` performs.
        """
        n_coef = 1 + 2 * self.d + self.d * (self.d - 1) // 2
        need = n_coef + 5
        half = max(2.0 * self.radius, 0.15)
        while True:
            lo, hi = self._box(half)
            inside = np.all((self.U >= lo - 1e-9) & (self.U <= hi + 1e-9), axis=1)
            if inside.sum() >= need or half >= 1.0:
                break
            half = min(half * 1.5, 1.0)
        if inside.sum() < n_coef:  # exhausted the cube: fit on everything there is
            lo, hi = np.zeros(self.d), np.ones(self.d)
            inside = np.ones(len(self.U), bool)
        return lo, hi, fit_rsm(self.U[inside], self.y[inside])

    # -- the campaign loop ----------------------------------------------------

    def ask(self, k: int = 8) -> NDArray[np.float64]:
        """The next block of ``k`` runs, whichever phase the campaign is in."""
        block = {
            "factorial": self._factorial_block,
            "ascent": self._ascent_block,
            "axial": self._axial_block,
            "canonical": self._canonical_block,
        }[self.phase](k)
        return np.clip(np.atleast_2d(block), 0.0, 1.0)

    def tell(self, U_block: ArrayLike, y_block: ArrayLike) -> None:
        """Record a block's observations and advance the phase."""
        U_block = np.atleast_2d(np.asarray(U_block, float))
        y_block = np.asarray(y_block, float)
        best_before = float(self.y.max())
        phase = self.phase

        self.U = np.vstack([self.U, U_block])
        self.y = np.concatenate([self.y, y_block])
        improved = float(y_block.max()) > best_before

        if phase == "factorial":
            # First-order model on the coded block: the classical Phase I fit.
            # The centre does not move here -- the block exists to measure the
            # gradient *at* the current operating point, and ascent starts there.
            r = min(self.radius, 0.5)
            X = (U_block - self._design_centre()) / r
            A = np.hstack([np.ones((len(X), 1)), X])
            coef, *_ = np.linalg.lstsq(A, y_block, rcond=None)
            self.gradient = coef[1:]
            self.phase = "ascent"
        elif phase == "ascent":
            if improved:
                # Still climbing: move to the best point on the path and take a
                # fresh direction from there.
                self.centre = self.U[int(np.argmax(self.y))].copy()
                self.phase = "factorial"
            else:
                self.phase = "axial"  # ascent exhausted -> second-order phase
        elif phase == "axial":
            # The star is centred where the two-level block was, so the two
            # together are a central composite design. Do not move the centre.
            self.phase = "canonical"
        else:  # canonical
            self.centre = self.U[int(np.argmax(self.y))].copy()
            self.radius = max(self.radius * self.shrink, self.min_radius)
            self.phase = "factorial"

        self.history.append(phase)
        self.round += 1
