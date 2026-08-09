"""Generator: the properties the ranking claims rest on."""

from __future__ import annotations

import numpy as np
import pytest

from engin_materials import (
    MONOMER_FEATURES,
    Monomer,
    Polymer,
    PropertyModel,
    make_dataset,
    sample_polymer,
    true_property,
)


def test_property_values_are_in_range():
    data = make_dataset(200, seed=1)
    vals = true_property(data)
    assert vals.min() >= 0.0 and vals.max() <= 1.0


def test_dataset_is_labeled_and_deterministic():
    a = make_dataset(50, seed=3)
    b = make_dataset(50, seed=3)
    assert all(p.property_value is not None for p in a)
    assert np.allclose([p.property_value for p in a], [p.property_value for p in b])


def test_weakest_link_must_be_a_fraction():
    with pytest.raises(ValueError, match="weakest_link"):
        PropertyModel(weakest_link=1.5)


def test_topology_weight_must_be_a_fraction():
    with pytest.raises(ValueError, match="topology_weight"):
        PropertyModel(topology_weight=-0.1)


def test_a_single_bad_unit_drags_the_property_down():
    # The weakest-link premise, checked directly on the generator rather than inferred
    # from a model's behaviour.
    good = [Monomer(features=dict.fromkeys(MONOMER_FEATURES, 0.9)) for _ in range(10)]
    healthy = Polymer(polymer_id="h", units=good)
    damaged = Polymer(
        polymer_id="d",
        units=[*good[:5], Monomer(features=dict.fromkeys(MONOMER_FEATURES, 0.05)), *good[6:]],
    )
    model = PropertyModel(weakest_link=0.9, topology_weight=0.0)
    assert model.value(damaged) < model.value(healthy) - 0.2


def test_weakest_link_zero_makes_the_property_a_pure_average():
    units = [Monomer(features=dict.fromkeys(MONOMER_FEATURES, v)) for v in (0.1, 0.5, 0.9, 0.5)]
    p = Polymer(polymer_id="p", units=units)
    model = PropertyModel(weakest_link=0.0, topology_weight=0.0)
    assert model.value(p) == pytest.approx(np.mean([0.1, 0.5, 0.9, 0.5]), abs=1e-9)


def test_crosslinking_helps_then_embrittles():
    # A non-monotone topology response — over-crosslinking is worse than optimal, which
    # is why a linear "more crosslinks is better" heuristic would also be wrong.
    units = [Monomer(features=dict.fromkeys(MONOMER_FEATURES, 0.5)) for _ in range(12)]
    model = PropertyModel(weakest_link=0.0, topology_weight=1.0)
    none = model.value(Polymer(polymer_id="a", units=units))
    some = model.value(
        Polymer(polymer_id="b", units=units, crosslinks=[(0, 5), (2, 7), (4, 9), (1, 8)])
    )
    many = model.value(
        Polymer(
            polymer_id="c",
            units=units,
            crosslinks=[(i, i + 2) for i in range(10)],
        )
    )
    assert some > none
    assert some > many


def test_sampled_polymers_are_valid_and_varied():
    rng = np.random.default_rng(0)
    ps = [sample_polymer(rng, f"p{i}") for i in range(40)]
    assert len({p.n_units for p in ps}) > 1
    assert any(p.crosslinks for p in ps)
    for p in ps:
        for i, j in p.crosslinks:
            assert abs(i - j) > 1


def test_prefix_avoids_id_collisions():
    a = {p.polymer_id for p in make_dataset(10, seed=1, prefix="x")}
    b = {p.polymer_id for p in make_dataset(10, seed=1, prefix="y")}
    assert not (a & b)
