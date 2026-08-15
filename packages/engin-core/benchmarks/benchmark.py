"""Reproducible benchmarks for engin-core (numpy only, no plotting).

Reports, averaged over several seeds so the numbers are not cherry-picked:

1. Forecast quality (RMSE, R^2) on held-out runs.
2. Calibration -- the honest-uncertainty story, three ways to form a 90% interval:
   - epistemic-only Gaussian (model uncertainty x 1.645): the naive trap,
     badly overconfident because it ignores observation noise;
   - total Gaussian (model + noise uncertainty x 1.645): closer on average but
     assumes normality and drifts seed to seed with no guarantee;
   - split-conformal (total uncertainty x conformal q90): distribution-free,
     adapts the multiplier to a held-out calibration set.
3. Active-learning lift: best *true* titer found by an EI-recommended batch vs a
   random batch and vs the optima of a fitted response surface (the "fewer DoE
   rounds" claim, against the method a process engineer would actually use).

Run, from ``packages/engin-core`` (the script lives in the package, not at the
repository root -- the docs printed the rootward path until 2026-08-13):

      python benchmarks/benchmark.py               # synthetic (D12 tier 1)
      python benchmarks/benchmark.py --data real   # 406 industrial batches (tier 3)

Baselines implemented here: random batch, and a second-order **response surface**
(``baselines.py``). BayBE, BioSTEAM, step-count and "use E. coli" are #20 and are
not built; docs/benchmarks.md marks which is which.

**RSM currently beats Engin on design choice** -- 18 of 20 seeds, mean +5.4
percentage points of lift -- while the two tie on forecast R^2. That is published
rather than tuned away; see docs/benchmarks.md for what it does and does not mean.

**Every run states which data it used**, in its first line of output. That is the
point of the flag: the difference between "our simulator" and "a working plant"
is the difference between demonstrating that the code runs and demonstrating that
the method works, and a number quoted without it is close to meaningless.
"""

from __future__ import annotations

import argparse

import numpy as np

from baselines import fit_rsm, rsm_recommend
from engin_core import (
    fit_gp,
    recommend_batch,
    simulate_unit,
    split_conformal_multiplier,
)

GAUSS_90 = 1.645  # z_{0.95}, the naive normal multiplier for a 90% interval


def add_noise(y, rng, rel=0.05, abs_=0.4):
    return np.maximum(y + rng.normal(0, rel * y + abs_), 0.0)


def one_seed(seed: int, d: int = 5):
    rng = np.random.default_rng(seed)
    N = 120
    U = rng.random((N, d))
    y_true = simulate_unit(U)
    y_obs = add_noise(y_true, rng)
    tr, ca, te = slice(0, 70), slice(70, 100), slice(100, 120)

    gp = fit_gp(U[tr], y_obs[tr], seed=seed)

    # forecast quality on held-out test runs
    m_te, sd_epi = gp.predict(U[te], include_noise=False)  # model uncertainty only
    m_te, sd_tot = gp.predict(U[te], include_noise=True)  # + observation noise
    resid = m_te - y_obs[te]
    rmse = float(np.sqrt(np.mean(resid**2)))
    r2 = float(1 - np.sum(resid**2) / np.sum((y_obs[te] - y_obs[te].mean()) ** 2))

    # calibration: three ways to build a 90% interval (see module docstring)
    mc, sdc = gp.predict(U[ca], include_noise=True)
    q90 = split_conformal_multiplier(y_obs[ca], mc, sdc, level=0.90)
    ar = np.abs(resid)
    cover_epi = float(np.mean(ar <= GAUSS_90 * sd_epi))  # naive, overconfident
    cover_tot = float(np.mean(ar <= GAUSS_90 * sd_tot))  # Gaussian, no guarantee
    cover_conf = float(np.mean(ar <= q90 * sd_tot))  # split-conformal, honest

    # The RSM baseline sees exactly what the GP saw -- same training split, same
    # noisy observations -- so the comparison is of methods, not of information.
    rsm = fit_rsm(U[tr], y_obs[tr])
    resid_rsm = rsm.predict(U[te]) - y_obs[te]
    r2_rsm = float(1 - np.sum(resid_rsm**2) / np.sum((y_obs[te] - y_obs[te].mean()) ** 2))
    # RSM's own textbook prediction interval, at the same nominal level. This is
    # the head-to-head the project's central claim predicts it should lose: an
    # OLS interval assumes its model class is right, and split conformal does not.
    lo_rsm, hi_rsm = rsm.predict_interval(U[te], level=0.90)
    cover_rsm = float(np.mean((y_obs[te] >= lo_rsm) & (y_obs[te] <= hi_rsm)))
    width_rsm = float(np.mean(hi_rsm - lo_rsm))

    # active learning: EI batch vs random batch, scored on *true* titer against
    # the best *true* titer in the initial DoE (apples to apples, noise-free).
    best_true_prior = float(y_true.max())
    Xnext, *_ = recommend_batch(gp, float(y_obs.max()), k=8, seed=seed + 100)
    best_ei = float(simulate_unit(Xnext).max())
    best_rand = float(simulate_unit(rng.random((8, d))).max())
    best_rsm = float(simulate_unit(rsm_recommend(rsm, k=8, seed=seed + 100)).max())
    lift_ei = 100.0 * (best_ei - best_true_prior) / best_true_prior
    lift_rand = 100.0 * (best_rand - best_true_prior) / best_true_prior
    lift_rsm = 100.0 * (best_rsm - best_true_prior) / best_true_prior

    return dict(
        rmse=rmse,
        r2=r2,
        r2_rsm=r2_rsm,
        lift_rsm=lift_rsm,
        cover_rsm=cover_rsm,
        width_rsm=width_rsm,
        width_conf=float(np.mean(2 * q90 * sd_tot)),
        cover_epi=cover_epi,
        cover_tot=cover_tot,
        cover_conf=cover_conf,
        q90=q90,
        lift_ei=lift_ei,
        lift_rand=lift_rand,
    )


def synthetic(seeds=None) -> None:
    seeds = range(8) if seeds is None else seeds
    rows = [one_seed(s) for s in seeds]

    def avg(k):
        return float(np.mean([r[k] for r in rows]))

    print(f"=== engin-core benchmarks: SYNTHETIC (mean over {len(rows)} seeds) ===")
    print("Source: engin_core.simulator -- this project's own mechanistic model.")
    print("Establishes that the loop runs end to end. Establishes nothing about real")
    print("bioprocess data: the model is being scored against its own assumptions.")
    print("D12 tier 1. For real data, run with --data real.\n")
    print("Forecast (held-out):")
    print(f"  RMSE            {avg('rmse'):6.2f} g/L")
    print(f"  R^2  GP         {avg('r2'):6.2f}")
    print(f"  R^2  RSM        {avg('r2_rsm'):6.2f}   <- second-order response surface\n")
    print("90% interval coverage (target 0.90):")
    print(f"  epistemic-only Gaussian  {avg('cover_epi'):5.2f}   <- naive, overconfident")
    print(f"  total Gaussian           {avg('cover_tot'):5.2f}   <- assumes normality")
    print(f"  split-conformal          {avg('cover_conf'):5.2f}   <- honest")
    print(
        f"  RSM prediction interval  {avg('cover_rsm'):5.2f}   <- OLS, assumes its model is right"
    )
    print(f"  conformal q90            {avg('q90'):5.2f}   (vs Gaussian {GAUSS_90})")
    print(
        f"  mean width: conformal {avg('width_conf'):5.1f} g/L   RSM {avg('width_rsm'):5.1f} g/L\n"
    )
    print("Active-learning lift over best true prior titer:")
    print(f"  EI batch      {avg('lift_ei'):+6.1f}%")
    print(f"  RSM optima    {avg('lift_rsm'):+6.1f}%   <- the baseline a process engineer uses")
    print(f"  random batch  {avg('lift_rand'):+6.1f}%")
    print("\nRSM is a real baseline, not a straw man. Where it wins, that is the result.")


def real() -> None:
    """Delegate to the real-data benchmark, which fetches its own dataset."""
    import real_data_coverage

    print("=== engin-core benchmarks: REAL (406 industrial batches) ===")
    print("Source: erythromycin production data, CC-BY-4.0, fetched and checksum-")
    print("verified at run time. D12 tier 3. Downloads 8 MB the first time.\n")
    real_data_coverage.main()


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--data",
        choices=("synthetic", "real"),
        default="synthetic",
        help=(
            "which data to benchmark against. 'synthetic' is this project's own "
            "simulator (D12 tier 1) and proves only that the code runs; 'real' is "
            "406 industrial batches (tier 3). The flag is mandatory-by-design in "
            "the output: every run says which it used."
        ),
    )
    args = parser.parse_args(argv)
    if args.data == "real":
        real()
    else:
        synthetic()


if __name__ == "__main__":
    main()
