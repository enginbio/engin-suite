"""Shared plumbing for the per-stage command-line entry points.

Each stage ships its own console script from the distribution that implements it
(`engin-host`, `engin-pathway`, `engin-process`) rather than one `engin` binary with
subcommands. Two reasons, recorded in #141: nothing depends on both stage packages so
no package could host a unified entry point, and the `engin` script name is already
taken on PyPI by a maintained dependency-injection framework that registers
``engin = "engin._cli:app"`` — installing both would silently overwrite one.

What is shared is the argument surface, so the three feel like one tool: the same
``--config``, ``--init`` and ``--json`` mean the same things everywhere.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from .config import ProjectConfig, load_project, starter_yaml

__all__ = ["base_parser", "run_stage", "emit", "rule"]

_EPILOG = """\
Every stage reads the same project.yaml. Start one with --init, edit it, then run
whichever stages you have filled in. Numbers are illustrative until validated:
https://docs.engin.bio/en/latest/limitations.html
"""


def base_parser(prog: str, description: str) -> argparse.ArgumentParser:
    """The argument surface every stage shares."""
    p = argparse.ArgumentParser(
        prog=prog,
        description=description,
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("-c", "--config", metavar="FILE", help="project file to read")
    p.add_argument(
        "--init",
        metavar="FILE",
        nargs="?",
        const="project.yaml",
        help="write a commented starter project file and exit (default: project.yaml)",
    )
    p.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    return p


def rule(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def emit(payload: dict[str, Any], as_json: bool, human: Callable[[], None]) -> None:
    """Print ``payload`` as JSON, or call ``human`` to print for a person."""
    if as_json:
        print(json.dumps(payload, indent=2, default=str))
    else:
        human()


def _write_starter(path: str) -> int:
    dest = Path(path)
    if dest.exists():
        print(f"{dest} already exists; not overwriting it.", file=sys.stderr)
        return 1
    dest.write_text(starter_yaml())
    print(f"Wrote {dest}\n\nEdit it, then run this command again with --config {dest}")
    return 0


def run_stage(
    argv: Sequence[str] | None,
    parser: argparse.ArgumentParser,
    section: str,
    body: Callable[[argparse.Namespace, ProjectConfig], int],
) -> int:
    """Parse args, handle ``--init``, load and check the config, then call ``body``.

    Returns a process exit status. Failures are reported as a sentence on stderr
    rather than a traceback: the reader this exists for did not ask for a stack.
    """
    args = parser.parse_args(argv)

    if args.init:
        return _write_starter(args.init)

    if not args.config:
        parser.print_usage(sys.stderr)
        print(
            f"\n{parser.prog}: need a project file. Start one with:\n    {parser.prog} --init",
            file=sys.stderr,
        )
        return 2

    try:
        project = load_project(args.config)
    except (FileNotFoundError, ValueError, ModuleNotFoundError) as exc:
        print(f"{parser.prog}: {exc}", file=sys.stderr)
        return 2

    if getattr(project, section, None) is None:
        print(
            f"{parser.prog}: {args.config} has no '{section}:' section, so there is "
            f"nothing for this stage to do.\n"
            f"Add one — `{parser.prog} --init` writes a commented example.",
            file=sys.stderr,
        )
        return 2

    return body(args, project)
