"""Schema: the validation that keeps a malformed formulation out of a fit."""

from __future__ import annotations

import numpy as np
import pytest

from engin_materials import MONOMER_FEATURES, Monomer, Polymer


def _unit(v: float = 0.5) -> Monomer:
    return Monomer(features=dict.fromkeys(MONOMER_FEATURES, v))


def test_monomer_requires_the_exact_feature_set():
    with pytest.raises(ValueError, match="must be exactly"):
        Monomer(features={"m_stiffness": 0.5})


def test_monomer_rejects_out_of_range_features():
    with pytest.raises(ValueError, match=r"not in \[0,1\]"):
        Monomer(features={**dict.fromkeys(MONOMER_FEATURES, 0.5), "m_stiffness": 1.4})


def test_monomer_vector_follows_declared_order():
    m = Monomer(features={**dict.fromkeys(MONOMER_FEATURES, 0.1), "m_hydrolytic": 0.9})
    assert m.vector()[MONOMER_FEATURES.index("m_hydrolytic")] == pytest.approx(0.9)


def test_polymer_requires_at_least_two_units():
    with pytest.raises(ValueError):
        Polymer(polymer_id="p", units=[_unit()])


def test_polymer_rejects_out_of_range_crosslink():
    with pytest.raises(ValueError, match="out of range"):
        Polymer(polymer_id="p", units=[_unit() for _ in range(4)], crosslinks=[(0, 9)])


def test_polymer_rejects_adjacent_crosslink():
    # The backbone bond is already there; a crosslink between neighbours is either a
    # duplicate edge or a modelling mistake, and silently accepting it would make
    # crosslink_density meaningless.
    with pytest.raises(ValueError, match="adjacent"):
        Polymer(polymer_id="p", units=[_unit() for _ in range(4)], crosslinks=[(1, 2)])


def test_polymer_rejects_self_crosslink():
    with pytest.raises(ValueError, match="adjacent"):
        Polymer(polymer_id="p", units=[_unit() for _ in range(4)], crosslinks=[(2, 2)])


def test_polymer_rejects_unnormalized_property():
    with pytest.raises(ValueError, match=r"\[0,1\]"):
        Polymer(polymer_id="p", units=[_unit(), _unit()], property_value=3.0)


def test_graph_includes_backbone_and_crosslinks():
    p = Polymer(polymer_id="p", units=[_unit() for _ in range(6)], crosslinks=[(0, 4)])
    g = p.graph()
    assert g.number_of_nodes() == 6
    assert g.number_of_edges() == 5 + 1  # 5 backbone bonds + 1 crosslink
    assert g.has_edge(0, 4)


def test_node_features_align_with_graph_nodes():
    # engin_graph's structural featurizer relies on this alignment.
    p = Polymer(polymer_id="p", units=[_unit(0.2), _unit(0.4), _unit(0.6)])
    X = p.node_features()
    assert X.shape == (3, len(MONOMER_FEATURES))
    assert np.allclose(X[1], 0.4)


def test_crosslink_density():
    p = Polymer(polymer_id="p", units=[_unit() for _ in range(10)], crosslinks=[(0, 5), (2, 8)])
    assert p.crosslink_density == pytest.approx(0.2)


def test_polymer_satisfies_graphlike():
    from engin_graph import GraphLike

    assert isinstance(Polymer(polymer_id="p", units=[_unit(), _unit()]), GraphLike)
