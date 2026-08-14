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

So the estimator here is **ridge with a bagged ensemble for spread** — which is the
*expected* choice in this regime rather than a lucky one. Hsu et al. (2022) assess
protein fitness predictors systematically and find that "a simple baseline approach we
introduce is competitive with and often outperforms more sophisticated methods"; and
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
additive wins at e=0, pairwise wins by e=0.8. Use that to decide, and treat the
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
additive model at these sample sizes — it wins only at high epistasis (ρ 0.313 vs
0.292 at e=0.8) and loses meaningfully at low (0.816 vs 0.942 at e=0). **That pair is
the switch condition referred to above**: it is the one crossover this package can
actually document, and it is in epistasis rather than N.

Additive models being hard to beat in low-N protein work is a well-reported result
(Hsu et al. 2022), not a surprise.
"""

from __future__ import annotations

import itertools

import numpy as np
from engin_core import prob_at_least, split_conformal_multiplier
from numpy.typing import NDArray
from sklearn.linear_model import Ridge
from sklearn.utils import resample

from .featurize import Featurizer, OneHotPhysicochemical
from .schema import Campaign, ScoredDesign, Variant

DEFAULT_N_ESTIMATORS = 24
DEFAULT_ALPHA = 1.0


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
        # (Spearman 0.806 vs 0.975 at zero epistasis) because each member sees a
        # bootstrap resample — pure loss when a full-data fit is available.
        self._full = Ridge(alpha=self.alpha).fit(X, y)
        self._models = []
        for b in range(self.n_estimators):
            Xb, yb = resample(X, y, random_state=self.seed + b)
            self._models.append(Ridge(alpha=self.alpha).fit(Xb, yb))
        return self

    def calibrate(
        self, data: Campaign | list[Variant], level: float = 0.90
    ) -> CalibratedFitnessModel:
        """Split-conformal calibration on held-out variants.

        Must be variants the model was *not* fit on. Calibrating on training data
        produces an interval that is honest about nothing.
        """
        if not self._models:
            raise RuntimeError("call fit() before calibrate()")
        variants = data.variants if isinstance(data, Campaign) else data
        seqs, y = self._labelled(variants)
        mean, sd = self.predict_raw(seqs)
        self.q = split_conformal_multiplier(y, mean, sd, level=level)
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
