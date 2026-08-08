"""Featurizer: protocol satisfaction, adjacency properties, and honest errors."""
from __future__ import annotations

import networkx as nx
import numpy as np
import pytest

from conftest import D_IN, Chain, NotAGraph
from engin_graph import GraphLike, normalized_adjacency, structural_featurizer


def test_chain_satisfies_graphlike():
    assert isinstance(Chain(np.zeros((3, D_IN))), GraphLike)
    assert not isinstance(NotAGraph(), GraphLike)


def test_structural_featurizer_returns_aligned_features_and_graph():
    obj = Chain(np.random.default_rng(0).uniform(0, 1, (5, D_IN)))
    X, g = structural_featurizer(obj)
    assert X.shape == (5, D_IN)
    assert g.number_of_nodes() == 5


def test_non_graphlike_gets_a_pointed_error():
    # An AttributeError here would send the reader hunting; the fix is "pass a
    # featurizer", so the message has to say that.
    with pytest.raises(TypeError, match="GraphFeaturizer"):
        structural_featurizer(NotAGraph())


def test_row_count_mismatch_is_caught():
    class Mismatched(Chain):
        def graph(self) -> nx.Graph:
            return nx.path_graph(len(self.feats) + 1)

    with pytest.raises(ValueError, match="rows but graph"):
        structural_featurizer(Mismatched(np.zeros((3, D_IN))))


def test_normalized_adjacency_is_symmetric_with_self_loops():
    Ah = normalized_adjacency(nx.path_graph(4))
    assert Ah.shape == (4, 4)
    assert np.allclose(Ah, Ah.T)
    assert np.all(np.diag(Ah) > 0)          # self-loops present
    assert np.all(Ah <= 1.0 + 1e-9)         # normalization bounds it


def test_adjacency_node_order_matches_feature_rows():
    # sorted(g.nodes) ordering is the contract the embedder relies on; a graph whose
    # insertion order differs from sorted order must still line up.
    g = nx.Graph()
    g.add_edges_from([(2, 0), (0, 1)])
    Ah = normalized_adjacency(g)
    # node 0 is the hub -> its row has the most nonzero off-diagonal entries
    offdiag_nonzero = [(Ah[i] > 0).sum() - 1 for i in range(3)]
    assert offdiag_nonzero[0] == 2
