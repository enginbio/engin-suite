"""engin-core: open bioprocess forecasting + calibration toolkit.

A mechanistic fed-batch simulator (scipy), a scikit-learn Gaussian-process titer
model with conformally calibrated uncertainty (split-conformal + MAPIE), an
active-learning next-batch recommender, and an ARD sensitivity readout.
"""
from __future__ import annotations

from .gp import (
    GP,
    conformal_multiplier_oof,
    fit_gp,
    mapie_split_interval,
    prob_at_least,
    split_conformal_multiplier,
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

__version__ = "0.1.0"

__all__ = [
    "GP",
    "fit_gp",
    "split_conformal_multiplier",
    "conformal_multiplier_oof",
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
    "__version__",
]
