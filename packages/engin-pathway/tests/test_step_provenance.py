"""Per-feature provenance on Step and Route (#140 item 4).

The disclosure has to survive crossing a function boundary. While every feature
was hand-typed, a docstring said that adequately; once `step_from_reaction`
started returning a *mixed* step, a docstring stopped being able to.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from engin_pathway.schema import FEATURES, Route, Step

_F = dict.fromkeys(FEATURES, 0.5)


def test_a_step_written_before_this_field_existed_is_correctly_labelled():
    """Default empty: additive, so no existing route needs editing."""
    step = Step(features=_F)
    assert step.measured == frozenset()
    assert step.fully_judged
    assert step.judged == frozenset(FEATURES)


def test_a_mixed_step_reports_both_halves():
    step = Step(features=_F, measured=frozenset({"g_thermo"}))
    assert not step.fully_judged
    assert step.measured == {"g_thermo"}
    assert step.judged == frozenset(FEATURES) - {"g_thermo"}


def test_measured_cannot_name_a_feature_that_does_not_exist():
    """A typo would otherwise silently claim provenance for nothing."""
    with pytest.raises(ValidationError, match="unknown features"):
        Step(features=_F, measured=frozenset({"g_thermodynamics"}))


def test_from_manual_scores_builds_a_fully_judged_route():
    route = Route.from_manual_scores("r1", [_F, _F])
    assert route.fully_judged
    assert len(route.steps) == 2
    assert all(s.fully_judged for s in route.steps)


def test_from_manual_scores_matches_direct_construction():
    """It adds a statement at the call site, not different behaviour."""
    manual = Route.from_manual_scores("r1", [_F])
    direct = Route(route_id="r1", steps=[Step(features=_F)])
    assert manual.model_dump() == direct.model_dump()


def test_a_route_is_not_fully_judged_if_any_step_carries_a_measurement():
    """One measured step is enough to make the ranking not purely a prior."""
    route = Route(
        route_id="r1",
        steps=[Step(features=_F), Step(features=_F, measured=frozenset({"g_thermo"}))],
    )
    assert not route.fully_judged


def test_provenance_survives_a_round_trip():
    """It crosses into a memo, a CLI or a handoff; it has to survive the trip."""
    step = Step(features=_F, measured=frozenset({"g_thermo"}))
    assert Step.model_validate_json(step.model_dump_json()) == step
