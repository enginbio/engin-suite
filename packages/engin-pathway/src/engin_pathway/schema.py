"""Typed schema for candidate metabolic routes (pydantic + networkx).

A candidate route to a target = a chain of enzymatic steps. Each step carries
"goodness" features in [0, 1] (higher = better). A route exposes a node-feature
matrix and a networkx graph so the graph model can read its *structure* — which
is where the manufacturability signal that step-count misses actually lives (a
single toxic or thermodynamically-uphill step tanks the whole route).
"""

from __future__ import annotations

import networkx as nx
import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field, field_validator, model_validator

# Per-step goodness features (higher = better), in engin-pathway order.
FEATURES: tuple[str, ...] = ("g_thermo", "g_enzyme", "g_cofactor", "g_tox", "g_expr")


class Step(BaseModel):
    """One enzymatic step: goodness features in [0, 1]."""

    features: dict[str, float]

    @field_validator("features")
    @classmethod
    def _check(cls, v: dict[str, float]) -> dict[str, float]:
        if set(v) != set(FEATURES):
            raise ValueError(f"step features must be exactly {FEATURES}, got {sorted(v)}")
        for k, x in v.items():
            if not 0.0 <= x <= 1.0:
                raise ValueError(f"feature {k!r}={x} not in [0,1]")
        return v

    def vector(self) -> NDArray[np.float64]:
        return np.array([self.features[f] for f in FEATURES], float)


class Route(BaseModel):
    """A candidate route: an ordered chain of steps + an optional label.

    ``manufacturability`` is the ground-truth (or measured) label in [0, 1] used
    for training/evaluation; ``None`` for a route we only want to *predict*.
    """

    route_id: str
    steps: list[Step] = Field(..., min_length=1)
    manufacturability: float | None = None

    @model_validator(mode="after")
    def _check_label(self) -> Route:
        if self.manufacturability is not None and not 0.0 <= self.manufacturability <= 1.0:
            raise ValueError("manufacturability must be in [0,1] or None")
        return self

    @property
    def n_steps(self) -> int:
        return len(self.steps)

    def node_features(self) -> NDArray[np.float64]:
        """``(L, n_features)`` node-feature matrix (one row per step)."""
        return np.vstack([s.vector() for s in self.steps])

    def graph(self) -> nx.Graph:
        """Undirected path graph over the steps, node attr ``x`` = feature vector."""
        g = nx.path_graph(self.n_steps)  # 0-1-2-...-(L-1)
        for i, s in enumerate(self.steps):
            g.nodes[i]["x"] = s.vector()
        return g
