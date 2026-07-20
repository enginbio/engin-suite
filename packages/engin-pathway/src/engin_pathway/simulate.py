"""Synthetic metabolic-route generator + ground-truth manufacturability.

The mechanistic bootstrap (à la engin's Plan 1): no real pathway data needed to
prove the ranking loop. Ground-truth manufacturability multiplies per-step scores
so it (a) decays with length — which step-count can partly capture — but (b) is
*tanked by a single bad step* (a toxic intermediate, a thermodynamic wall), which
step-count cannot see. That structural signal is what a graph model reading node
features should recover.

This generator is bespoke by design (the domain model). In M1 it is replaced by
real routes from KEGG/MetaCyc/BiGG via COBRApy, with ΔG node features from
eQuilibrator.
"""
from __future__ import annotations

import numpy as np

from .schema import FEATURES, Route, Step

# Per-feature importance in the ground-truth per-step score.
_W = np.array([1.3, 0.7, 0.6, 1.2, 0.8])


def sample_route(rng: np.random.Generator, route_id: str) -> Route:
    """Sample one route (2..7 steps) with a worst-step-dominated manufacturability."""
    L = int(rng.integers(2, 8))
    g = rng.beta(8, 1.5, size=(L, len(FEATURES)))       # steps are usually good (~0.84)
    if rng.random() < 0.6:                              # inject a genuinely bad step
        bad = int(rng.integers(0, L))
        col = int(rng.integers(0, len(FEATURES)))
        g[bad, col] = rng.beta(1.2, 6)                  # a low value (toxic / uphill step)
    # per-step score = weighted geometric mean of goodness features
    step_score = np.exp((np.log(np.clip(g, 1e-3, 1)) * _W).sum(1) / _W.sum())
    # manufacturability is dominated by the WORST step (structural, not length):
    #   soft-min(step) with a mild length penalty. Step-count sees only L.
    manuf = (0.6 * step_score.min() + 0.4 * step_score.mean()) * (0.96 ** (L - 2))
    manuf = float(np.clip(manuf + rng.normal(0, 0.02), 0.0, 1.0))
    steps = [Step(features=dict(zip(FEATURES, row, strict=True))) for row in g]
    return Route(route_id=route_id, steps=steps, manufacturability=manuf)


def make_dataset(n: int, seed: int = 0) -> list[Route]:
    """A list of ``n`` labeled synthetic routes."""
    rng = np.random.default_rng(seed)
    return [sample_route(rng, route_id=f"r{i}") for i in range(n)]
