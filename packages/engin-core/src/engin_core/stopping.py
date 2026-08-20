"""Stop or keep going: headroom left in a campaign, with its uncertainty.

Bayesian optimization is normally stopped when the budget runs out. That is a
decision about money rather than about the process, and it gives no answer to the
question a process lead actually asks -- *is there anything left to find?*

## What this implements, and whose idea it is

The **(ε, δ) framing** is Wilson's: stop once a candidate is within ε of the
optimum with probability at least 1 − δ.[^1] Nothing here invents a rule. Wilson
estimates it by Monte Carlo over the GP posterior; a 2026 follow-up derives
tighter regret-based criteria and reports higher success rates.[^2]

**Neither is adopted as-is, for two specific reasons.**

*The 2026 criterion is derived for GP-UCB, and Engin uses expected improvement.*
Its guarantee also rests on assumptions that are not checkable on a fermentation
run -- a bound on the objective's RKHS norm, a Lipschitz constant, and a known
noise variance. A guarantee whose preconditions nobody can verify on the data at
hand is a guarantee in name.

*Wilson's guarantee holds "under the model", and this project's own measurements
say the model is the problem.* `docs/methods/conformal-calibration.md` reports the
GP's epistemic-only interval covering about 0.55 at a nominal 0.90. A stopping
rule computed on that posterior inherits exactly that overconfidence, and it
inherits it in the dangerous direction: an overconfident posterior thinks there is
less left to find than there is, so it **stops early**.

## So the rule runs on the calibrated predictive, not the raw one

:func:`stop_decision` takes the split-conformal multiplier ``q`` from
:func:`engin_core.gp.split_conformal_multiplier` and widens the predictive scale
to match the interval that multiplier actually covers at. With ``q`` from a
calibration set, the probability below is computed against a distribution whose
width has been checked against held-out data rather than asserted by the kernel.

This is the same move the rest of the package makes, applied to a new question.
It does not make the guarantee distribution-free -- see *What this does not
establish* below.

[^1]: Wilson, *Stopping Bayesian Optimization with Probabilistic Regret Bounds*,
    arXiv:2402.16811 (2024).  ref: 2024-wilson-probabilistic-regret-bounds
[^2]: Wang, Wang & Wei, *Regret-Based (ε, δ)-optimal Stopping Criteria for
    Bayesian Optimization*, arXiv:2605.22561 (2026).
    ref: 2026-wang-regret-based-stopping
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray
from pydantic import BaseModel, Field
from scipy.stats import norm

from .gp import GP

__all__ = [
    "StopDecision",
    "ei_below_threshold",
    "headroom",
    "posterior_incumbent",
    "stop_decision",
]


class StopDecision(BaseModel):
    """Whether to run another round, and how sure that is.

    ``p_worthwhile`` is the probability that the **single most promising**
    candidate beats the incumbent by more than ``epsilon`` -- ``max_i p_i``, not a
    combination across candidates. The recommendation is to stop when it falls
    below ``delta``.

    It was ``1 - prod(1 - p_i)`` until 2026-08-20, which made the answer a function
    of how many rows the caller passed rather than of the process (#251). The name
    is unchanged because the quantity is still the probability the decision turns
    on; what changed is that it is now one.
    """

    stop: bool
    p_worthwhile: float = Field(..., ge=0.0, le=1.0)
    epsilon: float
    delta: float
    n_candidates: int
    calibrated: bool
    """False when ``q`` was left at its Gaussian default, which means the number
    above is the model's own opinion of itself. Reported rather than hidden: the
    uncalibrated case is the one that stops early."""

    rationale: str

    def __str__(self) -> str:  # pragma: no cover - convenience only
        verdict = "stop" if self.stop else "keep going"
        return f"{verdict}: P(gain > {self.epsilon:g}) = {self.p_worthwhile:.3f}"


def _calibrated_scale(sd: NDArray[np.float64], q: float, level: float) -> NDArray[np.float64]:
    """Predictive scale implied by a conformal interval of half-width ``q * sd``.

    ``split_conformal_multiplier`` returns ``q`` such that ``mean ± q*sd`` covers
    at ``level``. Reading that back as a normal scale means matching the widths:
    a normal covers ``level`` within ``z * s``, so ``s = q * sd / z``.

    At ``q = z`` -- conformal agreeing with the Gaussian -- this returns ``sd``
    unchanged, which is the identity the transformation ought to have.
    """
    z = float(norm.ppf(0.5 + level / 2.0))
    return np.asarray(sd, float) * (q / z)


def posterior_incumbent(gp: GP) -> float:
    """The incumbent to hand :func:`headroom` and :func:`stop_decision` (#250).

    The best *posterior mean* at the designs already run, rather than the best
    observed value. ``include_noise=False`` on purpose: the question is what the
    process achieves at that design, not what one assay happened to read.

    **Why not ``max(observed y)``.** The maximum of ``n`` noisy draws is an
    upward-biased estimate of the best achievable value -- Smith & Winkler's
    optimizer's curse -- and the bias is largest exactly where it hurts: one assay
    reading two or three sigma high becomes a permanent threshold nothing can beat,
    and the campaign is told to stop with headroom remaining.

    Measured on the bundled simulator over 12 seeds, with the calibrated rule and
    ``epsilon=2 g/L``: the observed maximum sat **above the true maximum of the
    response surface in 10 of 12 campaigns**, by a median of +2.4 g/L and as much as
    +9.9. In **3 of 12** the inflated incumbent stopped the campaign where this
    incumbent did not.  <!-- not-a-claim: measured on our own simulator -->

    This is the choice Gramacy & Lee promote and the one BayBE makes
    (``best_f`` from the posterior mean of the transformed targets). BoTorch
    documents its ``best_f`` as assuming *noiseless* observations, and ships a
    separate noisy acquisition for when they are not.

    # ref: 2006-smith-winkler-optimizers-curse
    """
    mean, _ = gp.predict(gp.X, include_noise=False)
    return float(np.max(mean))


def headroom(
    mean: ArrayLike,
    sd: ArrayLike,
    best: float,
    *,
    epsilon: float = 0.0,
    q: float | None = None,
    level: float = 0.90,
) -> NDArray[np.float64]:
    """Per-candidate ``P(f(x) > best + epsilon)`` under the calibrated predictive.

    ``q`` is the split-conformal multiplier; leave it ``None`` to use the raw GP
    posterior and accept its optimism.

    ```{warning}
    **``best`` must be a de-noised incumbent.** It enters as an absolute threshold
    on the objective, so any upward bias in it passes through undamped and this
    function reports less headroom than there is.

    ``max(observed y)`` is biased upward -- it is the maximum of noisy draws, the
    optimizer's curse -- and ``fit_gp`` fits a ``WhiteKernel``, so the model itself
    says the observations are noisy. On the bundled simulator it sat above the true
    maximum in 10 of 12 campaigns, by as much as **+9.9 g/L**, and in 3 of 12 that
    was enough to stop a campaign that a de-noised incumbent kept running (#250).
    Use :func:`posterior_incumbent`.  <!-- not-a-claim: measured on our own simulator -->

    This is *not* symmetric with the recommender. In ``recommend_batch`` the
    incumbent is a ranking offset and the ranking is robust to it; here it is the
    threshold the whole decision turns on.
    ```
    """
    mean = np.asarray(mean, float)
    scale = np.asarray(sd, float)
    if q is not None:
        scale = _calibrated_scale(scale, q, level)
    scale = np.maximum(scale, 1e-12)  # a noiseless point is a certainty, not a NaN
    return np.asarray(norm.sf(best + epsilon, loc=mean, scale=scale), float)


def stop_decision(
    mean: ArrayLike,
    sd: ArrayLike,
    best: float,
    *,
    epsilon: float,
    delta: float = 0.05,
    q: float | None = None,
    level: float = 0.90,
) -> StopDecision:
    """Recommend stopping when no candidate is likely to beat ``best`` by ``epsilon``.

    ``best`` must be a **de-noised** incumbent -- see :func:`posterior_incumbent`
    and the warning on :func:`headroom`. Passing ``max(observed y)`` is the
    documented trap, not the documented usage.

    **The combination across candidates is the maximum per-candidate probability,
    not a product over them.** Until 2026-08-20 this computed
    ``1 - prod(1 - p_i)``, defended in this docstring as conservative because a GP
    posterior is positively correlated and the independent maximum is
    stochastically larger. The direction of that argument was right and it was
    answering the wrong objection (#251).

    The problem was never the sign of the bias. It was that the bias was
    controlled by ``len(candidates)``, an argument with no statistical content.
    ``1 - prod(1-p) ~ 1 - exp(-sum p)``, so stopping required ``sum_i p_i`` below
    roughly ``delta`` -- at 4000 candidates and ``delta=0.05``, a mean
    per-candidate probability under about 1.25e-5. Measured on the bundled
    simulator, one pool sub-sampled and nothing else changed:

    ======  =============  =====
    ``n``   p_worthwhile   stop
    ======  =============  =====
    8       0.000000       True
    512     0.171560       False
    4000    0.946322       False
    ======  =============  =====

    The largest per-candidate probability over that same pool is **0.608** -- the
    honest answer to "is anything left to find" -- while the product reported
    0.946 and was still climbing with pool size.

    It was also inconsistent under refinement: ``P(max_i f(x_i) > c)`` converges to
    ``P(sup_X f > c)`` as the grid densifies, but the product diverges to 1,
    because neighbouring candidates have posterior correlation approaching 1 and
    were counted as independent draws. Doubling the grid halved the per-point
    probability the rule demanded.

    ``max_i p_i`` is what the plain-English question means, and it gives up no
    guarantee, because the product never carried one.

    **Be precise about what it is invariant to**, because "invariant to pool size"
    would be too strong. Duplicating candidates, or refining a grid over the same
    region, leaves it unchanged -- those are the changes with no statistical
    content. Adding genuinely *better* candidates still raises it, which is correct:
    that is new information about the design space. What it no longer does is climb
    toward 1 on candidate count alone. On the pool measured above it now reports
    0.608 -- equal to the best candidate's own probability, and bounded by it --
    where the product reported 0.946 and rising.

    A joint calculation over sample paths -- Wilson's actual construction, via
    Matheron's rule -- needs a joint predictive covariance that
    :class:`~engin_core.gp.GP` does not expose; that is a larger change and belongs
    with the regret-based work in #18.
    """
    p = headroom(mean, sd, best, epsilon=epsilon, q=q, level=level)
    if p.size == 0:
        raise ValueError("no candidates: nothing to decide about")
    p_worthwhile = float(np.max(p))
    stop = p_worthwhile < delta

    calibrated = q is not None
    if stop:
        rationale = (
            f"no candidate is likely to beat the incumbent by more than {epsilon:g}: "
            f"the best candidate's P = {p_worthwhile:.3f}, below the {delta:g} threshold"
        )
    else:
        rationale = (
            f"the best of {p.size} candidates has P = {p_worthwhile:.3f} of gaining "
            f"more than {epsilon:g}, at or above the {delta:g} threshold"
        )
    if not calibrated:
        rationale += (
            " -- computed on the raw GP posterior, which this project measures as "
            "overconfident, so treat it as an upper bound on certainty and expect "
            "it to stop early"
        )
    return StopDecision(
        stop=stop,
        p_worthwhile=p_worthwhile,
        epsilon=epsilon,
        delta=delta,
        n_candidates=int(p.size),
        calibrated=calibrated,
        rationale=rationale,
    )


def ei_below_threshold(ei: ArrayLike, threshold: float) -> bool:
    """The honest baseline: stop when the best expected improvement falls below a cut.

    This is what people actually do, and it is what the literature calls a
    heuristic offering "practical guidance but lacking theoretical
    guarantees".[^2] It is here to be reported against rather than to be used --
    the suite's rule is that every method ships next to the simpler thing it
    claims to beat.

    Its specific weakness is that the threshold has no units anyone can reason
    about: expected improvement is in the objective's units multiplied by a
    probability, so a cut that is sensible on one process is arbitrary on the
    next. ``epsilon`` in :func:`stop_decision` is in titer units and a process
    lead can state it.
    """
    return bool(np.max(np.asarray(ei, float)) < threshold)
