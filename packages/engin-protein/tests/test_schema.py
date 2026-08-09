"""Schema: validate loudly at the boundary, because these failures are otherwise silent."""

from __future__ import annotations

import pytest

from engin_protein import Campaign, ScoredDesign, Variant


def test_valid_variant():
    v = Variant(variant_id="v1", sequence="AGSD", fitness=0.5)
    assert v.length == 4


def test_rejects_non_canonical_residues():
    with pytest.raises(ValueError, match="non-canonical"):
        Variant(variant_id="v1", sequence="AGXD")


def test_rejects_empty_sequence():
    with pytest.raises(ValueError, match="non-empty"):
        Variant(variant_id="v1", sequence="")


def test_rejects_unnormalized_fitness():
    # A fitness on the raw assay scale is the likeliest real mistake, and it would
    # train a model that looks fine and ranks wrongly.
    with pytest.raises(ValueError, match="normalized"):
        Variant(variant_id="v1", sequence="AGSD", fitness=42.0)


def test_unmeasured_fitness_is_allowed():
    assert Variant(variant_id="v1", sequence="AGSD").fitness is None


def test_campaign_requires_uniform_length():
    with pytest.raises(ValueError, match="share a length"):
        Campaign(
            campaign_id="c",
            variants=[
                Variant(variant_id="a", sequence="AGSD", fitness=0.1),
                Variant(variant_id="b", sequence="AGS", fitness=0.2),
            ],
        )


def test_campaign_requires_unique_ids():
    # Caught a real bug: the planner pooled a seed campaign and a design library that
    # both numbered their variants from zero.
    with pytest.raises(ValueError, match="unique"):
        Campaign(
            campaign_id="c",
            variants=[
                Variant(variant_id="dup", sequence="AGSD", fitness=0.1),
                Variant(variant_id="dup", sequence="AGSA", fitness=0.2),
            ],
        )


def test_campaign_counts_and_accessors():
    c = Campaign(
        campaign_id="c",
        variants=[
            Variant(variant_id="a", sequence="AGSD", fitness=0.1),
            Variant(variant_id="b", sequence="AGSA"),
        ],
    )
    assert c.length == 4
    assert c.n_measured == 1
    assert len(c.measured()) == 1
    with pytest.raises(ValueError, match="unmeasured"):
        c.fitness_array()


def test_scored_design_rejects_inverted_interval():
    with pytest.raises(ValueError, match="exceeds"):
        ScoredDesign(variant_id="a", sequence="AGSD", predicted=0.5, lower=0.9, upper=0.1)


def test_scored_design_interval_width():
    s = ScoredDesign(variant_id="a", sequence="AGSD", predicted=0.5, lower=0.4, upper=0.7)
    assert s.interval_width == pytest.approx(0.3)


def test_scored_design_rejects_bad_probability():
    with pytest.raises(ValueError, match="prob_above_threshold"):
        ScoredDesign(
            variant_id="a",
            sequence="AGSD",
            predicted=0.5,
            lower=0.4,
            upper=0.6,
            prob_above_threshold=1.4,
        )
