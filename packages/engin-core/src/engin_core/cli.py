"""``engin-process`` — plan the next batch from a project file.

Stage [1] behind a command line. See #141 for why this is `engin-process` rather than
`engin process`; the script ships from `engin-core`, which implements this stage.

Optimizes **net cost per kilogram, not titer** (`D13`). That is a deliberate choice
and it makes the recommendations look worse on the metric most teams report, which is
why the output says which objective it used.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

import numpy as np

from .cliutil import base_parser, emit, run_stage
from .config import ProjectConfig
from .gp import fit_gp
from .recommend import recommend_batch
from .simulator import KNOB_NAMES, simulate_unit, unit_to_physical
from .tea import ParametricCostModel, cost_summary, recommend_batch_by_cost

DESCRIPTION = "Recommend the next batch of runs, by expected cost reduction (D13)."


def _parser() -> argparse.ArgumentParser:
    p = base_parser("engin-process", DESCRIPTION)
    p.add_argument(
        "--titer",
        action="store_true",
        help="optimize titer instead of net cost -- D13's comparison baseline",
    )
    return p


def _body(args: argparse.Namespace, project: ProjectConfig) -> int:
    section = project.process
    assert section is not None  # run_stage checked it

    reactor, costs = section.reactor, section.cost
    rng = np.random.default_rng(section.seed)

    # No run history is read yet: the runs are simulated from the configured vessel.
    # That is the honest limit of this stage today -- see the closing note.
    U = rng.random((section.n_runs, len(KNOB_NAMES)))
    y_true = simulate_unit(U, config=reactor)
    y = np.maximum(y_true + rng.normal(0, 0.05 * y_true + 0.4), 0.0)

    gp = fit_gp(U, y, seed=section.seed)
    model = ParametricCostModel(params=costs, config=reactor)

    summaries = cost_summary(gp, U, model=model, params=costs)
    best = min(s.expected_usd_per_kg for s in summaries)
    cheapest = summaries[int(np.argmin([s.expected_usd_per_kg for s in summaries]))]

    if args.titer:
        # D13's comparison baseline, kept so the trade is checkable rather than asserted.
        batch, _mean, _sd, gain = recommend_batch(
            gp, best_y=float(np.max(y)), k=section.batch_size, seed=section.seed
        )
        objective_label = "expected improvement in titer"
        gain_label, gain_fmt = "E[gain]", lambda g: f"{g:,.2f} g/L"
        gain_key = "expected_improvement_g_L"
    else:
        batch, gain = recommend_batch_by_cost(
            gp, best_cost=best, k=section.batch_size, seed=section.seed, model=model
        )
        objective_label = "expected cost reduction"
        gain_label, gain_fmt = "E[saving]", lambda g: f"${g:,.0f}/kg"
        gain_key = "expected_cost_reduction_usd_per_kg"

    phys = unit_to_physical(batch, reactor)

    payload = {
        "target": project.target,
        "objective": "titer_g_L" if args.titer else "net_usd_per_kg",
        "best_known": cheapest.model_dump(),
        "recommended": [
            {
                gain_key: float(g),
                **{n: float(v) for n, v in zip(KNOB_NAMES, row, strict=True)},
            }
            for row, g in zip(phys, gain, strict=True)
        ],
        "reactor": reactor.model_dump(),
    }

    def human() -> None:
        if project.target:
            print(f"target: {project.target}")
        print(
            f"vessel: {reactor.v0:g} L -> {reactor.vmax:g} L over {reactor.t_end:g} h"
            f"   ({section.n_runs} simulated runs)"
        )
        print(
            f"\nbest cost so far : ${cheapest.expected_usd_per_kg:,.0f}/kg  "
            f"[${cheapest.lower_usd_per_kg:,.0f}, ${cheapest.upper_usd_per_kg:,.0f}] (90%)"
        )
        print(
            f"clears ${costs.target_usd_per_kg:,.0f}/kg target with probability "
            f"{cheapest.prob_meets_target:.2f}"
        )

        print(f"\nnext {len(phys)} runs, by {objective_label}:")
        for i, (row, g) in enumerate(zip(phys, gain, strict=True), 1):
            knobs = "  ".join(f"{n}={v:.3g}" for n, v in zip(KNOB_NAMES, row, strict=True))
            print(f"  {i}. {gain_label}={gain_fmt(g)}   {knobs}")

        if args.titer:
            print(
                "\nThis ran D13's *baseline* objective, titer, which the project keeps only\n"
                "for comparison. Titer is inflatable by running longer and says nothing\n"
                "about the substrate cost that yield governs. Drop --titer for the\n"
                "objective this tool actually argues for."
            )
        else:
            print(
                "\nOptimizes net $/kg rather than titer (D13), so it will look worse than a\n"
                "titer-chasing tool on the number most teams report — that is the intended\n"
                "trade, and --titer runs the comparison."
            )
        print(
            "\nIt cannot read your actual run history yet: the runs above were simulated\n"
            "from the vessel in your project file, so this is only as good as that model."
        )

    emit(payload, args.json, human)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return run_stage(argv, _parser(), "process", _body)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
