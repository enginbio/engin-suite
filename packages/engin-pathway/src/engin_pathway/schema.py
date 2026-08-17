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
"""The five per-step goodness scores, each in [0, 1].

**Every one of these is supplied by hand today** -- there is no ingest from a route
database, no thermodynamics, and no enzyme data. `simulate.py` is the only in-repo
supplier. #140 records what that blocks.

## Where ``g_enzyme`` can legally come from, checked 2026-08-17

#140 item 2 asks for ``g_enzyme`` from a kcat/K\\ :sub:`M` source and flags a licence
check first. The check was done, and it decides the shape of any implementation:

============  ============================  ==========================================
Source        Licence                       Usable by an Apache-2.0 project?
============  ============================  ==========================================
BRENDA        CC BY 4.0                     **Yes**, with attribution
SABIO-RK      Non-Commercial Purpose        **No**
DLKcat        *no LICENSE file*             **No**
UniKP         *no LICENSE file*             **No**
CatPred       MIT *code*                    Code yes; **its dataset is the problem**
============  ============================  ==========================================

Three things are worth carrying forward rather than re-deriving.

**BRENDA changed, and the issue's premise is now half stale.** #140 says "several
enzyme databases are academic-use-only". BRENDA was, and is now CC BY 4.0 -- so the
one source with the broadest coverage is available. Read from the licence page, not
a badge.[^brenda]

**SABIO-RK's exclusion is broader than "do not sell the data".** Its terms exclude
use "in connection with a product or service which is sold, offered for sale,
**licensed**, leased, **loaned**, or rented". An Apache-2.0 library is licensed, so
this is not a corner case for us -- it is the ordinary one. Same class as the
NonCommercial constraint `D12` already encodes for datasets.[^sabio]

**An MIT model can carry a non-MIT training set.** CatPred is MIT and actively
maintained, and CatPred-DB is curated from *BRENDA release 2022_2 and SABIO-RK as of
November 2023*.[^catpred] Whether a model's weights inherit its training data's
licence is genuinely unsettled, and this docstring does not pretend to answer it.
The point is narrower and sufficient: **the question exists, and BRENDA-only avoids
having to answer it.**

So the buildable version of item 2 is BRENDA-direct. Anything routed through the ML
predictors needs the derived-data question resolved first, and two of them have no
licence at all.

[^brenda]: https://www.brenda-enzymes.org/license.php  ref: 2026-brenda-license
[^sabio]: https://sabiork.h-its.org/ui/terms  ref: 2026-sabiork-terms
[^catpred]: https://doi.org/10.1038/s41467-025-57215-9  ref: 2025-catpred-kinetics
"""


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
