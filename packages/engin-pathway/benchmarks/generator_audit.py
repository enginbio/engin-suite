"""Does 'beats step-count' measure the method, or the generator? (#124)

The package README reports Spearman rho 0.85 for the graph model against 0.51
for step-count on synthetic routes. This asks whether that gap is a property of
the ranking method or of :func:`engin_pathway.simulate.make_dataset`, which
produced both the routes and their labels.

**Run it yourself:**

    python benchmarks/generator_audit.py

## Why this audit exists

#88 found the sibling case in `engin-materials`: the headline topology result was
close to tautological on the generator that produced it, because the baseline
could not see the label's dominant term *by construction*. That is a correct
implementation check and it is not evidence about materials.

`engin-pathway` has the same shape and had never been checked. The generator's
own docstring is candid about the design -- manufacturability is "tanked by a
single bad step ... which step-count cannot see" -- so the question is not
whether anyone hid anything. It is whether a number that follows from a stated
design assumption was then published as though it followed from the data.

## What it measures

1. **Step-count's ceiling.** Step-count ranks by route length alone, so its
   Spearman against the label is a fixed property of the generator, not a
   result. Any length-only predictor scores identically.
2. **How the label is built.** The share of the label's variance carried by the
   worst-step term (which step-count cannot see) against the length term (which
   is all it can see).
3. **The decisive test.** Relabel the *same routes* with different generator
   constants and watch the gap move. If the win tracks the constants, it
   measures the generator.
"""

from __future__ import annotations

import numpy as np

from engin_pathway.schema import FEATURES
from engin_pathway.simulate import _W, make_dataset

N_ROUTES = 2000
SEED = 1


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    """Rank correlation, without pulling in scipy for one number."""
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def step_scores(route) -> np.ndarray:
    """Recompute the per-step scores the generator used to build the label."""
    g = np.array([[s.features[f] for f in FEATURES] for s in route.steps])
    return np.exp((np.log(np.clip(g, 1e-3, 1)) * _W).sum(1) / _W.sum())


def main() -> None:
    routes = make_dataset(N_ROUTES, seed=SEED)
    manuf = np.array([r.manufacturability for r in routes])
    length = np.array([len(r.steps) for r in routes], float)
    per_step = [step_scores(r) for r in routes]
    worst = np.array([s.min() for s in per_step])
    mean = np.array([s.mean() for s in per_step])

    print("=" * 74)
    print(f"1. Step-count's ceiling on this generator  (n={N_ROUTES}, seed={SEED})")
    print("=" * 74)
    print("   Step-count ranks by -length, so this is fixed by the generator.")
    print("   Every length-only predictor scores the same; none can do better.")
    print()
    print(f"   rho(-length, manufacturability)  = {spearman(-length, manuf):+.3f}   <- the ceiling")
    print(f"   rho(worst step,  manufacturability) = {spearman(worst, manuf):+.3f}")
    print(f"   rho(mean step,   manufacturability) = {spearman(mean, manuf):+.3f}")

    print()
    print("=" * 74)
    print("2. How the label is built  (simulate.py:37)")
    print("=" * 74)
    print("     manuf = (0.6*worst + 0.4*mean) * 0.96**(length-2)")
    print()
    structural = 0.6 * worst + 0.4 * mean
    penalty = 0.96 ** (length - 2)
    r2_struct = np.corrcoef(np.log(structural), np.log(manuf))[0, 1] ** 2
    r2_length = np.corrcoef(np.log(penalty), np.log(manuf))[0, 1] ** 2
    print(
        f"   structural term spans {structural.min():.3f}-{structural.max():.3f}"
        f"   r2 with the label = {r2_struct:.3f}"
    )
    print(
        f"   length term     spans {penalty.min():.3f}-{penalty.max():.3f}"
        f"   r2 with the label = {r2_length:.3f}"
    )
    print()
    print("   The term step-count CANNOT see carries most of the label. The term")
    print("   it CAN see was deliberately made mild. Both by construction.")

    print()
    print("=" * 74)
    print("3. Decisive: relabel the same routes, watch the gap move")
    print("=" * 74)
    print()
    print(f"   {'w_worst':>8} {'base':>6} | {'rho(step-count)':>16} {'rho(worst step)':>16}")
    print("   " + "-" * 60)
    for w_worst, base in ((0.6, 0.96), (0.3, 0.96), (0.0, 0.96), (0.6, 0.70), (0.0, 0.70)):
        relabelled = (w_worst * worst + (1 - w_worst) * mean) * (base ** (length - 2))
        tag = "  <- as shipped" if (w_worst, base) == (0.6, 0.96) else ""
        print(
            f"   {w_worst:>8.1f} {base:>6.2f} | {spearman(-length, relabelled):>16.3f}"
            f" {spearman(worst, relabelled):>16.3f}{tag}"
        )

    print()
    print("   Change one constant -- the length base, 0.96 -> 0.70 -- and step-count")
    print("   goes from worst predictor to best. Nothing about either method changed.")
    print()
    print("=" * 74)
    print("Verdict")
    print("=" * 74)
    print("   The comparison is a correct implementation check: the graph model does")
    print("   recover a worst-step signal that a length heuristic cannot see.")
    print()
    print("   It is NOT evidence about metabolic routes. The generator was designed")
    print("   so worst-step dominates and length is mild, and the margin follows from")
    print("   that choice. Whether real routes behave this way is an empirical")
    print("   question this package has not touched.")


if __name__ == "__main__":
    main()
