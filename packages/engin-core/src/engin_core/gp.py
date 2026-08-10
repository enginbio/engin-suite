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
entirely (that path covers ~0.62 at a nominal 0.90). Two honest fixes:

- :func:`split_conformal_multiplier` -- the sd-scaled (heteroscedastic) split
  conformal we prefer, because the GP gives a per-point sd. This is the classical
  normalized nonconformity measure (Papadopoulos/Gammerman/Vovk), normalizing by
  the model's own predictive sd; we keep the thin multiplier form so intervals
  stay ``mean +/- q*sd``.
- :func:`mapie_split_interval` -- a library-backed (MAPIE) constant-width split
  conformal, exposed as an honest baseline / cross-check.
"""

from __future__ import annotations

import warnings

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.stats import norm
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


def split_conformal_multiplier(
    y_cal: ArrayLike,
    mean_cal: ArrayLike,
    sd_cal: ArrayLike,
    level: float = 0.90,
) -> float:
    """Interval multiplier ``q`` so that ``mean +/- q*sd`` has ~``level`` coverage.

    Split conformal on the *normalized* residual ``|y - mean| / sd``, taking the
    finite-sample conformal quantile of the calibration scores. Distribution-free
    -- no normality assumption -- and heteroscedastic because it rides the GP's
    per-point sd.

    This is the classical **normalized nonconformity measure** of Papadopoulos,
    Gammerman and Vovk, ``R_i = |y_i - yhat_i| / sigma_i``, with ``sigma_i`` taken
    from the model's own predictive sd.

    ref: papadopoulos-normalized-nonconformity

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
    lvl = min(np.ceil((n + 1) * level) / n, 1.0)  # finite-sample conformal level
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
