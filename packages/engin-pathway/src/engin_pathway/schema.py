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

**Four of the five are supplied by hand.** ``g_thermo`` can now come from
eQuilibrator via :func:`~engin_pathway.thermo_bridge.step_from_reaction` (#140
item 3); the rest have no ingest, and `simulate.py` is the only other in-repo
supplier. Which is which travels with the step -- see :attr:`Step.measured`,
added because a mixed step was otherwise indistinguishable from a guessed one.

*This paragraph said "every one of these is supplied by hand today" until
2026-08-18, which was true when written and stopped being true one PR later.*

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

## Where a *route* can legally come from, checked 2026-08-18

#140 item 3's remaining half is traversal -- building routes from a pathway
database. #198's check covered kcat/K\\ :sub:`M` sources only and explicitly did
not cover these, so they were checked separately, from the licence text:

============  ==========================================  ===========================
Source        Terms                                       Usable by Apache-2.0?
============  ==========================================  ===========================
Rhea          CC BY 4.0                                   **Yes**, with attribution
KEGG          "Non-academic use requires a commercial
              license"                                    **No**
MetaCyc       separate academic / commercial licences     **No** without one
MetaNetX      CC BY 4.0 on its own namespace              **Partly** -- see below
============  ==========================================  ===========================

**Build traversal against Rhea.** Its licence says commercial use is permitted in
as many words -- "copy, distribute, display and make commercial use of the
database in all legislations, provided you credit Rhea" -- which is the only one
of the four that answers the question without a lawyer.

**KEGG is the one everybody reaches for first and it is out.** Same class as
SABIO-RK in #198: not hostile, just licensed on terms an Apache-2.0 project
cannot pass to its users.

**MetaNetX is not a way around that, and this is the part worth not
rediscovering.** Its own namespace mapping is CC BY 4.0, and it aggregates KEGG,
MetaCyc and SABIO-RK among others -- stating itself that "the licensing
agreements of those resources are specified in each of the downloadable files".
So a wholesale pull imports the restrictions of whatever it drew from. It is a
namespace, not a laundromat. Exactly the shape of CatPred in #198: a permissive
wrapper over mixed provenance.

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
    """One enzymatic step: goodness features in [0, 1].

    ``measured`` names the features that came from a source rather than from
    somebody's judgement. It defaults to empty, which is the truth for a
    hand-built step and keeps every route written before this field existed
    correctly labelled with no edits.

    **This became necessary when it stopped being uniform.** While every feature
    was typed by hand, "these are expert judgements" was true of all of them and a
    docstring said it adequately. :func:`~engin_pathway.thermo_bridge.step_from_reaction`
    now returns a step whose ``g_thermo`` is measured against eQuilibrator and
    whose other four are not, and without this field that step is
    indistinguishable from one where all five were guessed (#140 item 4).
    """

    features: dict[str, float]
    measured: frozenset[str] = frozenset()
    """Feature names backed by a source. Empty means every one is a judgement."""

    @field_validator("features")
    @classmethod
    def _check(cls, v: dict[str, float]) -> dict[str, float]:
        if set(v) != set(FEATURES):
            raise ValueError(f"step features must be exactly {FEATURES}, got {sorted(v)}")
        for k, x in v.items():
            if not 0.0 <= x <= 1.0:
                raise ValueError(f"feature {k!r}={x} not in [0,1]")
        return v

    @model_validator(mode="after")
    def _check_measured(self) -> Step:
        unknown = self.measured - set(FEATURES)
        if unknown:
            raise ValueError(f"measured names unknown features: {sorted(unknown)}")
        return self

    @property
    def judged(self) -> frozenset[str]:
        """Features resting on expert judgement -- the complement of ``measured``."""
        return frozenset(FEATURES) - self.measured

    @property
    def fully_judged(self) -> bool:
        """True when nothing in this step came from a source."""
        return not self.measured

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

    @classmethod
    def from_manual_scores(
        cls,
        route_id: str,
        step_features: list[dict[str, float]],
        manufacturability: float | None = None,
    ) -> Route:
        """Build a route whose every feature is an expert judgement.

        Identical in result to constructing :class:`Step` objects directly -- what
        it adds is that the call site *says so*. #140 item 4 asks for exactly
        that: the provenance of a ranking should be legible from the code that
        produced it, rather than inferred from the absence of anything saying
        otherwise.

        Use :func:`~engin_pathway.thermo_bridge.step_from_reaction` where a
        feature can be measured instead.
        """
        return cls(
            route_id=route_id,
            steps=[Step(features=f) for f in step_features],
            manufacturability=manufacturability,
        )

    @property
    def fully_judged(self) -> bool:
        """True when no step in this route carries a measured feature.

        The honest headline for a ranking: if this is True, the ordering reflects
        the priors of whoever typed the numbers, with a conformal interval around
        them.
        """
        return all(s.fully_judged for s in self.steps)

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
