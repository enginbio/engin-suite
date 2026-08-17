"""The calibration gate's thresholds (#20).

`benchmarks/benchmark.py --check` is what makes CI fail on a calibration
regression. Before it existed the step ran the benchmark and asserted nothing,
so a regression passed all nine required checks while three published baseline
tables rode on the numbers.

These test the thresholds rather than the benchmark: running it takes minutes,
and what can silently rot is the *decision rule*, not the arithmetic around it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# benchmarks/ is not a package and is not on the pythonpath (ADR 0004 keeps that
# list to the sources the suite imports), so point at it explicitly.
_BENCH = Path(__file__).resolve().parents[1] / "benchmarks"
sys.path.insert(0, str(_BENCH))

benchmark = pytest.importorskip("benchmark", reason="benchmarks/ not present")


def test_a_healthy_run_passes():
    """The values the current code actually produces at four seeds."""
    assert benchmark.check_thresholds(0.95, 15.7) == []


def test_the_naive_collapse_fails():
    """The regression this gate exists for: the conformal path bypassed, leaving
    the epistemic-only interval the same table reports at ~0.56."""
    failures = benchmark.check_thresholds(0.56, 15.7)
    assert len(failures) == 1
    assert "below the floor" in failures[0]


def test_coverage_bought_by_widening_fails():
    """The gate must not be satisfiable by making intervals enormous.

    This is the case a coverage-only gate waves through, and it is the failure
    docs/methods/out-of-distribution.md is about: an interval that always covers
    is trivially available.
    """
    failures = benchmark.check_thresholds(0.99, 80.0)
    assert len(failures) == 1
    assert "above the ceiling" in failures[0]


def test_both_failures_are_reported_together():
    """A run that is broken two ways should say so once, not make you fix and
    re-run to discover the second."""
    assert len(benchmark.check_thresholds(0.56, 80.0)) == 2


def test_the_thresholds_are_inclusive_at_the_boundary():
    assert benchmark.check_thresholds(benchmark.COVERAGE_FLOOR, benchmark.WIDTH_CEILING) == []


def test_the_floor_sits_between_healthy_and_broken():
    """The floor is only meaningful if it separates the two observed regimes.

    Healthy conformal coverage runs ~0.95 and the bypassed path ~0.56; a floor
    outside that interval would either never fire or fire constantly.
    """
    assert 0.56 < benchmark.COVERAGE_FLOOR < 0.95


def test_the_width_ceiling_leaves_room_above_the_healthy_value():
    """~16 g/L is healthy on this simulator, whose titers run around 50."""
    assert 16.0 < benchmark.WIDTH_CEILING < 50.0
