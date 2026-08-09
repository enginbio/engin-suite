"""The ``planner`` face [Plan 9]: run a multi-round campaign, and test transfer honestly.

    python examples/run_planner.py

The second half is the one that matters commercially. Cross-project priors are the
claimed moat, so the comparison has to be against a prior from a *related but
different* landscape — pooling a prior from the same landscape measures "more data",
not transfer, and would overstate the case.
"""
from __future__ import annotations

import numpy as np

from engin_protein import CampaignPlanner, make_landscape, random_campaign

ROUNDS, BATCH, SEEDS = 3, 6, 5


def main() -> None:
    print("engin-protein — planner face [Plan 9]")
    print(f"  {ROUNDS} rounds x {BATCH} variants = {ROUNDS * BATCH} assays, "
          f"vs a random campaign of the same budget\n")

    planned_all, random_all = [], []
    for seed in range(SEEDS):
        ls = make_landscape(epistasis=0.5, seed=seed)
        lib = ls.library(500, seed=seed + 20)

        def oracle(vs, _ls=ls):
            return _ls.measure(vs, seed=len(vs) * 7)

        seed_c = ls.sample_campaign(24, seed=seed + 30, campaign_id=f"s{seed}")
        res = CampaignPlanner().run(seed_c, lib, oracle, rounds=ROUNDS, batch_size=BATCH)
        rnd = random_campaign(lib, oracle, n=ROUNDS * BATCH, seed=seed)
        planned_all.append(ls.true_fitness(res["acquired"]).max())
        random_all.append(ls.true_fitness(rnd["acquired"]).max())

    print(f"  best true fitness found — planner {np.mean(planned_all):.3f} "
          f"vs random {np.mean(random_all):.3f} "
          f"(lift {np.mean(planned_all) - np.mean(random_all):+.3f})")

    print("\n  Transfer from a related campaign, by how related it is:")
    print(f"  {'similarity':>11}  {'mean lift':>10}  {'seeds won':>10}")
    print("  " + "-" * 36)

    target = make_landscape(epistasis=0.5, seed=0)
    lib = target.library(600, seed=2)

    def oracle(vs):
        return target.measure(vs, seed=len(vs) * 7)

    for sim in (0.9, 0.6, 0.0):
        prior = target.related(similarity=sim, seed=11).sample_campaign(
            60, seed=9, campaign_id=f"prior{int(sim * 10)}"
        )
        lifts = []
        for s in range(6):
            seed_c = target.sample_campaign(10, seed=100 + s, campaign_id=f"seed{s}")
            w = CampaignPlanner(prior_campaigns=[prior]).run(
                seed_c, lib, oracle, rounds=1, batch_size=6)
            o = CampaignPlanner().run(seed_c, lib, oracle, rounds=1, batch_size=6)
            lifts.append(
                float(target.true_fitness(w["acquired"]).max())
                - float(target.true_fitness(o["acquired"]).max())
            )
        print(f"  {sim:>11.1f}  {np.mean(lifts):>+10.4f}  {sum(x > 0 for x in lifts):>6}/6")

    print("\n  Read this honestly: the trend runs the right way, but an *unrelated*")
    print("  prior (similarity 0.0) still shows a positive mean lift, which means most")
    print("  of the effect is 'more training data' rather than transfer. Cross-project")
    print("  priors are NOT validated at M0. Establishing that needs many more seeds")
    print("  and real campaigns — it is the moat claim, so it deserves a real experiment.")


if __name__ == "__main__":
    main()
