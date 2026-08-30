"""The strain-to-scale funnel, end to end: host -> pathway -> process.

This is the example the README's diagram describes. It exists because each stage was
individually runnable long before the chain was: `engin_core.handoff` defined what a
decision looks like when it crosses a stage boundary, but nothing produced one, so the
uncertainty a stage reports had no way to reach the stage below it (#139).

What it demonstrates, and the only claim being made here, is **that the plumbing carries
uncertainty forward** — the interval the process stage plans against is wider than the
pathway stage's own, because the host decision above it was not certain.

Lives at the repository root rather than under a package because it imports two sibling
packages, and neither depends on the other.

    pip install -r requirements-dev.txt
    python examples/run_funnel.py

```{warning}
**The inputs are illustrative, and so is every number this prints.** The host knowledge
base is 54 hand-assigned values with no citations (#146) and the routes come from
engin-pathway's own synthetic generator, whose step-count margin is itself under audit
(#124). Read this as a demonstration of the interfaces, not as advice about a molecule.
```
"""

from __future__ import annotations

import numpy as np
from engin_core import fit_gp, process_brief, recommend_batch_by_cost, simulate_unit
from engin_core import simulator as sim
from engin_host import HostQuery, default_kb, score, to_decision
from engin_pathway import PathwayRanker, make_dataset, to_ranking

RNG = np.random.default_rng(7)


def rule(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def main() -> None:
    # ---- [4] host selection -------------------------------------------------
    rule("[4] host selection")

    kb = default_kb()
    # A secreted small molecule: secretion and titer matter, glycosylation does not.
    query = HostQuery(
        weights={"secretion": 1.0, "titer": 1.0, "scaleup": 0.7, "cost": 0.7, "tools": 0.4},
        hard={"secretion": 0.40},
    )
    scores = score(kb, query)
    decision = to_decision(scores, kb=kb)

    print(f"chosen      : {decision.host}   (feasible={decision.feasible})")
    print(f"score       : {decision.score:.3f}  ± {decision.band90:.3f} (90% band)")
    print(f"confidence  : {decision.confidence:.3f}   P(really the best feasible host)")
    print(f"drivers     : {', '.join(decision.key_drivers)}")
    print(f"alternatives: {', '.join(decision.alternatives) or '(none feasible)'}")

    demoted = [s.host for s in scores if not s.feasible]
    if demoted:
        print(f"demoted     : {', '.join(demoted)}  (failed a hard constraint)")

    # ---- [3] pathway ranking, conditioned on that host ----------------------
    rule("[3] pathway ranking")

    routes = make_dataset(n=160, seed=0)
    ranker = PathwayRanker(embed_seed=0).fit(routes[:100]).calibrate(routes[100:140])
    candidates = routes[140:]

    ranking = to_ranking(ranker, candidates, host=decision)
    top = ranking.top

    print(f"ranked      : {len(ranking.routes)} candidate routes")
    print(f"conditioned : {ranking.conditioned_on_host} (conf {ranking.host_confidence:.3f})")
    print(f"best route  : {top.route_id}")
    print(f"manufactur. : {top.manufacturability:.3f}  [{top.lo:.3f}, {top.hi:.3f}] (90%)")
    print(f"half-width  : {top.half_width:.4f}   <- split-conformal, this stage only")

    # ---- the handoff --------------------------------------------------------
    rule("handoff: where the funnel's uncertainty compounds")

    brief = process_brief(ranking)
    inflation = brief.uncertainty / top.half_width

    print(f"provenance  : {brief.provenance}")
    print(f"pathway said: ± {top.half_width:.4f}")
    print(f"process gets: ± {brief.uncertainty:.4f}   (×{inflation:.2f})")
    print(
        f"\nThe widening is the point. The host decision carried confidence "
        f"{decision.confidence:.2f},\nso the route interval is inflated by "
        f"(2 - {decision.confidence:.2f}) = {inflation:.2f} before the process stage\n"
        "plans against it. A confident host decision would leave it untouched."
    )
    print(
        "\nNote what the two numbers are. The pathway half-width is split-conformal.\n"
        "The inflation factor is a heuristic with no coverage guarantee, so their\n"
        "product is a propagated width, not a calibrated one — wider by construction,\n"
        "and un-measured. Plan conservatively against it; don't quote it as coverage."
    )

    # ---- [1] process optimization -------------------------------------------
    rule("[1] process: next batch to run")

    d = len(sim.KNOB_NAMES)
    U = RNG.random((40, d))
    y = simulate_unit(U)
    y = np.maximum(y + RNG.normal(0, 0.05 * y + 0.4), 0.0)  # observation noise
    gp = fit_gp(U, y, seed=0)

    from engin_core.tea import ParametricCostModel, cost_summary

    best_cost = min(s.expected_usd_per_kg for s in cost_summary(gp, U[:12]))
    batch, gain = recommend_batch_by_cost(gp, best_cost=best_cost, k=4, model=ParametricCostModel())

    print(f"planning for: route {brief.route_id} in {brief.host}")
    print(f"carrying    : ± {brief.uncertainty:.4f} of upstream uncertainty")
    print(f"best cost so far: ${best_cost:,.0f}/kg\n")
    print("next 4 batches, by expected cost reduction (D13 — cost, not titer):")
    for i, (u, g) in enumerate(zip(batch, gain, strict=True), 1):
        phys = sim.unit_to_physical(u[None, :])[0]
        knobs = "  ".join(f"{n}={v:.3g}" for n, v in zip(sim.KNOB_NAMES, phys, strict=True))
        print(f"  {i}. E[Δcost]=${g:,.0f}/kg   {knobs}")

    rule("what this run does and does not establish")
    print(
        "Establishes : the three stages compose, and uncertainty propagates rather than\n"
        "              being silently dropped at each boundary.\n"
        "Establishes : nothing about the hosts, routes, or economics above — the KB is\n"
        "              illustrative (#146) and the routes are synthetic (#124).\n"
        "See docs/limitations.md for what each validation tier does and does not prove."
    )


if __name__ == "__main__":
    main()
