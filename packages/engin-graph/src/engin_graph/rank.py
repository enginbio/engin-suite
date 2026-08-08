"""Calibrated ranking head: graph embedding -> ridge -> split-conformal interval.

The head is a scikit-learn ``Ridge`` on the standardized embedding. The interval is
**split-conformal**, reusing ``engin_core.split_conformal_multiplier`` so the whole
suite shares one calibrated-uncertainty vocabulary rather than each package inventing
its own notion of "confident".

The ridge residual is homoscedastic, so the calibrated interval is constant-width.
That is a property of this head, not of conformal prediction — a heteroscedastic head
would feed a per-point ``sd`` to the same multiplier and get varying widths.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from engin_core import split_conformal_multiplier
from numpy.typing import NDArray
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .embed import GCNEmbedder
from .featurize import GraphFeaturizer


class ConformalRankingHead:
    """Ridge regressor on precomputed embeddings + split-conformal interval."""

    def __init__(self, lam: float = 1.0) -> None:
        self._model = make_pipeline(StandardScaler(), Ridge(alpha=lam))
        self._res_sd: float | None = None
        self.q: float | None = None

    def fit(self, Phi: NDArray[np.float64], y: NDArray[np.float64]) -> ConformalRankingHead:
        self._model.fit(Phi, y)
        self._res_sd = float(np.std(y - self._model.predict(Phi)) + 1e-9)
        return self

    def predict(self, Phi: NDArray[np.float64]) -> NDArray[np.float64]:
        return self._model.predict(Phi)

    def calibrate(
        self, Phi: NDArray[np.float64], y: NDArray[np.float64], level: float = 0.90
    ) -> ConformalRankingHead:
        if self._res_sd is None:
            raise RuntimeError("call fit() before calibrate()")
        mean = self.predict(Phi)
        sd = np.full_like(np.asarray(y, float), self._res_sd)  # homoscedastic ridge residual
        self.q = split_conformal_multiplier(y, mean, sd, level=level)
        return self

    def half_width(self) -> float:
        """Calibrated interval half-width (constant, for this head)."""
        if self.q is None or self._res_sd is None:
            raise RuntimeError("call calibrate() before requesting an interval")
        return self.q * self._res_sd


class GraphRanker:
    """Embed graph-like objects, rank them, and report a calibrated interval.

    The usual entry point. A domain layer subclasses this only to supply ``d_in`` and
    to pull labels off its own objects; the model itself is domain-agnostic.
    """

    def __init__(
        self,
        d_in: int,
        h: int = 16,
        lam: float = 1.0,
        embed_seed: int = 0,
        featurizer: GraphFeaturizer | None = None,
    ) -> None:
        self.embedder = GCNEmbedder(d_in=d_in, h=h, seed=embed_seed, featurizer=featurizer)
        self.head = ConformalRankingHead(lam=lam)

    @property
    def q(self) -> float | None:
        """The conformal multiplier, once calibrated."""
        return self.head.q

    def fit(self, objs: list[Any], y: NDArray[np.float64]) -> GraphRanker:
        self.head.fit(self.embedder.matrix(objs), np.asarray(y, float))
        return self

    def predict(self, objs: list[Any]) -> NDArray[np.float64]:
        """Predicted target (the ranking score)."""
        return self.head.predict(self.embedder.matrix(objs))

    def calibrate(
        self, objs: list[Any], y: NDArray[np.float64], level: float = 0.90
    ) -> GraphRanker:
        """Split-conformal calibration of the interval."""
        self.head.calibrate(self.embedder.matrix(objs), np.asarray(y, float), level=level)
        return self

    def half_width(self) -> float:
        """Calibrated interval half-width."""
        return self.head.half_width()

    def predict_interval(
        self, objs: list[Any]
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """``(lower, upper)`` calibrated prediction interval per object."""
        mean = self.predict(objs)
        hw = self.half_width()
        return mean - hw, mean + hw
