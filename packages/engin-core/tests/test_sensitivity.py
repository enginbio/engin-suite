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

from engin_core import ard_importance, fit_gp, simulate_unit


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
