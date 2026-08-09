"""engin-graph: graph embedding + calibrated ranking over structured objects.

The shared graph engine of the engin strain-to-scale suite, extracted from
``engin-pathway`` so any domain whose candidates are graphs can rank them with an
honest interval. Metabolic routes (stage [3]) and polymer structures differ only in
the featurizer; every line of the model is shared.

The load-bearing design choice is **min/max pooling alongside mean**: in these
domains a candidate is usually killed by its *worst* part, and mean pooling smooths
exactly that signal away.
"""

from __future__ import annotations

from .embed import N_POOLINGS, GCNEmbedder
from .featurize import (
    GraphFeaturizer,
    GraphLike,
    normalized_adjacency,
    structural_featurizer,
)
from .metrics import best_of_k_regret, mean_regret, spearman
from .rank import ConformalRankingHead, GraphRanker

__version__ = "0.1.0"

__all__ = [
    "GraphLike",
    "GraphFeaturizer",
    "structural_featurizer",
    "normalized_adjacency",
    "GCNEmbedder",
    "N_POOLINGS",
    "ConformalRankingHead",
    "GraphRanker",
    "spearman",
    "best_of_k_regret",
    "mean_regret",
    "__version__",
]
