"""Formulation ranker — the materials domain layer over ``engin-graph``.

Almost nothing is here, and that is the point. The model (graph embedding with
min/max pooling → ridge head → split-conformal interval) lives in
``engin_graph.GraphRanker``, unchanged from what ``engin-pathway`` uses for metabolic
routes. What is domain-specific and therefore stays:

- pulling the ``property_value`` label off a :class:`~engin_materials.schema.Polymer`
- **composition average**, the honest baseline this wedge must beat — the heuristic a
  formulator uses today, and the direct analogue of step-count for routes

If this file were long, the extraction would have failed.
"""

from __future__ import annotations

import numpy as np
from engin_graph import GraphRanker, best_of_k_regret, spearman
from numpy.typing import NDArray

from .schema import MONOMER_FEATURES, Polymer

__all__ = [
    "labels",
    "composition_scores",
    "crosslink_densities",
    "PolymerRanker",
    "spearman",
    "best_of_k_regret",
]

# The composition heuristic weights units the way a formulator would: an average of
# the property-relevant descriptors. Deliberately the same weights the generator uses,
# so the baseline is as strong as it can honestly be made — it is blind to *where* the
# weak unit sits and to topology, not to which features matter.
_COMPOSITION_WEIGHTS = np.array([0.30, 0.20, 0.15, 0.25, 0.10])


def labels(polymers: list[Polymer]) -> NDArray[np.float64]:
    """Ground-truth property for labeled formulations; raises if any is missing."""
    if any(p.property_value is None for p in polymers):
        raise ValueError("all polymers must be labeled (property_value is not None)")
    return np.array([p.property_value for p in polymers], float)


def composition_scores(polymers: list[Polymer]) -> NDArray[np.float64]:
    """The composition-average heuristic — weighted mean over units.

    Blind by construction to which unit is weakest and to crosslink topology.
    """
    w = _COMPOSITION_WEIGHTS / _COMPOSITION_WEIGHTS.sum()
    return np.array([float((p.node_features() @ w).mean()) for p in polymers], float)


def crosslink_densities(polymers: list[Polymer]) -> NDArray[np.float64]:
    """Crosslinks per unit — for inspection and for the topology-blindness test."""
    return np.array([p.crosslink_density for p in polymers], float)


class PolymerRanker(GraphRanker):
    """Rank formulations by predicted property, with a calibrated interval.

    Takes polymers rather than ``(objects, labels)`` — the label rides on the
    ``Polymer``, so the domain API stays a single argument.
    """

    def __init__(self, lam: float = 1.0, embed_seed: int = 0) -> None:
        super().__init__(d_in=len(MONOMER_FEATURES), lam=lam, embed_seed=embed_seed)

    def fit(self, polymers: list[Polymer]) -> PolymerRanker:
        super().fit(polymers, labels(polymers))
        return self

    def calibrate(self, polymers: list[Polymer], level: float = 0.90) -> PolymerRanker:
        """Split-conformal calibration of the interval."""
        super().calibrate(polymers, labels(polymers), level=level)
        return self
