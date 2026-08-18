"""The vessel as data: defaults are exactly the old behaviour, and cost follows the config."""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from engin_core import KNOB_NAMES, simulate, simulate_unit, unit_to_physical
from engin_core.simulator import DEFAULT_REACTOR, ReactorConfig
from engin_core.tea import ParametricCostModel, design_context

# ------------------------------------------------------------------ defaults


def test_default_config_is_a_no_op():
    """The whole compatibility story: omitting config must change nothing."""
    rng = np.random.default_rng(0)
    U = rng.random((12, len(KNOB_NAMES)))
    assert np.array_equal(unit_to_physical(U), unit_to_physical(U, ReactorConfig()))
    assert np.array_equal(simulate_unit(U[:4]), simulate_unit(U[:4], config=ReactorConfig()))
    assert simulate(0.03, 8.0, 300.0, 10.0, 15.0)[0] == pytest.approx(
        simulate(0.03, 8.0, 300.0, 10.0, 15.0, config=DEFAULT_REACTOR)[0]
    )


def test_defaults_match_the_module_constants():
    from engin_core import simulator as sim

    cfg = ReactorConfig()
    assert (cfg.v0, cfg.vmax, cfg.t_end, cfg.dt, cfg.x0) == (
        sim.V0,
        sim.VMAX,
        sim.T_END,
        sim.DT,
        sim.X0,
    )
    assert cfg.knob_bounds == {name: (lo, hi) for name, lo, hi in sim.KNOBS}


# ------------------------------------------------------------- a real vessel


def test_a_bigger_vessel_produces_a_bigger_batch():
    small = ReactorConfig()
    big = ReactorConfig(v0=10.0, vmax=25.0)
    knobs = (0.5, 5.0, 300.0, 10.0, 20.0)

    _, trace_small = simulate(*knobs, config=small)
    _, trace_big = simulate(*knobs, config=big)
    assert trace_big[-1, 4] > trace_small[-1, 4]


def test_feeding_stops_at_the_configured_working_volume():
    cfg = ReactorConfig(v0=1.0, vmax=1.5)
    # a feed aggressive enough to overfill this vessel many times over
    _, trace = simulate(0.06, 3.0, 300.0, 10.0, 15.0, config=cfg)
    assert trace[:, 4].max() <= cfg.vmax + 1e-3


def test_a_plain_batch_reactor_is_expressible():
    """``v0 == vmax`` means no headroom, so nothing is fed — a batch process rather than
    a fed-batch one. Allowed on purpose: it is a different process, not an incoherent
    vessel, and it is the simplest thing a bench scientist actually runs."""
    cfg = ReactorConfig(v0=2.0, vmax=2.0)
    _, trace = simulate(0.06, 3.0, 300.0, 10.0, 15.0, config=cfg)  # max feed, ignored
    assert trace[:, 4].max() == pytest.approx(2.0)

    ctx = design_context(np.full((1, len(KNOB_NAMES)), 0.9), cfg)
    assert ctx["final_volume_L"][0] == pytest.approx(2.0)


def test_a_longer_run_uses_the_configured_horizon():
    _, short = simulate(0.03, 8.0, 300.0, 10.0, 15.0, config=ReactorConfig(t_end=24.0))
    _, long_ = simulate(0.03, 8.0, 300.0, 10.0, 15.0, config=ReactorConfig(t_end=96.0))
    assert short[-1, 0] == pytest.approx(24.0)
    assert long_[-1, 0] == pytest.approx(96.0)


def test_custom_knob_bounds_reinterpret_the_unit_cube():
    cfg = ReactorConfig(knob_bounds={**ReactorConfig().knob_bounds, "S0": (100.0, 200.0)})
    lo = unit_to_physical(np.zeros((1, len(KNOB_NAMES))), cfg)[0]
    hi = unit_to_physical(np.ones((1, len(KNOB_NAMES))), cfg)[0]
    j = KNOB_NAMES.index("S0")
    assert lo[j] == pytest.approx(100.0)
    assert hi[j] == pytest.approx(200.0)


# -------------------------------------------------------------- the cost seam


def test_design_context_volume_agrees_with_the_simulator():
    """The defect this config work uncovered: two parts of one package disagreeing
    about how much liquid is in the vessel. Cross-check them directly."""
    rng = np.random.default_rng(0)
    U = rng.random((10, len(KNOB_NAMES)))
    modelled = design_context(U)["final_volume_L"]

    for u, v_model in zip(U, modelled, strict=True):
        phys = unit_to_physical(u[None, :])[0]
        _, trace = simulate(*phys)
        assert v_model == pytest.approx(trace[-1, 4], abs=1e-3)


def test_design_context_never_exceeds_the_working_volume():
    """Pins the correction directly: before it, an aggressive feed reported 3.700 L
    against a 2.5 L vessel."""
    aggressive = np.ones((1, len(KNOB_NAMES)))
    aggressive[0, KNOB_NAMES.index("feed_start")] = 0.0  # feed early, at max rate
    assert design_context(aggressive)["final_volume_L"][0] <= DEFAULT_REACTOR.vmax + 1e-9


def test_cost_model_follows_a_custom_vessel():
    """The point of threading config into tea: a user's own reactor changes their cost."""
    U = np.full((1, len(KNOB_NAMES)), 0.5)
    titer = np.array([20.0])

    default_cost = ParametricCostModel().cost_per_kg(titer, U)[0]
    big_cost = ParametricCostModel(config=ReactorConfig(v0=50.0, vmax=125.0)).cost_per_kg(titer, U)[
        0
    ]
    assert big_cost != pytest.approx(default_cost)


def test_cost_breakdown_uses_the_same_config():
    cfg = ReactorConfig(v0=5.0, vmax=12.0)
    model = ParametricCostModel(config=cfg)
    U = np.full((1, len(KNOB_NAMES)), 0.5)
    titer = np.array([20.0])

    total = model.cost_per_kg(titer, U)[0]
    assert sum(v[0] for v in model.cost_breakdown(titer, U).values()) == pytest.approx(total)


# --------------------------------------------------------------- validation


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({"v0": 5.0, "vmax": 2.0}, "vmax"),
        ({"dt": 100.0, "t_end": 48.0}, "dt"),
        ({"v0": -1.0}, "greater than 0"),
        ({"t_end": 0.0}, "greater than 0"),
    ],
)
def test_incoherent_vessels_fail_loudly(kwargs, match):
    with pytest.raises(ValidationError, match=match):
        ReactorConfig(**kwargs)


def test_knob_set_is_fixed_by_the_equations():
    """A sixth knob is a change to _rhs, not a configuration -- so reject it here."""
    with pytest.raises(ValidationError, match="knob_bounds"):
        ReactorConfig(knob_bounds={**ReactorConfig().knob_bounds, "stirrer_rpm": (100.0, 900.0)})
    with pytest.raises(ValidationError, match="knob_bounds"):
        ReactorConfig(knob_bounds={"S0": (5.0, 30.0)})  # incomplete


def test_inverted_knob_range_is_rejected():
    with pytest.raises(ValidationError, match="feed_rate"):
        ReactorConfig(knob_bounds={**ReactorConfig().knob_bounds, "feed_rate": (0.06, 0.0)})


# ------------------------------------------------- the scale-invariance limitation


def test_scaling_the_whole_vessel_changes_nothing_about_titer():
    """Pins the limitation, so it cannot be quietly fixed or quietly worsened.

    ``_rhs`` sees volume only through the dilution term ``F/V``, and the feeding
    switch is ``V < vmax``. Scaling ``v0``, ``vmax`` and the (volumetric) feed rate
    by a common factor leaves both invariant, so the concentration trajectories are
    pointwise identical and only ``V`` scales.

    This is a **limitation under test, not a property worth having**: it is exactly
    what it means for the simulator to have no oxygen state, and it is why no
    statement about *scale* can be supported by this model. Documented under "The
    simulator has no oxygen, so scale is inert" in ``docs/limitations.md`` (#190).

    So a failure here is good news and a docs change, not a bug. Adding a
    dissolved-oxygen state, a kLa correlation or an overflow branch should break
    this test -- that is the signal that ``docs/limitations.md`` needs updating.
    """
    factor = 10_000.0
    feed_rate, rest = 0.03, (5.0, 300.0, 10.0, 20.0)
    big = ReactorConfig(v0=DEFAULT_REACTOR.v0 * factor, vmax=DEFAULT_REACTOR.vmax * factor)

    titer_bench, trace_bench = simulate(feed_rate, *rest)
    titer_big, trace_big = simulate(feed_rate * factor, *rest, config=big)

    # Tolerance sits far above RK45 truncation error (~1e-6 at these settings) and
    # far below any physical scale effect, so this fails on physics, not on noise.
    assert titer_big == pytest.approx(titer_bench, abs=1e-4)
    # X, S, P pointwise identical; V scales by exactly the factor.
    assert np.allclose(trace_big[:, 1:4], trace_bench[:, 1:4], atol=1e-4)
    assert np.allclose(trace_big[:, 4], trace_bench[:, 4] * factor, rtol=1e-6)
