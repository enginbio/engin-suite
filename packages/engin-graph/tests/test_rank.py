"""Ranker: beats its baseline, calibrated intervals, lower best-of-K regret."""

from __future__ import annotations

import numpy as np

from conftest import D_IN, make_dataset
from engin_graph import GraphRanker, best_of_k_regret, spearman


def _fit():
    objs, y = make_dataset(400, seed=1)
    ranker = GraphRanker(d_in=D_IN, lam=1.0, embed_seed=0)
    ranker.fit(objs[:250], y[:250])
    ranker.calibrate(objs[250:320], y[250:320], level=0.90)
    return ranker, objs[320:], y[320:]


def _node_count_baseline(objs) -> np.ndarray:
    """The dumb heuristic: fewer nodes assumed better. Blind to the worst node."""
    return -np.array([len(o.node_features()) for o in objs], float)


def test_graph_model_outranks_the_count_baseline():
    # The count baseline is unusually strong in this synthetic domain (~0.61): longer
    # chains have lower minima, so node count is a genuine proxy for the worst node,
    # not a strawman. The model's edge over it is real but modest (~0.72), so the
    # margin here is set where it won't flake rather than where it looks impressive.
    ranker, objs, y = _fit()
    rho_model = spearman(ranker.predict(objs), y)
    rho_count = spearman(_node_count_baseline(objs), y)
    assert rho_model > 0.65
    assert rho_model > rho_count + 0.05


def test_interval_is_calibrated():
    ranker, objs, y = _fit()
    lo, hi = ranker.predict_interval(objs)
    assert np.all(hi >= lo)
    cover = float(np.mean((y >= lo) & (y <= hi)))
    assert 0.80 <= cover <= 1.0  # ~90% nominal, finite-sample slack


def test_interval_before_calibration_raises():
    objs, y = make_dataset(40, seed=3)
    ranker = GraphRanker(d_in=D_IN).fit(objs, y)
    try:
        ranker.predict_interval(objs)
    except RuntimeError as e:
        assert "calibrate" in str(e)
    else:
        raise AssertionError("expected RuntimeError before calibrate()")


def test_calibrate_before_fit_raises():
    objs, y = make_dataset(20, seed=4)
    try:
        GraphRanker(d_in=D_IN).calibrate(objs, y)
    except RuntimeError as e:
        assert "fit" in str(e)
    else:
        raise AssertionError("expected RuntimeError before fit()")


def test_best_of_k_regret_beats_the_baseline():
    # The metric that matches how the tool is used: K slots, was the best in them?
    ranker, _, _ = _fit()
    rng = np.random.default_rng(7)
    model_reg, count_reg = [], []
    for _ in range(60):
        grp_objs, grp_y = make_dataset(6, seed=int(rng.integers(1_000, 100_000)))
        model_reg.append(best_of_k_regret(ranker.predict(grp_objs), grp_y, k=1))
        count_reg.append(best_of_k_regret(_node_count_baseline(grp_objs), grp_y, k=1))
    assert np.mean(model_reg) < np.mean(count_reg)


def test_wider_k_never_increases_regret():
    ranker, objs, y = _fit()
    scores = ranker.predict(objs[:20])
    r1 = best_of_k_regret(scores, y[:20], k=1)
    r5 = best_of_k_regret(scores, y[:20], k=5)
    assert r5 <= r1
