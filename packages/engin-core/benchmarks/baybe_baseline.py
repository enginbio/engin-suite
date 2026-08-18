"""The off-the-shelf Bayesian-optimization baseline (#20).

`docs/benchmarks.md` commits to reporting every claim against the simpler thing
it says it beats, and the BO-library row sat unbuilt. RSM already beats Engin on
two measures, and RSM is a *textbook* method -- so "Engin loses to RSM" was a
result without a ceiling. It said the floor is above us, not how far below the
top we sit. This is the ceiling.

## Why BayBE rather than Ax or ProcessOptimizer

All three pull torch, so the light-path argument does not separate them. What
does:

* **BayBE is Apache-2.0**, matching this project (`D3`), and its Python floor is
  ``>=3.10`` -- the same as engin-core. Ax requires ``>=3.11``.
* ProcessOptimizer is the one ``docs/ecosystem.md`` recommends when torch is
  disqualifying, and **it pulls torch too** -- verified from its PyPI metadata,
  reported on #191. That escape hatch does not exist.

## Why it is not a default dependency, and this is stronger than "heavy"

**On macOS x86_64 torch has no current wheel at all.** The last release carrying
one is 2.2.2; 2.3.0 onward ships zero. So on such a machine BayBE is installable
only by pinning a two-year-old torch -- and that pin brings its own chain,
because torch 2.2.2 predates the numpy 2 ABI and raises
``RuntimeError: Numpy is not available`` until numpy is held below 2.

A default torch dependency would therefore not merely bloat this package. It
would make it unbuildable on that platform at any current version, and buildable
only inside a frozen numpy/torch pair. Hence the ``[bo]`` extra.

Run it::

    pip install 'engin-core[bo]'
    python benchmarks/baybe_baseline.py --seeds 20
"""

from __future__ import annotations

import argparse
import sys
import warnings

import numpy as np

from engin_core.gp import fit_gp
from engin_core.recommend import recommend_batch
from engin_core.simulator import simulate_unit

D, K, N = 5, 8, 120
COLS = [f"x{i}" for i in range(D)]
TRAIN = slice(0, 70)


def _add_noise(y, rng):
    """The observation model used by benchmark.py, repeated so the comparison
    is against the same noisy data Engin sees."""
    return np.maximum(y + rng.normal(0, 0.05 * y + 0.4), 0.0)


def baybe_batch(u_train, y_train, batch: int = K):
    """``batch`` designs from BayBE, given the same observations Engin got."""
    try:
        import pandas as pd
        from baybe import Campaign
        from baybe.objectives import SingleTargetObjective
        from baybe.parameters import NumericalContinuousParameter
        from baybe.searchspace import SearchSpace
        from baybe.targets import NumericalTarget
    except ImportError as exc:  # pragma: no cover - depends on the extra
        raise SystemExit(
            "this baseline needs the optional extra: pip install 'engin-core[bo]'.\n"
            "On macOS x86_64 note that torch has no wheel past 2.2.2, which in turn "
            "needs numpy<2 -- see this module's docstring."
        ) from exc

    space = SearchSpace.from_product([NumericalContinuousParameter(c, (0.0, 1.0)) for c in COLS])
    campaign = Campaign(space, SingleTargetObjective(NumericalTarget(name="titer", mode="MAX")))
    frame = pd.DataFrame(u_train, columns=COLS)
    frame["titer"] = y_train
    campaign.add_measurements(frame)
    return campaign.recommend(batch_size=batch)[COLS].to_numpy(float)


def compare(seeds: range) -> list[dict[str, float]]:
    """One row per seed: lift over the best true titer in the initial DoE.

    Identical protocol to ``benchmark.py::one_seed`` -- same 120-point design,
    same 70-run training split, same batch of 8, and scored on *true* titer so
    no method is rewarded for a lucky noise draw.
    """
    rows = []
    for seed in seeds:
        rng = np.random.default_rng(seed)
        u = rng.random((N, D))
        y_true = simulate_unit(u)
        y_obs = _add_noise(y_true, rng)
        best_prior = float(y_true.max())

        gp = fit_gp(u[TRAIN], y_obs[TRAIN], seed=seed)
        x_ei, *_ = recommend_batch(gp, float(y_obs.max()), k=K, seed=seed + 100)

        def lift(x, prior=best_prior):
            # `prior` bound as a default rather than closed over: the closure
            # would be correct here, since it is called within the iteration,
            # but a late-binding closure in a loop is a footgun worth not
            # leaving for whoever moves this code.
            return 100.0 * (float(simulate_unit(x).max()) - prior) / prior

        rows.append(
            {
                "seed": float(seed),
                "baybe": lift(baybe_batch(u[TRAIN], y_obs[TRAIN])),
                "ei": lift(x_ei),
                "random": lift(rng.random((K, D))),
            }
        )
    return rows


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=20)
    args = parser.parse_args(argv)
    warnings.filterwarnings("ignore")

    rows = compare(range(args.seeds))
    mean = {k: float(np.mean([r[k] for r in rows])) for k in ("baybe", "ei", "random")}
    wins = sum(1 for r in rows if r["baybe"] > r["ei"])

    print(f"=== off-the-shelf BO baseline, {len(rows)} seeds, batch of {K} ===")
    print("Lift in best true titer over the best run in the initial DoE.\n")
    print(f"  BayBE        {mean['baybe']:+6.1f}%")
    print(f"  Engin EI     {mean['ei']:+6.1f}%")
    print(f"  random       {mean['random']:+6.1f}%")
    print(f"\n  BayBE beats Engin on {wins} of {len(rows)} seeds")
    print(
        "\nSynthetic only: this is D12 tier 1, measured on Engin's own simulator.\n"
        "Where the baseline wins, that is the result."
    )
    if wins > len(rows) / 2:
        print("\nEngin loses this comparison.", file=sys.stderr)


if __name__ == "__main__":
    main()
