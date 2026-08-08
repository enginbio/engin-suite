"""Route embedding — a thin binding of ``engin-graph`` to the metabolic domain.

The graph machinery (message-passing GCN, mean/max/min pooling, normalized
adjacency) lives in ``engin_graph`` so the materials domain can reuse every line of
it. All that remains here is the domain binding: routes carry ``len(FEATURES)``
per-step features, and ``Route`` already satisfies ``engin_graph.GraphLike`` via its
``node_features()`` / ``graph()`` methods, so no custom featurizer is needed.

Min-pooling is the load-bearing choice, and it is a metabolic-domain fact that
generalizes: a route is tanked by its *worst* step — the toxic or thermodynamically
uphill reaction — and mean pooling smooths exactly that signal away. See
``engin_graph.embed`` for the mechanism and the M0/M1 status of the weights.
"""
from __future__ import annotations

from engin_graph import GCNEmbedder

from .schema import FEATURES


class GraphEmbedder(GCNEmbedder):
    """Route embedder: ``engin_graph.GCNEmbedder`` fixed to the route feature width."""

    def __init__(self, d_in: int = len(FEATURES), h: int = 16, seed: int = 0) -> None:
        super().__init__(d_in=d_in, h=h, seed=seed)
