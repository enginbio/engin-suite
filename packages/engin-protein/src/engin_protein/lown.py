"""The ``lown`` face [Plan 5]: squeeze signal from a campaign of fewer than 100 points.

The regime this serves is the one where most protein engineering actually lives — a
few dozen assay measurements, an expensive next round, and no chance of the thousands
of points a deep model wants. Two things matter there:

1. **Modeling epistasis.** The default assumption in low-N work is additivity: fit
   per-position effects, sum them. That is exactly right when there is no epistasis
   and progressively wrong as there is. :class:`AdditiveBaseline` is that assumption,
   made explicit so the GP has to beat it rather than being assumed better.
2. **Choosing the next batch well.** With one shot at a round, batch composition
   matters more than squeezing the last bit of accuracy out of the model.

Cradle owns the funded lane here. The honest read from the shortlist is that this face
wins on the genuinely-low-N regime plus price, not on beating a well-resourced
competitor at their own game.
"""

from __future__ import annotations

import numpy as np
from engin_core import expected_improvement
from numpy.typing import NDArray
from sklearn.linear_model import Ridge

from .featurize import OneHotPhysicochemical
from .model import CalibratedFitnessModel
from .schema import Campaign, ScoredDesign, Variant


class AdditiveBaseline:
    """Per-position additive model — the standard low-N assumption, made explicit.

    Ridge on one-hot features with no interaction terms. On a landscape with zero
    epistasis this is *exactly* the right model and should be hard to beat; the gap
    that opens as epistasis rises is the low-N face's entire argument.
    """

    def __init__(self, alpha: float = 1.0) -> None:
        self._featurizer = OneHotPhysicochemical(use_descriptors=False)
        self._model = Ridge(alpha=alpha)

    def fit(self, data: Campaign | list[Variant]) -> AdditiveBaseline:
        variants = data.variants if isinstance(data, Campaign) else data
        seqs = [v.sequence for v in variants]
        y = np.array([v.fitness for v in variants], float)
        self._model.fit(self._featurizer(seqs), y)
        return self

    def predict(self, variants: list[Variant]) -> NDArray[np.float64]:
        return self._model.predict(self._featurizer([v.sequence for v in variants]))


class LowNCopilot:
    """Fit a small campaign, then recommend the next batch to assay."""

    def __init__(self, model: CalibratedFitnessModel | None = None, cal_fraction: float = 0.3):
        self.model = model or CalibratedFitnessModel()
        self.cal_fraction = cal_fraction
        self._best_observed: float | None = None

    def fit(self, campaign: Campaign, level: float = 0.90) -> LowNCopilot:
        variants = campaign.measured()
        if len(variants) < 4:
            raise ValueError(f"need at least 4 measured variants; got {len(variants)}")
        n_cal = max(2, int(round(self.cal_fraction * len(variants))))
        self.model.fit(variants[:-n_cal]).calibrate(variants[-n_cal:], level=level)
        self._best_observed = float(max(v.fitness for v in variants))
        return self

    def recommend(
        self, library: list[Variant], k: int = 8, xi: float = 0.01, min_hamming: int = 1
    ) -> list[Variant]:
        """The next ``k`` variants to assay, by Expected Improvement.

        ``min_hamming`` enforces batch diversity: EI is computed per-candidate and
        greedily taking the top-k tends to return near-duplicates, which wastes a
        round because they teach nearly the same thing. Enforcing a minimum pairwise
        distance is the cheap fix that doesn't require a joint acquisition function.
        """
        if self._best_observed is None:
            raise RuntimeError("call fit() before recommend()")
        if k < 1:
            raise ValueError("k must be at least 1")
        mean, sd = self.model.predict(library)
        ei = expected_improvement(mean, sd, best=self._best_observed, xi=xi)

        chosen: list[Variant] = []
        for idx in np.argsort(-ei):
            cand = library[int(idx)]
            if all(_hamming(cand.sequence, c.sequence) >= min_hamming for c in chosen):
                chosen.append(cand)
            if len(chosen) == k:
                break
        return chosen

    def score(self, designs: list[Variant], threshold: float | None = None) -> list[ScoredDesign]:
        return self.model.score(designs, threshold=threshold)

    def acquisition(self, library: list[Variant], xi: float = 0.01) -> NDArray[np.float64]:
        """Raw EI values, in input order — for inspection and testing."""
        if self._best_observed is None:
            raise RuntimeError("call fit() before acquisition()")
        mean, sd = self.model.predict(library)
        return expected_improvement(mean, sd, best=self._best_observed, xi=xi)


def _hamming(a: str, b: str) -> int:
    return sum(x != y for x, y in zip(a, b, strict=True))
