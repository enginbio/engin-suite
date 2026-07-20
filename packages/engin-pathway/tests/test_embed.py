"""Embedder: shape, determinism, and worst-step sensitivity."""
from __future__ import annotations

import numpy as np

from engin_pathway import FEATURES, GraphEmbedder, Route, Step


def _route(rid, tox_of_middle=0.9):
    steps = [Step(features=dict.fromkeys(FEATURES, 0.9)) for _ in range(5)]
    steps[2] = Step(features={**dict.fromkeys(FEATURES, 0.9), "g_tox": tox_of_middle})
    return Route(route_id=rid, steps=steps)


def test_embedding_shape_and_determinism():
    emb = GraphEmbedder(seed=0)
    v1 = emb.embed(_route("a"))
    v2 = GraphEmbedder(seed=0).embed(_route("a"))
    # 3 poolings x 5 node feats + 3 poolings x 16 hidden = 15 + 48 = 63
    assert v1.shape == (63,)
    assert np.allclose(v1, v2)                 # deterministic given seed


def test_embedding_sees_the_worst_step():
    # A route with a toxic middle step must embed differently from an all-good one;
    # the min-pool of the node features should drop with the injected bad step.
    emb = GraphEmbedder(seed=0)
    healthy = emb.embed(_route("healthy", tox_of_middle=0.9))
    toxic = emb.embed(_route("toxic", tox_of_middle=0.05))
    assert not np.allclose(healthy, toxic)
    # node-feature min-pool is the first 5..10 slots (X.min block); g_tox is index 3
    assert toxic[10:15].min() < healthy[10:15].min()
