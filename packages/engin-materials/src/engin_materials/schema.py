"""Typed schema for polymer formulations (pydantic + networkx).

A candidate biomaterial is a chain of monomer units plus a **topology** — which units
are crosslinked to which. Both matter, and the second is what a composition-average
heuristic cannot see.

``Polymer`` satisfies ``engin_graph.GraphLike`` structurally, through ``node_features()``
and ``graph()``, so it drops straight into the shared graph engine with no adapter. That
is the extraction paying off: nothing about the model had to learn what a polymer is.
"""

from __future__ import annotations

import networkx as nx
import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field, field_validator, model_validator

# Per-unit "goodness" features (higher = better), in engin-materials order.
MONOMER_FEATURES: tuple[str, ...] = (
    "m_stiffness",  # backbone rigidity
    "m_thermal",  # thermal stability of the unit
    "m_bonding",  # H-bonding / intermolecular cohesion
    "m_hydrolytic",  # resistance to hydrolytic cleavage
    "m_packing",  # how well the unit packs (steric regularity)
)


class Monomer(BaseModel):
    """One repeat unit: goodness features in [0, 1]."""

    features: dict[str, float]

    @field_validator("features")
    @classmethod
    def _check(cls, v: dict[str, float]) -> dict[str, float]:
        if set(v) != set(MONOMER_FEATURES):
            raise ValueError(
                f"monomer features must be exactly {MONOMER_FEATURES}, got {sorted(v)}"
            )
        for k, x in v.items():
            if not 0.0 <= x <= 1.0:
                raise ValueError(f"feature {k!r}={x} not in [0,1]")
        return v

    def vector(self) -> NDArray[np.float64]:
        return np.array([self.features[f] for f in MONOMER_FEATURES], float)


class Polymer(BaseModel):
    """A candidate formulation: a chain of units, optional crosslinks, optional label.

    ``crosslinks`` are extra edges between non-adjacent units. They are where the
    topology signal lives: two formulations with identical composition can differ
    substantially in property because one is crosslinked and the other isn't.

    ``property_value`` is the measured or ground-truth target in [0, 1]; ``None`` for
    a formulation we only want to *predict*.
    """

    polymer_id: str
    units: list[Monomer] = Field(..., min_length=2)
    crosslinks: list[tuple[int, int]] = Field(default_factory=list)
    property_value: float | None = None

    @model_validator(mode="after")
    def _check(self) -> Polymer:
        n = len(self.units)
        for i, j in self.crosslinks:
            if not (0 <= i < n and 0 <= j < n):
                raise ValueError(f"crosslink ({i},{j}) out of range for {n} units")
            if abs(i - j) <= 1:
                raise ValueError(
                    f"crosslink ({i},{j}) joins adjacent or identical units; "
                    "the backbone bond is already there and a self-loop is meaningless"
                )
        if self.property_value is not None and not 0.0 <= self.property_value <= 1.0:
            raise ValueError("property_value must be in [0,1] or None")
        return self

    @property
    def n_units(self) -> int:
        return len(self.units)

    @property
    def crosslink_density(self) -> float:
        """Crosslinks per unit — the topology summary a composition average misses."""
        return len(self.crosslinks) / self.n_units

    def node_features(self) -> NDArray[np.float64]:
        """``(n_units, n_features)`` node-feature matrix, one row per unit."""
        return np.vstack([u.vector() for u in self.units])

    def graph(self) -> nx.Graph:
        """Backbone path graph plus crosslink edges; node attr ``x`` = feature vector."""
        g = nx.path_graph(self.n_units)
        g.add_edges_from(self.crosslinks)
        for i, u in enumerate(self.units):
            g.nodes[i]["x"] = u.vector()
        return g
