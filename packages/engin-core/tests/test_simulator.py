"""Simulator sanity: positivity, determinism, a real interior optimum, mapping."""

from __future__ import annotations

import numpy as np

from engin_core import KNOBS, simulate, simulate_unit, unit_to_physical


def test_titer_is_positive_and_finite():
    titer, trace = simulate(0.03, 8.0, 300.0, 10.0, 15.0)
    assert np.isfinite(titer)
    assert titer > 0.0
    assert np.all(np.isfinite(trace))
    # states stay non-negative
    assert np.all(trace[:, 1:] >= 0.0)


def test_simulation_is_deterministic():
    a, _ = simulate(0.03, 8.0, 300.0, 10.0, 15.0)
    b, _ = simulate(0.03, 8.0, 300.0, 10.0, 15.0)
    assert a == b


def test_unit_to_physical_maps_corners():
    lo = unit_to_physical(np.zeros((1, len(KNOBS))))[0]
    hi = unit_to_physical(np.ones((1, len(KNOBS))))[0]
    mid = unit_to_physical(np.full((1, len(KNOBS)), 0.5))[0]
    for j, (_, klo, khi) in enumerate(KNOBS):
        assert lo[j] == klo
        assert hi[j] == khi
        assert abs(mid[j] - 0.5 * (klo + khi)) < 1e-9


def test_real_interior_optimum_exists():
    # Product inhibition means "crank every knob to max" is NOT optimal: an
    # interior design beats the all-max corner, so there is a real optimum to
    # find (the premise of the whole recommend loop).
    rng = np.random.default_rng(1)
    U = rng.random((500, len(KNOBS)))
    y = simulate_unit(U)
    assert y.std() > 1.0  # meaningful spread
    all_max_corner = simulate_unit(np.ones((1, len(KNOBS))))[0]
    assert y.max() > all_max_corner  # interior beats corner
