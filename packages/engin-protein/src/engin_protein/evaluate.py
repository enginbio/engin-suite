"""The ``evaluate`` face [Plan 2]: rank a batch of designs by predicted wet-lab success.

The pitch is that structure-prediction confidence — pLDDT, ipTM — tells you whether a
design is *plausible*, not whether it *works*, and teams order variants off those
scores because nothing better is at hand. A function-aware ranker trained on even a
small amount of assay data should beat them.

**What M0 can and cannot show.** The baseline here is a simulated confidence signal
from the synthetic landscape, constructed to correlate with the additive component and
be blind to epistasis. Beating it demonstrates the ranking loop is wired correctly and
calibrated. It is *not* evidence about pLDDT, because we built the weakness we then
exploit. The kill criterion — beat pLDDT/ipTM on held-out wet data — is an M1 question.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.stats import spearmanr

from .model import CalibratedFitnessModel
from .schema import Campaign, ScoredDesign, Variant


def spearman(a: NDArray[np.float64], b: NDArray[np.float64]) -> float:
    """Spearman rank correlation, NaN-safe -> 0.0 for degenerate input."""
    rho = spearmanr(a, b).statistic
    return float(rho) if np.isfinite(rho) else 0.0


def top_k_hit_rate(
    scores: NDArray[np.float64], truth: NDArray[np.float64], k: int, quantile: float = 0.9
) -> float:
    """Fraction of the top-``k`` by score that are truly in the top ``quantile``.

    The metric that matches the decision: you order K variants, how many are good?
    Rank correlation over the whole library can look respectable while the actual
    top of the list is junk.
    """
    scores, truth = np.asarray(scores, float), np.asarray(truth, float)
    if not 1 <= k <= scores.size:
        raise ValueError(f"k={k} out of range for {scores.size} designs")
    bar = np.quantile(truth, quantile)
    picked = np.argsort(-scores)[:k]
    return float(np.mean(truth[picked] >= bar))


class DesignEvaluator:
    """Score and rank candidate designs, with calibrated intervals.

    Splits a campaign internally into fit and calibration halves, because an
    interval calibrated on training data is not an interval.
    """

    def __init__(self, model: CalibratedFitnessModel | None = None, cal_fraction: float = 0.3):
        self.model = model or CalibratedFitnessModel()
        self.cal_fraction = cal_fraction

    def fit(self, campaign: Campaign, level: float = 0.90) -> DesignEvaluator:
        variants = campaign.measured()
        n_cal = max(2, int(round(self.cal_fraction * len(variants))))
        if len(variants) - n_cal < 2:
            raise ValueError(
                f"campaign of {len(variants)} measured variants is too small to split "
                f"into fit and calibration sets; need at least 4"
            )
        self.model.fit(variants[:-n_cal]).calibrate(variants[-n_cal:], level=level)
        return self

    def rank(self, designs: list[Variant], threshold: float | None = None) -> list[ScoredDesign]:
        """Designs sorted by predicted fitness, best first."""
        scored = self.model.score(designs, threshold=threshold)
        return sorted(scored, key=lambda s: s.predicted, reverse=True)

    def scores(self, designs: list[Variant]) -> NDArray[np.float64]:
        """Raw ranking scores, in input order — for metric computation."""
        mean, _ = self.model.predict(designs)
        return mean

    def compare_to_baseline(
        self,
        designs: list[Variant],
        truth: NDArray[np.float64],
        baseline_scores: NDArray[np.float64],
        k: int = 10,
    ) -> dict[str, float]:
        """Model vs baseline on the same designs, same split. Honest side-by-side.

        Returns both rank correlation and top-k hit rate, because they can disagree
        and the second one is what the buyer actually experiences.
        """
        model_scores = self.scores(designs)
        return {
            "model_spearman": spearman(model_scores, truth),
            "baseline_spearman": spearman(baseline_scores, truth),
            "model_hit_rate": top_k_hit_rate(model_scores, truth, k=k),
            "baseline_hit_rate": top_k_hit_rate(baseline_scores, truth, k=k),
            "random_hit_rate": 0.1,  # by construction: top-10% quantile bar
        }
