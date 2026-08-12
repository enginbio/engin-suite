"""Calibration coverage on real industrial fermentation data (D12 tier 3).

Everything published before this measured coverage against Engin's own
simulator, which demonstrates that the code runs. This measures it against 406
erythromycin production batches from a working plant.

**Run it yourself:**

    python benchmarks/real_data_coverage.py

It fetches the dataset (CC-BY-4.0, ~8 MB) via :mod:`engin_core.datasets`, which
verifies the checksum against the publisher's and writes a provenance manifest.
Nothing is redistributed with Engin (`D12`).

## The task, and why it is not the task Engin was built for

Engin forecasts a scalar outcome from a *design point*. This dataset is not a
design of experiments -- it is production history, so the process conditions were
recorded rather than chosen. The closest honest analogue is **early batch
outcome prediction**: from process variables averaged over the first N hours,
predict the batch's final potency.

That is a real task practitioners care about, and it exercises exactly the
machinery under test -- features to a scalar, with a calibrated interval.

## What the time axis required

``hh`` is an absolute process hour, not elapsed time from inoculation: batches
begin anywhere between hour 30 and hour 83. Each batch is therefore aligned to
its own start before any window is taken. Getting this wrong silently produces
empty feature windows, which is how it was noticed.

## Reading the result

Coverage is not the interesting number on its own -- see
``docs/methods/out-of-distribution.md``. Report it beside ``r2`` and ``width``,
because a model that predicts nothing can still be perfectly calibrated, and
this script demonstrates precisely that.
"""

from __future__ import annotations

import numpy as np

from engin_core.datasets import fetch
from engin_core.gp import fit_gp, split_conformal_multiplier

NOMINAL = 0.90
TARGET = "hx"
"""The dataset's target column: chemical potency.

Confirmed from the authors' own code (``run_EFP.py`` in YifeiSunEcust/MASTER
defaults ``--target`` to ``hx``) rather than inferred from the column's position
or behaviour. The remaining 22 columns are unglossed abbreviations and are used
without interpretation -- which is legitimate for a forecast and would not be for
any claim about mechanism.
"""

SEEDS = range(5)
CUTOFFS = (24, 48, 72)


def load_frame():
    import pandas as pd

    (path,) = fetch("erythromycin-efp")
    return pd.read_csv(path)


def build(df, cutoff_h: int, include_potency: bool):
    """Window-mean features per batch; target is that batch's final potency."""
    process = [c for c in df.columns if c not in ("date", "batch_id", "hh", TARGET)]
    rows, targets = [], []
    for _, batch in df.groupby("batch_id"):
        batch = batch.sort_values("hh")
        elapsed = batch["hh"] - batch["hh"].min()
        if elapsed.max() < cutoff_h + 2:
            continue
        window = batch[elapsed <= cutoff_h]
        if window.empty:
            continue
        features = list(window[process].mean().values)
        if include_potency:
            # Early potency is legitimate for a soft sensor and partly
            # autoregressive, so it is reported separately rather than folded in.
            features += [
                float(window[TARGET].iloc[-1]),
                float(window[TARGET].iloc[-1]) - float(window[TARGET].iloc[0]),
            ]
        rows.append(features)
        targets.append(float(batch[TARGET].iloc[-1]))
    return np.asarray(rows, float), np.asarray(targets, float)


def evaluate(X, y):
    """Split-conformal coverage, interval width and R^2, averaged over seeds."""
    finite = np.isfinite(X).all(axis=1) & np.isfinite(y)
    X, y = X[finite], y[finite]
    lo, hi = X.min(0), X.max(0)
    U = (X - lo) / np.where(hi - lo > 0, hi - lo, 1.0)  # fit_gp's kernel assumes a unit cube

    coverage, width, r2 = [], [], []
    for seed in SEEDS:
        rng = np.random.default_rng(seed)
        idx = rng.permutation(len(U))
        n = len(idx)
        train, calib, test = (
            idx[: int(0.6 * n)],
            idx[int(0.6 * n) : int(0.8 * n)],
            idx[int(0.8 * n) :],
        )

        gp = fit_gp(U[train], y[train], seed=seed)
        mc, sdc = gp.predict(U[calib], include_noise=True)
        q = split_conformal_multiplier(y[calib], mc, sdc, level=NOMINAL)

        mean, sd = gp.predict(U[test], include_noise=True)
        residual = np.abs(mean - y[test])
        coverage.append(np.mean(residual <= q * sd))
        width.append(np.mean(2 * q * sd))
        r2.append(1 - np.sum((mean - y[test]) ** 2) / np.sum((y[test] - y[test].mean()) ** 2))
    return len(U), float(np.mean(coverage)), float(np.mean(width)), float(np.mean(r2))


def main() -> None:
    df = load_frame()
    print(f"erythromycin-efp: {df['batch_id'].nunique()} batches, {len(df):,} hourly rows")
    print(f"nominal coverage {NOMINAL}, {len(list(SEEDS))} seeds\n")
    print(f"  {'features':<22}{'cutoff':>7}{'n':>6}{'coverage':>10}{'width':>10}{'R2':>8}")
    for include_potency in (False, True):
        label = "process + early hx" if include_potency else "process only"
        for cutoff in CUTOFFS:
            n, cov, w, r2 = evaluate(*build(df, cutoff, include_potency))
            print(f"  {label:<22}{cutoff:>6}h{n:>6}{cov:>10.3f}{w:>10.1f}{r2:>8.3f}")
    print(
        "\nRead coverage and R2 together: a model that predicts nothing can still be\n"
        "perfectly calibrated, and on this task that is close to what happens."
    )


if __name__ == "__main__":
    main()
