"""Uncertainty-aware titer model (scikit-learn GP + conformal calibration).

An ARD-RBF Gaussian Process gives a calibrated predictive distribution over titer
for any design point -- the whole point of the wedge: *forecast titer with
credible intervals, not a point estimate*. The ARD lengthscales double as a
sensitivity readout ("which knobs move titer", see :mod:`engin_core.sensitivity`).

The GP is scikit-learn's :class:`~sklearn.gaussian_process.GaussianProcessRegressor`
(a `Constant * RBF(ARD) + WhiteKernel`, hyperparameters fit by L-BFGS on the exact
log marginal likelihood) rather than a hand-rolled Cholesky GP -- a solved wheel we
no longer reinvent. The normal CDF/PDF come from :mod:`scipy.stats`.

**Calibration is first-class.** A raw GP interval is overconfident here: a
space-filling DoE is "easier" than the future query points the model is asked
about (covariate shift), and the *epistemic* sd ignores observation noise
entirely (that path covers roughly 0.55-0.62 at a nominal 0.90, depending on how
many seeds are averaged -- the spread is real, so read any single figure for it as
an order of magnitude rather than a measurement). Two honest fixes:

- :func:`split_conformal_multiplier` -- the sd-scaled (heteroscedastic) split
  conformal we prefer, because the GP gives a per-point sd. This is the classical
  normalized nonconformity measure (Papadopoulos, Proedrou, Vovk and Gammerman,
  2002), normalizing by the model's own predictive sd; we keep the thin multiplier
  form so intervals stay ``mean +/- q*sd``. Its coverage guarantee is **marginal**
  -- see that function's docstring, because the distinction is easy to overstate
  and this project's argument depends on not overstating it.
- :func:`mapie_split_interval` -- a library-backed (MAPIE) constant-width split
  conformal, exposed as an honest baseline / cross-check.

**Calibration sets are usually small here, and that costs something measurable.**
The coverage a split-conformal interval actually delivers is a *random quantity*
determined by which calibration set you happened to draw; the nominal level is
its average, not its value. :func:`conformal_coverage_interval` reports the
spread, and :func:`smallest_calibration_set` reports the size below which the
requested level is not attainable at all. See #144 -- the regime a first
fermentation campaign lands in is exactly the one where this matters.
"""

from __future__ import annotations

import warnings

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.stats import beta, norm
from sklearn.exceptions import ConvergenceWarning
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel, WhiteKernel


def _Phi(z: ArrayLike) -> NDArray[np.float64]:
    """Standard-normal CDF (kept under this name for the recommender's import)."""
    return norm.cdf(z)


def _phi(z: ArrayLike) -> NDArray[np.float64]:
    """Standard-normal PDF."""
    return norm.pdf(z)


class GP:
    """Thin wrapper over a fitted sklearn GP exposing the engin-core API.

    Attributes
    ----------
    X : training inputs (unit-cube design points).
    ell : ARD lengthscales (per design knob) -- the sensitivity readout.
    ymean, ystd : target mean/scale (physical g/L).
    q90 : conformal interval multiplier, set by a calibration step (else None).
    """

    def __init__(
        self,
        gpr: GaussianProcessRegressor,
        X: ArrayLike,
        ymean: float,
        ystd: float,
        ell: ArrayLike,
        noise_var: float,
    ) -> None:
        self._gpr = gpr
        self.X = np.asarray(X, float)
        self.ymean = float(ymean)
        self.ystd = float(ystd)
        self.ell = np.asarray(ell, float)
        self._noise_var = float(noise_var)  # observation-noise variance, physical g/L^2
        self.q90: float | None = None

    def predict(
        self, Xs: ArrayLike, include_noise: bool = True
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Predictive ``(mean, sd)`` in physical units (g/L).

        ``include_noise=True`` returns the total predictive sd (model + observation
        noise); ``False`` returns the epistemic (model-only) sd. sklearn's
        ``return_std`` is the total sd, so the epistemic part is recovered by
        subtracting the fitted noise variance.
        """
        Xs = np.atleast_2d(np.asarray(Xs, float))
        mean, sd_total = self._gpr.predict(Xs, return_std=True)  # physical, incl. noise
        if include_noise:
            sd = sd_total
        else:
            sd = np.sqrt(np.maximum(sd_total**2 - self._noise_var, 0.0))
        return mean, sd


def fit_gp(X: ArrayLike, y: ArrayLike, seed: int = 0, n_restarts: int = 8) -> GP:
    """Fit an ARD-RBF GP (sklearn, LML-optimized) and return the engin-core wrapper.

    The returned model is *not yet calibrated* -- call
    :func:`split_conformal_multiplier` (preferred) or :func:`conformal_multiplier_oof`
    and store the result on ``gp.q90`` before trusting its intervals.
    """
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    d = X.shape[1]
    kernel = ConstantKernel(1.0, (1e-2, 1e2)) * RBF([0.3] * d, (0.05, 1e2)) + WhiteKernel(
        0.1, (1e-4, 1.0)
    )
    gpr = GaussianProcessRegressor(
        kernel=kernel, normalize_y=True, n_restarts_optimizer=n_restarts, random_state=seed
    )
    with warnings.catch_warnings():
        # A maxed-out lengthscale means the knob is irrelevant, not a fit failure.
        warnings.simplefilter("ignore", ConvergenceWarning)
        gpr.fit(X, y)
    ystd = float(y.std() + 1e-9)
    ell = np.atleast_1d(np.asarray(gpr.kernel_.k1.k2.length_scale, float))
    noise_level = float(gpr.kernel_.k2.noise_level)
    gp = GP(gpr, X, float(y.mean()), ystd, ell, noise_level * ystd**2)
    gp.log_ml_final = float(gpr.log_marginal_likelihood_value_)
    return gp


_FP_SLACK = 1e-12
"""Tolerance for the two integer boundaries below, which land exactly on ties.

Not defensive padding. At the default level these quantities are integer-valued
in exact arithmetic and *not* in binary floating point: ``(9 + 1) * 0.90`` is
``9.000000000000002``, so a bare ``ceil`` returns 10 and declares n=9 short of a
floor that n=9 exactly meets. ``1 - 0.90`` is ``0.09999999999999998``, so a bare
``floor`` of ``(9 + 1) * alpha`` returns 0 rather than 1.

Both errors are ~2e-15, so 1e-12 separates them from any real difference while
being far smaller than one unit of rank. This bit ``split_conformal_multiplier``
before #144 as well: at n=9, level=0.90 it computed a conformal level of
``10 / 9 > 1``, clipped to 1.0, and silently returned ``max(scores)`` for a
calibration set that in fact supports the requested quantile.
"""


def _conformal_rank(n: int, level: float) -> int:
    """The rank ``ceil((n+1) * level)`` of the calibration score to take."""
    return int(np.ceil((n + 1) * level - _FP_SLACK))


def smallest_calibration_set(level: float = 0.90) -> int:
    """Smallest calibration set for which ``level`` is attainable at all.

    Split conformal takes the ``ceil((n+1) * level)``-th smallest calibration
    score. That index has to exist, so ``ceil((n+1) * level) <= n``, which is
    ``n >= level / (1 - level)``. At the default 0.90 that is **n = 9**; at 0.95
    it is 19, and at 0.99 it is 99.

    Below the floor there is no quantile to take and the guarantee is simply
    unavailable -- :func:`split_conformal_multiplier` falls back to the largest
    observed score, which is the widest interval the calibration set can justify
    but is *not* the requested level. It warns when it does so.

    # implements D8; ref: 2018-lei-distribution-free
    """
    if not 0.0 < level < 1.0:
        raise ValueError(f"level must be in (0, 1), got {level}")
    n = max(1, int(np.ceil(level / (1.0 - level) - _FP_SLACK)))
    # The closed form is the answer in exact arithmetic; step to the defining
    # condition so the two never disagree at a boundary.
    while _conformal_rank(n, level) > n:
        n += 1
    while n > 1 and _conformal_rank(n - 1, level) <= n - 1:
        n -= 1
    return n


def conformal_coverage_interval(
    n_cal: int, level: float = 0.90, delta: float = 0.10
) -> tuple[float, float, float]:
    """``(lower, mean, upper)`` on the coverage a calibration set of size ``n_cal`` buys.

    The coverage of a split-conformal interval, *conditional on the calibration
    set*, is not the nominal level -- it is a draw from

    .. math:: \\mathrm{Beta}(n + 1 - l,\\; l), \\qquad l = \\lfloor (n+1)\\alpha \\rfloor

    with :math:`\\alpha = 1 - level`. The nominal level is that distribution's
    mean; any one calibration set gives you a coverage somewhere in its spread.
    The result is Vovk's; the form quoted here is the restatement in Angelopoulos
    and Bates, section 3.2.

    Returns the central ``1 - delta`` interval and the mean. At the default
    ``level=0.90, delta=0.10`` this is the 5th percentile, the mean and the 95th.

    This is the honest answer to "how noisy is my multiplier". Note it is stated
    as a spread on **coverage** rather than on ``q`` itself: the literature
    result is about coverage, and converting it to an interval on the multiplier
    would need a distributional assumption on the scores that split conformal
    exists precisely to avoid.

    Worked numbers at the default 90%, which are the argument for this function
    existing: n=9 (the floor) gives roughly [0.72, 0.99] -- a "90%" interval
    whose true coverage could be 72%. n=50 gives [0.83, 0.96]. n=406, the
    industrial set the quickstart uses, gives [0.876, 0.925].

    # implements D8; ref: 2012-vovk-conditional-validity
    # ref: 2021-angelopoulos-gentle-intro
    """
    n = int(n_cal)
    if n < 1:
        raise ValueError(f"n_cal must be positive, got {n_cal}")
    if not 0.0 < level < 1.0:
        raise ValueError(f"level must be in (0, 1), got {level}")
    alpha = 1.0 - level
    ell = int(np.floor((n + 1) * alpha + _FP_SLACK))
    if ell < 1:
        # Below the floor the Beta is degenerate -- there is no l-th largest
        # score to exclude, so no coverage statement is available.
        return (float("nan"), float("nan"), float("nan"))
    dist = beta(n + 1 - ell, ell)
    return (float(dist.ppf(delta / 2.0)), float(dist.mean()), float(dist.ppf(1.0 - delta / 2.0)))


def split_conformal_multiplier(
    y_cal: ArrayLike,
    mean_cal: ArrayLike,
    sd_cal: ArrayLike,
    level: float = 0.90,
    warn_below_slack: float | None = 0.05,
) -> float:
    """Interval multiplier ``q`` so that ``mean +/- q*sd`` has ~``level`` coverage.

    Split conformal on the *normalized* residual ``|y - mean| / sd``, taking the
    finite-sample conformal quantile of the calibration scores. Distribution-free
    -- no normality assumption -- and heteroscedastic because it rides the GP's
    per-point sd.

    This is the classical **normalized nonconformity measure** of Papadopoulos,
    Proedrou, Vovk and Gammerman (2002), ``R_i = |y_i - yhat_i| / sigma_i``, with
    ``sigma_i`` taken from the model's own predictive sd. The finite-sample split
    conformal guarantee is Lei et al. (2018).

    **The guarantee is marginal, not conditional.** Coverage holds on average over
    the joint distribution of (X, Y) -- not for any particular x, and not for any
    subgroup picked out afterwards. So a per-region coverage number, of the kind
    the out-of-distribution methods page reports, is *not* the theorem being
    honoured region by region: conditional coverage is provably unattainable
    distribution-free without further assumptions. Those numbers are measurements.

    **It is also noisy at small n, and that used to be silent.** Coverage
    conditional on the calibration set is Beta-distributed (see
    :func:`conformal_coverage_interval`), so a small calibration set buys a
    multiplier whose true coverage may sit well away from ``level``. Two warnings
    now fire:

    - **Below** :func:`smallest_calibration_set`, the requested level is not
      attainable at all -- the conformal index does not exist and this function
      falls back to ``max(scores)``. That fallback was previously silent, which
      on a project whose central claim is honest intervals was the worst place
      for a silent degradation.
    - **Above the floor but still small**, the coverage spread is reported.
      ``warn_below_slack`` is the half-width of the central 90% coverage interval
      above which a warning fires; pass ``None`` to silence it.

    ``warn_below_slack=0.05`` is a **default, not a finding.** The computation
    behind it is the cited Beta result; the choice of 0.05 as the point where a
    spread becomes worth interrupting for is editorial, which is why it is a
    parameter rather than a constant.

    # implements D8; ref: 2002-papadopoulos-inductive-confidence
    # ref: 2018-lei-distribution-free

    **Not** the same as MAPIE's ``ResidualNormalisedScore``, despite an earlier
    claim here. That score belongs to the same family but estimates ``sigma_i``
    with a *separate learned model* fitted to log-residuals (conformalized residual
    fitting). Using the GP's own predictive sd needs no second model, which matters
    in the low-N regime this project targets, and is the natural choice when the
    base estimator already emits a principled uncertainty. MAPIE does not offer
    normalize-by-base-model-sd out of the box, which is why this function exists
    rather than wrapping it (D9).
    """
    y_cal = np.asarray(y_cal, float)
    mean_cal = np.asarray(mean_cal, float)
    sd_cal = np.asarray(sd_cal, float)
    scores = np.abs(y_cal - mean_cal) / np.maximum(sd_cal, 1e-9)
    n = len(scores)

    n_min = smallest_calibration_set(level)
    if n < n_min:
        warnings.warn(
            f"calibration set of {n} is below the floor of {n_min} for a "
            f"{level:.0%} split-conformal interval: ceil((n+1)*level) exceeds n, "
            f"so the conformal quantile does not exist. Falling back to the "
            f"largest calibration score, which is the widest interval these {n} "
            f"points justify but does NOT deliver {level:.0%} coverage. "
            f"Collect at least {n_min} calibration points, or lower `level`.",
            UserWarning,
            stacklevel=2,
        )
    elif warn_below_slack is not None:
        lo, _, hi = conformal_coverage_interval(n, level=level)
        if max(hi - level, level - lo) > warn_below_slack:
            warnings.warn(
                f"calibration set of {n} gives a {level:.0%} interval whose true "
                f"coverage lies in roughly [{lo:.2f}, {hi:.2f}] (central 90%, "
                f"Beta(n+1-l, l)). The multiplier is honest on average and noisy "
                f"here. Pass `warn_below_slack=None` to silence, or see "
                f"`conformal_coverage_interval` for the size you need.",
                UserWarning,
                stacklevel=2,
            )

    lvl = min(_conformal_rank(n, level) / n, 1.0)  # finite-sample conformal level
    return float(np.quantile(scores, lvl, method="higher"))


def conformal_multiplier_oof(
    X: ArrayLike, y: ArrayLike, level: float = 0.90, k: int = 5, seed: int = 0
) -> float:
    """Out-of-fold conformal multiplier -- the no-held-out-set fallback.

    Refits the GP on k-1 folds and scores the held-out fold, so the residuals are
    honestly out-of-sample. Prefer :func:`split_conformal_multiplier` when you can
    spare a calibration set; use this when every run is too precious to hold out.
    """
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    n = len(X)
    rng = np.random.default_rng(seed)
    folds = np.array_split(rng.permutation(n), k)
    scores = []
    for f in folds:
        mask = np.ones(n, bool)
        mask[f] = False
        gp = fit_gp(X[mask], y[mask], seed=seed)
        m, sd = gp.predict(X[f], include_noise=True)
        scores.append(np.abs(y[f] - m) / np.maximum(sd, 1e-9))
    return float(np.quantile(np.concatenate(scores), level))


def mapie_split_interval(
    gp: GP,
    X_cal: ArrayLike,
    y_cal: ArrayLike,
    X_new: ArrayLike,
    level: float = 0.90,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Library-backed (MAPIE) split-conformal prediction interval.

    Wraps the already-fitted GP in MAPIE's ``SplitConformalRegressor`` (absolute
    conformity score -> constant-width interval) and returns ``(lower, upper)`` for
    ``X_new`` at coverage ``level``. This is the honest distribution-free baseline;
    :func:`split_conformal_multiplier` is the heteroscedastic variant we ship.
    """
    from mapie.regression import SplitConformalRegressor

    scr = SplitConformalRegressor(
        estimator=gp._gpr, confidence_level=level, conformity_score="absolute", prefit=True
    )
    scr.conformalize(np.asarray(X_cal, float), np.asarray(y_cal, float))
    _, interval = scr.predict_interval(np.atleast_2d(np.asarray(X_new, float)))
    return interval[:, 0, 0], interval[:, 1, 0]


def prob_at_least(mean: ArrayLike, sd: ArrayLike, target: float) -> NDArray[np.float64]:
    """``P(titer >= target)`` under the GP predictive normal."""
    mean = np.asarray(mean, float)
    sd = np.maximum(np.asarray(sd, float), 1e-9)
    return 1.0 - _Phi((target - mean) / sd)
