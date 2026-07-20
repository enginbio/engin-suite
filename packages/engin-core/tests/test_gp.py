"""GP forecast quality + the calibration guarantee (the product's trust wedge)."""
from __future__ import annotations

import numpy as np

from engin_core import (
    fit_gp,
    mapie_split_interval,
    prob_at_least,
    simulate_unit,
    split_conformal_multiplier,
)

GAUSS_90 = 1.645


def _dataset(seed=0, d=5, n=120):
    rng = np.random.default_rng(seed)
    U = rng.random((n, d))
    y_true = simulate_unit(U)
    y_obs = np.maximum(y_true + rng.normal(0, 0.05 * y_true + 0.4), 0.0)
    return U, y_obs


def test_forecast_is_accurate_on_held_out():
    U, y = _dataset(seed=0)
    tr, te = slice(0, 90), slice(90, 120)
    gp = fit_gp(U[tr], y[tr], seed=0)
    m, _ = gp.predict(U[te], include_noise=True)
    resid = m - y[te]
    r2 = 1 - np.sum(resid ** 2) / np.sum((y[te] - y[te].mean()) ** 2)
    assert r2 > 0.85          # strong fit on this smooth mechanistic landscape


def test_split_conformal_is_calibrated():
    # The core guarantee: split-conformal 90% intervals cover ~90% out of sample,
    # and are not wildly overconfident like the naive Gaussian multiplier.
    covers_conf, covers_naive = [], []
    for seed in range(6):
        U, y = _dataset(seed=seed)
        tr, ca, te = slice(0, 70), slice(70, 100), slice(100, 120)
        gp = fit_gp(U[tr], y[tr], seed=seed)
        mc, sdc = gp.predict(U[ca], include_noise=True)
        q90 = split_conformal_multiplier(y[ca], mc, sdc, level=0.90)
        assert np.isfinite(q90) and q90 > 0.0
        m, sd = gp.predict(U[te], include_noise=True)
        resid = np.abs(m - y[te])
        covers_conf.append(np.mean(resid <= q90 * sd))
        covers_naive.append(np.mean(resid <= GAUSS_90 * sd))
    mean_conf = float(np.mean(covers_conf))
    mean_naive = float(np.mean(covers_naive))
    # Honest: within a tolerance band of the 0.90 nominal (finite-sample slack).
    assert 0.80 <= mean_conf <= 1.0
    # And a real correction: conformal covers no worse than the overconfident naive.
    assert mean_conf >= mean_naive - 1e-9


def test_mapie_interval_is_calibrated_and_ordered():
    # The library-backed (MAPIE) split-conformal interval covers ~90% out of sample.
    covers = []
    for seed in range(4):
        U, y = _dataset(seed=seed)
        tr, ca, te = slice(0, 70), slice(70, 100), slice(100, 120)
        gp = fit_gp(U[tr], y[tr], seed=seed)
        lo, hi = mapie_split_interval(gp, U[ca], y[ca], U[te], level=0.90)
        assert np.all(hi >= lo)
        covers.append(np.mean((y[te] >= lo) & (y[te] <= hi)))
    assert 0.80 <= float(np.mean(covers)) <= 1.0


def test_prob_at_least_is_monotone_in_target():
    mean = np.array([50.0])
    sd = np.array([5.0])
    assert prob_at_least(mean, sd, 40.0)[0] > prob_at_least(mean, sd, 60.0)[0]
    assert 0.0 <= prob_at_least(mean, sd, 50.0)[0] <= 1.0
    assert abs(prob_at_least(mean, sd, 50.0)[0] - 0.5) < 1e-6   # target == mean
