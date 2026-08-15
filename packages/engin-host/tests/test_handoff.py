"""Stage [4] -> funnel adapter: what a HostDecision must carry, and what confidence means."""

from __future__ import annotations

import pytest
from engin_core import HostDecision

from engin_host import HostQuery, default_kb, score, to_decision
from engin_host.handoff import decision_confidence
from engin_host.schema import HostScore


def _hs(host: str, s: float, sd: float, feasible: bool = True) -> HostScore:
    return HostScore(
        host=host,
        score=s,
        sd=sd,
        band90=1.645 * sd,
        contributions=[("titer", 0.3), ("cost", 0.2), ("speed", 0.1)],
        flags=[] if feasible else ["glyco 0.05 < required 0.50"],
        feasible=feasible,
    )


def test_to_decision_produces_the_handoff_type_from_real_scores():
    kb = default_kb()
    query = HostQuery(weights={"secretion": 1.0, "titer": 1.0, "scaleup": 0.5})
    decision = to_decision(score(kb, query), kb=kb)

    assert isinstance(decision, HostDecision)
    assert decision.host == score(kb, query)[0].host  # the top-ranked host
    assert 0.0 <= decision.confidence <= 1.0
    assert decision.key_drivers  # non-empty rationale
    assert set(decision.capability_profile) == set(kb.capabilities)


def test_empty_scores_is_an_error_not_a_default_decision():
    with pytest.raises(ValueError, match="empty score list"):
        to_decision([])


def test_capability_profile_is_empty_rather_than_wrong_without_a_kb():
    """Without the KB the true profile is unavailable; contributions are a different
    quantity and must not be substituted for it."""
    decision = to_decision([_hs("E. coli", 0.8, 0.02)])
    assert decision.capability_profile == {}


def test_confidence_falls_when_the_top_two_are_a_close_call():
    clear = decision_confidence(_hs("A", 0.90, 0.02), _hs("B", 0.50, 0.02))
    close = decision_confidence(_hs("A", 0.90, 0.02), _hs("B", 0.89, 0.02))
    assert clear > close
    assert close == pytest.approx(0.5, abs=0.15)  # near a coin flip


def test_confidence_falls_when_the_knowledge_base_is_thin():
    """Same margin, wider bands -> less confident. This is the #146 case: an illustrative
    KB must not be able to produce a confident-looking decision."""
    firm = decision_confidence(_hs("A", 0.80, 0.01), _hs("B", 0.70, 0.01))
    thin = decision_confidence(_hs("A", 0.80, 0.30), _hs("B", 0.70, 0.30))
    assert firm > thin


def test_uncontested_choice_is_confident_but_says_nothing_about_quality():
    decision = to_decision([_hs("E. coli", 0.31, 0.02)])
    assert decision.confidence == 1.0
    assert decision.score == pytest.approx(0.31)  # the band/score carry the bad news


def test_infeasible_hosts_do_not_contest_a_feasible_decision():
    """A demoted host is not an alternative, and must not drag the confidence down."""
    scores = [_hs("P. pastoris", 0.70, 0.02), _hs("E. coli", 0.69, 0.02, feasible=False)]
    decision = to_decision(scores)

    assert decision.feasible
    assert decision.alternatives == []  # the infeasible rival is not an alternative
    assert decision.confidence == 1.0  # uncontested among feasible hosts


def test_decision_is_infeasible_when_nothing_clears_the_hard_constraint():
    kb = default_kb()
    # glycosylation required: every prokaryote in the KB fails it
    query = HostQuery(weights={"glyco": 1.0, "cost": 1.0}, hard={"glyco": 0.99})
    decision = to_decision(score(kb, query), kb=kb)
    assert not decision.feasible
