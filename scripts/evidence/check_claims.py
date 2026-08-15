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
#
# **Package READMEs are in scope, and were not until 2026-08-15.** The register
# already held claim rows against `packages/engin-materials/README.md` and
# `packages/engin-host/README.md`, so the register and this check disagreed about
# what Tier A contained -- and this check is the half that fails builds. The cost
# was concrete: two corrections reached the docs site and never reached
# `README.md`, because `docs/` is globbed as a tree while everything else was a
# hand-maintained list nobody extended.
#
# So the non-docs half is globbed too, from the manifest of published root files
# plus every package README. Adding a package no longer means remembering this.
_ROOT_DOCS = (
    "README.md",
    "DECISIONS.md",
    "GOVERNANCE.md",
    "BIOSECURITY.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
    "AGENTS.md",
)

TIER_A = sorted(
    [p for p in (ROOT / "docs").rglob("*.md") if "_build" not in p.parts]
    + [ROOT / n for n in _ROOT_DOCS]
    + list((ROOT / "packages").glob("*/README.md"))
)

FENCE = re.compile(r"^\s*(```|:::)")
INLINE_CODE = re.compile(r"`[^`]*`")
LINK_TARGET = re.compile(r"\]\([^)]*\)")
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
"""An HTML comment, possibly spanning lines.

A number inside a comment is invisible to a reader, so it cannot be an uncited
*published* claim -- and a note explaining why a figure was dropped naturally
quotes the figure. Found immediately: writing such a note made the check flag its
own explanation of a number it had just caused to be removed.

Applied across the whole file rather than per line, because comments span lines
exactly as fences do. Two per-line attempts were wrong before this one: a
`^.*?-->` alternative for closing lines ate the prose in front of an inline
comment, and neither reached the middle line of a multi-line comment.
"""
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
      | \s*(?:g/L|mg/L|g/kg|kg|L/h|USD|\$/kg|x)\b
      | \s*(?:[KMGT]B)\b                # data sizes: a 2.5 GB dataset is a claim
      # `×` carries no trailing \b, and that is not a style choice. U+00D7 is
      # category Sm, not a word character, so `×\b` demands a word character
      # *after* the sign -- which "9× lower" and "**9×**" do not have. The
      # alternative was dead from the day it was written, and it hid the
      # `engin-pathway` README's "roughly 9× lower regret" the whole time.
      # Found by running the check over a file it had never seen, not by reading it.
      | \s*×
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


def blank_comments(lines: list[str]) -> list[str]:
    """``lines`` with comment bodies blanked and the line count preserved.

    Line numbering has to survive so findings still point at the right line, so
    each stripped character becomes a space and each newline stays a newline.
    ``ref:`` and ``not-a-claim`` are read off the *raw* lines before this is
    consulted, so blanking here does not disarm them.
    """
    blanked = HTML_COMMENT.sub(
        lambda m: "".join("\n" if c == "\n" else " " for c in m.group(0)),
        "\n".join(lines),
    )
    return blanked.split("\n")


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
    prose = blank_comments(lines)

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
        # `not-a-claim` clears its own LINE, not the paragraph.
        #
        # It used to clear `block`. The docstring justifies the escape hatch on
        # the grounds that using it is "a visible act in the diff" -- which is
        # true of a line and false of a paragraph: one marker added for one
        # number silently covered every number a later edit put in the same
        # hard-wrapped block. In `docs/limitations.md` two markers were switching
        # off checking for the whole first techno-economic bullet.
        #
        # Footnotes and `ref:` comments stay paragraph-scoped on purpose (see
        # below) -- those *add* evidence, so landing a line away is a formatting
        # accident. This one *removes* checking, so its blast radius should be
        # exactly what the author looked at.
        if in_fence or NOT_A_CLAIM.search(raw):
            continue

        for ref in REF_COMMENT.findall(raw):
            if ref not in known_ids:
                findings.append((n, raw.strip(), f"cites unknown source id {ref!r}"))

        line = strip_noise(prose[n - 1])
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


def _quantities(text: str) -> set[str]:
    """The unit-carrying quantities in a string, normalized for comparison.

    ``"roughly 45-92% of cost"`` -> ``{"45-92%"}``. Whitespace and case are
    folded so ``45 %`` and ``45%`` compare equal.
    """
    return {"".join(m.split()).lower() for m in CLAIMISH.findall(text)}


def _overlaps(line: str, claim: str) -> bool:
    """True when a register row plausibly covers this line.

    Still loose about *wording* -- the register records each claim in its own
    words, so an exact match would never fire -- but no longer loose about
    *which number*.

    It used to clear a line when any digit-string on it appeared anywhere in any
    claim for that document. That is unsound in the direction that matters:
    `docs/benchmarks.md` has rows whose text contains 406, 2, 5 and 1, so a newly
    added and genuinely uncited "2x" or "5%" cleared itself against the NIST
    row's "2^(5-2)". A guard that passes silently is the failure this check
    exists to prevent.

    So the match is on the **unit-carrying quantity** -- the thing CLAIMISH
    flagged -- rather than on any digit inside it. A bare `2` in a claim no
    longer vouches for `2x` on a line; `45-92%` vouches for `45-92%`.
    """
    return bool(_quantities(line) & _quantities(claim))


# Matches `ref: id` whether it sits in a `#` comment or in a docstring. The `#`
# was required until 2026-08-13, and a docstring `ref:` pointing at a source id
# that had never been added sat in gp.py the whole time while this check reported
# every ref resolving. A guard with a blind spot is worse than no guard, because
# its passing is taken as evidence.
CODE_REF = re.compile(r"(?:#\s*(?:.*?;\s*)?|^\s*)ref:\s*([a-z0-9-]+)", re.MULTILINE)


def scan_code(register: dict) -> list[tuple[Path, int, str]]:
    """Every ``ref: id`` in shipped source must resolve to a register row.

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
