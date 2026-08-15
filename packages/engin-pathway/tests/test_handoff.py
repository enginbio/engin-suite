"""Stage [3] -> funnel adapter: intervals cross the boundary, and stay conformal."""

from __future__ import annotations

import pytest
from engin_core import HostDecision, RouteRanking, process_brief

from engin_pathway import PathwayRanker, make_dataset, to_ranking


@pytest.fixture
def fitted():
    routes = make_dataset(n=120, seed=0)
    ranker = PathwayRanker(embed_seed=0).fit(routes[:80]).calibrate(routes[80:])
    return ranker, routes[:12]


def test_to_ranking_produces_the_handoff_type(fitted):
    ranker, routes = fitted
    ranking = to_ranking(ranker, routes)

    assert isinstance(ranking, RouteRanking)
    assert len(ranking.routes) == len(routes)
    assert {r.route_id for r in ranking.routes} == {r.route_id for r in routes}
    assert ranking.top.manufacturability == max(r.manufacturability for r in ranking.routes)


def test_intervals_are_the_rankers_calibrated_bounds_unmodified(fitted):
    """The handoff must not quietly widen a conformal interval — see to_ranking's docstring."""
    ranker, routes = fitted
    ranking = to_ranking(ranker, routes)
    hw = ranker.half_width()

    for ranked in ranking.routes:
        assert ranked.half_width == pytest.approx(hw)
        assert ranked.lo == pytest.approx(ranked.manufacturability - hw)
        assert ranked.hi == pytest.approx(ranked.manufacturability + hw)


def test_an_uncalibrated_ranker_cannot_cross_the_boundary():
    """A ranking without an interval is the thing the handoff vocabulary exists to stop."""
    routes = make_dataset(n=40, seed=1)
    uncalibrated = PathwayRanker(embed_seed=0).fit(routes)
    with pytest.raises(RuntimeError, match="calibrate"):
        to_ranking(uncalibrated, routes[:5])


def test_empty_routes_is_an_error(fitted):
    ranker, _ = fitted
    with pytest.raises(ValueError, match="empty route list"):
        to_ranking(ranker, [])


def test_upstream_host_is_recorded_and_reaches_the_process_brief(fitted):
    ranker, routes = fitted
    host = HostDecision(host="P. pastoris", feasible=True, score=0.72, band90=0.05, confidence=0.6)
    ranking = to_ranking(ranker, routes, host=host)

    assert ranking.conditioned_on_host == "P. pastoris"
    assert ranking.host_confidence == pytest.approx(0.6)

    brief = process_brief(ranking)
    assert brief.host == "P. pastoris"
    assert "P. pastoris" in brief.provenance
    # the recorded confidence is what the funnel inflates by, downstream of here
    assert brief.uncertainty == pytest.approx(ranking.top.half_width * 1.4)


def test_host_agnostic_ranking_records_no_upstream(fitted):
    ranker, routes = fitted
    ranking = to_ranking(ranker, routes)
    assert ranking.conditioned_on_host is None
    assert ranking.host_confidence is None
