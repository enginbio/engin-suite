"""Where the conformal intervals stop holding, measured on the simulator.

Produces the two tables published in ``docs/methods/out-of-distribution.md``.

**This is a committed script rather than an executed documentation cell, and the
reason is worth stating.** The page's cells take well over five minutes to run --
past ``nb_execution_timeout`` in ``docs/conf.py`` -- so a cold documentation build
could not execute them and failed outright. The committed jupyter-cache hid that
for as long as the cache kept hitting: a cached cell is never re-run, so it is
never re-verified. See issue #169.

The trade is explicit. This page is no longer covered by ``D15``'s "building the
docs verifies them" guarantee, so this script is what has to be run instead. It is
the same trade ``real_data_coverage.py`` already makes for the same reason.

Run it from the package directory::

    cd packages/engin-core
    python benchmarks/ood_coverage.py
"""

from __future__ import annotations

import numpy as np

from engin_core import Kinetics, simulate_unit
from engin_core.gp import fit_gp, split_conformal_multiplier

NOMINAL, D, TRAIN_HI = 0.90, 5, 0.6
SEEDS = range(5)

REGIONS = [
    ("in-distribution", 0.0, 0.6),
    ("just outside", 0.6, 0.7),
    ("far outside", 0.9, 1.0),
]

VARIANTS = {
    "same process": Kinetics(),
    "stronger inhibition kp 18->6": Kinetics(kp=6.0),
    "slower growth mu_max .35->.22": Kinetics(mu_max=0.22),
    "several at once": Kinetics(kp=8.0, alpha=0.05, mu_max=0.26),
}


def observed(U, rng, kinetics=None):
    """Titer with heteroscedastic measurement noise."""
    y = simulate_unit(U, kinetics=kinetics)
    return np.maximum(y + rng.normal(0, 0.05 * y + 0.4), 0.0)


def calibrated_model(seed):
    """Fit and conformally calibrate on the lower 60% of every design axis."""
    rng = np.random.default_rng(seed)
    Utr = rng.uniform(0, TRAIN_HI, (70, D))
    Uca = rng.uniform(0, TRAIN_HI, (30, D))
    gp = fit_gp(Utr, observed(Utr, rng), seed=seed)
    mc, sdc = gp.predict(Uca, include_noise=True)
    q = split_conformal_multiplier(observed(Uca, rng), mc, sdc, level=NOMINAL)
    return gp, q, rng


def region_sweep():
    """Coverage, width and error as queries move outside the design region."""
    results = {name: [] for name, _, _ in REGIONS}
    for seed in SEEDS:
        gp, q, rng = calibrated_model(seed)
        for name, lo, hi in REGIONS:
            U = rng.uniform(lo, hi, (40, D))
            y = observed(U, rng)
            m, sd = gp.predict(U, include_noise=True)
            err = np.abs(m - y)
            results[name].append((np.mean(err <= q * sd), np.mean(2 * q * sd), np.mean(err)))
    return results


def process_sweep():
    """Coverage when the design distribution holds but the kinetics change."""
    out = {}
    for label, kin in VARIANTS.items():
        covs = []
        for seed in SEEDS:
            gp, q, rng = calibrated_model(seed)
            U = rng.uniform(0, TRAIN_HI, (40, D))
            y = observed(U, rng, kinetics=kin)
            m, sd = gp.predict(U, include_noise=True)
            covs.append(np.mean(np.abs(m - y) <= q * sd))
        out[label] = float(np.mean(covs))
    return out


def main() -> None:
    print(f"nominal coverage {NOMINAL}, {len(list(SEEDS))} seeds, D={D}\n")

    print("Shift one: querying outside the design region")
    print(f"  {'region':<17}{'coverage':>9}{'width':>9}{'error':>9}")
    for name, vals in region_sweep().items():
        cov, width, mae = np.array(vals).mean(axis=0)
        print(f"  {name:<17}{cov:>9.3f}{width:>9.1f}{mae:>9.1f}")

    print("\nShift two: a different process")
    print(f"  {'test process':<32}{'coverage':>9}")
    for label, cov in process_sweep().items():
        print(f"  {label:<32}{cov:>9.3f}")

    print(
        "\nRead coverage and width together: coverage recovering far outside the\n"
        "design region is the intervals growing large enough to contain anything,\n"
        "not the model becoming safe."
    )


if __name__ == "__main__":
    main()
