"""A minimal graph-like domain object, so the tests don't depend on any domain package.

Deliberately not imported from ``engin_pathway``: engin-graph must be provably usable
by a domain it has never heard of, which is the whole point of the extraction.
"""
from __future__ import annotations

import networkx as nx
import numpy as np
import pytest
from numpy.typing import NDArray

D_IN = 4


class Chain:
    """A chain of nodes, each with ``D_IN`` goodness features in [0, 1]."""

    def __init__(self, feats: NDArray[np.float64]) -> None:
        self.feats = np.asarray(feats, float)

    def node_features(self) -> NDArray[np.float64]:
        return self.feats

    def graph(self) -> nx.Graph:
        return nx.path_graph(len(self.feats))


class NotAGraph:
    """Satisfies neither half of the protocol — for the error-path test."""


def worst_node_score(feats: NDArray[np.float64]) -> float:
    """Truth: dominated by the worst node, with a mild length penalty.

    This is the structure a count-based baseline is blind to, and the reason
    min-pooling exists.
    """
    return float(0.8 * feats.min() + 0.2 * feats.mean() - 0.01 * len(feats))


def make_dataset(n: int, seed: int = 0) -> tuple[list[Chain], NDArray[np.float64]]:
    rng = np.random.default_rng(seed)
    objs, ys = [], []
    for _ in range(n):
        L = int(rng.integers(3, 9))
        feats = rng.uniform(0.2, 1.0, (L, D_IN))
        objs.append(Chain(feats))
        ys.append(worst_node_score(feats) + rng.normal(0, 0.01))
    return objs, np.array(ys, float)


@pytest.fixture
def dataset():
    return make_dataset(400, seed=1)
