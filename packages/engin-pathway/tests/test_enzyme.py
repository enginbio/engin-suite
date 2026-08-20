"""``g_enzyme`` from UniProt: the transform offline, the adapter against the API."""

from __future__ import annotations

import pytest

from engin_pathway.enzyme import (
    S_REFERENCE_UM,
    EnzymeUnavailable,
    MichaelisRecord,
    g_enzyme_affinity,
    g_enzyme_for_uniprot,
    michaelis_constants,
)

# ------------------------------------------------------------------ transform


def test_km_equal_to_reference_scores_exactly_neutral():
    """The property that makes the number mean something rather than be tuned."""
    assert g_enzyme_affinity(S_REFERENCE_UM) == pytest.approx(0.5)


def test_transform_is_monotone_decreasing_and_bounded():
    values = [g_enzyme_affinity(km) for km in (0.1, 1, 10, 100, 1_000, 10_000, 100_000)]
    assert values == sorted(values, reverse=True)
    assert all(0.0 < v < 1.0 for v in values)


def test_transform_does_not_saturate_at_either_end():
    """Bisected rather than eyeballed, because #206 documented a saturation point
    that was wrong by fifty kJ/mol -- read off a rounded print rather than measured.

    The saturation fraction is asymptotic, so there is no finite K_M at which it
    clips. What matters is that extreme inputs stay strictly inside (0, 1) at
    double precision, so ordering survives.
    """
    assert 0.0 < g_enzyme_affinity(1e12) < 1e-6
    assert 1.0 - 1e-9 < g_enzyme_affinity(1e-9) < 1.0


@pytest.mark.parametrize("bad", [0.0, -1.0, -1e-9])
def test_non_positive_km_is_rejected_not_clamped(bad):
    """Clamping would score a corrupt record as the best possible enzyme."""
    with pytest.raises(ValueError, match="must be positive"):
        g_enzyme_affinity(bad)


def test_reference_concentration_is_a_parameter():
    """A reviewer must be able to move the modelling choice."""
    assert g_enzyme_affinity(100.0, s_reference_um=100.0) == pytest.approx(0.5)
    assert g_enzyme_affinity(100.0, s_reference_um=10.0) == pytest.approx(10 / 110)


# ------------------------------------------------------------------ selection


def test_worst_affinity_wins_when_an_entry_has_several(monkeypatch):
    """The weakest binding step is the one most likely to limit the reaction, and
    taking the best-looking number would flatter every multi-substrate enzyme."""
    records = [
        MichaelisRecord("X", 10.0, "good"),
        MichaelisRecord("X", 5_000.0, "bad"),
    ]
    monkeypatch.setattr("engin_pathway.enzyme.michaelis_constants", lambda *a, **k: records)
    g, rec = g_enzyme_for_uniprot("X")
    assert rec.substrate == "bad"
    assert g == pytest.approx(g_enzyme_affinity(5_000.0))


def test_substrate_selects_a_specific_binding_event(monkeypatch):
    records = [MichaelisRecord("X", 10.0, "good"), MichaelisRecord("X", 5_000.0, "bad")]
    monkeypatch.setattr("engin_pathway.enzyme.michaelis_constants", lambda *a, **k: records)
    g, rec = g_enzyme_for_uniprot("X", substrate="good")
    assert rec.substrate == "good"
    assert g == pytest.approx(g_enzyme_affinity(10.0))


def test_missing_kinetics_raises_rather_than_defaulting(monkeypatch):
    """Roughly 70% of enzymes land here, so the common path must be loud."""
    monkeypatch.setattr("engin_pathway.enzyme.michaelis_constants", lambda *a, **k: [])
    with pytest.raises(EnzymeUnavailable, match="no K_M"):
        g_enzyme_for_uniprot("X")


# ------------------------------------------------------------------ network


@pytest.mark.network
def test_uniprot_entry_with_kinetics_resolves():
    g, rec = g_enzyme_for_uniprot("P00350")
    assert 0.0 < g < 1.0
    assert rec.km_um > 0


@pytest.mark.network
def test_uniprot_entry_without_kinetics_says_so():
    with pytest.raises(EnzymeUnavailable):
        g_enzyme_for_uniprot("P0A6F5")


@pytest.mark.network
def test_units_other_than_micromolar_are_skipped_not_converted():
    """A silent unit conversion is how affinity goes wrong by three orders."""
    for rec in michaelis_constants("P00350"):
        assert rec.km_um > 0
