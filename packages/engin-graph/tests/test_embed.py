"""Embedder: shape, determinism, and worst-node sensitivity."""
from __future__ import annotations

import numpy as np

from conftest import D_IN, Chain
from engin_graph import GCNEmbedder


def _chain(worst: float = 0.9, L: int = 5) -> Chain:
    feats = np.full((L, D_IN), 0.9)
    feats[2, 3] = worst                       # inject a bad node in the middle
    return Chain(feats)


def test_embedding_shape_matches_declared_dim():
    emb = GCNEmbedder(d_in=D_IN, h=16, seed=0)
    v = emb.embed(_chain())
    assert v.shape == (emb.dim,)
    assert emb.dim == 3 * D_IN + 3 * 16       # mean/max/min over raw and hidden


def test_embedding_is_deterministic_given_seed():
    v1 = GCNEmbedder(d_in=D_IN, seed=0).embed(_chain())
    v2 = GCNEmbedder(d_in=D_IN, seed=0).embed(_chain())
    assert np.allclose(v1, v2)


def test_different_seeds_give_different_embeddings():
    v1 = GCNEmbedder(d_in=D_IN, seed=0).embed(_chain())
    v2 = GCNEmbedder(d_in=D_IN, seed=1).embed(_chain())
    assert not np.allclose(v1, v2)


def test_embedding_sees_the_worst_node():
    # The reason min-pooling exists: a graph with one bad node must embed
    # differently from an all-good one, and the raw min-pool must drop.
    emb = GCNEmbedder(d_in=D_IN, seed=0)
    healthy = emb.embed(_chain(worst=0.9))
    damaged = emb.embed(_chain(worst=0.05))
    assert not np.allclose(healthy, damaged)
    assert emb.raw_min_block(damaged).min() < emb.raw_min_block(healthy).min()


def test_raw_min_block_tracks_declared_offsets():
    # Guards the documented pooling order, which consumers index into.
    emb = GCNEmbedder(d_in=D_IN, seed=0)
    obj = _chain(worst=0.05)
    v = emb.embed(obj)
    assert np.allclose(emb.raw_min_block(v), obj.node_features().min(0))


def test_matrix_stacks_rows():
    emb = GCNEmbedder(d_in=D_IN, seed=0)
    M = emb.matrix([_chain(), _chain(worst=0.1), _chain(L=7)])
    assert M.shape == (3, emb.dim)


def test_wrong_feature_width_is_rejected():
    emb = GCNEmbedder(d_in=D_IN, seed=0)
    try:
        emb.embed(Chain(np.zeros((4, D_IN + 2))))
    except ValueError as e:
        assert "expected" in str(e)
    else:
        raise AssertionError("expected a ValueError for mismatched feature width")


def test_pooling_is_invariant_to_chain_length_in_dim_only():
    # Different node counts must still produce the same embedding length.
    emb = GCNEmbedder(d_in=D_IN, seed=0)
    assert emb.embed(_chain(L=3)).shape == emb.embed(_chain(L=8)).shape
