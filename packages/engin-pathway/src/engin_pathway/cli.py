"""``engin-pathway`` — rank candidate routes from a project file.

Stage [3] behind a command line. See #141 for why this is `engin-pathway` rather than
`engin pathway`.

The awkward part, surfaced rather than hidden: ranking needs a *trained* model, and a
user's candidate routes are by definition unlabelled. If the project file supplies
enough measured routes the model trains on those; otherwise it trains on this package's
own synthetic generator and says so, loudly, every run. That fallback is a real
limitation (#124, #140), not a detail.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from engin_core.cliutil import base_parser, emit, run_stage
from engin_core.config import ProjectConfig, RouteSpec
from pydantic import ValidationError

from .handoff import to_ranking
from .rank import PathwayRanker
from .schema import FEATURES, Route, Step
from .simulate import make_dataset

DESCRIPTION = "Rank candidate biosynthetic routes by manufacturability, with an interval."

#: Below this many measured routes there is not enough to both fit and calibrate on,
#: so the synthetic generator is used instead and the output says so.
MIN_LABELLED = 40


def _to_routes(specs: list[RouteSpec]) -> list[Route]:
    routes = []
    for spec in specs:
        try:
            steps = [Step(features=s) for s in spec.steps]
        except ValidationError as exc:
            raise ValueError(
                f"route {spec.id!r}: {exc.errors()[0]['msg']}\n"
                f"Each step needs exactly these five keys: {', '.join(FEATURES)}"
            ) from exc
        routes.append(
            Route(route_id=spec.id, steps=steps, manufacturability=spec.manufacturability)
        )
    return routes


def _parser() -> argparse.ArgumentParser:
    p = base_parser("engin-pathway", DESCRIPTION)
    p.add_argument("--seed", type=int, default=0, help="makes a run reproducible (default: 0)")
    return p


def _body(args: argparse.Namespace, project: ProjectConfig) -> int:
    section = project.pathway
    assert section is not None  # run_stage checked it

    try:
        routes = _to_routes(section.routes)
    except ValueError as exc:
        print(f"engin-pathway: {exc}", file=sys.stderr)
        return 2

    labelled = [r for r in routes if r.manufacturability is not None]
    trained_on_synthetic = len(labelled) < MIN_LABELLED

    ranker = PathwayRanker(embed_seed=args.seed)
    if trained_on_synthetic:
        corpus = make_dataset(n=160, seed=args.seed)
        ranker.fit(corpus[:100]).calibrate(corpus[100:140])
    else:
        cut = int(len(labelled) * 0.7)
        ranker.fit(labelled[:cut]).calibrate(labelled[cut:])

    ranking = to_ranking(ranker, routes)
    ordered = sorted(ranking.routes, key=lambda r: -r.manufacturability)

    payload = {
        "target": project.target,
        "ranking": [r.model_dump() for r in ordered],
        "trained_on": "synthetic generator" if trained_on_synthetic else "supplied labels",
        "n_labelled_supplied": len(labelled),
    }

    def human() -> None:
        if project.target:
            print(f"target: {project.target}")
        print(f"\n{'rank':>4}  {'route':<24} {'manufacturability':>18}  90% interval")
        for i, r in enumerate(ordered, 1):
            print(
                f"{i:>4}  {r.route_id:<24} {r.manufacturability:>18.3f}  [{r.lo:.3f}, {r.hi:.3f}]"
            )

        best, worst = ordered[0], ordered[-1]
        if len(ordered) > 1 and best.lo <= worst.hi:
            print(
                f"\nThe intervals for {best.route_id} and {worst.route_id} overlap, so this\n"
                "ranking does not separate them. Treat the order as a shortlist, not a winner."
            )

        if trained_on_synthetic:
            print(
                f"\n  !! The model was trained on this package's own synthetic route\n"
                f"     generator, not on real routes — you supplied {len(labelled)} measured\n"
                f"     route(s) and {MIN_LABELLED} are needed to train on your own data.\n"
                f"     Its published margin over step-count may be an artifact of that\n"
                f"     generator (issue #124). The step features you entered are also your\n"
                f"     own judgement: nothing computes them from structure yet (issue #140).\n"
                f"     This orders your routes by a model of a different world. Read it as\n"
                f"     a prompt for discussion, not as a measurement."
            )

    emit(payload, args.json, human)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return run_stage(argv, _parser(), "pathway", _body)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
