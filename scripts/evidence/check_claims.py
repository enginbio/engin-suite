"""Fail the build on an uncited claim about the world. Implements D23.

    python scripts/evidence/check_claims.py            # fail on findings
    python scripts/evidence/check_claims.py --report   # list them, exit 0

**The register rests on this.** Under a solo maintainer (`D18`) a review cadence
decays and a failing check does not. Without it, D23 is a more ceremonious
hand-maintained table: same decay, more overhead.

## The hard part is deciding what counts

A number is not automatically a claim. Version numbers, counts of things in this
repository, and figures inside a worked example are facts about *us*, checkable
by looking. "Media is roughly 35-50% of precision-fermentation cost of goods" is
a claim about the world, and it needs a source.

Too strict and the check gets switched off, which is worse than never having it.
So the rule is deliberately narrow, tuned against the real corpus rather than
guessed, and it errs toward silence:

1. Only prose is scanned. Fenced code, inline code, tables of generated output,
   link targets and image sizes are skipped.
2. A number is a candidate only if it carries a **unit or a magnitude word** --
   ``%``, ``g/L``, ``x``, ``million`` -- or sits in a range like ``35-50%``.
   A bare integer is almost always a count of ours.
3. Candidates are cleared by any of: a ``[^source-id]`` footnote on the line, a
   ``<!-- ref: id -->`` comment, a matching row in ``sources.yaml`` for that
   document, or an explicit ``<!-- not-a-claim -->``.

The escape hatch exists because the alternative is a disabled check. Using it is
a visible act in the diff, which is the point: an unevidenced claim should cost a
sentence of justification, not be impossible.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTER = ROOT / "sources.yaml"

# Tier A: what a stranger reads. The vault is Tier B/C and is checked separately.
TIER_A = sorted(
    [p for p in (ROOT / "docs").rglob("*.md") if "_build" not in p.parts]
    + [ROOT / n for n in ("README.md", "DECISIONS.md", "GOVERNANCE.md", "BIOSECURITY.md")]
)

FENCE = re.compile(r"^\s*(```|:::)")
INLINE_CODE = re.compile(r"`[^`]*`")
LINK_TARGET = re.compile(r"\]\([^)]*\)")
FOOTNOTE = re.compile(r"\[\^[a-z0-9-]+\]")
REF_COMMENT = re.compile(r"<!--\s*ref:\s*([a-z0-9-]+)\s*-->")
NOT_A_CLAIM = re.compile(r"<!--\s*not-a-claim\b[^>]*-->")

# A number that carries a unit or magnitude, or a range. Bare integers are
# excluded on purpose -- they are nearly always counts of our own things.
CLAIMISH = re.compile(
    r"""
    (?<![\w.])                       # not mid-identifier
    \d[\d,]*(?:\.\d+)?               # the number
    \s*
    (?:
        -\s*\d[\d,]*(?:\.\d+)?\s*%   # a range like 35-50%
      | %                            # percentage
      | \s*(?:g/L|mg/L|g/kg|kg|L/h|USD|\$/kg|x|×)\b
      | \s*(?:million|billion|thousand|orders\ of\ magnitude)\b
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Things that look claim-shaped and are not.
EXEMPT = (
    re.compile(r"\bpython[_\s-]?version\b", re.I),
    re.compile(r"\b\d+\.\d+(\.\d+)?\b(?=\s*(or later|\+))", re.I),  # 3.10 or later
    re.compile(r"^\s*\|"),  # table rows of our own generated results
    # A nominal level is a parameter of our own method, not a claim about the
    # world: "a 90% interval" says what we asked for, not what anyone found.
    re.compile(r"\d+\s*%\s*(interval|coverage|level|nominal|confidence|credible)", re.I),
    re.compile(r"(nominal|target|level)\s*(of\s*)?\d+\s*%", re.I),
)


def load_register() -> dict:
    return yaml.safe_load(REGISTER.read_text()) if REGISTER.exists() else {}


def strip_noise(line: str) -> str:
    return LINK_TARGET.sub("]", INLINE_CODE.sub("`code`", line))


def scan(path: Path, register: dict) -> list[tuple[int, str, str]]:
    """Return (line number, line, reason) for every uncited candidate claim."""
    known_ids = {s.get("id") for s in register.get("sources") or []}
    doc_rel = str(path.relative_to(ROOT))
    documented = {
        " ".join(str(c.get("claim", "")).split())
        for c in register.get("claims") or []
        if c.get("doc") == doc_rel
    }

    lines = path.read_text().splitlines()

    # Citations clear a *paragraph*, not a line. Prose here is hard-wrapped, so a
    # footnote naturally lands a line or two away from the number it supports;
    # requiring them on the same line would push authors to write worse markdown
    # to satisfy a checker.
    para_of: dict[int, int] = {}
    para_text: dict[int, str] = {}
    para, fenced = 0, False
    for i, raw in enumerate(lines):
        if FENCE.match(raw):
            fenced = not fenced
        if not raw.strip():
            para += 1
            continue
        para_of[i] = para
        para_text[para] = para_text.get(para, "") + " " + raw

    findings: list[tuple[int, str, str]] = []
    in_fence = False
    for n, raw in enumerate(lines, start=1):
        if FENCE.match(raw):
            in_fence = not in_fence
            continue
        block = para_text.get(para_of.get(n - 1, -1), "")
        if in_fence or NOT_A_CLAIM.search(block):
            continue

        for ref in REF_COMMENT.findall(raw):
            if ref not in known_ids:
                findings.append((n, raw.strip(), f"cites unknown source id {ref!r}"))

        line = strip_noise(raw)
        if any(rx.search(line) for rx in EXEMPT):
            continue
        matches = CLAIMISH.findall(line) or CLAIMISH.search(line)
        if not matches:
            continue
        if FOOTNOTE.search(block) or REF_COMMENT.search(block):
            continue
        # A register row whose claim text overlaps this line counts as cited.
        stripped = " ".join(line.split())
        if any(_overlaps(stripped, claim) for claim in documented):
            continue
        findings.append((n, raw.strip()[:110], "numeric claim with no source"))
    return findings


def _overlaps(line: str, claim: str) -> bool:
    """True when a register row plausibly covers this line.

    Deliberately loose: the register records the claim in its own words, so an
    exact match would never fire. Shared distinctive numbers are the signal.
    """
    line_nums = set(re.findall(r"\d[\d,]*(?:\.\d+)?", line))
    claim_nums = set(re.findall(r"\d[\d,]*(?:\.\d+)?", claim))
    return bool(line_nums & claim_nums)


CODE_REF = re.compile(r"#\s*(?:.*?;\s*)?ref:\s*([a-z0-9-]+)")


def scan_code(register: dict) -> list[tuple[Path, int, str]]:
    """Every ``# ref: id`` in shipped source must resolve to a register row.

    A code comment claiming evidence that is not in the register is the same
    failure as an uncited number, one layer down: it looks like provenance and
    resolves to nothing.
    """
    known = {s.get("id") for s in register.get("sources") or []}
    bad: list[tuple[Path, int, str]] = []
    # Shipped source only. Test files legitimately contain `ref:` strings as
    # fixtures for this very check, and scanning them makes the checker fail on
    # its own test suite.
    for path in sorted((ROOT / "packages").glob("*/src/**/*.py")):
        if any(part in {".venv", "_build"} for part in path.parts):
            continue
        for n, line in enumerate(path.read_text().splitlines(), start=1):
            for ref in CODE_REF.findall(line):
                if ref not in known:
                    bad.append((path, n, ref))
    return bad


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true", help="list findings, exit 0")
    args = parser.parse_args(argv)

    register = load_register()
    total = 0
    for path in TIER_A:
        if not path.exists():
            continue
        findings = scan(path, register)
        if not findings:
            continue
        total += len(findings)
        print(f"\n{path.relative_to(ROOT)}")
        for n, line, reason in findings:
            print(f"  {n:>4}  {reason}")
            print(f"        {line}")

    for path, n, ref in scan_code(register):
        total += 1
        print(f"\n{path.relative_to(ROOT)}")
        print(f"  {n:>4}  code cites unknown source id {ref!r}")

    if not total:
        print(
            f"no uncited claims across {len(TIER_A)} Tier A documents, "
            "and every code `ref:` resolves"
        )
        return 0

    print(f"\n{total} uncited claim(s) across Tier A documents.")
    print(
        "Each needs one of: a [^source-id] footnote, a <!-- ref: id --> comment, a row\n"
        "in sources.yaml for this document, or <!-- not-a-claim --> if it is a fact\n"
        "about this repository rather than about the world."
    )
    return 0 if args.report else 1


if __name__ == "__main__":
    raise SystemExit(main())
