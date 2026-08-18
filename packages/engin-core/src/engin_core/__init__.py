"""engin-core: open bioprocess forecasting + calibration toolkit.

A mechanistic fed-batch simulator (scipy), a scikit-learn Gaussian-process titer
model with conformally calibrated uncertainty (split-conformal + MAPIE), an
active-learning next-batch recommender, and an ARD sensitivity readout.
"""

from __future__ import annotations

from .evidence import (
    Assumption,
    Baseline,
    EvidenceReport,
    IntervalClaim,
    IntervalKind,
    ReproStamp,
    ValidationTier,
    report,
)
from .gp import (
    GP,
    conformal_coverage_interval,
    conformal_multiplier_oof,
    fit_gp,
    mapie_split_interval,
    prob_at_least,
    smallest_calibration_set,
    split_conformal_multiplier,
)
from .handoff import (
    HostDecision,
    ProcessBrief,
    RankedRoute,
    RouteRanking,
    inflate_uncertainty,
    process_brief,
)
from .recommend import expected_improvement, recommend_batch
from .sensitivity import ard_importance
from .simulator import (
    KNOB_NAMES,
    KNOBS,
    simulate,
    simulate_unit,
    unit_to_physical,
)
from .tea import (
    BioSteamCostModel,
    CostModel,
    CostParameters,
    CostSummary,
    ParametricCostModel,
    cost_samples,
    cost_summary,
    design_context,
    expected_cost_reduction,
    recommend_batch_by_cost,
)

__version__ = "0.1.0"

__all__ = [
    "GP",
    "fit_gp",
    "split_conformal_multiplier",
    "conformal_multiplier_oof",
    "conformal_coverage_interval",
    "smallest_calibration_set",
    "mapie_split_interval",
    "prob_at_least",
    "expected_improvement",
    "recommend_batch",
    "ard_importance",
    "simulate",
    "simulate_unit",
    "unit_to_physical",
    "KNOBS",
    "KNOB_NAMES",
    "Assumption",
    "Baseline",
    "EvidenceReport",
    "IntervalClaim",
    "IntervalKind",
    "ReproStamp",
    "ValidationTier",
    "report",
    "HostDecision",
    "RankedRoute",
    "RouteRanking",
    "ProcessBrief",
    "inflate_uncertainty",
    "process_brief",
    "CostParameters",
    "CostModel",
    "CostSummary",
    "ParametricCostModel",
    "BioSteamCostModel",
    "cost_samples",
    "cost_summary",
    "design_context",
    "expected_cost_reduction",
    "recommend_batch_by_cost",
    "__version__",
]
