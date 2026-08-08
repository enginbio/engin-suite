"""The domain boundary: how an arbitrary object becomes a graph.

Everything downstream (embedding, ranking, calibration) is domain-agnostic. This
module is the one place a domain plugs in. Two ways to do it:

1. **Structural** — the object already exposes ``node_features()`` and ``graph()``,
   satisfying :class:`GraphLike`. ``engin_pathway.Route`` does this, and so should
   most pydantic domain models. Nothing else is needed.
2. **Adapter** — the object exposes something else (an RDKit mol, a raw dict). Write
   a :class:`GraphFeaturizer` and pass it to the embedder.

Keeping the featurizer *outside* the embedder is what makes the graph stack reusable:
metabolic routes and polymer structures share every line of the model and differ only
here.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import networkx as nx
import numpy as np
from numpy.typing import NDArray


@runtime_checkable
class GraphLike(Protocol):
    """An object that can describe itself as a graph.

    ``node_features()`` returns ``(n_nodes, d_in)`` with rows ordered to match
    ``sorted(graph().nodes)`` — the embedder relies on that alignment.
    """

    def node_features(self) -> NDArray[np.float64]: ...

    def graph(self) -> nx.Graph: ...


class GraphFeaturizer(Protocol):
    """Maps a domain object to ``(node_features, graph)``."""

    def __call__(self, obj: Any) -> tuple[NDArray[np.float64], nx.Graph]: ...


def structural_featurizer(obj: Any) -> tuple[NDArray[np.float64], nx.Graph]:
    """Default featurizer: call the object's own ``node_features()`` / ``graph()``.

    Raises a pointed error rather than an ``AttributeError`` when the object doesn't
    satisfy :class:`GraphLike`, since "pass a featurizer" is the fix and it isn't
    obvious from a missing-attribute traceback.
    """
    if not isinstance(obj, GraphLike):
        raise TypeError(
            f"{type(obj).__name__} does not satisfy GraphLike (needs node_features() and "
            "graph()). Either add those methods or pass a GraphFeaturizer to the embedder."
        )
    X = np.asarray(obj.node_features(), dtype=float)
    g = obj.graph()
    if X.ndim != 2:
        raise ValueError(f"node_features() must be 2-D (n_nodes, d_in); got shape {X.shape}")
    if X.shape[0] != g.number_of_nodes():
        raise ValueError(
            f"node_features() has {X.shape[0]} rows but graph() has {g.number_of_nodes()} nodes"
        )
    return X, g


def normalized_adjacency(g: nx.Graph) -> NDArray[np.float64]:
    """Symmetric-normalized adjacency with self-loops: ``D^-1/2 (A + I) D^-1/2``.

    Nodes are ordered by ``sorted(g.nodes)`` to match the node-feature row order.
    """
    A = nx.to_numpy_array(g, nodelist=sorted(g.nodes))
    A = A + np.eye(A.shape[0])
    d = A.sum(1)
    dinv = 1.0 / np.sqrt(np.maximum(d, 1e-9))
    return (A * dinv[None, :]) * dinv[:, None]
