"""The ``planner`` face [Plan 9]: run a multi-round campaign, with transfer across projects.

Batch Bayesian optimization over a fitness landscape. The competitive problem is that
generic BO is a solved, open-source commodity — BayBE is Apache-2.0 and well built. A
wrapper around generic BO differentiates on nothing.

What can differentiate is **biology-specific priors**: warm-starting a new campaign
from related ones, so round one of project N+1 starts where round three of project N
left off. :class:`CampaignPlanner` supports that through ``prior_campaigns``, and
crucially it is *measured* — :func:`transfer_benefit` reports the lift against the
same planner with no prior, because an unmeasured prior is a story rather than a moat.
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

from .lown import LowNCopilot
from .model import CalibratedFitnessModel
from .schema import Campaign, Variant

Oracle = Callable[[list[Variant]], list[Variant]]
"""Assays a batch: takes unmeasured variants, returns them with fitness set."""


class CampaignPlanner:
    """Multi-round batch active learning over a design library."""

    def __init__(
        self,
        model_factory: Callable[[], CalibratedFitnessModel] | None = None,
        prior_campaigns: list[Campaign] | None = None,
    ) -> None:
        self.model_factory = model_factory or CalibratedFitnessModel
        self.prior_campaigns = prior_campaigns or []

    def _seed_variants(self, campaign: Campaign) -> list[Variant]:
        """Training pool: this campaign plus any transferred prior campaigns.

        Pooling is the simplest defensible transfer mechanism and it degrades
        gracefully — an unrelated prior campaign adds noise the GP can down-weight,
        rather than a structural assumption that breaks. A hierarchical prior is the
        better answer and is an M1+ question.
        """
        pooled = list(campaign.measured())
        for prior in self.prior_campaigns:
            if prior.length != campaign.length:
                continue  # different target; positional features won't align
            pooled.extend(prior.measured())
        return pooled

    def run(
        self,
        seed_campaign: Campaign,
        library: list[Variant],
        oracle: Oracle,
        rounds: int = 3,
        batch_size: int = 8,
    ) -> dict[str, object]:
        """Run ``rounds`` of propose → assay → refit.

        Returns the history and the best *measured* fitness after each round. Scoring
        a campaign by the best value it actually found is the honest metric: it is
        what the team walks away with.
        """
        remaining = {v.variant_id: v for v in library}
        acquired: list[Variant] = []
        history: list[dict[str, float]] = []

        for r in range(rounds):
            train = self._seed_variants(seed_campaign) + acquired
            copilot = LowNCopilot(model=self.model_factory()).fit(
                Campaign(campaign_id=f"round{r}", variants=train)
            )
            picks = copilot.recommend(list(remaining.values()), k=batch_size)
            measured = oracle(picks)
            for m in measured:
                remaining.pop(m.variant_id, None)
            acquired.extend(measured)
            history.append(
                {
                    "round": float(r + 1),
                    "n_acquired": float(len(acquired)),
                    "best_acquired": float(max(v.fitness for v in acquired)),
                }
            )

        return {
            "history": history,
            "acquired": acquired,
            "best_acquired": max(v.fitness for v in acquired),
        }


def random_campaign(
    library: list[Variant], oracle: Oracle, n: int, seed: int = 0
) -> dict[str, object]:
    """The honest baseline: assay ``n`` variants chosen at random.

    Every planner claim is reported against this. Same budget, no model.
    """
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(library), size=min(n, len(library)), replace=False)
    measured = oracle([library[int(i)] for i in idx])
    return {"acquired": measured, "best_acquired": max(v.fitness for v in measured)}


def transfer_benefit(
    seed_campaign: Campaign,
    library: list[Variant],
    oracle: Oracle,
    prior_campaigns: list[Campaign],
    rounds: int = 2,
    batch_size: int = 8,
) -> dict[str, float]:
    """Best-found with transferred priors vs without, same budget and library.

    The number that decides whether cross-project priors are a moat or a slide.
    """
    with_prior = CampaignPlanner(prior_campaigns=prior_campaigns).run(
        seed_campaign, library, oracle, rounds=rounds, batch_size=batch_size
    )
    without = CampaignPlanner().run(
        seed_campaign, library, oracle, rounds=rounds, batch_size=batch_size
    )
    return {
        "with_priors": float(with_prior["best_acquired"]),
        "without_priors": float(without["best_acquired"]),
        "lift": float(with_prior["best_acquired"]) - float(without["best_acquired"]),
    }


def best_true_found(variants: list[Variant], truth_fn: Callable[[list[Variant]], NDArray]) -> float:
    """Best *true* fitness among acquired variants.

    Scored true-vs-true deliberately: the best *observed* value can be a
    noise-inflated outlier above what the landscape can produce, and comparing
    against it is an unfair bar that makes every method look worse than it is.
    """
    return float(truth_fn(variants).max())
