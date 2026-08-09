"""engin-protein: three faces of the protein design cycle over one calibrated engine.

Plans 2, 5, and 9 from the venture shortlist are the same GP + Expected-Improvement +
conformal-interval loop pointed at a fitness landscape instead of fermentation knobs:

- :class:`DesignEvaluator` [2] — rank candidate designs by predicted wet-lab success
- :class:`LowNCopilot` [5] — squeeze signal from <100 assay points, recommend a batch
- :class:`CampaignPlanner` [9] — multi-round batch BO with transfer across campaigns

**M0 status: everything here runs on a synthetic fitness landscape.** The numbers show
the loops are wired and calibrated; they are not evidence about real proteins. See the
README for what the kill criteria actually require (real wet data, M1).
"""

from __future__ import annotations

from .evaluate import DesignEvaluator, spearman, top_k_hit_rate
from .featurize import Featurizer, OneHotPhysicochemical, PrecomputedFeaturizer
from .landscape import FitnessLandscape, make_landscape
from .lown import AdditiveBaseline, LowNCopilot
from .model import CalibratedFitnessModel
from .planner import CampaignPlanner, best_true_found, random_campaign, transfer_benefit
from .schema import AMINO_ACIDS, Campaign, ScoredDesign, Variant

__version__ = "0.1.0"

__all__ = [
    # schema
    "Variant",
    "Campaign",
    "ScoredDesign",
    "AMINO_ACIDS",
    # featurization
    "Featurizer",
    "OneHotPhysicochemical",
    "PrecomputedFeaturizer",
    # synthetic domain
    "FitnessLandscape",
    "make_landscape",
    # core
    "CalibratedFitnessModel",
    # the three faces
    "DesignEvaluator",
    "LowNCopilot",
    "CampaignPlanner",
    # baselines + metrics
    "AdditiveBaseline",
    "random_campaign",
    "transfer_benefit",
    "best_true_found",
    "spearman",
    "top_k_hit_rate",
    "__version__",
]
