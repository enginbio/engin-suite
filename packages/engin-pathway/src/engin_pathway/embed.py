"""Graph message-passing embedder for routes.

A 2-layer message-passing GCN over the route graph turns each route into a
fixed-length embedding via mean-, max- AND min-pooling. Max/min pooling is what
lets the embedding represent the *worst step* (the toxic/uphill reaction that
tanks the route) — the structural signal step-count is blind to.

**M0 stand-in.** The weights are random (no training): a random-weight GCN + a
ridge head captures graph structure with zero backprop, enough to prove the
ranking loop beats step-count. The M1 upgrade swaps this for a *trained* GNN on
**PyTorch Geometric**; the route-as-graph interface (via networkx) stays the same.
The graph is built with networkx so branched real routes (M1) drop straight in.
"""

from __future__ import annotations

import networkx as nx
import numpy as np
from numpy.typing import NDArray

from .schema import FEATURES, Route


def _normalized_adjacency(g: nx.Graph) -> NDArray[np.float64]:
    """Symmetric-normalized adjacency with self-loops: D^-1/2 (A + I) D^-1/2."""
    A = nx.to_numpy_array(g, nodelist=sorted(g.nodes))
    A = A + np.eye(A.shape[0])
    d = A.sum(1)
    dinv = 1.0 / np.sqrt(np.maximum(d, 1e-9))
    return (A * dinv[None, :]) * dinv[:, None]


class GraphEmbedder:
    """Random-weight GCN embedder (M0). Deterministic given ``seed``."""

    def __init__(self, d_in: int = len(FEATURES), h: int = 16, seed: int = 0) -> None:
        rng = np.random.default_rng(seed)
        self.W1 = rng.normal(0, 1, (d_in, h)) / np.sqrt(d_in)
        self.W2 = rng.normal(0, 1, (h, h)) / np.sqrt(h)

    def embed(self, route: Route) -> NDArray[np.float64]:
        """Embed one route -> a fixed-length vector (pooled node + hidden features)."""
        X = route.node_features()
        Ah = _normalized_adjacency(route.graph())
        H1 = np.maximum(Ah @ X @ self.W1, 0.0)
        H2 = np.maximum(Ah @ H1 @ self.W2, 0.0)
        # min-pool included so the embedding can see the *worst step*.
        return np.concatenate(
            [
                X.mean(0),
                X.max(0),
                X.min(0),
                H2.mean(0),
                H2.max(0),
                H2.min(0),
            ]
        )

    def matrix(self, routes: list[Route]) -> NDArray[np.float64]:
        """Embed a list of routes -> ``(n_routes, embedding_dim)``."""
        return np.array([self.embed(r) for r in routes])
