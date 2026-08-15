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
      python benchmarks/benchmark.py --multi-round # several rounds, equal budget

Baselines implemented here: random batch, a second-order **response surface**
(``baselines.py``) and **sequential Box--Wilson RSM** (``sequential_rsm.py``).
BayBE, BioSTEAM, step-count and "use E. coli" are #20 and are not built;
docs/benchmarks.md marks which is which.

**RSM currently beats Engin on design choice** -- 18 of 20 seeds, mean +5.4
percentage points of lift -- while the two tie on forecast R^2. That is published
rather than tuned away; see docs/benchmarks.md for what it does and does not mean.

``--multi-round`` exists because that number scores **one** round, which
systematically favours pure exploitation: EI spends part of every batch on
uncertainty it expects to repay in later rounds, and a single-round benchmark
collects the cost while cancelling the repayment. The multi-round mode gives both
methods the same initial data and the same per-round budget and reports the whole
trajectory, so a reader can see whether the exploration ever pays back and at
which round -- if it does.

**Multi-round needs a simulator and therefore cannot run on ``--data real``.**
An adaptive campaign has to be able to query an arbitrary new design; 406 fixed
industrial batches cannot answer one. So this comparison is D12 tier 1 by
construction, and no amount of real data available today would change that.

**Every run states which data it used**, in its first line of output. That is the
point of the flag: the difference between "our simulator" and "a working plant"
is the difference between demonstrating that the code runs and demonstrating that
the method works, and a number quoted without it is close to meaningless.
"""

from __future__ import annotations

import argparse
import sys

import numpy as np

from baselines import fit_rsm, rsm_recommend
from engin_core import (
    fit_gp,
    recommend_batch,
    simulate_unit,
    split_conformal_multiplier,
)
from sequential_rsm import SequentialRSM

GAUSS_90 = 1.645  # z_{0.95}, the naive normal multiplier for a 90% interval

# The multi-round budget, fixed before the first run and not revisited after it.
# Writing it down as a constant is the point: a budget chosen after seeing which
# split favours the tool is not evidence, and the temptation is real enough that
# the honest defence is to make changing it visible in the diff.
N_INIT = 40  # shared initial DoE, identical designs and observations for both
ROUNDS = 10  # adaptive rounds
BATCH = 8  # runs per round -- eight parallel bioreactors, the same for both
SEEDS = 20  # matches the seed count of the published single-round comparison
# The region half-width the sequential RSM starts from. Swept rather than picked,
# and the *best* setting is what gets reported as the baseline's result: tuning
# the opponent up is the only direction that is safe to tune in. The sweep spans
# the whole admissible range -- 0.5 is a box covering every knob's full span --
# so the reported setting can never be an artifact of a range that stopped short.
RADII = (0.10, 0.20, 0.30, 0.40, 0.50)


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
    print(f"  conformal q90            {avg('q90'):5.2f}   (vs Gaussian {GAUSS_90})\n")
    print("Active-learning lift over best true prior titer:")
    print(f"  EI batch      {avg('lift_ei'):+6.1f}%")
    print(f"  RSM optima    {avg('lift_rsm'):+6.1f}%   <- the baseline a process engineer uses")
    print(f"  random batch  {avg('lift_rand'):+6.1f}%")
    print("\nRSM is a real baseline, not a straw man. Where it wins, that is the result.")


def _lift(traj: list[float]) -> list[float]:
    """Best-true-titer trajectory as % over the best run in the initial DoE."""
    return [100.0 * (b - traj[0]) / traj[0] for b in traj]


def ei_campaign(U0, y0_obs, y0_true, seed, rounds: int, k: int) -> list[float]:
    """Engin's loop: fit the GP on everything so far, recommend ``k``, observe, refit."""
    rng = np.random.default_rng(seed + 10_000)
    U, y_obs = U0.copy(), y0_obs.copy()
    best = [float(y0_true.max())]
    for t in range(rounds):
        gp = fit_gp(U, y_obs, seed=seed)
        Xn, *_ = recommend_batch(gp, float(y_obs.max()), k=k, seed=seed + 100 + t)
        y_true = simulate_unit(Xn)
        U = np.vstack([U, Xn])
        y_obs = np.concatenate([y_obs, add_noise(y_true, rng)])
        best.append(max(best[-1], float(y_true.max())))
    return best


def rsm_campaign(U0, y0_obs, y0_true, seed, radius, rounds: int, k: int) -> list[float]:
    """Box--Wilson: fit, ascend the gradient, re-centre, augment to a CCD, refit."""
    rng = np.random.default_rng(seed + 20_000 + int(round(radius * 100)))
    camp = SequentialRSM(U0, y0_obs, radius=radius, seed=seed)
    best = [float(y0_true.max())]
    for _ in range(rounds):
        Xn = camp.ask(k)
        y_true = simulate_unit(Xn)
        camp.tell(Xn, add_noise(y_true, rng))
        best.append(max(best[-1], float(y_true.max())))
    return best


def single_shot_rsm_campaign(U0, y0_obs, y0_true, seed, rounds: int, k: int) -> list[float]:
    """The published single-round baseline, simply run again each round.

    Refit the global quadratic on everything observed so far, go to its optima,
    repeat. This is not Box--Wilson -- there is no region of interest, no
    steepest ascent and no CCD -- but it is the obvious way to make ``baselines.py``
    multi-round, it is trivially strong, and reporting it removes the objection
    that the sequential implementation was the weak version of RSM. Where it wins,
    it is what the RSM column reports.
    """
    rng = np.random.default_rng(seed + 30_000)
    U, y_obs = U0.copy(), y0_obs.copy()
    best = [float(y0_true.max())]
    for t in range(rounds):
        Xn = rsm_recommend(fit_rsm(U, y_obs), k=k, seed=seed + 100 + t)
        y_true = simulate_unit(Xn)
        U = np.vstack([U, Xn])
        y_obs = np.concatenate([y_obs, add_noise(y_true, rng)])
        best.append(max(best[-1], float(y_true.max())))
    return best


def _mean_se(rows: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Column means and standard errors of a ``(seeds, rounds+1)`` array."""
    n = rows.shape[0]
    return rows.mean(axis=0), rows.std(axis=0, ddof=1) / np.sqrt(n)


def multi_round(
    seeds=None,
    d: int = 5,
    n_init: int = N_INIT,
    rounds: int = ROUNDS,
    k: int = BATCH,
    radii: tuple[float, ...] = RADII,
) -> None:
    """Several rounds of each method, same total budget, trajectory reported."""
    seeds = range(SEEDS) if seeds is None else list(seeds)
    ei_rows: list[list[float]] = []
    shot_rows: list[list[float]] = []
    rsm_rows: dict[float, list[list[float]]] = {r: [] for r in radii}

    for i, s in enumerate(seeds):
        rng = np.random.default_rng(s)
        U0 = rng.random((n_init, d))
        y0_true = simulate_unit(U0)
        y0_obs = add_noise(y0_true, rng)  # one shared initial DoE, every method
        ei_rows.append(_lift(ei_campaign(U0, y0_obs, y0_true, s, rounds, k)))
        shot_rows.append(_lift(single_shot_rsm_campaign(U0, y0_obs, y0_true, s, rounds, k)))
        for r in radii:
            rsm_rows[r].append(_lift(rsm_campaign(U0, y0_obs, y0_true, s, r, rounds, k)))
        print(f"  seed {s} done ({i + 1}/{len(seeds)})", file=sys.stderr, flush=True)

    ei = np.array(ei_rows)
    shot = np.array(shot_rows)
    rsm_all = {r: np.array(v) for r, v in rsm_rows.items()}
    # The sequential baseline's headline is its best region half-width, judged
    # over the whole trajectory rather than the endpoint -- picking on the last
    # round alone would hide a setting that is stronger where it matters.
    best_r = max(radii, key=lambda r: rsm_all[r].mean())
    seq = rsm_all[best_r]
    # The RSM column is whichever RSM is ahead, seed by seed and round by round.
    # That is an oracle over baselines and is generous to them by construction;
    # it is the right direction to be generous in.
    rsm = np.maximum(seq, shot)
    gap = rsm - ei  # paired, seed by seed

    ei_m, ei_se = _mean_se(ei)
    seq_m, seq_se = _mean_se(seq)
    shot_m, shot_se = _mean_se(shot)
    gap_m, gap_se = _mean_se(gap)
    wins = (gap > 0).sum(axis=0)

    n = len(seeds)
    total = n_init + rounds * k
    print(f"=== engin-core benchmarks: MULTI-ROUND, SYNTHETIC (mean over {n} seeds) ===")
    print("Source: engin_core.simulator -- this project's own mechanistic model.")
    print("D12 tier 1. It cannot be run on real data: an adaptive campaign has to")
    print("query new design points, and a fixed dataset cannot answer.\n")
    print("Budget, identical for every method and fixed before the first run:")
    print(f"  {n_init}-run shared initial DoE, then {rounds} rounds of {k}")
    print(f"  -> {total} runs each. Same initial designs, same noisy observations,")
    print("  so what is compared is what each method does with the next")
    print(f"  {rounds * k} runs.\n")
    print("Two RSM arms, because a sequential implementation that turned out weak")
    print("would make the whole comparison worthless:")
    print(f"  sequential  Box--Wilson, region half-width {best_r:.2f} (best of {radii})")
    print("  single-shot the published one-round baseline, refit and re-run each round\n")
    print("Best-true-titer lift over the best run of the shared initial DoE:\n")
    head = "  round  runs   Engin (GP+EI)   sequential RSM   single-shot RSM"
    print(head + "    best RSM - EI   RSM wins")
    for t in range(rounds + 1):
        runs = n_init + t * k
        cells = (
            f"  {t:5d} {runs:5d}  {ei_m[t]:+6.1f} +-{ei_se[t]:4.1f}   "
            f"{seq_m[t]:+6.1f} +-{seq_se[t]:4.1f}    {shot_m[t]:+6.1f} +-{shot_se[t]:4.1f}   "
        )
        if t == 0:
            print(cells + "       --          --")
        else:
            print(cells + f"  {gap_m[t]:+6.1f} +-{gap_se[t]:4.1f}    {wins[t]:2d}/{n}")
    print("  round 0 is the shared initial DoE: identical for all three by construction.")

    # Two crossovers, reported separately on purpose. A mean that crosses while
    # most seeds still go the other way is not a crossover, it is a couple of
    # seeds with large gaps, and quoting only the mean would hide that.
    mean_cross = next((t for t in range(1, rounds + 1) if gap_m[t] < 0), None)
    seed_cross = next((t for t in range(1, rounds + 1) if wins[t] * 2 < n), None)
    lo, hi = int(wins[1:].min()), int(wins[1:].max())
    print()
    if mean_cross is None and seed_cross is None:
        print("No crossover, on either reading. RSM leads the mean at every one of")
        print(f"the {rounds} rounds, and wins between {lo}/{n} and {hi}/{n} seeds per round.")
        print("EI's exploration does not pay back within this budget on this simulator.")
    else:
        if mean_cross is None:
            print(f"The mean gap favours RSM at every one of the {rounds} rounds.")
        else:
            print(f"Mean crossover at round {mean_cross}: the average gap first favours Engin")
            print(f"there, with RSM still ahead on {wins[mean_cross]}/{n} seeds.")
        if seed_cross is None:
            print(f"RSM wins a majority of seeds at every round ({lo}/{n} to {hi}/{n}).")
        else:
            w = wins[seed_cross]
            print(f"Seed crossover at round {seed_cross}: RSM drops to {w}/{n} seeds.")
        print("Where those two rounds differ, the later one is the honest answer.")

    print("\nSequential RSM region half-width sweep (mean lift by round). Printed in")
    print("full: a headline setting picked from a sweep that is not shown is a")
    print("result nobody can check.")
    print("  radius  " + " ".join(f"{t:6d}" for t in range(rounds + 1)))
    for r in radii:
        mark = "  <- reported above" if r == best_r else ""
        row = " ".join(f"{x:+6.1f}" for x in rsm_all[r].mean(axis=0))
        print(f"    {r:.2f}  {row}{mark}")
    print("    shot  " + " ".join(f"{x:+6.1f}" for x in shot.mean(axis=0)))
    print("      EI  " + " ".join(f"{x:+6.1f}" for x in ei.mean(axis=0)))
    print("\nThe sweep tunes the baseline, not the tool. There is no corresponding")
    print("sweep over EI's xi, the GP's kernel or the batch diversity radius, and")
    print("there should not be one.")


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
    parser.add_argument(
        "--multi-round",
        action="store_true",
        help=(
            "several rounds of each method under one shared budget, reporting the "
            "trajectory rather than the endpoint. Synthetic only -- an adaptive "
            "campaign must be able to query new design points, which a fixed "
            "dataset cannot do."
        ),
    )
    parser.add_argument(
        "--seeds", type=int, default=SEEDS, help=f"seeds for --multi-round (default {SEEDS})"
    )
    args = parser.parse_args(argv)
    if args.multi_round:
        if args.data == "real":
            parser.error("--multi-round needs a simulator to query; --data real cannot supply one")
        multi_round(seeds=range(args.seeds))
    elif args.data == "real":
        real()
    else:
        synthetic()


if __name__ == "__main__":
    main()
