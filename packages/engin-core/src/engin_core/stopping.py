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

__all__ = ["StopDecision", "ei_below_threshold", "headroom", "stop_decision"]


class StopDecision(BaseModel):
    """Whether to run another round, and how sure that is.

    ``p_worthwhile`` is the probability that **at least one** candidate beats the
    incumbent by more than ``epsilon``. The recommendation is to stop when that
    falls below ``delta``.
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

    **The combination across candidates assumes independence, and that is the
    conservative direction.** A GP posterior is positively correlated across
    nearby points, so the true maximum over candidates is stochastically smaller
    than the independent maximum with the same marginals. Treating them as
    independent therefore *overstates* the chance something is left to find, and
    the rule says "keep going" more often than a joint calculation would. For a
    stopping rule that is the error worth making: the cost is a wasted round, and
    the alternative is stopping while headroom remains.

    The exact calculation needs joint posterior samples, which
    :class:`~engin_core.gp.GP` does not expose -- it returns marginals only.
    """
    p = headroom(mean, sd, best, epsilon=epsilon, q=q, level=level)
    if p.size == 0:
        raise ValueError("no candidates: nothing to decide about")
    p_worthwhile = float(1.0 - np.prod(1.0 - p))
    stop = p_worthwhile < delta

    calibrated = q is not None
    if stop:
        rationale = (
            f"no candidate is likely to beat the incumbent by more than {epsilon:g}: "
            f"P = {p_worthwhile:.3f}, below the {delta:g} threshold"
        )
    else:
        rationale = (
            f"P = {p_worthwhile:.3f} that at least one of {p.size} candidates gains "
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
