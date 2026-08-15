"""Handoff contracts: validation, uncertainty inflation, brief distillation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from engin_core import (
    HostDecision,
    RankedRoute,
    RouteRanking,
    inflate_uncertainty,
    process_brief,
)


def test_confidence_must_be_a_probability():
    HostDecision(host="CHO", feasible=True, score=0.7, band90=0.04, confidence=0.8)
    with pytest.raises(ValidationError):
        HostDecision(host="CHO", feasible=True, score=0.7, band90=0.04, confidence=1.5)


def test_inflate_uncertainty_is_monotone_in_confidence():
    hw = 0.05
    assert inflate_uncertainty(hw, 1.0) == pytest.approx(hw)  # confident -> unchanged
    assert inflate_uncertainty(hw, 0.5) == pytest.approx(1.5 * hw)
    assert inflate_uncertainty(hw, 0.0) == pytest.approx(2.0 * hw)  # unsure -> doubled
    assert inflate_uncertainty(hw, None) == hw  # no upstream -> unchanged
    # strictly widens as confidence falls
    widths = [inflate_uncertainty(hw, c) for c in (0.9, 0.6, 0.3, 0.0)]
    assert widths == sorted(widths)


def test_route_ranking_top_and_brief():
    ranking = RouteRanking(
        routes=[
            RankedRoute(route_id="r1", manufacturability=0.6, lo=0.55, hi=0.65),
            RankedRoute(route_id="r2", manufacturability=0.8, lo=0.72, hi=0.88),
            RankedRoute(route_id="r3", manufacturability=0.5, lo=0.45, hi=0.55),
        ],
        conditioned_on_host="CHO (mammalian)",
        host_confidence=0.7,
    )
    assert ranking.top.route_id == "r2"  # highest manufacturability
    brief = process_brief(ranking)
    assert brief.route_id == "r2"
    assert brief.expected_manufacturability == pytest.approx(0.8)
    # stage half-width (0.88-0.72)/2 = 0.08, inflated by the upstream host decision:
    # factor (2 - 0.7) = 1.3. Uninflated 0.08 was the pre-2026-08-15 behaviour.
    assert brief.uncertainty == pytest.approx(0.08 * 1.3)
    assert brief.host == "CHO (mammalian)"
    assert "process" in brief.provenance


def test_brief_uncertainty_is_not_inflated_without_an_upstream_decision():
    """A host-agnostic ranking has nothing to inflate by, so the stage width passes through."""
    ranking = RouteRanking(
        routes=[RankedRoute(route_id="r1", manufacturability=0.6, lo=0.55, hi=0.65)]
    )
    assert process_brief(ranking).uncertainty == pytest.approx(0.05)


def test_uncertainty_never_narrows_across_the_funnel():
    """The funnel's contract: no hop may report more certainty than the one feeding it.

    This is the property the whole handoff vocabulary exists to enforce, so it is pinned
    directly rather than inferred from the inflation factor's own monotonicity.
    """
    stage_half_width = 0.06
    routes = [RankedRoute(route_id="r1", manufacturability=0.6, lo=0.54, hi=0.66)]

    for host_confidence in (1.0, 0.9, 0.6, 0.3, 0.0):
        ranking = RouteRanking(
            routes=routes,
            conditioned_on_host="E. coli",
            host_confidence=host_confidence,
        )
        brief = process_brief(ranking)
        assert brief.uncertainty >= stage_half_width - 1e-12

    # and strictly widens as the upstream decision gets shakier
    widths = [
        process_brief(
            RouteRanking(routes=routes, conditioned_on_host="E. coli", host_confidence=c)
        ).uncertainty
        for c in (0.9, 0.6, 0.3, 0.0)
    ]
    assert widths == sorted(widths)
