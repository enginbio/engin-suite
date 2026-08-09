"""Landscape: the properties the rest of the package's claims depend on."""
from __future__ import annotations

import numpy as np
import pytest

from engin_protein import AdditiveBaseline, make_landscape
from engin_protein.evaluate import spearman


def test_fitness_is_in_unit_interval():
    ls = make_landscape(seed=0)
    vals = ls.true_fitness(ls.library(200, seed=1))
    assert vals.min() >= 0.0 and vals.max() <= 1.0


def test_fitness_is_deterministic():
    ls = make_landscape(seed=0)
    seq = ls.library(1, seed=3)[0].sequence
    assert ls.fitness(seq) == ls.fitness(seq)


def test_wrong_length_sequence_is_rejected():
    ls = make_landscape(length=8, seed=0)
    with pytest.raises(ValueError, match="length"):
        ls.fitness("AGS")


def test_epistasis_must_be_a_fraction():
    with pytest.raises(ValueError, match="epistasis"):
        make_landscape(epistasis=1.5)


def test_zero_epistasis_makes_an_additive_model_nearly_exact():
    # The negative control. At e=0 fitness IS additive, so a per-position ridge should
    # essentially solve it — and any method that can't is broken, not challenged.
    ls = make_landscape(epistasis=0.0, seed=0)
    train = ls.sample_campaign(60, seed=1).measured()
    lib = ls.library(300, seed=2)
    pred = AdditiveBaseline().fit(train).predict(lib)
    assert spearman(pred, ls.true_fitness(lib)) > 0.85


def test_epistasis_degrades_the_additive_model():
    # The premise of the low-N face: additivity stops being enough as epistasis rises.
    ls_lo = make_landscape(epistasis=0.0, seed=0)
    ls_hi = make_landscape(epistasis=0.9, seed=0)
    rhos = []
    for ls in (ls_lo, ls_hi):
        train = ls.sample_campaign(60, seed=1).measured()
        lib = ls.library(300, seed=2)
        rhos.append(spearman(AdditiveBaseline().fit(train).predict(lib), ls.true_fitness(lib)))
    assert rhos[0] > rhos[1] + 0.3


def test_confidence_is_not_a_transform_of_fitness():
    # If confidence were a monotone function of fitness it would be a perfect oracle
    # and every comparison against it would be meaningless.
    ls = make_landscape(epistasis=0.5, seed=0)
    lib = ls.library(300, seed=2)
    rho = spearman(ls.confidence_scores(lib), ls.true_fitness(lib))
    assert 0.0 < rho < 0.95


def test_measure_adds_noise_but_stays_in_range():
    ls = make_landscape(seed=0)
    lib = ls.library(50, seed=1)
    measured = ls.measure(lib, noise=0.05, seed=2)
    vals = np.array([v.fitness for v in measured])
    assert vals.min() >= 0.0 and vals.max() <= 1.0
    assert not np.allclose(vals, ls.true_fitness(lib))


def test_library_prefix_prevents_id_collisions():
    ls = make_landscape(seed=0)
    a = {v.variant_id for v in ls.library(10, seed=1, prefix="x")}
    b = {v.variant_id for v in ls.library(10, seed=1, prefix="y")}
    assert not (a & b)


def test_related_landscape_interpolates():
    ls = make_landscape(epistasis=0.5, seed=0)
    lib = ls.library(300, seed=2)
    truth = ls.true_fitness(lib)
    near = spearman(ls.related(similarity=0.95, seed=5).true_fitness(lib), truth)
    far = spearman(ls.related(similarity=0.0, seed=5).true_fitness(lib), truth)
    assert near > far
    assert near > 0.5           # a near-identical protein behaves near-identically
    assert abs(far) < 0.5       # an unrelated one carries little signal
