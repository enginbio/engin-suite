"""Pin the ρ comparisons :mod:`engin_protein.model` publishes.

That docstring quotes measured Spearman ρ values to justify ridge over the GP, a
full-data mean over the bagged one, and ``interactions=False`` by default — and since
the interaction pair became a documented *switch condition*, a published design rule
rests on numbers nothing recomputed. Same failure shape as the docs execution cache
before CI checked it.

**These assert orderings, not values.** The published figures are single-seed, and
single seeds move by ~0.05-0.10 ρ here — the switch condition's high-epistasis half
reverses outright on 2 seeds in 20. So every assertion averages over campaign seeds
and leaves several standard errors of headroom, with the measured mean and sd quoted
beside each bound. Regenerate them with
``python benchmarks/docstring_claims.py --seeds 20``.

One published comparison is *not* asserted here: ridge over ``engin_core.fit_gp``. It
reproduces — 12/12 seeds at e=0, 11/12 at e=0.5 and e=0.8 — but a GP fit is ~15 s
(L-BFGS over a few hundred ARD lengthscales), so pinning it would cost nine minutes a
run to re-confirm the least contested claim in the docstring. It lives behind
``--gp`` in the benchmark instead.
"""

from __future__ import annotations

import numpy as np
import pytest

# The measurement lives in benchmarks/docstring_claims.py so the script a reader runs
# and the one CI gates on are the same code; conftest.py puts it on the path.
from docstring_claims import sweep

# Eight campaign seeds: enough that the seed average is stable (the gaps below sit
# 4-8 standard errors clear of their bounds), cheap enough to keep the suite fast.
SEEDS = range(1, 9)


@pytest.fixture(scope="module")
def flat():
    """e=0, where an additive model is *exactly* correct — the negative control."""
    return sweep(0.0, SEEDS)


@pytest.fixture(scope="module")
def rugged():
    """e=0.8, where most of the signal is pairwise-epistatic."""
    return sweep(0.8, SEEDS)


def _gap(results, better, worse):
    return results[better] - results[worse]


def test_additive_beats_pairwise_on_a_flat_landscape(flat):
    # Docstring: ρ 0.816 (pairwise) vs 0.942 (additive) at e=0.
    # Measured over 20 seeds: gap +0.136 ± 0.030, held on 20/20.
    gap = _gap(flat, "additive", "pairwise")
    assert gap.mean() > 0.05
    assert (gap > 0).sum() >= 6


def test_pairwise_beats_additive_on_a_rugged_landscape(rugged):
    # Docstring: ρ 0.313 (pairwise) vs 0.292 (additive) at e=0.8. The weaker half of
    # the switch condition: measured +0.066 ± 0.042 over 20 seeds, held on 18/20, so
    # the bound is loose and the per-seed count allows three reversals.
    gap = _gap(rugged, "pairwise", "additive")
    assert gap.mean() > 0.01
    assert (gap > 0).sum() >= 5


def test_the_interaction_switch_condition_changes_sign_with_epistasis(flat, rugged):
    """The rule the docstring sells: additive at low epistasis, pairwise at high.

    Asserted as one statement because it is one claim — a *switch*. Either half
    alone is a fact about a landscape, not a rule for choosing ``interactions``.
    """
    assert _gap(flat, "pairwise", "additive").mean() < 0
    assert _gap(rugged, "pairwise", "additive").mean() > 0


def test_full_data_fit_beats_the_bagged_mean_on_a_flat_landscape(flat):
    # Docstring: ρ 0.806 (bagged) vs 0.873 (full-data) at e=0 — the reason the class
    # takes its mean from the full fit and uses the ensemble only for spread.
    # Measured over 20 seeds: gap +0.052 ± 0.016, held on 20/20.
    gap = _gap(flat, "additive", "bagged_mean")
    assert gap.mean() > 0.01
    assert (gap > 0).sum() >= 6


def test_the_bagged_mean_is_only_a_loss_at_low_epistasis(rugged):
    """Scope the claim above to where it was measured.

    At e=0.8 the two are a wash (measured -0.011 ± 0.034 over 20 seeds, the full fit
    ahead on only 6/20), so the docstring qualifies the comparison with "at e=0". This
    pins that qualifier: if the gap ever became large *here*, the docstring would be
    understating the case and should be rewritten to say so.
    """
    assert abs(_gap(rugged, "additive", "bagged_mean").mean()) < 0.10


def test_holding_out_a_calibration_split_costs_ranking_accuracy(flat):
    # Docstring: ρ 0.873 (70% split) vs 0.975 (full campaign) at e=0 — "the honest
    # price of a calibrated interval". Measured: +0.123 ± 0.051, held on 20/20.
    gap = _gap(flat, "additive", "calibration_split")
    assert gap.mean() > 0.03
    assert (gap > 0).sum() >= 6


def test_the_rankings_are_in_the_published_neighbourhood(flat, rugged):
    """Generous bands on the absolute values, so orderings cannot hold degenerately.

    Wide on purpose: the published figures are single-seed and land at the optimistic
    end of the spread (the e=0.8 pair especially — 0.292/0.313 published against
    seed-averaged 0.140/0.206). These bounds catch a collapse or a sign flip, not
    drift within seed noise.
    """
    assert 0.75 < flat["additive"].mean() < 1.0
    assert 0.55 < flat["pairwise"].mean() < 1.0
    assert 0.02 < rugged["additive"].mean() < 0.45
    assert 0.05 < rugged["pairwise"].mean() < 0.50
    # No estimator produces a NaN or an out-of-range ρ on any seed -- a degenerate
    # fit can otherwise satisfy a comparison of two means without ranking anything.
    for results in (flat, rugged):
        for values in results.values():
            assert np.all(np.isfinite(values))
            assert np.all(np.abs(values) <= 1.0)
