"""engin-pathway: metabolic route manufacturability ranking.

Stage [3] of the engin strain-to-scale suite. Rank candidate routes to a target by
predicted *manufacturability* (not just feasibility), with a calibrated interval,
so a team spends its foundry cycles on the routes most likely to hit titer. A graph
model reads route structure (esp. the worst step) to recover the signal step-count
misses. A thin domain layer over ``engin_core``'s conformal calibration.
"""
from __future__ import annotations

from .embed import GraphEmbedder
from .rank import PathwayRanker, labels, spearman, step_counts
from .schema import FEATURES, Route, Step
from .simulate import make_dataset, sample_route

__version__ = "0.1.0"

__all__ = [
    "Step",
    "Route",
    "FEATURES",
    "GraphEmbedder",
    "PathwayRanker",
    "labels",
    "step_counts",
    "spearman",
    "make_dataset",
    "sample_route",
    "__version__",
]
