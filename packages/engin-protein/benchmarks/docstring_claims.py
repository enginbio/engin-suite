"""Regenerate the Spearman ρ comparisons quoted in :mod:`engin_protein.model`.

That module's docstring publishes measured rank correlations to justify three choices:
ridge rather than ``engin_core.fit_gp``, a full-data mean rather than the bagged one,
and ``interactions=False`` by default. Since 2026-08-13 the last of those is documented
as a *switch condition* — the rule for when to turn pairwise features on — so the
numbers underneath it are load-bearing and something has to recompute them. This
script is that something; ``tests/test_docstring_claims.py`` asserts the orderings it
produces, so a drift in the ranking behaviour fails CI rather than sitting in a
docstring.

Run, from ``packages/engin-protein``::

    python benchmarks/docstring_claims.py                 # ridge comparisons, 8 seeds
    python benchmarks/docstring_claims.py --seeds 20      # tighter standard errors
    python benchmarks/docstring_claims.py --gp            # add the GP row (~15 s/fit)

**Read the per-seed spread, not the mean alone.** Every comparison here varies more
across campaign seeds than the gap being measured in some regimes, which is why the
docstring's figures are single-seed illustrations and the test asserts orderings over
a seed average instead of pinning values. The ``positive`` column — how many seeds
the ordering actually held on — is the honest summary, and two of the published
comparisons do not hold on every seed.

The protocol matches what the docstring describes: a 60-variant measured campaign on
a fixed landscape, ranking a 300-design library against noiseless true fitness.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.stats import spearmanr

from engin_protein import CalibratedFitnessModel, OneHotPhysicochemical, Variant, make_landscape

CAMPAIGN_N = 60  # the docstring's "60-variant campaign"
LIBRARY_N = 300
LANDSCAPE_SEED = 0
LIBRARY_SEED = 2
# The faces hold out a calibration split and train on ~70% of the campaign; the
# "price of a calibrated interval" comparison needs the same fraction.
TRAIN_FRACTION = 0.7


def rank_correlation(predicted: NDArray[np.float64], truth: NDArray[np.float64]) -> float:
    """Spearman ρ of a predicted ranking against true fitness."""
    return float(spearmanr(predicted, truth).statistic)


@dataclass(frozen=True)
class Task:
    """One campaign/library draw: what every estimator below is scored on."""

    campaign: list[Variant]
    sequences: list[str]
    truth: NDArray[np.float64]


def make_task(epistasis: float, seed: int, campaign_n: int = CAMPAIGN_N) -> Task:
    """A measured campaign and the held-out library it is asked to rank."""
    landscape = make_landscape(epistasis=epistasis, seed=LANDSCAPE_SEED)
    campaign = landscape.sample_campaign(campaign_n, seed=seed).measured()
    library = landscape.library(LIBRARY_N, seed=LIBRARY_SEED)
    return Task(
        campaign=campaign,
        sequences=[v.sequence for v in library],
        truth=landscape.true_fitness(library),
    )


def ridge_rhos(task: Task) -> dict[str, float]:
    """The four ridge-based ρ values the docstring compares against each other."""
    additive = CalibratedFitnessModel(interactions=False).fit(task.campaign)
    out = {"additive": rank_correlation(additive.predict_raw(task.sequences)[0], task.truth)}

    # The bagged mean is deliberately not reachable through the public API -- the class
    # returns the full-data mean by design, and this comparison is *why*. Reaching for
    # the members measures the ensemble the class actually builds, rather than a
    # reimplementation of it that could drift from the shipped one.
    X = additive._design_matrix(task.sequences)
    bagged = np.array([member.predict(X) for member in additive._models]).mean(axis=0)
    out["bagged_mean"] = rank_correlation(bagged, task.truth)

    pairwise = CalibratedFitnessModel(interactions=True).fit(task.campaign)
    out["pairwise"] = rank_correlation(pairwise.predict_raw(task.sequences)[0], task.truth)

    k = int(TRAIN_FRACTION * len(task.campaign))
    split = CalibratedFitnessModel(interactions=False).fit(task.campaign[:k])
    out["calibration_split"] = rank_correlation(split.predict_raw(task.sequences)[0], task.truth)
    return out


def gp_rho(task: Task) -> float:
    """``engin_core.fit_gp`` on the same one-hot features — the rejected estimator.

    Slow (L-BFGS over a few hundred ARD lengthscales), which is why the test does not
    call it and this script keeps it behind ``--gp``.
    """
    from engin_core import fit_gp

    featurizer = OneHotPhysicochemical(use_descriptors=False)
    X = featurizer([v.sequence for v in task.campaign])
    y = np.array([v.fitness for v in task.campaign], float)
    mean, _ = fit_gp(X, y, seed=0).predict(featurizer(task.sequences))
    return rank_correlation(mean, task.truth)


def sweep(epistasis: float, seeds: range | list[int], gp: bool = False) -> dict[str, NDArray]:
    """Every ρ, per campaign seed, at one epistasis level."""
    rows = []
    for seed in seeds:
        task = make_task(epistasis, seed)
        row = ridge_rhos(task)
        if gp:
            row["gp"] = gp_rho(task)
        rows.append(row)
    return {k: np.array([r[k] for r in rows]) for k in rows[0]}


# --------------------------------------------------------------------------- report

# (label, better, worse) -- "better" is the arm the docstring claims wins.
COMPARISONS = [
    ("additive over pairwise", "additive", "pairwise"),
    ("full-data mean over bagged", "additive", "bagged_mean"),
    ("full campaign over 70% split", "additive", "calibration_split"),
    ("ridge over GP", "additive", "gp"),
]


def _report(epistasis: float, results: dict[str, NDArray]) -> None:
    n = len(next(iter(results.values())))
    print(f"\n=== epistasis {epistasis}  ({n} campaign seeds) ===")
    print(f"  {'estimator':<20} {'mean ρ':>8} {'sd':>7} {'min':>8} {'max':>8}")
    for key, values in results.items():
        print(
            f"  {key:<20} {values.mean():>+8.3f} {values.std():>7.3f} "
            f"{values.min():>+8.3f} {values.max():>+8.3f}"
        )
    print(f"\n  {'ordering':<32} {'mean gap':>9} {'sd':>7} {'held on':>9}")
    for label, better, worse in COMPARISONS:
        if better not in results or worse not in results:
            continue
        gap = results[better] - results[worse]
        print(f"  {label:<32} {gap.mean():>+9.3f} {gap.std():>7.3f} {int((gap > 0).sum()):>5}/{n}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seeds", type=int, default=8, help="campaign seeds to average over")
    parser.add_argument("--gp", action="store_true", help="include engin_core.fit_gp (slow)")
    parser.add_argument(
        "--epistasis",
        type=float,
        nargs="+",
        default=[0.0, 0.5, 0.8],
        help="epistasis levels to measure",
    )
    args = parser.parse_args()

    print("engin-protein — regenerating the ρ values quoted in engin_protein.model")
    print(
        f"  {CAMPAIGN_N}-variant campaign -> rank a {LIBRARY_N}-design library, "
        f"landscape seed {LANDSCAPE_SEED}, campaign seeds 1..{args.seeds}"
    )
    for epistasis in args.epistasis:
        _report(epistasis, sweep(epistasis, range(1, args.seeds + 1), gp=args.gp))
    print(
        "\nSingle-seed values move by ~0.05-0.10 ρ; read any one figure as 'roughly this'.\n"
        "The orderings, not the values, are what tests/test_docstring_claims.py asserts."
    )


if __name__ == "__main__":
    main()
