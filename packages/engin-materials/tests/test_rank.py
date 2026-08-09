"""Ranker: beats the composition heuristic, calibrated, and *why* it beats it."""

from __future__ import annotations

import numpy as np
import pytest

from engin_materials import (
    PolymerRanker,
    best_of_k_regret,
    composition_scores,
    crosslink_densities,
    labels,
    make_dataset,
    spearman,
    true_property,
)


def _fit(weakest_link: float = 0.6, topology_weight: float = 0.25, n: int = 500, seed: int = 1):
    data = make_dataset(n, seed=seed, weakest_link=weakest_link, topology_weight=topology_weight)
    ranker = PolymerRanker().fit(data[:300]).calibrate(data[300:380])
    return ranker, data[380:]


def test_graph_model_outranks_the_composition_heuristic():
    ranker, test = _fit()
    truth = true_property(test)
    assert spearman(ranker.predict(test), truth) > spearman(composition_scores(test), truth)


def test_interval_is_calibrated():
    # The suite-wide requirement: coverage asserted, not quoted.
    ranker, test = _fit()
    truth = true_property(test)
    lo, hi = ranker.predict_interval(test)
    assert np.all(hi >= lo)
    cover = float(np.mean((truth >= lo) & (truth <= hi)))
    assert 0.85 <= cover <= 1.0


def test_the_advantage_comes_from_topology_not_min_pooling():
    # The finding that corrects this package's motivating story. With topology removed,
    # the graph model only ties the composition average, even where the property is
    # almost entirely weakest-link driven. Pinned as a test so it can't quietly become
    # folklore in the other direction.
    ranker, test = _fit(weakest_link=0.9, topology_weight=0.0)
    truth = true_property(test, weakest_link=0.9, topology_weight=0.0)
    graph = spearman(ranker.predict(test), truth)
    comp = spearman(composition_scores(test), truth)
    assert abs(graph - comp) < 0.1  # a tie, not a win

    ranker2, test2 = _fit(weakest_link=0.0, topology_weight=0.25)
    truth2 = true_property(test2, weakest_link=0.0, topology_weight=0.25)
    graph2 = spearman(ranker2.predict(test2), truth2)
    comp2 = spearman(composition_scores(test2), truth2)
    assert graph2 > comp2 + 0.05  # topology alone earns the win


def test_composition_heuristic_wins_when_it_is_correct():
    # The negative control. With no weakest-link term and no topology, the property IS
    # the composition average, and a model that beat it there would be evidence of a
    # leak rather than of skill.
    ranker, test = _fit(weakest_link=0.0, topology_weight=0.0)
    truth = true_property(test, weakest_link=0.0, topology_weight=0.0)
    assert spearman(composition_scores(test), truth) > spearman(ranker.predict(test), truth)


def test_composition_heuristic_is_blind_to_topology():
    # Establishes that the topology signal is real and invisible to the baseline.
    data = make_dataset(400, seed=2)
    truth = true_property(data)
    assert spearman(crosslink_densities(data), truth) > 0.3  # topology carries signal
    # ...and the composition average cannot see it: identical composition, different
    # crosslinking, identical heuristic score.
    from engin_materials import Polymer

    base = data[0]
    a = Polymer(polymer_id="a", units=base.units, crosslinks=[])
    b = Polymer(polymer_id="b", units=base.units, crosslinks=[(0, 4)])
    assert composition_scores([a])[0] == pytest.approx(composition_scores([b])[0])


def test_best_of_k_regret_beats_the_heuristic():
    # Averaged over many small candidate groups. Top-5-of-120 is trivially solved by
    # both rankers (regret 0.0 each), so a single large pool would let this pass
    # without measuring anything. Small groups are also the realistic decision: you
    # get a handful of formulation slots, not a hundred.
    ranker, test = _fit()
    rng = np.random.default_rng(0)
    model_r, comp_r = [], []
    for _ in range(40):
        idx = rng.choice(len(test), size=8, replace=False)
        group = [test[int(i)] for i in idx]
        truth = true_property(group)
        model_r.append(best_of_k_regret(ranker.predict(group), truth, k=1))
        comp_r.append(best_of_k_regret(composition_scores(group), truth, k=1))
    assert np.mean(model_r) < np.mean(comp_r)


def test_labels_requires_every_polymer_to_be_labeled():
    data = make_dataset(10, seed=1)
    from engin_materials import Polymer

    unlabeled = Polymer(polymer_id="u", units=data[0].units)
    with pytest.raises(ValueError, match="labeled"):
        labels([*data, unlabeled])


def test_interval_before_calibration_raises():
    data = make_dataset(60, seed=1)
    ranker = PolymerRanker().fit(data)
    with pytest.raises(RuntimeError, match="calibrate"):
        ranker.predict_interval(data[:5])
