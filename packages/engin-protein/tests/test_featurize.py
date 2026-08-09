"""Featurizers: shape, the light default, and the precomputed-embedding path."""

from __future__ import annotations

import numpy as np
import pytest

from engin_protein import OneHotPhysicochemical, PrecomputedFeaturizer
from engin_protein.schema import AMINO_ACIDS


def test_one_hot_shape_with_and_without_descriptors():
    seqs = ["AGSD", "KLVW"]
    n_aa = len(AMINO_ACIDS)
    assert OneHotPhysicochemical(use_descriptors=False)(seqs).shape == (2, 4 * n_aa)
    assert OneHotPhysicochemical(use_descriptors=True)(seqs).shape == (2, 4 * (n_aa + 5))


def test_one_hot_sets_exactly_one_identity_per_position():
    X = OneHotPhysicochemical(use_descriptors=False)(["AGSD"])
    assert X.sum() == pytest.approx(4.0)


def test_identical_sequences_featurize_identically():
    f = OneHotPhysicochemical()
    assert np.allclose(f(["AGSD"]), f(["AGSD"]))


def test_ragged_sequences_are_rejected():
    with pytest.raises(ValueError, match="share a length"):
        OneHotPhysicochemical()(["AGSD", "AGS"])


def test_empty_input_is_rejected():
    with pytest.raises(ValueError, match="empty"):
        OneHotPhysicochemical()([])


def test_precomputed_serves_embeddings():
    emb = {"AGSD": np.arange(8.0), "KLVW": np.ones(8)}
    X = PrecomputedFeaturizer(emb)(["KLVW", "AGSD"])
    assert X.shape == (2, 8)
    assert np.allclose(X[0], np.ones(8))


def test_precomputed_rejects_ragged_widths():
    with pytest.raises(ValueError, match="share a width"):
        PrecomputedFeaturizer({"A": np.zeros(3), "G": np.zeros(4)})


def test_precomputed_rejects_empty_mapping():
    with pytest.raises(ValueError, match="empty"):
        PrecomputedFeaturizer({})


def test_precomputed_raises_on_unseen_sequence():
    # Substituting a zero vector would be a plausible-looking input that quietly
    # poisons a low-N fit — far worse than a loud failure.
    with pytest.raises(KeyError, match="no precomputed embedding"):
        PrecomputedFeaturizer({"AGSD": np.zeros(4)})(["KLVW"])
