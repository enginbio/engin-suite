"""Fail the build when a retracted claim is still published somewhere else.

    python scripts/evidence/check_corrections.py             # fail on findings
    python scripts/evidence/check_corrections.py --report    # list them, exit 0
    python scripts/evidence/check_corrections.py --vault PATH # also check the vault mirror

## Why this exists

Three times in one week a correction landed in a canonical document and did not
reach the documents repeating it:

1. `D13`'s "recovery cost is determined upstream but incurred downstream"
   justification was withdrawn 2026-08-10. On 2026-08-13 it was still in
   `README.md`, on the docs front page, and in `docs/guides/cost.md` -- which
   cited `D13` as its authority for a claim `D13` had retracted.
2. The "media is 35-50% of precision-fermentation COGS" figure was dropped from
   the repo 2026-08-11 and survived two more days in the vault mirror.
3. `standard_impl: none exists` for the data convention, while the vault's `D11`
   already named MIFE/MIFD and resolved to adopt them.

All three were found by accident, while looking for something else. **The failure
is never the original error. It is that fixing one document gets taken for fixing
the claim**, and nothing was watching the difference.

`DECISIONS.md` says it in the imperative already: "When a justification is
withdrawn here, grep the tree for it -- the phrase, not the decision id, because
the documents that repeat it rarely quote the id." This is that instruction, run
by CI instead of by memory.

## How it works

A correction notice in `DECISIONS.md` quotes the text it is retracting -- that is
already the house style, because corrections stay in the record rather than being
deleted. So the retracted phrasing is machine-readable: find the notices, take
their quoted spans, and fail if any span appears anywhere else in Tier A.

Matching is on a normalized core rather than the exact string, since the same
sentence acquires different quote marks, dashes and line wrapping as it moves
between documents -- which is precisely how these survive a naive grep.

**The vault is optional and off by default.** It is not in this repository, so CI
cannot see it; pass `--vault` locally to check the mirror too. That asymmetry is
the reason the vault drift lasted two days.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DECISIONS = ROOT / "DECISIONS.md"

# Where a retracted claim would do damage if it resurfaced: what a stranger reads.
TIER_A = sorted(
    [p for p in (ROOT / "docs").rglob("*.md") if "_build" not in p.parts]
    + [
        ROOT / n
        for n in ("README.md", "DECISIONS.md", "GOVERNANCE.md", "BIOSECURITY.md", "CONTRIBUTING.md")
    ]
)

# A correction notice. The house style marks these explicitly so they survive as
# record; that is what makes them extractable.
NOTICE = re.compile(
    r"(?:\*\*)?(?:Corrected|Withdrawn|Superseded|Amended|Retracted)\b", re.IGNORECASE
)

# Wider vocabulary for deciding whether a *reappearance* is a quotation rather
# than a republication. Auditing prose and post-mortems discuss retracted claims
# at length without opening the paragraph with the word "Corrected".
# Deliberately *meta* vocabulary only. An earlier version included "backwards"
# and "was wrong" -- words that appear in the retracted claims themselves, so a
# planted claim suppressed its own detection and the check passed. Every term
# here must be about the act of correcting, never about the subject matter.
DISCUSSING = re.compile(
    r"\b(corrected|withdraw\w*|retract\w*|supersed\w*|amended|previously read|previously said|"
    r"used to (?:read|say)|this bullet|this page|this section|this decision|earlier draft|"
    r"first draft|no longer says|kept because)\b",
    re.IGNORECASE,
)

# How far either side of a hit to look for that vocabulary.
CONTEXT_CHARS = 500

# Explicit opt-out, for a document that quotes a retraction deliberately and whose
# surrounding prose does not happen to use the vocabulary above -- an audit
# write-up under a "What we assert" heading, say. Same design as
# `not-a-claim` in check_claims.py: visible in the diff, costs a sentence of
# justification, and is far better than a checker people switch off.
QUOTES_RETRACTED = re.compile(r"<!--\s*quotes-retracted\b[^>]*-->")

# Files whose job is to hold retracted text. Excluding them is not a loophole:
# a register that could not quote a withdrawn claim could not record it.
EXEMPT_NAMES = {
    "references.md",  # generated register view; `contested` rows quote the claim
    "log.md",  # append-only history
    "CHANGES.md",  # editorial commentary on past expansions
}

# Quoted spans inside a notice: straight, curly, or italicized-quoted.
QUOTED = re.compile(r"[\"“]([^\"“”]{40,})[\"”]")

# How much of a quoted span must reappear before it counts. Long enough that
# ordinary shared phrasing does not trip it, short enough to survive rewrapping
# and light editing of the tail.
CORE_CHARS = 70


def normalize(text: str) -> str:
    """Collapse the differences a sentence picks up as it moves between documents."""
    text = unicodedata.normalize("NFKD", text)
    # Typographic punctuation varies by document and by editor.
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"')):
        text = text.replace(a, b)
    text = re.sub(r"[‐-―]", "-", text)  # dash family
    text = re.sub(r"[*_`]", "", text)  # markdown emphasis
    return re.sub(r"\s+", " ", text).strip().lower()


def retracted_phrases(decisions: str) -> list[str]:
    """Normalized cores of every claim `DECISIONS.md` says it has retracted."""
    cores: list[str] = []
    for para in re.split(r"\n\s*\n", decisions):
        if not NOTICE.search(para):
            continue
        for quoted in QUOTED.findall(para):
            core = normalize(quoted)[:CORE_CHARS]
            if len(core) >= CORE_CHARS:
                cores.append(core)
    return cores


def scan(paths: list[Path], cores: list[str]) -> list[tuple[Path, str]]:
    """Files republishing a retracted phrase, outside its own correction notice."""
    found: list[tuple[Path, str]] = []
    for path in paths:
        if not path.is_file() or path.name in EXEMPT_NAMES:
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        if QUOTES_RETRACTED.search(raw):
            continue
        flat = normalize(raw)
        for core in cores:
            start = flat.find(core)
            if start == -1:
                continue
            # Quoting a retraction is the point of keeping corrections in the
            # record. Republishing it as live prose is the failure. The
            # difference is whether the surrounding text is discussing it.
            # Look *around* the match, never inside it: a retracted claim must
            # not be able to vouch for itself. That bug shipped in the first
            # draft of this file and a planted claim went undetected.
            before = flat[max(0, start - CONTEXT_CHARS) : start]
            after = flat[start + len(core) : start + len(core) + CONTEXT_CHARS]
            if not (DISCUSSING.search(before) or DISCUSSING.search(after)):
                found.append((path, core))
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", action="store_true", help="list findings, exit 0")
    parser.add_argument(
        "--vault",
        type=Path,
        default=None,
        help="also scan a vault directory (not visible to CI; run locally)",
    )
    args = parser.parse_args(argv)

    if not DECISIONS.is_file():
        print("DECISIONS.md not found", file=sys.stderr)
        return 1

    cores = retracted_phrases(DECISIONS.read_text(encoding="utf-8"))
    if not cores:
        print("no retracted claims recorded in DECISIONS.md — nothing to check")
        return 0

    targets = list(TIER_A)
    if args.vault:
        targets += sorted(p for p in args.vault.rglob("*.md") if ".git" not in p.parts)

    findings = scan(targets, cores)
    scope = f"{len(targets)} documents" + (" (including the vault)" if args.vault else "")
    if not findings:
        print(f"no retracted claim is still published across {scope}")
        return 0

    print()
    for path, core in findings:
        try:
            shown = path.relative_to(ROOT)
        except ValueError:
            shown = path
        print(f'{shown}\n    still publishes a claim DECISIONS.md retracted:\n    "{core}..."\n')
    print(f"{len(findings)} retracted claim(s) still published.")
    print("Fix the document, or — if the text legitimately quotes the retraction —")
    print("mark that paragraph as a correction notice so it is recognised as one.")
    if not args.vault:
        print("\nNote: the vault was not scanned. Run with --vault <path> to include it.")
    return 0 if args.report else 1


if __name__ == "__main__":
    raise SystemExit(main())
