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
    assert brief.uncertainty == pytest.approx(0.08)  # (0.88-0.72)/2
    assert brief.host == "CHO (mammalian)"
    assert "process" in brief.provenance
