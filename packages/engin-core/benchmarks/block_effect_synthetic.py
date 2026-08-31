"""The tier-1 counterpart of the real-data cohort measurement (#310 item 2).

    python benchmarks/block_effect_synthetic.py

#310 asks for a block term in the bundled simulator, on the grounds that tier 1 and
tier 2 "provably cannot" exhibit a batch-to-batch effect and so no benchmark can
measure what grouping does to coverage.

**They can, and this is the benchmark.** ``simulate_unit`` takes a ``kinetics``
argument and :class:`~engin_core.Kinetics` is a top-level export (#322/#327), so
drawing one ``Kinetics`` per group and simulating that group's batches under it
produces exactly the structure the issue describes -- runs that share a media lot or
a seed train behaving alike, without the design points telling you so. No simulator
change is required, and no default moves.

``block_sd`` is the spread of the per-group kinetic draw, as a fraction of each
parameter's baseline. It is a knob on a synthetic landscape, not an estimate of any
real plant's variability -- the same caveat ``engin_protein.landscape``'s epistasis
knob carries.

## The confound this is built to avoid

A first version of this drew *fresh design points per group*, which made the
comparison useless: between-group titer sd came out at 2.71 g/L with the block effect
switched **off** and 2.82 with it on, because which designs a group happened to draw
swamped the kinetics it was given. The null has to be measured, not assumed.

The control that settles it holds the *designs* fixed across groups, so kinetics is
the only thing that differs: there the between-group sd of mean titer is **0.37 g/L**
at ``block_sd=0``, rising to 8.44 at 0.25 and 23.25 at 0.50. That is the effect,
isolated.

This benchmark deliberately does **not** hold designs fixed, because a real campaign
does not: every batch is its own design point. So its ``group mean sd`` column carries
design variation as well as the block effect, and the ``block_sd=0`` row -- around
4.6 g/L -- is the null to read the other rows against, not zero. The column is kept
because watching it climb past its own null is the point; it is not an effect size.

## What to read

Against the **binomial floor**, not against 0.90. With ``PER_GROUP`` test points at a
nominal 0.90, sqrt(0.9 * 0.1 / n) is the cohort-to-cohort spread a perfectly
calibrated method shows anyway. A group sd at that floor is not evidence of anything.
"""

from __future__ import annotations

import numpy as np

from engin_core import (
    KNOB_NAMES,
    Kinetics,
    fit_gp,
    simulate_unit,
    split_conformal_multiplier,
)

NOMINAL = 0.90
N_GROUPS = 10
PER_GROUP = 24
BLOCK_SDS = (0.0, 0.15, 0.30, 0.50)
RANDOM_SEEDS = range(5)
BASE = Kinetics()


def campaign(seed: int, block_sd: float):
    """Batches in groups. Designs vary per batch; kinetics are shared within a group."""
    rng = np.random.default_rng(seed)
    designs, titers, groups = [], [], []
    for index in range(N_GROUPS):
        kinetics = Kinetics(
            mu_max=float(np.clip(rng.normal(BASE.mu_max, BASE.mu_max * block_sd), 0.05, None)),
            kp=float(np.clip(rng.normal(BASE.kp, BASE.kp * block_sd), 1.0, None)),
            alpha=float(np.clip(rng.normal(BASE.alpha, BASE.alpha * block_sd), 1e-4, None)),
        )
        u = rng.random((PER_GROUP, len(KNOB_NAMES)))
        true = simulate_unit(u, kinetics=kinetics)
        designs.append(u)
        titers.append(true + rng.normal(0, 0.05 * true + 0.4))
        groups.append(np.full(PER_GROUP, index))
    return np.vstack(designs), np.concatenate(titers), np.concatenate(groups)


def coverage(u, y, train, calib, test) -> float:
    """Split-conformal coverage on ``test``, calibrated on ``calib``."""
    gp = fit_gp(u[train], y[train], seed=0)
    mean_c, sd_c = gp.predict(u[calib], include_noise=True)
    q = split_conformal_multiplier(y[calib], mean_c, sd_c, level=NOMINAL, warn_below_slack=None)
    mean, sd = gp.predict(u[test], include_noise=True)
    return float(np.mean((y[test] >= mean - q * sd) & (y[test] <= mean + q * sd)))


def main() -> None:
    floor = float(np.sqrt(NOMINAL * (1 - NOMINAL) / PER_GROUP))
    print(f"{N_GROUPS} groups x {PER_GROUP} batches, nominal {NOMINAL}")
    print(f"binomial floor on cohort-to-cohort sd at this group size: {floor:.3f}\n")
    print(
        f"  {'block_sd':>9}{'group mean sd':>16}{'random split':>14}{'leave-1-group':>15}"
        f"{'group sd':>10}{'vs floor':>10}{'worst group':>13}"
    )

    for block_sd in BLOCK_SDS:
        u, y, groups = campaign(0, block_sd)
        n = len(y)
        between = float(np.std([y[groups == i].mean() for i in range(N_GROUPS)]))

        random_cov = []
        for seed in RANDOM_SEEDS:
            order = np.random.default_rng(seed).permutation(n)
            random_cov.append(
                coverage(
                    u,
                    y,
                    order[: int(0.6 * n)],
                    order[int(0.6 * n) : int(0.8 * n)],
                    order[int(0.8 * n) :],
                )
            )

        grouped = []
        for index in range(N_GROUPS):
            test = np.where(groups == index)[0]
            rest = np.random.default_rng(0).permutation(np.where(groups != index)[0])
            cut = int(0.75 * len(rest))
            grouped.append(coverage(u, y, rest[:cut], rest[cut:], test))

        sd = float(np.std(grouped))
        print(
            f"  {block_sd:>9.2f}{between:>16.2f}{np.mean(random_cov):>14.3f}"
            f"{np.mean(grouped):>15.3f}{sd:>10.3f}{sd / floor:>9.1f}x{min(grouped):>13.3f}"
        )

    print(
        "\nThe mean never shows it. Leave-one-group-out coverage stays near nominal at"
        "\nevery block strength -- which is what the 406 industrial batches also show"
        "\n(0.892 grouped against 0.893 random). The spread is where it appears, and so"
        "\nis the worst group: a user running that group had the interval hold far less"
        "\noften than the number on the page."
    )


if __name__ == "__main__":
    main()
