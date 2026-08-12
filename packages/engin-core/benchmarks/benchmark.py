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
   random batch of the same size (the "fewer DoE rounds" claim).

Run:  python benchmarks/benchmark.py                # synthetic (D12 tier 1)
      python benchmarks/benchmark.py --data real   # 406 industrial batches (tier 3)

**Every run states which data it used**, in its first line of output. That is the
point of the flag: the difference between "our simulator" and "a working plant"
is the difference between demonstrating that the code runs and demonstrating that
the method works, and a number quoted without it is close to meaningless.
"""

from __future__ import annotations

import argparse

import numpy as np

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

    # active learning: EI batch vs random batch, scored on *true* titer against
    # the best *true* titer in the initial DoE (apples to apples, noise-free).
    best_true_prior = float(y_true.max())
    Xnext, *_ = recommend_batch(gp, float(y_obs.max()), k=8, seed=seed + 100)
    best_ei = float(simulate_unit(Xnext).max())
    best_rand = float(simulate_unit(rng.random((8, d))).max())
    lift_ei = 100.0 * (best_ei - best_true_prior) / best_true_prior
    lift_rand = 100.0 * (best_rand - best_true_prior) / best_true_prior

    return dict(
        rmse=rmse,
        r2=r2,
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
    print(f"  R^2             {avg('r2'):6.2f}\n")
    print("90% interval coverage (target 0.90):")
    print(f"  epistemic-only Gaussian  {avg('cover_epi'):5.2f}   <- naive, overconfident")
    print(f"  total Gaussian           {avg('cover_tot'):5.2f}   <- assumes normality")
    print(f"  split-conformal          {avg('cover_conf'):5.2f}   <- honest")
    print(f"  conformal q90            {avg('q90'):5.2f}   (vs Gaussian {GAUSS_90})\n")
    print("Active-learning lift over best true prior titer:")
    print(f"  EI batch      {avg('lift_ei'):+6.1f}%")
    print(f"  random batch  {avg('lift_rand'):+6.1f}%")


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
