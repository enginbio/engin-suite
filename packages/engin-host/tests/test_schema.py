"""Schema validation: the KB fails loudly on malformed data."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from engin_host import Host, HostQuery, KnowledgeBase, QpsRecord, default_kb


def test_default_kb_is_valid():
    kb = default_kb()
    assert len(kb.hosts) == 6
    names, C, S = kb.matrices()
    assert C.shape == S.shape == (6, len(kb.capabilities))
    assert (S >= 0).all()


def test_host_rejects_out_of_range_capability():
    with pytest.raises(ValidationError):
        Host(name="bad", caps={"a": 1.5}, conf={"a": 0.9})  # 1.5 not in [0,1]


def test_host_rejects_mismatched_conf_keys():
    with pytest.raises(ValidationError):
        Host(name="bad", caps={"a": 0.5}, conf={"b": 0.9})  # keys differ


def test_kb_rejects_host_with_wrong_capabilities():
    good = Host(name="ok", caps={"a": 0.5, "b": 0.5}, conf={"a": 0.9, "b": 0.9})
    bad = Host(name="bad", caps={"a": 0.5}, conf={"a": 0.9})  # missing 'b'
    with pytest.raises(ValidationError):
        KnowledgeBase(capabilities=["a", "b"], hosts=[good, bad])


def test_query_rejects_all_zero_weights():
    with pytest.raises(ValidationError):
        HostQuery(weights={"a": 0.0})


# -- Provenance (#146). The shipped KB is sixty hand-assigned numbers, disclosed
# in prose. Prose does not survive a function boundary, so provenance is a field
# and these assert it cannot be quietly lost or quietly claimed.

_CAPS = {"a": 0.5, "b": 0.5}
_CONF = {"a": 0.9, "b": 0.9}


def test_provenance_defaults_to_illustrative():
    """An existing KB is correctly labelled with no edits, and a forgotten cell
    cannot claim to be sourced by omission."""
    host = Host(name="X", caps=_CAPS, conf=_CONF)
    assert host.provenance_of("a") == "illustrative"


def test_default_kb_is_entirely_illustrative():
    kb = default_kb()
    assert all(h.provenance_of(c) == "illustrative" for h in kb.hosts for c in kb.capabilities)


def test_sourced_cell_must_name_its_source():
    """Otherwise 'sourced' is an assertion rather than a pointer (D23)."""
    with pytest.raises(ValidationError, match="carries no sources.yaml id"):
        Host(name="Z", caps=_CAPS, conf=_CONF, provenance={"a": "sourced"})


def test_provenance_rejects_unknown_capability():
    with pytest.raises(ValidationError, match="unknown capability"):
        Host(name="W", caps=_CAPS, conf=_CONF, provenance={"nope": "illustrative"})


def test_score_provenance_is_the_worst_input_not_the_majority():
    """One invented input makes the output not a sourced number."""
    from engin_host.scoring import score

    partly = Host(
        name="Y",
        caps=_CAPS,
        conf=_CONF,
        provenance={"a": "sourced"},
        sources={"a": "some-source-id"},
    )
    kb = KnowledgeBase(capabilities=["a", "b"], hosts=[partly])
    result = score(kb, HostQuery(weights={"a": 1.0, "b": 1.0}))[0]
    assert result.provenance == "illustrative"
    assert result.unsourced == ["b"]


def test_zero_weighted_capability_does_not_taint_provenance():
    """A capability with no weight is not an input to the score, so an unsourced
    value there should not make the answer unsourced."""
    from engin_host.scoring import score

    partly = Host(
        name="Y",
        caps=_CAPS,
        conf=_CONF,
        provenance={"a": "sourced"},
        sources={"a": "some-source-id"},
    )
    kb = KnowledgeBase(capabilities=["a", "b"], hosts=[partly])
    result = score(kb, HostQuery(weights={"a": 1.0}))[0]
    assert result.provenance == "sourced"
    assert result.unsourced == []


def test_hard_constraint_capability_counts_even_at_zero_weight():
    """A hard constraint reads a capability, so it is an input to feasibility."""
    from engin_host.scoring import score

    partly = Host(
        name="Y",
        caps=_CAPS,
        conf=_CONF,
        provenance={"a": "sourced"},
        sources={"a": "some-source-id"},
    )
    kb = KnowledgeBase(capabilities=["a", "b"], hosts=[partly])
    result = score(kb, HostQuery(weights={"a": 1.0}, hard={"b": 0.1}))[0]
    assert result.provenance == "illustrative"
    assert result.unsourced == ["b"]


def test_memo_derives_its_basis_line_rather_than_hardcoding_it():
    from engin_host.memo import render_memo
    from engin_host.scoring import score

    sourced = Host(
        name="Y",
        caps=_CAPS,
        conf=_CONF,
        provenance={"a": "sourced", "b": "sourced"},
        sources={"a": "s1", "b": "s2"},
    )
    kb = KnowledgeBase(capabilities=["a", "b"], hosts=[sourced])
    memo = render_memo("t", score(kb, HostQuery(weights={"a": 1.0, "b": 1.0})))
    assert "All capability values behind these scores are sourced" in memo
    assert "illustrative" not in memo


# --------------------------------------------- EFSA QPS status (ADR 0010, #146)


def test_a_qps_status_that_is_a_claim_about_the_world_needs_a_source():
    """`listed` and `excluded` are D23 claims; `out_of_scope` is a scope fact."""
    with pytest.raises(ValidationError, match="sources.yaml id"):
        QpsRecord(status="listed", taxonomic_unit="Bacillus subtilis")
    with pytest.raises(ValidationError, match="sources.yaml id"):
        QpsRecord(status="excluded", taxonomic_unit="Escherichia coli")

    # out_of_scope is the one that may stand alone: nobody assessed it.
    assert QpsRecord(status="out_of_scope").source is None


def test_out_of_scope_cannot_carry_qualifications():
    """A qualification is something EFSA attached; unassessed means there is none."""
    with pytest.raises(ValidationError, match="never assessed"):
        QpsRecord(status="out_of_scope", qualifications=["should not harbour ..."])


def test_an_empty_qualification_list_is_a_fact_not_a_gap():
    """K. phaffii is listed with no qualification, and that is worth distinguishing."""
    rec = QpsRecord(
        status="listed", taxonomic_unit="Komagataella phaffii", source="2026-efsa-qps-list"
    )
    assert rec.qualifications == []


def test_the_shipped_kb_carries_a_verified_status_for_every_host():
    """Every host has one, and every claim-bearing one cites the register."""
    from engin_host.kb import default_kb

    for h in default_kb().hosts:
        assert h.qps is not None, f"{h.name} has no QPS record"
        if h.qps.status != "out_of_scope":
            assert h.qps.source == "2026-efsa-qps-list"
            assert h.qps.taxonomic_unit


def test_gras_is_gone_from_the_capability_list():
    """ADR 0010 retired it; a query weighting it should now be an error, not a score."""
    from engin_host.kb import CAPABILITIES

    assert "gras" not in CAPABILITIES
