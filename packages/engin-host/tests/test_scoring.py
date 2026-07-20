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


def test_small_molecule_query_picks_gras_yeast():
    kb = default_kb()
    q = HostQuery(
        weights=dict(smallmol=1.0, gras=1.0, cost=0.9, titer=0.7, speed=0.7),
        hard=dict(gras=0.7),
    )
    ranked = score(kb, q)
    assert ranked[0].host == "S. cerevisiae"     # GRAS, cheap, good small-molecule host
    assert ranked[0].feasible


def test_two_queries_pick_different_hosts():
    kb = default_kb()
    a = score(kb, HostQuery(weights=dict(glyco=1.0, protein=1.0), hard=dict(glyco=0.6)))
    b = score(kb, HostQuery(weights=dict(smallmol=1.0, gras=1.0), hard=dict(gras=0.7)))
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
    p = prob_meets(ranked[0], threshold=ranked[0].score)   # threshold == mean
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
