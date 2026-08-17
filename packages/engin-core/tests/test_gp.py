"""GP forecast quality + the calibration guarantee (the product's trust wedge)."""

from __future__ import annotations

import warnings

import numpy as np
import pytest
from scipy.stats import beta

from engin_core import (
    conformal_coverage_interval,
    fit_gp,
    mapie_split_interval,
    prob_at_least,
    simulate_unit,
    smallest_calibration_set,
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
    r2 = 1 - np.sum(resid**2) / np.sum((y[te] - y[te].mean()) ** 2)
    assert r2 > 0.85  # strong fit on this smooth mechanistic landscape


def test_split_conformal_is_calibrated():
    # The core guarantee: split-conformal 90% intervals cover ~90% out of sample,
    # and are not wildly overconfident like the naive Gaussian multiplier.
    covers_conf, covers_naive = [], []
    for seed in range(6):
        U, y = _dataset(seed=seed)
        tr, ca, te = slice(0, 70), slice(70, 100), slice(100, 120)
        gp = fit_gp(U[tr], y[tr], seed=seed)
        mc, sdc = gp.predict(U[ca], include_noise=True)
        # n=30 is genuinely in the noisy band #144 added the warning for, and the
        # loose assertion below is why. Silenced deliberately rather than left to
        # clutter every run of the suite.
        q90 = split_conformal_multiplier(y[ca], mc, sdc, level=0.90, warn_below_slack=None)
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
    assert abs(prob_at_least(mean, sd, 50.0)[0] - 0.5) < 1e-6  # target == mean


# --- Low-N honesty (#144). The regime a first fermentation campaign lands in. ---


def test_smallest_calibration_set_matches_the_conformal_index_condition():
    # The floor is not a rule of thumb: it is the smallest n for which the
    # ceil((n+1)*level)-th smallest score exists at all.
    for level in (0.80, 0.90, 0.95, 0.99):
        n_min = smallest_calibration_set(level)
        assert np.ceil((n_min + 1) * level) <= n_min
        assert np.ceil(n_min * level) > n_min - 1  # and n_min - 1 fails
    assert smallest_calibration_set(0.90) == 9
    assert smallest_calibration_set(0.95) == 19
    assert smallest_calibration_set(0.99) == 99


def test_below_the_floor_warns_instead_of_degrading_silently():
    # The failure this issue is about: with n < 9 at level 0.90 the conformal
    # index does not exist, the quantile clips to max(scores), and before #144
    # nothing said so.
    rng = np.random.default_rng(0)
    n = 8
    y, mean = rng.normal(size=n), np.zeros(n)
    sd = np.ones(n)
    with pytest.warns(UserWarning, match="below the floor of 9"):
        q = split_conformal_multiplier(y, mean, sd, level=0.90)
    assert q == pytest.approx(np.abs(y).max())  # the documented fallback


def test_small_but_valid_calibration_set_reports_its_coverage_spread():
    rng = np.random.default_rng(1)
    n = 20  # above the floor of 9, still far too few
    y, mean, sd = rng.normal(size=n), np.zeros(n), np.ones(n)
    with pytest.warns(UserWarning, match=r"true coverage lies in roughly"):
        split_conformal_multiplier(y, mean, sd, level=0.90)
    # ...and the escape hatch is honoured.
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        split_conformal_multiplier(y, mean, sd, level=0.90, warn_below_slack=None)


def test_large_calibration_set_does_not_warn():
    rng = np.random.default_rng(2)
    n = 500
    y, mean, sd = rng.normal(size=n), np.zeros(n), np.ones(n)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        split_conformal_multiplier(y, mean, sd, level=0.90)


def test_coverage_interval_is_the_beta_result():
    # Beta(n + 1 - l, l) with l = floor((n+1)*alpha) -- Vovk, as restated in
    # Angelopoulos & Bates section 3.2.
    n, level, delta = 100, 0.90, 0.10
    ell = int(np.floor((n + 1) * (1 - level)))
    dist = beta(n + 1 - ell, ell)
    lo, mean, hi = conformal_coverage_interval(n, level=level, delta=delta)
    assert lo == pytest.approx(dist.ppf(delta / 2))
    assert hi == pytest.approx(dist.ppf(1 - delta / 2))
    assert mean == pytest.approx(dist.mean())
    # The nominal level is the mean of the distribution, not its value.
    assert abs(mean - level) < 0.01


def test_coverage_interval_narrows_with_n_and_documents_the_headline_numbers():
    widths = []
    for n in (9, 20, 50, 100, 406, 1000):
        lo, _, hi = conformal_coverage_interval(n, level=0.90)
        assert lo < 0.90 < hi
        widths.append(hi - lo)
    assert widths == sorted(widths, reverse=True)  # monotonically tighter

    # The three figures quoted in the docstring and in the docs page.
    assert conformal_coverage_interval(9)[0] == pytest.approx(0.72, abs=0.01)
    lo50, _, hi50 = conformal_coverage_interval(50)
    assert (lo50, hi50) == (pytest.approx(0.83, abs=0.01), pytest.approx(0.96, abs=0.01))
    lo406, _, hi406 = conformal_coverage_interval(406)
    assert (lo406, hi406) == (pytest.approx(0.876, abs=0.001), pytest.approx(0.925, abs=0.001))


def test_coverage_interval_is_undefined_below_the_floor():
    lo, mean, hi = conformal_coverage_interval(5, level=0.90)
    assert all(np.isnan(v) for v in (lo, mean, hi))
