"""Ranker: beats step-count, calibrated intervals, lower best-route regret."""
from __future__ import annotations

import numpy as np

from engin_pathway import (
    PathwayRanker,
    labels,
    make_dataset,
    sample_route,
    spearman,
    step_counts,
)


def _fit():
    data = make_dataset(500, seed=1)
    ranker = PathwayRanker(lam=1.0, embed_seed=0).fit(data[:320])
    ranker.calibrate(data[320:410], level=0.90)
    return ranker, data[410:]


def test_graph_model_outranks_step_count():
    ranker, test = _fit()
    y = labels(test)
    rho_model = spearman(ranker.predict(test), y)
    rho_steps = spearman(-step_counts(test), y)           # fewer steps = "better"
    assert rho_model > 0.7                                # strong structural ranker
    assert rho_model > rho_steps + 0.1                    # clearly beats step-count


def test_interval_is_calibrated():
    ranker, test = _fit()
    y = labels(test)
    lo, hi = ranker.predict_interval(test)
    assert np.all(hi >= lo)
    cover = float(np.mean((y >= lo) & (y <= hi)))
    assert 0.80 <= cover <= 1.0                           # ~90% nominal, finite-sample slack


def test_best_route_selection_beats_step_count():
    # Pick the best of K alternatives across many groups; the model's picks should
    # have higher true manufacturability (lower regret) than the step-count pick.
    ranker, _ = _fit()
    rng = np.random.default_rng(7)
    K, G = 6, 60
    model_reg, step_reg = [], []
    for gi in range(G):
        grp = [sample_route(rng, f"g{gi}_{k}") for k in range(K)]
        yt = labels(grp)
        model_pick = yt[int(np.argmax(ranker.predict(grp)))]
        step_pick = yt[int(np.argmin(step_counts(grp)))]
        model_reg.append(yt.max() - model_pick)
        step_reg.append(yt.max() - step_pick)
    assert np.mean(model_reg) < np.mean(step_reg)         # lower regret vs oracle
