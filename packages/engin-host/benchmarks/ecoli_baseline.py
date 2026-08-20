"""The "just use *E. coli*" baseline for host selection (#20, D12).

**The baseline is trivial and the measurement is not.** Answering "always *E.
coli*" takes one line. Deciding what it means to beat it takes the rest of this
docstring, because the obvious comparison is circular.

*What cannot be measured here.* Whether ``engin-host`` picks the **right** host.
The only ground truth in this repository is ``kb.py``, which is the table the
scorer reads. Grading the scorer against its own inputs would return a number
near 100% and mean nothing by it. `#146` records that the knowledge base is 60
hand-assigned values with no citations, so there is no second opinion to grade
against either.

*What can.* Two questions about the **machinery**, neither of which needs the
knowledge base to be right:

1. **Does the tool differ from the default at all, and does the difference
   survive its own uncertainty?** A recommendation of *P. pastoris* 0.83 +/- 0.07
   over *E. coli* 0.79 +/- 0.08 has not distinguished them. This counts how often
   the 90% bands actually separate.
2. **When a hard constraint rules *E. coli* out, is it ruled out?** This one is
   categorical rather than score-based: hard constraints demote below every
   feasible host regardless of score, which is engin-host's stated principle.

**Band overlap is deliberately not reported for the hard-constraint case.** When
*E. coli* is infeasible it is demoted on feasibility, not on score, so comparing
bands there would be measuring a quantity the ranking does not use -- a number
that looks like a result and is an artifact.

    python benchmarks/ecoli_baseline.py
"""

from __future__ import annotations

import collections

import numpy as np

from engin_host.kb import CAPABILITIES, default_kb
from engin_host.schema import HostQuery
from engin_host.scoring import score

BASELINE = "E. coli"
N_QUERIES = 2_000
SEED = 0


def sample(n: int, k: int, hard: dict[str, float] | None, seed: int) -> dict[str, float]:
    """Fractions over ``n`` random queries weighting ``k`` capabilities.

    Dirichlet weights over a random subset, because a real query names a handful
    of things that matter rather than scoring all ten. ``k`` is swept for that
    reason: if the result only held at one sparsity it would be an artifact of
    the sampler.
    """
    kb, rng = default_kb(), np.random.default_rng(seed)
    agree = separated = overlap = infeasible = 0
    for _ in range(n):
        caps = rng.choice(CAPABILITIES, size=k, replace=False)
        weights = rng.dirichlet(np.ones(k))
        query = HostQuery(
            weights={c: float(w) for c, w in zip(caps, weights, strict=True)},
            hard=hard or {},
        )
        ranked = score(kb, query, top_k=len(kb.hosts))
        top = ranked[0]
        base = next(h for h in ranked if h.host == BASELINE)
        if not base.feasible:
            infeasible += 1
        if top.host == BASELINE:
            agree += 1
        elif top.score - top.band90 > base.score + base.band90:
            separated += 1
        else:
            overlap += 1
    return {
        "agree": agree / n,
        "separated": separated / n,
        "overlap": overlap / n,
        "infeasible": infeasible / n,
    }


def picks(n: int, k: int, seed: int) -> collections.Counter[str]:
    kb, rng = default_kb(), np.random.default_rng(seed)
    out: collections.Counter[str] = collections.Counter()
    for _ in range(n):
        caps = rng.choice(CAPABILITIES, size=k, replace=False)
        weights = rng.dirichlet(np.ones(k))
        query = HostQuery(weights={c: float(w) for c, w in zip(caps, weights, strict=True)})
        out[score(kb, query, top_k=1)[0].host] += 1
    return out


def main() -> None:
    print(f"=== host selection vs 'just use {BASELINE}' ===")
    print(f"{N_QUERIES:,} random queries per row. The knowledge base is ILLUSTRATIVE (#146),")
    print("so this measures the scoring machinery, not the organisms.\n")

    print("No hard constraints -- does the tool differ, and does the difference hold up?\n")
    print(f"  {'capabilities weighted':<24} {'agrees':>8} {'separated':>11} {'overlaps':>10}")
    for k in (2, 3, 5, 10):
        r = sample(N_QUERIES, k, None, SEED)
        print(f"  {k:<24} {r['agree']:>8.1%} {r['separated']:>11.1%} {r['overlap']:>10.1%}")

    print("\n  'agrees'    -- the tool also picks E. coli, so it added nothing")
    print("  'separated' -- picks another host AND its 90% band clears E. coli's")
    print("  'overlaps'  -- picks another host but cannot distinguish it from E. coli")

    r = sample(N_QUERIES, 3, {"glyco": 0.5}, SEED)
    print("\nWith a hard constraint E. coli fails (glyco >= 0.5), 3 capabilities weighted:")
    print(f"  E. coli flagged infeasible : {r['infeasible']:.0%}")
    print(f"  E. coli ever recommended   : {r['agree']:.0%}")
    print("\n  Categorical, not score-based -- a hard constraint demotes below every")
    print("  feasible host regardless of score. Band overlap is not reported here")
    print("  because the ranking does not use it, so it would be an artifact.")

    print(f"\nWhat it picks, {N_QUERIES:,} queries over 3 capabilities:")
    for host, count in picks(N_QUERIES, 3, SEED).most_common():
        print(f"  {host:<20} {count / N_QUERIES:>6.1%}")


if __name__ == "__main__":
    main()
