"""``engin-host`` — pick a chassis from a project file.

Stage [4] behind a command line, so choosing a host does not require writing Python.
See #141 for why this is `engin-host` rather than `engin host`.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from engin_core.cliutil import base_parser, emit, run_stage
from engin_core.config import ProjectConfig

from .handoff import to_decision
from .kb import default_kb
from .memo import render_memo
from .schema import HostQuery
from .scoring import score

DESCRIPTION = "Rank candidate host organisms for a target, with an honest confidence band."


def _parser() -> argparse.ArgumentParser:
    p = base_parser("engin-host", DESCRIPTION)
    p.add_argument("--top", type=int, default=3, help="how many hosts to show (default: 3)")
    return p


def _body(args: argparse.Namespace, project: ProjectConfig) -> int:
    section = project.host
    assert section is not None  # run_stage checked it

    kb = default_kb()
    unknown = set(section.weights) | set(section.hard)
    unknown -= set(kb.capabilities)
    if unknown:
        print(
            f"engin-host: unknown capabilities {sorted(unknown)}.\n"
            f"Known capabilities are: {', '.join(kb.capabilities)}",
            file=sys.stderr,
        )
        return 2

    scores = score(kb, HostQuery(weights=section.weights, hard=section.hard))
    decision = to_decision(scores, kb=kb)
    shown = scores[: max(args.top, 1)]

    payload = {
        "target": project.target,
        "decision": decision.model_dump(),
        "ranking": [s.model_dump() for s in shown],
        "kb_provenance": "illustrative",  # see #146
    }

    def human() -> None:
        print(render_memo(project.target or "unnamed target", shown))
        print(
            f"\nconfidence: {decision.confidence:.2f}  "
            f"— P({decision.host} really is the best feasible host here)"
        )
        print(
            "\nThe capability knowledge base is illustrative: 54 hand-assigned values\n"
            "with no citations behind them (issue #146). Treat this as a structured\n"
            "way to argue about the choice, not as evidence for it."
        )

    emit(payload, args.json, human)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    return run_stage(argv, _parser(), "host", _body)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
