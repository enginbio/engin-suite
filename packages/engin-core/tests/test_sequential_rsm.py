"""The sequential RSM baseline exists so it can win, so the tests check it is real.

``test_baselines.py`` says the same thing about the single-shot version. It
matters more here: a *weak* implementation of Box--Wilson would make the whole
multi-round comparison worthless while still producing a table full of numbers,
and nothing in the output would look wrong. So these tests check the design
against the catalogue, check the ascent actually climbs, and check the budget
accounting the fairness of the comparison rests on.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))

from baselines import fit_rsm  # noqa: E402
from sequential_rsm import (  # noqa: E402
    SequentialRSM,
    maximize_in_box,
    stationary_point,
    two_level_design,
)

# -- the designs, against the published catalogue -----------------------------


def test_five_factor_block_is_the_catalogued_2_5_2_fraction():
    """NIST/SEMATECH table 3.17: 8 runs, generators D = AB and E = AC."""
    X = two_level_design(5)
    assert X.shape == (8, 5)
    assert set(np.unique(X)) == {-1.0, 1.0}
    assert np.allclose(X[:, 3], X[:, 0] * X[:, 1])  # D = AB
    assert np.allclose(X[:, 4], X[:, 0] * X[:, 2])  # E = AC


def test_the_block_is_orthogonal_so_main_effects_are_estimable():
    """The whole point of a designed block: X'X diagonal, every column balanced."""
    for d in range(1, 8):
        X = two_level_design(d)
        assert X.shape == (8, d)
        assert np.allclose(X.sum(axis=0), 0.0)
        assert np.allclose(X.T @ X, 8.0 * np.eye(d))


def test_no_eight_run_design_is_claimed_for_more_than_seven_factors():
    """Eight runs saturate at seven factors; pretending otherwise would alias
    a main effect with the intercept."""
    for bad in (0, 8, 12):
        try:
            two_level_design(bad)
        except ValueError:
            continue
        raise AssertionError(f"d={bad} should not have an eight-run design")


# -- canonical analysis -------------------------------------------------------


def test_stationary_point_finds_a_known_maximum_and_calls_it_one():
    rng = np.random.default_rng(0)
    U = rng.random((80, 3))
    peak = np.array([0.3, 0.7, 0.45])
    model = fit_rsm(U, -np.sum((U - peak) ** 2, axis=1))
    xs, eig = stationary_point(model)
    assert np.allclose(xs, peak, atol=1e-6)
    assert np.all(eig < 0)  # all-negative eigenvalues == a maximum


def test_a_one_optimum_surface_still_spends_its_whole_batch_on_distinct_runs():
    """A near-planar fit sends every multi-start to the same corner. Padding the
    batch with copies of it would spend eight bioreactors to learn one number,
    since the simulator is deterministic -- so the spare runs go to a small
    design around the optimum instead."""
    rng = np.random.default_rng(4)
    U = rng.random((60, 4))
    model = fit_rsm(U, U @ np.array([1.0, 0.7, 0.4, 0.9]))  # a plane: one vertex
    batch = maximize_in_box(model, np.zeros(4), np.ones(4), k=8, seed=0)
    assert batch.shape == (8, 4)
    assert len(np.unique(batch.round(9), axis=0)) == 8


def test_maximize_in_box_stays_inside_the_region_it_was_given():
    """A response surface is only trusted where it was fitted; the optimizer
    must not walk out of the region of interest to find a better prediction."""
    rng = np.random.default_rng(1)
    U = rng.random((80, 3))
    peak = np.array([0.9, 0.9, 0.9])
    model = fit_rsm(U, -np.sum((U - peak) ** 2, axis=1))
    lo, hi = np.zeros(3), np.full(3, 0.4)
    batch = maximize_in_box(model, lo, hi, k=4, seed=0)
    assert batch.shape == (4, 3)
    assert np.all(batch >= lo - 1e-9) and np.all(batch <= hi + 1e-9)
    assert np.allclose(batch[0], hi, atol=1e-3)  # pushed against the near face


# -- the campaign -------------------------------------------------------------


def _campaign(truth, seed=0, n0=40, d=5, rounds=8, k=8, radius=0.2):
    """Run a noiseless campaign against ``truth`` and return the state."""
    rng = np.random.default_rng(seed)
    U0 = rng.random((n0, d))
    camp = SequentialRSM(U0, truth(U0), radius=radius, seed=seed)
    for _ in range(rounds):
        X = camp.ask(k)
        camp.tell(X, truth(X))
    return camp


def test_the_budget_is_exactly_what_was_promised():
    """Equal-budget is the whole claim of the multi-round comparison: every
    block must be k runs whatever phase the campaign happens to be in."""
    rng = np.random.default_rng(2)
    U0 = rng.random((40, 5))
    camp = SequentialRSM(U0, rng.random(40), radius=0.2, seed=0)
    for _ in range(12):
        X = camp.ask(8)
        assert X.shape == (8, 5)
        assert np.all(X >= 0.0) and np.all(X <= 1.0)
        camp.tell(X, rng.random(8))
    assert len(camp.U) == 40 + 12 * 8
    assert len(camp.y) == len(camp.U)


def test_all_four_box_wilson_phases_are_reached():
    """factorial -> ascent -> axial -> canonical. A campaign that never leaves
    the first two is doing steepest ascent, not response surface methodology."""
    peak = np.array([0.55, 0.45, 0.5, 0.6, 0.4])
    camp = _campaign(lambda U: -np.sum((U - peak) ** 2, axis=1), rounds=10)
    assert set(camp.history) == {"factorial", "ascent", "axial", "canonical"}


def test_steepest_ascent_climbs_a_linear_surface_to_its_corner():
    """On a plane the optimum is a vertex, and the path of steepest ascent is
    the whole method. If this does not reach the corner, the gradient is wrong."""
    w = np.array([1.0, 0.6, 0.9, 0.3, 0.7])
    camp = _campaign(lambda U: U @ w, rounds=6)
    best = camp.U[int(np.argmax(camp.y))]
    assert np.all(best > 0.9)


def test_recentring_converges_on_a_known_interior_optimum():
    """The refit-and-re-centre cycle should walk to an interior peak that no
    initial design point is near."""
    peak = np.array([0.31, 0.72, 0.48, 0.63, 0.27])
    camp = _campaign(lambda U: -np.sum((U - peak) ** 2, axis=1), rounds=8)
    best = camp.U[int(np.argmax(camp.y))]
    assert np.linalg.norm(best - peak) < 0.05
    assert camp.radius < 0.2  # the region shrank, which is how it converged


def test_a_cornered_centre_still_produces_a_full_block():
    """The best point sitting on a face of the cube is the common case, not an
    edge case: the gradient there points partly out of the design space."""
    camp = _campaign(lambda U: U.sum(axis=1), rounds=6, radius=0.4)
    assert camp.U.shape == (40 + 6 * 8, 5)
    assert np.all(camp.U >= 0.0) and np.all(camp.U <= 1.0)
    for block_start in range(40, len(camp.U), 8):
        block = camp.U[block_start : block_start + 8]
        assert len(np.unique(block.round(6), axis=0)) > 1  # not eight copies


def test_the_second_order_fit_starts_global_and_is_not_starved():
    """A quadratic in five knobs needs 21 coefficients. The region of interest
    grows until it holds enough runs, so the first fit is the global one the
    single-shot baseline performs -- this method starts at least that strong."""
    rng = np.random.default_rng(3)
    U0 = rng.random((40, 5))
    camp = SequentialRSM(U0, rng.random(40), radius=0.05, seed=0)
    lo, hi, model = camp._region_fit()
    inside = np.all((camp.U >= lo - 1e-9) & (camp.U <= hi + 1e-9), axis=1)
    assert inside.sum() >= 21
    assert model.d == 5
