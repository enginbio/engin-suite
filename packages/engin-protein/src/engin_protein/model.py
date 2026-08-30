"""The shared core all three faces sit on: featurize → bagged ridge → conformal interval.

**Why not the GP.** The plan for this package specified ``engin_core``'s GP head. It
was measured and rejected. ``fit_gp`` builds an ARD-RBF kernel initialized at
``length_scale=0.3`` over a unit cube — correct for six continuous fermentation knobs,
wrong for a few hundred sparse binary sequence features, where typical pairwise
distances are ~10x the length scale and every point looks infinitely far from every
other. Predictions collapse toward the mean. Measured on the synthetic landscape
(Spearman ρ against truth, 60-variant campaign):

    epistasis   additive ridge   GP (best config)
    0.0         0.942            0.423
    0.5         0.508            0.100
    0.8         0.292            0.104

**Read that table as a kernel mismatch, not an architecture verdict.** It says this
GP configuration is wrong for these features; it does not say Gaussian processes lose
to ridge on protein fitness. A GP with a sequence-appropriate kernel is a different
experiment, and this project has not run it.

**The ordering holds; the margins in that table do not.** Re-measured over 12 campaign
seeds with plain ``fit_gp``, ridge leads by ρ 0.755 at e=0 (12/12 seeds), 0.246 at
e=0.5 and 0.096 at e=0.8 (11/12 each) — so the bottom row is a ~0.1 lead against a
0.09 spread, not the 3x it reads as. Note also that "best config" above is not
recorded anywhere and so cannot be regenerated: the benchmark runs ``fit_gp`` as
shipped, which scores *below* that column. Treat the GP column as an anecdote and the
ordering as the claim.

So the estimator here is **ridge with a bagged ensemble for spread** — a defensible
choice, and the honest case for it is narrower than the one this docstring used to
make.

**Corrected 2026-08-29 (#302): the sentence quoted here was not in the paper.** It
read: *"a simple baseline approach we introduce is competitive with and often
outperforms more sophisticated methods."* The abstract of Hsu et al. (2022) says:
*"we propose a simple **combination** approach that is competitive with, and **on
average** outperforms more sophisticated methods. Our approach uses ridge regression
on site-specific amino acid features **combined with one probability density feature
from modeling the evolutionary data**."* Dropping "combination" is what turned a
sentence about ridge-plus-an-evolutionary-prior into an endorsement of the plain ridge
that ships here. Verified against the publisher record via Europe PMC.

**What Hsu actually supports, stated at the right strength.** The paper does name
plain one-hot regression as a neglected baseline: *"even a simple linear regression
using one-hot amino acid encoding performed quite well. This baseline has sometimes
been neglected in comparisons of vastly more complicated methods."* That is about the
un-augmented model — the augmented approach is introduced two sentences earlier as
their own *new* baseline, and a new baseline cannot be one that has "sometimes been
neglected".

**But the regime is wrong for us, and that is the part that bites.** Both endorsements
are scoped to larger data: "in the relatively larger data settings" and "among the top
performers in the **80-20 split** setting". Across their low-N sweep the finding
inverts — *"No matter which density model we augmented, the augmented version of the
model always improved the performance, regardless of the training data set size."* A
60-variant campaign sits in that sweep, not in the 80-20 setting.

**So Hsu supports the estimator class and not this configuration of it.** What would
answer the paper on its own terms is an evolutionary density feature alongside the
one-hot block, which this package does not ship and which is a dependency decision
rather than a citation fix — tracked on #302. Until then the honest claim is that
ridge on one-hot features is a real baseline this literature takes seriously, and that
the strongest evidence at *this* sample size points at the augmented variant.

"low-N" in this literature means tens of assayed variants — Biswas et al. (2021) build
a usable landscape from as few as 24 — which puts a 60-variant campaign squarely
inside it.

# implements D9; ref: 2022-hsu-protein-fitness-baselines
# ref: 2021-biswas-low-n

**The switch condition is epistasis, not sample size.** Searching the low-N literature
for a crossover N above which the more expressive model starts winning does not turn
one up: the regime statement is qualitative, and the boundary depends on how much of
the signal is epistatic relative to the labelled budget, not on N alone. What *is*
measurable here is the epistasis crossover in the interaction-feature numbers below —
additive wins at e=0, pairwise from about e=0.4 up. Use that to decide, and treat the
absence of a clean N* as a documented finding rather than an unasked question.

This is not a departure from the "reuse
the engine" rule: the engine's actual shared asset is its *uncertainty vocabulary* —
``split_conformal_multiplier``, ``prob_at_least``, ``expected_improvement`` — and all
three are estimator-agnostic. All three are used here unchanged. What changed is the
thing underneath them, which is a domain choice.

The mean comes from a fit on **all** the training data; the bootstrap ensemble supplies
only the epistemic ``sd`` that EI and conformal calibration need. Taking the mean from
the ensemble instead costs real ranking accuracy (ρ 0.806 vs 0.873 at e=0) for nothing,
since a full-data fit is right there.

A remaining gap to a plain additive ridge (ρ 0.873 vs 0.975 at e=0) is **not** a model
defect: the faces hold out a calibration split, so they train on ~70% of the campaign.
That is the honest price of a calibrated interval, and it should be quoted as such
rather than tuned away.

**On interaction features.** Pairwise one-hot expansion is available via
``interactions=True`` and is *off by default*, because it did not reliably beat the
additive model at these sample sizes — it loses meaningfully at low epistasis
(ρ 0.816 vs 0.942 at e=0) and wins at high (ρ 0.313 vs 0.292 at e=0.8). **That pair is
the switch condition referred to above**: it is the one crossover this package can
actually document, and it is in epistasis rather than N.

**The crossover is near e≈0.4, not at the top of the range.** A pair of endpoints says
a switch exists without saying where it sits. Over 20 campaign seeds the additive model
leads by ρ 0.094 at e=0.2 and 0.037 at e=0.3, is level at e=0.4 (8 seeds of 20), and
trails by 0.044 at e=0.5. So turn interactions on above roughly e=0.4 — this said "wins
only at high epistasis" until it was measured, which gives away the middle of the range.

Additive models being hard to beat in low-N protein work is a well-reported result
(Hsu et al. 2022), not a surprise.

**Every ρ quoted above is a single seed, and lands at the optimistic end.** Campaign
seed changes them by ~0.05-0.10, and more at high epistasis: the e=0.8 pair reads
0.292/0.313 here against a 20-seed mean of 0.140/0.206. Read each as "roughly this"
and the *orderings* as the claim. Regenerate them with
``python benchmarks/docstring_claims.py --seeds 20``; ``tests/test_docstring_claims.py``
asserts the orderings on every run, so these numbers can no longer drift unnoticed.
"""

from __future__ import annotations

import itertools
import warnings

import numpy as np
from engin_core import (
    highest_attainable_level,
    prob_at_least,
    smallest_calibration_set,
    split_conformal_multiplier,
)
from numpy.typing import NDArray
from sklearn.linear_model import Ridge
from sklearn.utils import resample

from .featurize import Featurizer, OneHotPhysicochemical
from .schema import Campaign, ScoredDesign, Variant

DEFAULT_N_ESTIMATORS = 24
DEFAULT_ALPHA = 1.0


def level_for_split(n_cal: int, level: float, *, context: str) -> float:
    """The requested ``level``, or the highest one ``n_cal`` can support (#197).

    The faces in ``engin_protein.lown`` and :mod:`engin_protein.evaluate` choose
    their own calibration split from ``cal_fraction``, so a user who asks for a 90%
    interval on a 24-variant campaign never chose the ``n_cal = 7`` that cannot
    deliver it. Raising there would make the low-N face unusable in the low-N
    regime, which is the regime it exists for.

    So the level is **downgraded to what the split supports, loudly**, and the
    achieved value is recorded on the model as
    :attr:`CalibratedFitnessModel.level`. The user asked for 0.90 and gets 0.875 --
    correctly labelled, which is the only part that was ever non-negotiable.

    :meth:`CalibratedFitnessModel.calibrate` still *raises* on the same condition,
    and the asymmetry is deliberate: there the caller named the level explicitly
    against a calibration set they supplied, so there is nothing to adapt on their
    behalf.
    """
    ceiling = highest_attainable_level(n_cal)
    if level <= ceiling:
        return float(level)
    warnings.warn(
        f"{context}: a calibration split of {n_cal} cannot support a "
        f"{level:.0%} interval -- the ceiling is n/(n+1) = {ceiling:.4f}. "
        f"Calibrating at {ceiling:.4f} instead and recording it as `model.level`. "
        f"For {level:.0%}, assay more variants or raise `cal_fraction` so the "
        f"split reaches {smallest_calibration_set(level)}.",
        UserWarning,
        stacklevel=3,
    )
    return float(ceiling)


class CalibratedFitnessModel:
    """Bagged ridge over featurized sequences, with a split-conformal interval.

    Not a face in its own right — ``evaluate``, ``lown``, and ``planner`` each wrap
    it. Kept separate so there is exactly one place where the protein domain meets
    ``engin_core``.
    """

    def __init__(
        self,
        featurizer: Featurizer | None = None,
        alpha: float = DEFAULT_ALPHA,
        n_estimators: int = DEFAULT_N_ESTIMATORS,
        interactions: bool = False,
        seed: int = 0,
    ) -> None:
        self.featurizer: Featurizer = featurizer or OneHotPhysicochemical(use_descriptors=False)
        self.alpha = alpha
        self.n_estimators = n_estimators
        self.interactions = interactions
        self.seed = seed
        self._models: list[Ridge] = []
        self._full: Ridge | None = None
        self._length: int | None = None
        self._width: int | None = None
        self.q: float | None = None
        self.level: float | None = None
        """Coverage level the multiplier was calibrated at. Set by :meth:`calibrate`."""
        self.n_calibration: int | None = None
        """Calibration-set size behind ``q``. Kept so the interval's provenance
        travels with the model rather than living in the caller's memory -- at this
        package's sample sizes it is what decides whether the level means anything."""

    # ---------------------------------------------------------------- internals

    def _expand(self, X: NDArray[np.float64]) -> NDArray[np.float64]:
        """Optional pairwise interaction expansion. Off by default — see module docs."""
        if not self.interactions or self._length is None or self._width is None:
            return X
        L, W = self._length, self._width
        X3 = X.reshape(len(X), L, W)
        blocks = [X]
        for i, j in itertools.combinations(range(L), 2):
            blocks.append((X3[:, i, :, None] * X3[:, j, None, :]).reshape(len(X), -1))
        return np.hstack(blocks)

    def _design_matrix(self, sequences: list[str]) -> NDArray[np.float64]:
        X = self.featurizer(sequences)
        if self._length is None:
            self._length = len(sequences[0])
            self._width = X.shape[1] // self._length
        return self._expand(X)

    @staticmethod
    def _labelled(variants: list[Variant]) -> tuple[list[str], NDArray[np.float64]]:
        missing = [v.variant_id for v in variants if v.fitness is None]
        if missing:
            raise ValueError(
                f"{len(missing)} variant(s) have no fitness (first: {missing[0]}); "
                "only measured variants can be used for fitting or calibration"
            )
        return [v.sequence for v in variants], np.array([v.fitness for v in variants], float)

    # ------------------------------------------------------------------- public

    def fit(self, data: Campaign | list[Variant]) -> CalibratedFitnessModel:
        variants = data.variants if isinstance(data, Campaign) else data
        seqs, y = self._labelled(variants)
        if len(seqs) < 2:
            raise ValueError(f"need at least 2 measured variants to fit; got {len(seqs)}")
        X = self._design_matrix(seqs)
        # The mean comes from a fit on *all* the data; the ensemble supplies only the
        # spread. Using the bagged mean instead measurably costs ranking accuracy
        # (Spearman 0.806 vs 0.873 at zero epistasis) because each member sees a
        # bootstrap resample — pure loss when a full-data fit is available. This
        # comment read "0.806 vs 0.975" until 2026-08-13, which compared the bagged
        # mean against the *uncalibrated* full-campaign ridge from a different
        # experiment and so tripled the apparent cost of bagging.
        self._full = Ridge(alpha=self.alpha).fit(X, y)
        self._models = []
        for b in range(self.n_estimators):
            Xb, yb = resample(X, y, random_state=self.seed + b)
            self._models.append(Ridge(alpha=self.alpha).fit(Xb, yb))
        return self

    def calibrate(
        self,
        data: Campaign | list[Variant],
        level: float = 0.90,
        warn_below_slack: float | None = 0.05,
    ) -> CalibratedFitnessModel:
        """Split-conformal calibration on held-out variants.

        Must be variants the model was *not* fit on. Calibrating on training data
        produces an interval that is honest about nothing.

        **A level the calibration set cannot support is refused, not approximated**
        (#197). Split conformal takes the ``ceil((n+1) * level)``-th smallest score,
        so ``level`` is capped at ``n / (n+1)`` -- 0.973 at n=36. Above that the
        quantile does not exist and ``split_conformal_multiplier`` falls back to the
        largest observed score: the widest interval those points justify, but *not*
        the requested level.

        engin-core warns there. This raises, and the difference is deliberate.
        engin-core is a general library whose caller may legitimately want the
        widest-justifiable interval. Here the multiplier is minted into
        :class:`ScoredDesign` bounds that a user reads as *the* interval at
        ``level``, and this package's stated regime is a few dozen assay
        measurements (see ``engin_protein.lown``) -- exactly where the ceiling
        binds. A mislabelled interval is worse than an exception on a package whose
        deliverable is the label.

        The achievable level is on the exception, so the fix is in the message
        rather than in a doc somewhere.

        ``warn_below_slack`` passes through to engin-core's coverage-spread warning.
        At this package's sample sizes that warning fires almost always and is
        correct to; pass ``None`` where the smallness is already understood and the
        noise is not telling the caller anything new.
        """
        if not self._models:
            raise RuntimeError("call fit() before calibrate()")
        variants = data.variants if isinstance(data, Campaign) else data
        seqs, y = self._labelled(variants)
        ceiling = highest_attainable_level(len(y))
        if level > ceiling:
            raise ValueError(
                f"level={level} is above what {len(y)} calibration variants can "
                f"support: the ceiling is n/(n+1) = {ceiling:.4f}. Split conformal "
                f"has no quantile to take above it, so the interval would be the "
                f"widest these points justify while being labelled {level:.0%}. "
                f"Use level <= {ceiling:.4f}, or calibrate on at least "
                f"{smallest_calibration_set(level)} variants."
            )
        mean, sd = self.predict_raw(seqs)
        self.q = split_conformal_multiplier(
            y, mean, sd, level=level, warn_below_slack=warn_below_slack
        )
        self.level = float(level)
        self.n_calibration = int(len(y))
        return self

    def predict_raw(self, sequences: list[str]) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """``(mean, epistemic sd)`` — mean from the full-data fit, sd from the ensemble."""
        if not self._models:
            raise RuntimeError("call fit() before predict")
        X = self._design_matrix(sequences)
        P = np.array([m.predict(X) for m in self._models])
        # Floor the sd: a unanimous ensemble is overconfident, not certain, and a
        # zero sd would make EI degenerate and the conformal multiplier infinite.
        return self._full.predict(X), np.maximum(P.std(axis=0), 1e-6)

    def predict(self, variants: list[Variant]) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        return self.predict_raw([v.sequence for v in variants])

    def score(self, variants: list[Variant], threshold: float | None = None) -> list[ScoredDesign]:
        """Predictions as :class:`ScoredDesign` — value, calibrated interval, P(≥ threshold)."""
        if self.q is None:
            raise RuntimeError(
                "call calibrate() before score(); an uncalibrated interval is not honest"
            )
        mean, sd = self.predict(variants)
        hw = self.q * sd
        probs = (
            prob_at_least(mean, sd, threshold) if threshold is not None else [None] * len(variants)
        )
        return [
            ScoredDesign(
                variant_id=v.variant_id,
                sequence=v.sequence,
                predicted=float(m),
                lower=float(m - h),
                upper=float(m + h),
                prob_above_threshold=None if p is None else float(p),
            )
            for v, m, h, p in zip(variants, mean, hw, probs, strict=True)
        ]

    def position_importance(self) -> NDArray[np.float64]:
        """Per-position importance from the mean absolute ridge coefficients.

        Answers "which residues matter" directly — no projection back through a
        reduction step, because there isn't one.
        """
        if self._full is None or self._length is None or self._width is None:
            raise RuntimeError("call fit() before requesting importance")
        coefs = np.abs(self._full.coef_)
        base = coefs[: self._length * self._width]  # ignore interaction block
        per_position = base.reshape(self._length, self._width).sum(axis=1)
        total = per_position.sum()
        return per_position / total if total > 0 else per_position
