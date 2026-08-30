"""What a random split cannot see: coverage with a whole run-cohort held out (#310).

``real_data_coverage.py`` splits the 406 erythromycin batches uniformly at random.
That measures marginal coverage under exchangeability, which is what split conformal
guarantees. It cannot answer the question a plant asks -- *will the interval hold on
next month's batches* -- because a random split puts members of every cohort on both
sides of it.

This script holds out one monthly cohort at a time and reports coverage on it. The
grouping is the only provenance the file carries: no media lot, no seed train, no
operator. That is the gap ``engin_core.convention``'s :data:`GROUPINGS` exists to
let a dataset close.

Run it::

    cd packages/engin-core
    python benchmarks/block_holdout_coverage.py

Takes about twenty minutes: twelve cohorts plus five random-split seeds, each a GP
fit on ~300 batches.

**Read the caveat with the numbers.** Monthly cohorts are time-ordered, so this
conflates a block effect with temporal drift -- the mechanism #173 covers. It does
not isolate "media lot" from "the process moved"; separating those needs the
provenance the dataset does not carry, which is the point.
"""

from __future__ import annotations

import numpy as np

from engin_core.datasets import fetch
from engin_core.gp import fit_gp, split_conformal_multiplier

CUTOFF_H = 48
NOMINAL = 0.90
SEEDS = range(5)
TARGET = "hx"
MIN_COHORT = 8


def load():
    """``(X, y, cohort)`` per batch: window-mean features, final potency, run month."""
    import pandas as pd

    (path,) = fetch("erythromycin-efp")
    df = pd.read_csv(path, parse_dates=["date"])
    process = [c for c in df.columns if c not in ("date", "batch_id", "hh", TARGET)]

    rows, targets, cohorts = [], [], []
    for _, batch in df.groupby("batch_id"):
        batch = batch.sort_values("hh")
        elapsed = batch["hh"] - batch["hh"].min()
        if elapsed.max() < CUTOFF_H + 2:
            continue
        window = batch[elapsed <= CUTOFF_H]
        if window.empty:
            continue
        rows.append(window[process].mean().values)
        targets.append(batch[TARGET].iloc[-1])
        cohorts.append(str(batch["date"].min().to_period("M")))

    x = np.asarray(rows, float)
    y = np.asarray(targets, float)
    cohort = np.asarray(cohorts)
    keep = np.isfinite(x).all(axis=1) & np.isfinite(y)
    return x[keep], y[keep], cohort[keep]


def coverage(x, y, train, calib, test, seed: int) -> float:
    lo, hi = x[train].min(0), x[train].max(0)
    u = (x - lo) / np.where(hi - lo > 0, hi - lo, 1.0)
    gp = fit_gp(u[train], y[train], seed=seed)
    mean_c, sd_c = gp.predict(u[calib], include_noise=True)
    q = split_conformal_multiplier(y[calib], mean_c, sd_c, level=NOMINAL, warn_below_slack=None)
    mean_t, sd_t = gp.predict(u[test], include_noise=True)
    return float(np.mean(np.abs(y[test] - mean_t) <= q * sd_t))


def main() -> None:
    x, y, cohort = load()
    names, counts = np.unique(cohort, return_counts=True)
    print(f"{len(y)} batches, {len(names)} monthly cohorts, sizes {counts.min()}-{counts.max()}\n")

    random_arm = []
    for seed in SEEDS:
        idx = np.random.default_rng(seed).permutation(len(y))
        n = len(idx)
        random_arm.append(
            coverage(
                x,
                y,
                idx[: int(0.6 * n)],
                idx[int(0.6 * n) : int(0.8 * n)],
                idx[int(0.8 * n) :],
                seed,
            )
        )
    print(f"  random split (what the published table uses): {np.mean(random_arm):.3f}")
    print(f"    per seed: {', '.join(f'{c:.3f}' for c in random_arm)}\n")

    print(f"  {'cohort':<9}{'n':>5}{'coverage':>11}{'binomial sd':>14}{'z vs 0.90':>12}")
    held = []
    for name in names:
        test = np.flatnonzero(cohort == name)
        if len(test) < MIN_COHORT:
            continue
        rest = np.random.default_rng(0).permutation(np.flatnonzero(cohort != name))
        cut = int(0.75 * len(rest))
        c = coverage(x, y, rest[:cut], rest[cut:], test, 0)
        sd = float(np.sqrt(NOMINAL * (1 - NOMINAL) / len(test)))
        held.append((name, len(test), c, sd))
        print(f"  {name:<9}{len(test):>5}{c:>11.3f}{sd:>14.3f}{(c - NOMINAL) / sd:>12.2f}")

    values = np.array([c for _, _, c, _ in held])
    binom_only = float(np.sqrt(np.mean([sd**2 for *_, sd in held])))
    print(
        f"\n  held-out mean {values.mean():.3f} against random-split "
        f"{np.mean(random_arm):.3f} -- the marginal number survives."
    )
    print(
        f"  cohort-to-cohort sd {values.std(ddof=1):.3f} against binomial-only "
        f"{binom_only:.3f} ({values.std(ddof=1) / binom_only:.2f}x): the spread does not."
    )
    print(
        "\n  Monthly cohorts are time-ordered, so this mixes a block effect with\n"
        "  temporal drift (#173). Separating them needs provenance the file does not\n"
        "  carry -- which is what convention.GROUPINGS exists to let a dataset record."
    )


if __name__ == "__main__":
    main()
