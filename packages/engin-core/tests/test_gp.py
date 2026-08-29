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
    resampled_coverage_interval,
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

    # n=81, not 406 (#276). 406 is the batch count; the quickstart splits
    # 60/20/20, so the industrial run calibrates on int(0.8n) - int(0.6n) = 81.
    # This test's name promises it documents the headline numbers, and it was
    # pinning the wrong one -- which is why the error survived in five places.
    lo81, _, hi81 = conformal_coverage_interval(81)
    assert (lo81, hi81) == (pytest.approx(0.844, abs=0.001), pytest.approx(0.950, abs=0.001))


def test_the_industrial_split_really_does_give_81_calibration_points():
    """Pins the arithmetic the corrected headline number rests on (#276).

    The band above is only the right band if the split really yields 81. Both
    ``examples/quickstart_real_data.py`` and ``benchmarks/real_data_coverage.py``
    use an identical 60/20/20, and the dataset is 406 batches -- 405 at the 72h
    cutoff. Asserting the arithmetic rather than the prose is what stops the two
    drifting apart again.
    """
    for n in (406, 405):
        assert int(0.8 * n) - int(0.6 * n) == 81

    # And that 81 crosses the warning threshold the published 406 implied it cleared.
    lo, _, hi = conformal_coverage_interval(81)
    assert max(abs(lo - 0.90), abs(hi - 0.90)) > 0.05


def test_coverage_interval_is_undefined_below_the_floor():
    lo, mean, hi = conformal_coverage_interval(5, level=0.90)
    assert all(np.isnan(v) for v in (lo, mean, hi))


def test_no_uncalibrated_second_multiplier_is_exported():
    # #226. `conformal_multiplier_oof` was exported, recommended by `fit_gp`, called
    # by nothing and tested by nothing -- and used a plain interpolated quantile,
    # missing every guard #144 added to its sibling in the same file. It undercovered
    # where this project lives: 0.87 against a nominal 0.90 at n=20.
    #
    # Removed rather than repaired: pooling out-of-fold residuals against an all-data
    # refit is a jackknife-family construction with no finite-sample guarantee, so a
    # repaired version would need a docstring explaining why not to trust it.
    # This pins the removal so it is not reintroduced by reflex.
    import engin_core

    assert not hasattr(engin_core, "conformal_multiplier_oof")
    assert "conformal_multiplier_oof" not in engin_core.__all__
    from engin_core import gp as gp_module

    assert not hasattr(gp_module, "conformal_multiplier_oof")


def test_fit_gp_points_somewhere_real_when_there_is_no_calibration_split():
    # Deleting the only alternative and saying nothing would be its own small
    # dishonesty, so `fit_gp` names MAPIE's CV+ implementation. Assert the
    # destination exists rather than trusting the docstring -- naming a capability
    # a library does not have is exactly the #225 failure this pass also fixed.
    from engin_core import fit_gp

    doc = fit_gp.__doc__
    assert "CrossConformalRegressor" in doc
    from mapie.regression import CrossConformalRegressor  # noqa: F401


# ------------------------------------------------- the band a benchmark should print


def test_resampled_matches_the_analytic_case():
    """With one seed the simulation has a closed form, so check it against one.

    Coverage conditional on the calibration set is ``Beta(n+1-l, l)``; scored on a
    finite test set it becomes Beta-Binomial. The simulator must reproduce that, or
    nothing it says about the multi-seed case is trustworthy either.
    """
    from scipy.stats import beta as beta_dist
    from scipy.stats import binom

    n_cal, n_test, level = 81, 82, 0.90
    lo, _mean, hi = resampled_coverage_interval(
        406, n_cal, n_test, n_seeds=1, level=level, replicates=20_000, seed=1
    )

    ell = int(np.floor((n_cal + 1) * (1 - level) + 1e-9))
    rng = np.random.default_rng(7)
    c = beta_dist(n_cal + 1 - ell, ell).rvs(200_000, random_state=rng)
    draws = binom.rvs(n_test, c, random_state=rng) / n_test
    a_lo, a_hi = np.quantile(draws, [0.05, 0.95])

    assert lo == pytest.approx(a_lo, abs=0.005)
    assert hi == pytest.approx(a_hi, abs=0.005)


def test_averaging_seeds_narrows_the_band_and_the_beta_does_not_know():
    """The #306 defect, as a test: the Beta is the wrong reference for a seed mean.

    Averaging re-splits shrinks the calibration-draw spread, so a band computed
    from ``conformal_coverage_interval`` is far too wide for the statistic the
    benchmark actually publishes -- it accepted ~99% of it while claiming 90%.
    """
    one = resampled_coverage_interval(406, 81, 82, n_seeds=1, replicates=8_000, seed=2)
    five = resampled_coverage_interval(406, 81, 82, n_seeds=5, replicates=8_000, seed=2)
    beta_lo, _, beta_hi = conformal_coverage_interval(81, level=0.90)

    assert (five[2] - five[0]) < (one[2] - one[0]), "averaging seeds must narrow the band"
    # Measured ratio is ~0.67; asserting against 0.85 leaves room for Monte Carlo
    # noise rather than sitting on the boundary, which is how #293 happened.
    assert (five[2] - five[0]) < 0.85 * (beta_hi - beta_lo), (
        "the five-seed band must be markedly tighter than the Beta the benchmark used"
    )
    # and the Beta is not a stand-in for the single-split case either: it ignores
    # the finite test set, so it is too *narrow* there.
    assert (one[2] - one[0]) > (beta_hi - beta_lo)


def test_resampled_is_reproducible_and_validates_its_split():
    assert resampled_coverage_interval(
        406, 81, 82, n_seeds=3, replicates=2_000, seed=5
    ) == resampled_coverage_interval(406, 81, 82, n_seeds=3, replicates=2_000, seed=5)

    with pytest.raises(ValueError, match="exceeds n_total"):
        resampled_coverage_interval(100, 60, 60, replicates=100)
