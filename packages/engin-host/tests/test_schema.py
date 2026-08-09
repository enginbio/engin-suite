"""Schema validation: the KB fails loudly on malformed data."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from engin_host import Host, HostQuery, KnowledgeBase, default_kb


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
