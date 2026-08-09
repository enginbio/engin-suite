"""ARD sensitivity readout.

The GP's per-dimension inverse lengthscales double as a cheap global sensitivity
measure: a short lengthscale on knob *j* means titer changes fast along *j*, so
that knob matters. Normalized, these answer "which knobs actually move titer".
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from .gp import GP


def ard_importance(gp: GP) -> NDArray[np.float64]:
    """Inverse lengthscale, normalized -> relative sensitivity per knob (sums to 1)."""
    inv = 1.0 / gp.ell
    return inv / inv.sum()
