"""ARD sensitivity readout (#283).

``sensitivity.py`` was the only module in ``engin_core`` with a public export and
no test file, while the number it produces is printed in the demo memo -- the
artifact most likely to leave this repository as a screenshot.

**These tests pin the ordering and the invariants, not the share.** That split is
the finding #283 reported and it is worth stating in the tests themselves: on the
bundled simulator the top knob's share ranges roughly 30-56% across campaigns of
the same process, so a test asserting "feed_rate is 43%" would be pinning one draw
from a wide distribution. What survives across campaigns is *which knob leads*,
and what is guaranteed by construction is the normalisation.
"""

from __future__ import annotations

import numpy as np
import pytest

from engin_core import ard_importance, cross_validated_r2, fit_gp, simulate_unit


def _campaign(seed, n=40, d=5):
    rng = np.random.default_rng(seed)
    U = rng.random((n, d))
    y_true = simulate_unit(U)
    y_obs = np.maximum(y_true + rng.normal(0, 0.05 * y_true + 0.4), 0.0)
    return fit_gp(U, y_obs, seed=seed)


def test_importances_are_a_normalised_distribution():
    imp = ard_importance(_campaign(0))
    assert imp.shape == (5,)
    assert np.all(imp > 0.0)
    assert imp.sum() == pytest.approx(1.0)


def test_a_shorter_lengthscale_means_a_larger_share():
    """The whole readout is this one monotone relationship."""
    gp = _campaign(0)
    order_by_importance = np.argsort(-ard_importance(gp))
    order_by_lengthscale = np.argsort(gp.ell)  # shortest first
    assert list(order_by_importance) == list(order_by_lengthscale)


def test_the_top_knob_is_stable_across_campaigns_even_though_its_share_is_not():
    """#283's central measurement, as an assertion.

    Six independent campaigns from the same process. The leading knob agrees every
    time; its *share* does not, and the spread is wide enough that printing the
    integer without a caveat overstates what one campaign knows. The demo memo now
    prints rank first and labels the share as approximate.
    """
    tops, shares = [], []
    for seed in range(6):
        imp = ard_importance(_campaign(seed))
        tops.append(int(np.argmax(imp)))
        shares.append(float(imp.max()))

    assert len(set(tops)) == 1, f"leading knob disagreed across campaigns: {tops}"
    # The point of the test: the same quantity moves materially between campaigns.
    assert max(shares) - min(shares) > 0.05


def test_rescaling_all_lengthscales_leaves_the_readout_unchanged():
    """Relative sensitivity is scale-free, which is why it can be reported at all."""
    gp = _campaign(1)
    before = ard_importance(gp)
    gp.ell = gp.ell * 7.0
    assert ard_importance(gp) == pytest.approx(before)


def test_the_ranking_survives_the_other_common_convention():
    """Convention moves the digits, not the order (#283).

    Engin normalises ``1/l``; GPy's ``input_sensitivity`` uses ``variance / l**2``.
    Squaring is monotone and the variance is a common factor, so the two disagree
    on every printed percentage and agree on every rank. That is exactly why the
    memo may quote the ordering and must hedge the share.
    """
    gp = _campaign(2)
    ours = ard_importance(gp)
    gpy_style = (1.0 / gp.ell**2) / (1.0 / gp.ell**2).sum()

    assert list(np.argsort(-ours)) == list(np.argsort(-gpy_style))
    assert not np.allclose(ours, gpy_style)


# --------------------------------------------- the null regime the readout cannot see


def _null_campaign(seed, n=70, d=5):
    """A response drawn independently of the design: nothing to be sensitive to."""
    rng = np.random.default_rng(seed)
    U = rng.random((n, d))
    y = rng.normal(80.0, 12.0, n)
    return U, y


def test_the_share_does_not_reveal_the_null_regime():
    """#309: the top share is no smaller on noise than on signal -- it is larger.

    This is the reason `cross_validated_r2` exists. A user reading only the share
    cannot tell which regime produced it, so no threshold on the share would help.
    """
    null_tops = []
    for seed in range(1000, 1006):
        U, y = _null_campaign(seed)
        null_tops.append(float(ard_importance(fit_gp(U, y, seed=seed)).max()))

    sim_tops = [float(ard_importance(_campaign(s, n=70)).max()) for s in range(6)]

    assert min(null_tops) > 0.20, "uniform would be 20%; the null readout is not uniform"
    # The headline: noise does not produce a visibly flatter readout than signal.
    assert max(null_tops) >= min(sim_tops)


def test_the_leading_knob_is_not_stable_when_there_is_no_signal():
    """The condition #283's "ordering is the reliable part" was missing.

    `test_the_top_knob_is_stable_across_campaigns_even_though_its_share_is_not`
    asserts stability on the bundled simulator, where it genuinely holds. It does
    not hold in general, and the memo now says which case it is claiming.
    """
    tops = set()
    for seed in range(1000, 1008):
        U, y = _null_campaign(seed)
        tops.add(int(np.argmax(ard_importance(fit_gp(U, y, seed=seed)))))
    assert len(tops) > 1, f"expected the leading knob to wander on noise, got {tops}"


def test_cross_validated_r2_separates_the_two_regimes():
    """The evidence number does the job the share cannot.

    Thresholds are set well inside the measured gap rather than on it: over ten null
    seeds the score ran -0.435 to **+0.013**, and over six simulator seeds +0.986 to
    +0.997. Note the null side is not reliably *negative* -- one seed came out
    marginally positive -- so "below zero" is the wrong test and "nowhere near the
    signal case" is the right one.
    """
    nulls = [cross_validated_r2(*_null_campaign(s), seed=0) for s in range(1000, 1004)]
    assert max(nulls) < 0.2, f"null scores should sit near zero, got {nulls}"

    rng = np.random.default_rng(3)
    Us = rng.random((70, 5))
    ys = simulate_unit(Us) + rng.normal(0.0, 0.5, 70)
    signal = cross_validated_r2(Us, ys, seed=0)
    assert signal > 0.8
    assert signal - max(nulls) > 0.5, "the two regimes must be far apart, not just ordered"


def test_cross_validated_r2_validates_its_arguments():
    U, y = _null_campaign(1000, n=20)
    with pytest.raises(ValueError, match="folds must be in"):
        cross_validated_r2(U, y, folds=1)
    with pytest.raises(ValueError, match="rows but"):
        cross_validated_r2(U, y[:-1])


def test_an_interpolating_fit_warns_when_its_shares_are_read():
    """The free detector: specific, not sensitive, and never silent about that."""
    seeds = range(1000, 1020)
    fired = 0
    for seed in seeds:
        U, y = _null_campaign(seed, n=30)
        gp = fit_gp(U, y, seed=seed)
        if gp.interpolates_at_noise_floor():
            with pytest.warns(UserWarning, match="kernel floor"):
                ard_importance(gp)
            fired += 1
    assert fired > 0, "no null fit hit the noise floor; the detector cannot be exercised"

    # It must not fire on the bundled simulator, or it would be noise itself.
    for seed in range(4):
        assert not _campaign(seed, n=70).interpolates_at_noise_floor()
