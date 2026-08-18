"""Reproduce the scale-invariance numbers in ``docs/limitations.md``.

The claim being reproduced is not "the simulator is inaccurate at scale". It is
that the simulator is **exactly** scale-invariant: ``_rhs`` depends on volume only
through the dilution term ``F/V`` and the feeding switch ``V < vmax``, so scaling
``v0``, ``vmax`` and ``feed_rate`` by a common factor leaves the concentration
trajectories pointwise identical and scales only ``V``.

That distinction is the whole point, and it is why this script tightens the solver
tolerance rather than just reporting one difference. A residual that stays put as
tolerance falls would be a real (if small) scale effect; a residual that tracks
tolerance is the integrator. It is the second.

    python benchmarks/scale_invariance.py
"""

from __future__ import annotations

import functools

import numpy as np

import engin_core.simulator as sim
from engin_core.simulator import (
    DEFAULT_REACTOR,
    KNOB_NAMES,
    ReactorConfig,
    simulate,
    unit_to_physical,
)

N_DESIGNS = 6
N_RANDOM = 3_000
TOP_K = 40
SEED = 0


def _scaled(x: np.ndarray, factor: float, cfg: ReactorConfig) -> float:
    """Titer for design ``x`` in a vessel ``factor`` times larger.

    ``feed_rate`` is knob 0 and is the one extensive knob -- it is a volumetric
    flow, so it scales with the vessel. The other four are intensive (times and
    concentrations) and are passed through unchanged.
    """
    return float(simulate(*([x[0] * factor] + list(x[1:])), config=cfg)[0])


def invariance_table(designs: np.ndarray) -> list[tuple[float, float, float]]:
    base = np.array([simulate(*x)[0] for x in designs])
    rows = []
    for factor in (10, 1_000, 10_000, 100_000):
        cfg = ReactorConfig(v0=DEFAULT_REACTOR.v0 * factor, vmax=DEFAULT_REACTOR.vmax * factor)
        got = np.array([_scaled(x, factor, cfg) for x in designs])
        rows.append((factor, cfg.vmax, float(np.abs(got - base).max())))
    return rows


def tolerance_sweep(designs: np.ndarray, factor: int = 10_000) -> list[tuple[float, float]]:
    """Largest titer difference at ``factor`` as the integrator tolerance falls.

    Patches ``solve_ivp`` in the simulator's namespace because the tolerances are
    deliberately not configurable -- they are a property of the shipped model, and
    exposing them as a knob to make this script easier would change the thing being
    measured.
    """
    original = sim.solve_ivp
    cfg = ReactorConfig(v0=DEFAULT_REACTOR.v0 * factor, vmax=DEFAULT_REACTOR.vmax * factor)
    rows = []
    try:
        for rtol, atol in ((1e-6, 1e-8), (1e-9, 1e-11), (1e-12, 1e-14)):

            @functools.wraps(original)
            def tightened(*args, _r=rtol, _a=atol, **kwargs):
                kwargs["rtol"], kwargs["atol"] = _r, _a
                return original(*args, **kwargs)

            sim.solve_ivp = tightened
            base = np.array([simulate(*x)[0] for x in designs])
            got = np.array([_scaled(x, factor, cfg) for x in designs])
            rows.append((rtol, float(np.abs(got - base).max())))
    finally:
        sim.solve_ivp = original
    return rows


def headroom() -> tuple[float, float, np.ndarray]:
    """Peak biomass at the knob ceiling, and where the best designs sit."""
    at_max = simulate(*unit_to_physical(np.ones((1, 5)))[0])[1][:, 1].max()
    rng = np.random.default_rng(SEED)
    U = rng.random((N_RANDOM, 5))
    physical = unit_to_physical(U)
    peaks = np.array([simulate(*p)[1][:, 1].max() for p in physical])
    titers = np.array([simulate(*p)[0] for p in physical])
    return float(at_max), float((peaks > 100).mean()), U[np.argsort(-titers)[:TOP_K]].mean(0)


def main() -> None:
    rng = np.random.default_rng(SEED)
    designs = unit_to_physical(rng.random((N_DESIGNS, 5)))

    print(f"Scale invariance, {N_DESIGNS} random designs")
    print(f"  bench vessel: v0={DEFAULT_REACTOR.v0} L, vmax={DEFAULT_REACTOR.vmax} L\n")
    print(f"  {'factor':>9}  {'vessel':>13}  {'largest titer difference':>25}")
    for factor, vmax, diff in invariance_table(designs):
        print(f"  {factor:>8,}x  {vmax:>11,.0f} L  {diff:>23.1e} g/L")

    print("\nIs the residual a scale effect or the integrator?")
    print("  (a real effect stays put as tolerance falls; truncation error tracks it)\n")
    print(f"  {'rtol':>9}  {'largest difference at 10,000x':>30}")
    for rtol, diff in tolerance_sweep(designs):
        print(f"  {rtol:>9.0e}  {diff:>28.1e} g/L")

    at_max, frac_hcd, top_mean = headroom()
    print(f"\nNo feasibility ceiling on feed_rate (vessel is {DEFAULT_REACTOR.vmax} L)")
    print(f"  peak biomass with every knob at its upper bound: {at_max:.1f} g/L DCW")
    print(f"  fraction of {N_RANDOM:,} random designs exceeding 100 g/L: {frac_hcd:.1%}")

    print(f"\nMean unit-cube coordinate, top {TOP_K} of {N_RANDOM:,} random designs")
    for name, value in zip(KNOB_NAMES, top_mean, strict=True):
        flag = "  <- pinned near upper bound" if value > 0.8 else ""
        print(f"  {name:<16} {value:.2f}{flag}")


if __name__ == "__main__":
    main()
