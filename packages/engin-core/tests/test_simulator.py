"""Simulator sanity: positivity, determinism, a real interior optimum, mapping."""

from __future__ import annotations

import numpy as np

from engin_core import KNOBS, simulate, simulate_unit, unit_to_physical
from engin_core.simulator import Kinetics


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


# ------------------------------------------------------- process variation (D12)


def test_default_kinetics_reproduce_the_bundled_process_exactly():
    """The defaults must stay byte-identical, not merely close.

    Two pinned findings depend on this simulator's exact behaviour -- the ~2%
    raw-material cost share and the agreement of the cost and titer optima. If a
    refactor perturbs the defaults at all, those tests start reporting on a
    different process than the one they were written about.
    """
    from engin_core.simulator import ALPHA, BETA, DEFAULT_KINETICS, KP, KS, MU_MAX, YXS, M

    assert (DEFAULT_KINETICS.mu_max, DEFAULT_KINETICS.ks, DEFAULT_KINETICS.yxs) == (MU_MAX, KS, YXS)
    assert (DEFAULT_KINETICS.m, DEFAULT_KINETICS.alpha) == (M, ALPHA)
    assert (DEFAULT_KINETICS.beta, DEFAULT_KINETICS.kp) == (BETA, KP)

    rng = np.random.default_rng(0)
    U = rng.random((25, len(KNOBS)))
    assert np.array_equal(simulate_unit(U), simulate_unit(U, kinetics=Kinetics()))


def test_altered_kinetics_give_a_genuinely_different_process():
    """Otherwise 'train on one process, test on another' tests nothing."""
    rng = np.random.default_rng(0)
    U = rng.random((25, len(KNOBS)))
    base = simulate_unit(U)
    shifted = simulate_unit(U, kinetics=Kinetics(kp=6.0, alpha=0.03))
    assert not np.allclose(base, shifted)
    assert np.isfinite(shifted).all() and (shifted >= 0).all()


def test_kinetics_reject_unphysical_values():
    import pytest
    from pydantic import ValidationError

    for bad in ({"mu_max": 0.0}, {"kp": -1.0}, {"yxs": 0.0}, {"alpha": -0.1}):
        with pytest.raises(ValidationError):
            Kinetics(**bad)
