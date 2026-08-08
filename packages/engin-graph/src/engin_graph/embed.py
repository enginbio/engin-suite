"""Message-passing graph embedder with worst-node-preserving pooling.

A 2-layer message-passing GCN turns a graph into a fixed-length vector via mean-,
max- AND min-pooling of both the raw node features and the hidden representation.

**Why min-pooling earns its place.** In the domains this serves, quality is often
decided by the *worst* part, not the average one — a single thermodynamically-uphill
reaction tanks a metabolic route; a single weak bond tanks a polymer. Mean pooling
smooths exactly that signal away. Min/max pooling keeps the extremes visible to the
head, and that is the structural information a count-based baseline is blind to.

**M0 stand-in.** The weights are random (no training). A random-weight GCN plus a
ridge head captures graph structure with zero backprop — enough to prove a ranking
loop beats its baseline, without pulling PyTorch into the default install (ADR 0002).
The M1 upgrade swaps this for a trained GNN on PyTorch Geometric behind an extra; the
object-as-graph interface stays the same, so domain layers don't change.
"""
from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray

from .featurize import GraphFeaturizer, normalized_adjacency, structural_featurizer

# Pooling order is part of the public contract: consumers index into the embedding
# to inspect specific blocks (e.g. the raw-feature min-pool). Do not reorder.
N_POOLINGS = 3  # mean, max, min — applied to raw features and to hidden features


class GCNEmbedder:
    """Random-weight message-passing embedder (M0). Deterministic given ``seed``.

    The embedding is ``[X.mean, X.max, X.min, H.mean, H.max, H.min]`` concatenated,
    so its length is ``3 * d_in + 3 * h``.
    """

    def __init__(
        self,
        d_in: int,
        h: int = 16,
        seed: int = 0,
        featurizer: GraphFeaturizer | None = None,
    ) -> None:
        rng = np.random.default_rng(seed)
        self.d_in = d_in
        self.h = h
        self.W1 = rng.normal(0, 1, (d_in, h)) / np.sqrt(d_in)
        self.W2 = rng.normal(0, 1, (h, h)) / np.sqrt(h)
        self.featurize: GraphFeaturizer = featurizer or structural_featurizer

    @property
    def dim(self) -> int:
        """Length of the embedding this produces."""
        return N_POOLINGS * (self.d_in + self.h)

    def embed(self, obj: Any) -> NDArray[np.float64]:
        """Embed one object -> a fixed-length vector (pooled node + hidden features)."""
        X, g = self.featurize(obj)
        if X.shape[1] != self.d_in:
            raise ValueError(f"expected {self.d_in} node features, got {X.shape[1]}")
        Ah = normalized_adjacency(g)
        H1 = np.maximum(Ah @ X @ self.W1, 0.0)
        H2 = np.maximum(Ah @ H1 @ self.W2, 0.0)
        # min-pool included so the embedding can see the *worst node*.
        return np.concatenate([
            X.mean(0), X.max(0), X.min(0),
            H2.mean(0), H2.max(0), H2.min(0),
        ])

    def matrix(self, objs: list[Any]) -> NDArray[np.float64]:
        """Embed a list of objects -> ``(n_objs, dim)``."""
        return np.array([self.embed(o) for o in objs])

    def raw_min_block(self, embedding: NDArray[np.float64]) -> NDArray[np.float64]:
        """The raw-feature min-pool slice — the 'worst node' view, for inspection.

        Saves consumers from hardcoding offsets that shift if ``d_in`` changes.
        """
        return embedding[2 * self.d_in : 3 * self.d_in]
