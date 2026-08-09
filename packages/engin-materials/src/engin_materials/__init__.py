"""engin-materials: structure→property ranking for biomaterial formulations [Plan 15].

The materials cousin of metabolic route ranking. Both domains share a shape — a
candidate is killed by its *worst* part, and topology matters beyond composition — so
both run on the same ``engin_graph`` engine with a different featurization. This
package is deliberately thin; if it grew thick, the shared-engine thesis would be
failing.

**Status: M0, and framed as a probe rather than a lead bet.** The shortlist is blunt
about the commercial read — niche buyers, slow wet validation. What this package is
for is proving the graph edge *transfers*, cheaply, before anyone over-invests.
"""

from __future__ import annotations

from .rank import (
    PolymerRanker,
    best_of_k_regret,
    composition_scores,
    crosslink_densities,
    labels,
    spearman,
)
from .schema import MONOMER_FEATURES, Monomer, Polymer
from .simulate import PropertyModel, make_dataset, sample_polymer, true_property

__version__ = "0.1.0"

__all__ = [
    "Monomer",
    "Polymer",
    "MONOMER_FEATURES",
    "PropertyModel",
    "make_dataset",
    "sample_polymer",
    "true_property",
    "PolymerRanker",
    "labels",
    "composition_scores",
    "crosslink_densities",
    "spearman",
    "best_of_k_regret",
    "__version__",
]
