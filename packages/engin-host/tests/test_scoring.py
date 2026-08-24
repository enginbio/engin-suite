"""Scoring behavior: right picks, hard-constraint demotion, honest bands."""

from __future__ import annotations

import numpy as np
import pytest

from engin_host import HostQuery, default_kb, prob_meets, render_memo, score


def test_glycoprotein_query_picks_cho():
    # A secreted human glycoprotein with a hard glycosylation requirement should
    # pick CHO, and must demote high-scoring but glyco-incapable prokaryotes.
    kb = default_kb()
    q = HostQuery(
        weights=dict(glyco=1.0, secretion=0.9, protein=1.0, titer=0.6, scaleup=0.7),
        hard=dict(glyco=0.6),
    )
    ranked = score(kb, q)
    assert ranked[0].host == "CHO (mammalian)"
    assert ranked[0].feasible
    # E. coli (glyco 0.05) must be flagged infeasible and ranked below all feasible.
    ecoli = next(d for d in ranked if d.host == "E. coli")
    assert not ecoli.feasible and ecoli.flags
    assert ranked.index(ecoli) > max(i for i, d in enumerate(ranked) if d.feasible)


def test_small_molecule_query_ranks_on_capability_alone_now():
    """The ranking moved when `gras` was retired, and that is the point (ADR 0010).

    This test used to weight and hard-constrain on `gras` and assert *S. cerevisiae*
    won. It does not any more: on capability alone the winner is **E. coli**, which
    is cheaper, faster and a better small-molecule host on this KB.

    The old answer was produced by a column that "corresponds to no citable fact" --
    a scalar that ordered *E. coli* (assessed and refused by EFSA) above CHO (never
    in scope) as though those were points on one axis. Removing it removes a
    demotion that was never evidence.

    The food-safety consideration did not disappear; it stopped being a score. It is
    now a displayed QPS status the reader applies against their own target market,
    which is the next test.
    """
    kb = default_kb()
    q = HostQuery(weights=dict(smallmol=1.0, cost=0.9, titer=0.7, speed=0.7))
    ranked = score(kb, q)
    assert ranked[0].host == "E. coli"
    assert ranked[0].feasible


def test_the_food_safety_fact_survives_as_a_status_not_a_score():
    """What the retired column was gesturing at, now stated exactly."""
    kb = default_kb()
    q = HostQuery(weights=dict(smallmol=1.0, cost=0.9, titer=0.7, speed=0.7))
    by_host = {d.host: d for d in score(kb, q)}

    assert by_host["S. cerevisiae"].qps.status == "listed"
    assert by_host["E. coli"].qps.status == "excluded"
    assert by_host["CHO (mammalian)"].qps.status == "out_of_scope"

    # Genuinely not in the arithmetic: a host EFSA *excluded* outranks a host EFSA
    # *listed*. Under the retired column that could not happen, which is what made
    # the column a disguised policy rather than a capability.
    assert by_host["E. coli"].score > by_host["S. cerevisiae"].score


def test_two_queries_pick_different_hosts():
    kb = default_kb()
    a = score(kb, HostQuery(weights=dict(glyco=1.0, protein=1.0), hard=dict(glyco=0.6)))
    b = score(kb, HostQuery(weights=dict(smallmol=1.0, cost=1.0)))
    assert a[0].host != b[0].host


def test_band_widens_with_lower_confidence():
    # Cell-free (TXTL) has the lowest confidences -> a wider band than E. coli
    # under a broad, equal-weight query.
    kb = default_kb()
    q = HostQuery(weights={c: 1.0 for c in kb.capabilities})
    ranked = {d.host: d for d in score(kb, q)}
    assert ranked["Cell-free (TXTL)"].sd > ranked["E. coli"].sd


def test_prob_meets_is_a_probability():
    kb = default_kb()
    ranked = score(kb, HostQuery(weights=dict(titer=1.0, speed=1.0)))
    p = prob_meets(ranked[0], threshold=ranked[0].score)  # threshold == mean
    assert abs(p - 0.5) < 1e-6
    assert prob_meets(ranked[0], 0.0) > prob_meets(ranked[0], 1.0)


def test_unknown_capability_raises():
    kb = default_kb()
    with pytest.raises(KeyError):
        score(kb, HostQuery(weights=dict(not_a_capability=1.0)))


def test_memo_renders_recommendation():
    kb = default_kb()
    ranked = score(kb, HostQuery(weights=dict(glyco=1.0), hard=dict(glyco=0.6)))
    memo = render_memo("test", ranked)
    assert "Recommendation:" in memo and ranked[0].host in memo
    assert np.isfinite(ranked[0].score)
