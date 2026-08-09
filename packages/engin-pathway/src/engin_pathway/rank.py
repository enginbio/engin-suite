"""Manufacturability ranker: graph embedding -> ridge head -> calibrated interval.

The head is a scikit-learn ``Ridge`` on the graph embedding (standardized). The
interval is **split-conformal**, reusing ``engin_core.split_conformal_multiplier``
so the whole suite shares one calibrated-uncertainty vocabulary — here the ridge
residual is homoscedastic, so the calibrated interval is constant-width. Ranking
quality is measured with Spearman ρ (scipy) against the honest baseline the wedge
must beat: **step-count** (fewer steps assumed better).
"""

from __future__ import annotations

import numpy as np
from engin_core import split_conformal_multiplier
from numpy.typing import NDArray
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .embed import GraphEmbedder
from .schema import Route


def labels(routes: list[Route]) -> NDArray[np.float64]:
    """Ground-truth manufacturability for labeled routes; raises if any is missing."""
    if any(r.manufacturability is None for r in routes):
        raise ValueError("all routes must be labeled (manufacturability is not None)")
    return np.array([r.manufacturability for r in routes], float)


def step_counts(routes: list[Route]) -> NDArray[np.float64]:
    """Number of steps per route (the step-count heuristic's raw signal)."""
    return np.array([r.n_steps for r in routes], float)


def spearman(a: NDArray[np.float64], b: NDArray[np.float64]) -> float:
    """Spearman rank correlation (scipy), NaN-safe -> 0.0 for degenerate input."""
    rho = spearmanr(a, b).statistic
    return float(rho) if np.isfinite(rho) else 0.0


class PathwayRanker:
    """Rank routes by predicted manufacturability, with a calibrated interval."""

    def __init__(self, lam: float = 1.0, embed_seed: int = 0) -> None:
        self.embedder = GraphEmbedder(seed=embed_seed)
        self._model = make_pipeline(StandardScaler(), Ridge(alpha=lam))
        self._res_sd: float | None = None
        self.q: float | None = None

    def fit(self, routes: list[Route]) -> PathwayRanker:
        Phi = self.embedder.matrix(routes)
        y = labels(routes)
        self._model.fit(Phi, y)
        self._res_sd = float(np.std(y - self._model.predict(Phi)) + 1e-9)
        return self

    def predict(self, routes: list[Route]) -> NDArray[np.float64]:
        """Predicted manufacturability (the ranking score)."""
        return self._model.predict(self.embedder.matrix(routes))

    def calibrate(self, routes: list[Route], level: float = 0.90) -> PathwayRanker:
        """Split-conformal calibration of the (constant-width) interval."""
        y = labels(routes)
        mean = self.predict(routes)
        sd = np.full_like(y, self._res_sd)  # homoscedastic ridge residual
        self.q = split_conformal_multiplier(y, mean, sd, level=level)
        return self

    def half_width(self) -> float:
        """Calibrated 90% interval half-width (constant)."""
        if self.q is None:
            raise RuntimeError("call calibrate() before requesting an interval")
        return self.q * self._res_sd

    def predict_interval(
        self, routes: list[Route]
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """``(lower, upper)`` calibrated 90% prediction interval per route."""
        mean = self.predict(routes)
        hw = self.half_width()
        return mean - hw, mean + hw
