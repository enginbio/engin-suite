"""Manufacturability ranker — the metabolic domain layer over ``engin-graph``.

The model (graph embedding → ridge head → split-conformal interval) lives in
``engin_graph.GraphRanker``. What's domain-specific, and therefore what stays here:

- pulling the ``manufacturability`` label off a :class:`~engin_pathway.schema.Route`
- **step count**, the honest baseline this wedge must beat (fewer steps assumed
  better) — the heuristic a practitioner uses today, and the thing the graph model
  has to outrank to justify existing

``spearman`` is re-exported from ``engin_graph`` so the suite reports ranking quality
one way; import it from either place.
"""
from __future__ import annotations

import numpy as np
from engin_graph import GraphRanker, spearman
from numpy.typing import NDArray

from .schema import FEATURES, Route

__all__ = ["labels", "step_counts", "spearman", "PathwayRanker"]


def labels(routes: list[Route]) -> NDArray[np.float64]:
    """Ground-truth manufacturability for labeled routes; raises if any is missing."""
    if any(r.manufacturability is None for r in routes):
        raise ValueError("all routes must be labeled (manufacturability is not None)")
    return np.array([r.manufacturability for r in routes], float)


def step_counts(routes: list[Route]) -> NDArray[np.float64]:
    """Number of steps per route (the step-count heuristic's raw signal)."""
    return np.array([r.n_steps for r in routes], float)


class PathwayRanker(GraphRanker):
    """Rank routes by predicted manufacturability, with a calibrated interval.

    Takes routes rather than ``(objects, labels)`` — the label rides along on the
    ``Route``, so the domain API stays a single argument.
    """

    def __init__(self, lam: float = 1.0, embed_seed: int = 0) -> None:
        super().__init__(d_in=len(FEATURES), lam=lam, embed_seed=embed_seed)

    def fit(self, routes: list[Route]) -> PathwayRanker:
        super().fit(routes, labels(routes))
        return self

    def calibrate(self, routes: list[Route], level: float = 0.90) -> PathwayRanker:
        """Split-conformal calibration of the (constant-width) interval."""
        super().calibrate(routes, labels(routes), level=level)
        return self
