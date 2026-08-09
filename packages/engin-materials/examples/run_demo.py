"""engin-materials demo: rank formulations, and decompose where the edge comes from.

    python examples/run_demo.py

The second table is the one worth reading. It separates the graph model's two possible
advantages over a composition average — seeing which unit is weakest, and seeing
topology — because a claim that doesn't say which one is working isn't worth much.
"""

from __future__ import annotations

import numpy as np

from engin_materials import (
    PolymerRanker,
    best_of_k_regret,
    composition_scores,
    crosslink_densities,
    make_dataset,
    spearman,
    true_property,
)

N, TRAIN, CAL = 500, 300, 380


def _run(weakest_link: float, topology_weight: float, seed: int = 1):
    data = make_dataset(N, seed=seed, weakest_link=weakest_link, topology_weight=topology_weight)
    ranker = PolymerRanker().fit(data[:TRAIN]).calibrate(data[TRAIN:CAL])
    test = data[CAL:]
    truth = true_property(test, weakest_link=weakest_link, topology_weight=topology_weight)
    lo, hi = ranker.predict_interval(test)
    return {
        "graph": spearman(ranker.predict(test), truth),
        "composition": spearman(composition_scores(test), truth),
        "coverage": float(np.mean((truth >= lo) & (truth <= hi))),
        "graph_regret": best_of_k_regret(ranker.predict(test), truth, k=5),
        "comp_regret": best_of_k_regret(composition_scores(test), truth, k=5),
    }


def main() -> None:
    print("engin-materials — formulation ranking [Plan 15]")
    print(
        f"  {N} synthetic formulations; train {TRAIN} / calibrate {CAL - TRAIN} / test {N - CAL}\n"
    )

    print("  Default setting (weakest_link=0.6, topology=0.25)")
    r = _run(0.6, 0.25)
    print(f"    graph model rho        {r['graph']:+.3f}")
    print(f"    composition heuristic  {r['composition']:+.3f}")
    print(f"    coverage (nominal 90%) {r['coverage']:.3f}")
    print(f"    best-of-5 regret       {r['graph_regret']:.4f} vs {r['comp_regret']:.4f}\n")

    print("  Where does the edge come from?")
    print(f"    {'weakest_link':>13} {'topology':>9} {'graph':>8} {'composition':>12}   isolates")
    print("    " + "-" * 72)
    for wl, tw, note in (
        (0.0, 0.0, "neither -> heuristic is CORRECT"),
        (0.9, 0.0, "weakest-link only"),
        (0.0, 0.25, "topology only"),
        (0.9, 0.25, "both"),
    ):
        x = _run(wl, tw)
        print(f"    {wl:>13} {tw:>9} {x['graph']:>+8.3f} {x['composition']:>+12.3f}   {note}")

    data = make_dataset(400, seed=2)
    print(
        f"\n    topology signal: rho(crosslink density, property) = "
        f"{spearman(crosslink_densities(data), true_property(data)):+.3f}"
    )

    print("\n  Read the decomposition, not just the headline. With topology switched")
    print("  off the graph model only TIES the heuristic, even where the property is")
    print("  almost entirely weakest-link driven. The edge is topology, not min-pooling")
    print("  — which contradicts this package's original motivation and is the more")
    print("  useful finding: the graph engine transfers to domains where TOPOLOGY")
    print("  carries signal, a narrower claim than 'domains with a worst part'.")
    print("\n  M0: synthetic structure->property model, random-weight GCN. A probe to")
    print("  test whether the engine transfers — not a claim about real biomaterials.")


if __name__ == "__main__":
    main()
