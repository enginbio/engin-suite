"""Mechanistic fed-batch bioreactor simulator.

A minimal but non-trivial Monod / Luedeking-Piret model with product
inhibition, so that titer is a *non-monotonic* function of the operator's
design knobs (there is a real interior optimum to find). This is the
synthetic-data engine for engin-core: it lets us build and validate the
forecasting + recommendation loop with zero partner data.

The mechanistic *equations* are bespoke (they are the domain model); the
*integrator* is scipy's ``solve_ivp`` (RK45) rather than a hand-rolled RK4 --
a solved wheel we no longer reinvent. The RHS has hard switches at ``feed_start``
and ``induction_time``, so we integrate *piecewise between those breakpoints*:
each segment is smooth, letting RK45 adapt freely (fast) without stepping over a
discontinuity (accurate -- matches a fine fixed-step RK4 to <0.03 g/L).

State vector ``y = [X, S, P, V]``:

    X  biomass            (g/L)
    S  substrate          (g/L)
    P  product / titer    (g/L)
    V  volume             (L)

Design knobs (what a process team actually controls in a DoE):

    feed_rate       constant feed after ``feed_start``   (L/h)
    feed_start      when feeding begins                  (h)
    Sf              substrate conc in the feed           (g/L)
    induction_time  when product formation switches on   (h)
    S0              initial batch substrate              (g/L)
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.integrate import solve_ivp

# Fixed biological / strain constants (would be fit per strain in production)
MU_MAX = 0.35  # 1/h   max specific growth rate
KS = 0.5  # g/L   Monod half-saturation
YXS = 0.5  # g/g   biomass yield on substrate
M = 0.02  # 1/h   maintenance coefficient
ALPHA = 0.09  # g/g   growth-associated product formation
BETA = 0.03  # 1/h   non-growth-associated product formation
KP = 18.0  # g/L   product-inhibition constant
X0 = 0.2  # g/L   inoculum biomass
V0 = 1.0  # L     initial volume
VMAX = 2.5  # L     max working volume (stop feeding when reached)
T_END = 48.0  # h
DT = 0.05  # h     output grid + solver max step (keeps switches sharp)

# Physical ranges for the 5 design knobs (unit cube [0,1] maps into these).
KNOBS: list[tuple[str, float, float]] = [
    ("feed_rate", 0.00, 0.06),  # L/h
    ("feed_start", 3.0, 20.0),  # h
    ("Sf", 150.0, 450.0),  # g/L
    ("induction_time", 3.0, 26.0),  # h
    ("S0", 5.0, 30.0),  # g/L
]
KNOB_NAMES: list[str] = [k[0] for k in KNOBS]


def unit_to_physical(U: ArrayLike) -> NDArray[np.float64]:
    """Map points in the unit cube ``[0, 1]^5`` to physical knob values."""
    U = np.atleast_2d(np.asarray(U, float))
    lo = np.array([k[1] for k in KNOBS])
    hi = np.array([k[2] for k in KNOBS])
    return lo + U * (hi - lo)


def _rhs(
    t: float,
    y: NDArray[np.float64],
    feed_rate: float,
    feed_start: float,
    Sf: float,
    induction_time: float,
) -> list[float]:
    X, S, P, V = y
    S = max(S, 0.0)
    mu = MU_MAX * S / (KS + S) * (1.0 / (1.0 + P / KP))  # growth w/ product inhibition
    F = feed_rate if (t >= feed_start and V < VMAX) else 0.0
    dil = F / V
    dX = mu * X - dil * X
    dS = -(mu / YXS) * X - M * X + dil * (Sf - S)
    prod_on = 1.0 if t >= induction_time else 0.0
    dP = (ALPHA * mu + BETA) * X * prod_on - dil * P
    dV = F
    return [dX, dS, dP, dV]


def simulate(
    feed_rate: float,
    feed_start: float,
    Sf: float,
    induction_time: float,
    S0: float,
) -> tuple[float, NDArray[np.float64]]:
    """Integrate one run (RK45, piecewise); return ``(final_titer_gL, trace)``.

    ``trace`` has shape ``(n_steps + 1, 5)`` with columns ``[t, X, S, P, V]``,
    sampled on the ``DT`` grid via the solver's dense output.
    """
    args = (feed_rate, feed_start, Sf, induction_time)
    grid = np.arange(0.0, T_END + DT / 2, DT)
    # Breakpoints: integrate smooth segments between the RHS switch times.
    breaks = sorted({0.0, T_END} | {t for t in (feed_start, induction_time) if 0.0 < t < T_END})

    y = np.array([X0, S0, 0.0, V0], float)
    times = [np.array([0.0])]
    states = [y[None, :].copy()]
    for a, b in zip(breaks[:-1], breaks[1:], strict=False):
        sol = solve_ivp(
            _rhs,
            (a, b),
            y,
            args=args,
            method="RK45",
            rtol=1e-6,
            atol=1e-8,
            dense_output=True,
        )
        pts = grid[(grid > a) & (grid <= b)]  # grid points in this segment
        if pts.size:
            times.append(pts)
            states.append(sol.sol(pts).T)
        y = np.maximum(sol.y[:, -1], 0.0)  # carry exact endpoint forward

    t = np.concatenate(times)
    y_all = np.maximum(np.vstack(states), 0.0)  # clamp tiny negatives
    trace = np.column_stack([t, y_all])  # (n+1, 5): [t, X, S, P, V]
    return float(y[2]), trace


def simulate_unit(U: ArrayLike) -> NDArray[np.float64]:
    """Titer for a batch of unit-cube design points -> ``(n,)`` array."""
    phys = unit_to_physical(U)
    return np.array([simulate(*row)[0] for row in phys])


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    U = rng.random((200, 5))
    y = simulate_unit(U)
    print(
        f"titer  min={y.min():.2f}  med={np.median(y):.2f}  "
        f"max={y.max():.2f}  std={y.std():.2f}  (g/L)"
    )
