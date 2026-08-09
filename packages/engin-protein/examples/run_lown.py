"""The ``lown`` face [Plan 5]: pick the next batch from a small campaign.

    python examples/run_lown.py

Compares the EI-selected batch against a random batch of the same size, and against
the additive baseline that low-N protein work usually relies on.
"""
from __future__ import annotations

import numpy as np

from engin_protein import AdditiveBaseline, LowNCopilot, make_landscape
from engin_protein.evaluate import spearman

BATCH = 8
SEEDS = 6


def main() -> None:
    print("engin-protein — low-N face [Plan 5]")
    print(f"  batch size {BATCH}, averaged over {SEEDS} campaigns\n")
    print(f"  {'campaign N':>11}  {'EI batch mean':>14}  {'random mean':>12}  {'lift':>7}")
    print("  " + "-" * 50)

    for n in (24, 48, 96):
        ei_means, rand_means = [], []
        for seed in range(SEEDS):
            ls = make_landscape(epistasis=0.5, seed=seed)
            cop = LowNCopilot().fit(ls.sample_campaign(n, seed=seed + 10))
            lib = ls.library(400, seed=seed + 20)
            ei_means.append(ls.true_fitness(cop.recommend(lib, k=BATCH)).mean())
            rng = np.random.default_rng(seed)
            idx = rng.choice(len(lib), BATCH, replace=False)
            rand_means.append(ls.true_fitness([lib[int(i)] for i in idx]).mean())
        ei, rd = float(np.mean(ei_means)), float(np.mean(rand_means))
        print(f"  {n:>11}  {ei:>14.3f}  {rd:>12.3f}  {ei - rd:>+7.3f}")

    print("\n  Model vs the additive baseline, by epistasis (Spearman rho on a held-out library):")
    print(f"  {'epistasis':>10}  {'bagged ridge':>13}  {'additive':>9}")
    print("  " + "-" * 36)
    for eps in (0.0, 0.5, 0.9):
        ls = make_landscape(epistasis=eps, seed=0)
        camp = ls.sample_campaign(80, seed=1)
        lib = ls.library(300, seed=2)
        truth = ls.true_fitness(lib)
        cop = LowNCopilot().fit(camp)
        add = AdditiveBaseline().fit(camp.measured()).predict(lib)
        print(f"  {eps:>10.1f}  {spearman(cop.model.predict(lib)[0], truth):>+13.3f}"
              f"  {spearman(add, truth):>+9.3f}")

    print("\n  Note the additive baseline is genuinely strong — that is the honest")
    print("  finding, and it matches the low-N protein literature. The wedge here is")
    print("  calibrated uncertainty and batch selection, not raw ranking accuracy.")


if __name__ == "__main__":
    main()
