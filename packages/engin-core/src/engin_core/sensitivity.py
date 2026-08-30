"""ARD sensitivity readout, and the evidence that says whether to believe it.

The GP's per-dimension inverse lengthscales double as a cheap global sensitivity
measure: a short lengthscale on knob *j* means titer changes fast along *j*, so
that knob matters. Normalized, these answer "which knobs actually move titer".

**They answer it whether or not the data contains an answer, which is why
:func:`cross_validated_r2` is here (#309).** Fitted to a response drawn
independently of the design, ``ard_importance`` still hands one of five knobs about
half the total, and which knob it names moves between campaigns. Measured over 20
seeds at ``n_train`` = 30/70/150:

============================  ==========  ==========  ==========
regime                        n=30        n=70        n=150
============================  ==========  ==========  ==========
top share, pure noise         55.5%       55.0%       41.1%
top share, bundled simulator  44.3%       48.0%       51.0%
modal top knob, pure noise    6/20        7/20        9/20
modal top knob, simulator     20/20       20/20       20/20
held-out R², pure noise       -0.25       -0.15       -0.08
held-out R², simulator        +0.98       +0.99       +1.00
============================  ==========  ==========  ==========

Read the first two rows together: **the share is not merely unreliable in the null
regime, it is larger there than in the signal regime**, so no threshold on the
share separates them. Uniform over five knobs would be 20%.

The third and fourth rows are why "ordering is the reliable part" (#283) needs a
condition attached. Ordering *is* stable with signal and unstable without -- but
distinguishing those two costs twenty campaigns, and a user has one.

**What does separate them, on a single campaign, is a cross-validated score.**
Hence :func:`cross_validated_r2`, which reuses ``fit_gp`` and needs no new
dependency (``D9``).

.. rubric:: A tempting alternative that does not work

Comparing the marginal likelihood of the fitted ARD kernel against a
``ConstantKernel + WhiteKernel`` null looks like the cheaper test and it is
actively wrong. On pure noise the median ΔLML is **+2.55 / +3.51 / +4.35** at
n=30/70/150, positive in 60 of 60 fits, and the margin *grows* with n: the LML
carries no penalty for the ARD kernel's extra hyperparameters, and this is not a
regular likelihood-ratio test because the parameters sit on a boundary, so no χ²
threshold rescues it. Shipping it would certify noise as signal, more confidently
the more null data a user collected. Recorded here because it is the first thing
the next person will reach for (measured and reported on #309).
"""

from __future__ import annotations

import warnings

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .gp import GP, fit_gp


def ard_importance(gp: GP, *, warn_on_interpolation: bool = True) -> NDArray[np.float64]:
    """Inverse lengthscale, normalized -> relative sensitivity per knob (sums to 1).

    **This number is always well-formed and is not always meaningful.** It describes
    the fitted surface, not the data: if the GP learned nothing, it reports the shape
    of what it learned from noise. Pair it with :func:`cross_validated_r2` on the same
    design before quoting it (#309).

    When ``gp`` sits on the interpolating optimum -- observation noise driven to the
    kernel floor -- a :class:`UserWarning` is raised, because the lengthscales are
    then fitted to noise by construction. That check is specific rather than
    sensitive: it never fired on the bundled simulator across 20 seeds and catches
    roughly half of the null-regime fits, so silence is not reassurance. Pass
    ``warn_on_interpolation=False`` when you have already checked the evidence.
    """
    if warn_on_interpolation and gp.interpolates_at_noise_floor():
        warnings.warn(
            "ard_importance: this GP drove observation noise to the kernel floor, so "
            "it interpolates its training data and the lengthscales are fitted partly "
            "to noise. The shares below describe that surface, not necessarily the "
            "process. Check cross_validated_r2(X, y) before quoting them (#309).",
            UserWarning,
            stacklevel=2,
        )
    inv = 1.0 / gp.ell
    return inv / inv.sum()


def cross_validated_r2(X: ArrayLike, y: ArrayLike, *, folds: int = 5, seed: int = 0) -> float:
    """K-fold cross-validated R² of ``fit_gp`` on this design -- the evidence number.

    Answers the question :func:`ard_importance` cannot: **is there anything here to
    be sensitive to?** A value at or below zero means the fitted GP predicts held-out
    titer no better than the training mean, and any importance readout from it is a
    description of noise.

    Measured at ``n``=70, this separates cleanly where the importance share does not:
    over ten null campaigns the score ran **-0.435 to +0.013**, over six simulator
    campaigns **+0.986 to +0.997**. Note the null side is *near* zero rather than
    reliably below it -- one seed came out marginally positive -- so treat "close to
    zero" as the warning sign, not "negative".

    There is no universal pass mark. This project's own tier-3 industrial data sits
    at R² 0.02-0.10 with honest intervals, which is *weak signal* rather than *no
    signal*, and the readout there is a hint rather than a ranking.

    Uses ``fit_gp`` itself, so the score describes the estimator that will be used
    rather than a stand-in, and adds no dependency (``D9``).
    """
    X = np.atleast_2d(np.asarray(X, float))
    y = np.asarray(y, float).ravel()
    n = len(y)
    if n != X.shape[0]:
        raise ValueError(f"X has {X.shape[0]} rows but y has {n} entries")
    if folds < 2 or folds > n:
        raise ValueError(f"folds must be in [2, len(y)={n}], got {folds}")

    order = np.random.default_rng(seed).permutation(n)
    predicted = np.empty(n)
    for k, test_idx in enumerate(np.array_split(order, folds)):
        train_idx = np.setdiff1d(order, test_idx, assume_unique=False)
        model = fit_gp(X[train_idx], y[train_idx], seed=seed + k)
        predicted[test_idx], _ = model.predict(X[test_idx], include_noise=True)

    ss_res = float(np.sum((y - predicted) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    if ss_tot == 0.0:
        return float("nan")  # a constant target has no variance to explain
    return 1.0 - ss_res / ss_tot
