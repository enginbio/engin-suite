"""Validate the evidence register and render its markdown view. Implements D23.

    python scripts/evidence/render.py           # write docs/references.md
    python scripts/evidence/render.py --check   # CI: fail if the view is stale

``sources.yaml`` is the source of truth; ``docs/references.md`` is generated and
must not be hand-edited. This mirrors how the jupyter-cache is handled: the
generated artefact is committed so readers get it, and a check fails the build
when it drifts from its source.

## What is validated, and why each rule exists

- **Every claim resolves to a known source id.** A citation pointing at nothing
  is worse than no citation, because it reads as evidence.
- **Tier A and B citations must reach ``archived`` or ``doi``.** A bare URL rots,
  and a public document whose evidence has rotted is a document making an
  unfalsifiable claim. Internal documents and things that only exist as web pages
  may use ``url`` — with ``accessed`` filled in.
- **No public citation may resolve to a private path.** This is D23's hard
  constraint. A reader who cannot open the evidence has been shown a gesture at
  evidence. Enforced here rather than left to review.
- **Ids are unique and well-formed**, because the id is what gets written into
  code comments and archive filenames; a duplicate silently redirects a citation.

Rows with ``strength: contradicts`` or ``superseded`` are not failures. They are
the output the exercise exists to produce, and they stay in the register after
the document is corrected, as the record that it was.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
REGISTER = ROOT / "sources.yaml"
VIEW = ROOT / "docs" / "references.md"

STABILITIES = {"archived", "doi", "url", "dead"}
DURABLE = {"archived", "doi"}
TYPES = {
    "paper",
    "preprint",
    "dataset",
    "standard",
    "software",
    "benchmark",
    "interview",
    "web",
    "regulation",
}
STRENGTHS = {"supports", "partially supports", "contested", "contradicts", "superseded"}
STANCES = {"standard", "wrapped", "bespoke-justified", "bespoke-unjustified", "unaudited"}
ID_PATTERN = re.compile(r"^\d{4}-[a-z0-9]+-[a-z0-9-]+$")

# Paths that exist only in the private vault or the private repos. A public
# citation resolving to one of these is D23's single hard failure.
PRIVATE_MARKERS = (
    "/Users/",
    "obsidian/vaults",
    "ventures/",
    "enginbio/ops",
    "engin-wiki",
    "sources.vault.yaml",
)


def load() -> dict:
    return yaml.safe_load(REGISTER.read_text())


def validate(reg: dict) -> list[str]:
    """Return every problem found. Empty means the register is sound."""
    problems: list[str] = []
    sources = reg.get("sources") or []
    claims = reg.get("claims") or []
    components = reg.get("components") or []

    seen: set[str] = set()
    for source in sources:
        sid = source.get("id", "")
        if sid in seen:
            problems.append(
                f"duplicate source id {sid!r} — a duplicate silently redirects a citation"
            )
        seen.add(sid)
        if not ID_PATTERN.match(sid):
            problems.append(f"{sid!r}: id must look like YYYY-firstauthor-shorttitle")
        if source.get("stability") not in STABILITIES:
            problems.append(f"{sid!r}: stability must be one of {sorted(STABILITIES)}")
        if source.get("type") not in TYPES:
            problems.append(f"{sid!r}: type must be one of {sorted(TYPES)}")
        location = str(source.get("location", ""))
        if source.get("stability") == "url" and not source.get("accessed"):
            problems.append(f"{sid!r}: a url source needs `accessed`, because urls rot")
        if any(marker in location for marker in PRIVATE_MARKERS):
            problems.append(
                f"{sid!r}: location {location!r} looks like a private path. A public "
                "citation must never resolve somewhere the reader cannot go (D23)."
            )

    for claim in claims:
        doc = claim.get("doc", "<no doc>")
        sid = claim.get("source_id")
        if sid not in seen:
            problems.append(f"{doc}: claim cites unknown source id {sid!r}")
        if claim.get("strength") not in STRENGTHS:
            problems.append(f"{doc}: strength must be one of {sorted(STRENGTHS)}")
        if claim.get("tier") not in {"A", "B", "C"}:
            problems.append(f"{doc}: tier must be A, B or C")
        text = str(claim.get("claim", "")).strip()
        if len(text) < 20:
            problems.append(
                f"{doc}: claim text is too thin ({text!r}). Record the specific "
                "sentence or number, not 'background'."
            )
        if any(marker in str(doc) for marker in ("ventures/", "obsidian/")):
            problems.append(
                f"{doc}: a Tier A/B row in the *public* register points at a vault "
                "document. Those rows belong in sources.vault.yaml."
            )

    by_id = {s.get("id"): s for s in sources}
    for claim in claims:
        if claim.get("tier") in {"A", "B"}:
            source = by_id.get(claim.get("source_id"))
            if source and source.get("stability") not in DURABLE:
                # The spec allows an exception for things that genuinely only exist
                # as web pages -- library documentation, an organisation's own
                # statement of its rules. It is an exception rather than a loophole,
                # so it has to be *stated* on the source and is rendered as a known
                # weakness of the register rather than passing silently.
                if not str(source.get("url_only_because", "")).strip():
                    problems.append(
                        f"{claim.get('doc')}: tier {claim.get('tier')} cites "
                        f"{claim.get('source_id')!r}, whose stability is "
                        f"{source.get('stability')!r}, with no `url_only_because`. "
                        "Tier A/B evidence must be archived or have a DOI; if this "
                        "genuinely only exists as a web page, say why on the source."
                    )

    for component in components:
        name = component.get("component", "<unnamed>")
        if component.get("stance") not in STANCES:
            problems.append(f"{name!r}: stance must be one of {sorted(STANCES)}")
        for sid in component.get("evidence") or []:
            if sid not in seen:
                problems.append(f"{name!r}: evidence cites unknown source id {sid!r}")
        if component.get("stance") == "bespoke-justified" and not (component.get("evidence")):
            problems.append(
                f"{name!r}: stance is bespoke-justified with no evidence. "
                "'We looked and there was nothing' is a claim about the field and "
                "needs a citation like any other."
            )
    return problems


def render(reg: dict) -> str:
    sources = sorted(reg.get("sources") or [], key=lambda s: s.get("id", ""))
    claims = reg.get("claims") or []
    components = reg.get("components") or []

    out: list[str] = [
        "# References",
        "",
        "```{note}",
        "Generated from `sources.yaml` by `scripts/evidence/render.py`. Do not edit",
        "by hand — CI fails when this file drifts from the register (`D23`).",
        "```",
        "",
        "Every substantive claim in a public document should resolve to a row here.",
        "Where the evidence *contradicts* or *supersedes* what a document said, the row",
        "stays after the document is corrected — that record is the point of keeping a",
        "register rather than a bibliography.",
        "",
        "## Works cited",
        "",
        "| id | work | year | type | stability |",
        "|---|---|---|---|---|",
    ]
    for s in sources:
        authors = ", ".join(s.get("authors") or []) or "—"
        link = f"[{s.get('title', '').strip()}]({s.get('location')})"
        out.append(
            f"| `{s['id']}` | {link}<br/>{authors} — *{s.get('venue', '')}* "
            f"| {s.get('year', '')} | {s.get('type', '')} | {s.get('stability', '')} |"
        )

    out += ["", "## Claims", "", "| document | claim | source | strength |", "|---|---|---|---|"]
    for c in sorted(claims, key=lambda c: (str(c.get("doc")), str(c.get("source_id")))):
        strength = str(c.get("strength", ""))
        marked = f"**{strength}**" if strength in {"contradicts", "superseded"} else strength
        claim_text = " ".join(str(c.get("claim", "")).split())
        out.append(f"| `{c.get('doc')}` | {claim_text} | `{c.get('source_id')}` | {marked} |")

    audited = [c for c in components if c.get("stance") != "unaudited"]
    out += [
        "",
        "## Components",
        "",
        f"**{len(audited)} of {len(components)} audited.** `unaudited` is the honest",
        "default, not an oversight — reducing it is the programme this register exists",
        "to serve.",
        "",
        "| component | package | stance | standard implementation | evidence |",
        "|---|---|---|---|---|",
    ]
    for comp in components:
        ev = ", ".join(f"`{e}`" for e in (comp.get("evidence") or [])) or "—"
        stance = str(comp.get("stance"))
        marked = f"**{stance}**" if stance in {"bespoke-unjustified", "unaudited"} else stance
        out.append(
            f"| {comp.get('component')} | `{comp.get('package')}` | {marked} "
            f"| {comp.get('standard_impl')} | {ev} |"
        )

    cited_by_public = {c.get("source_id") for c in claims if c.get("tier") in {"A", "B"}}
    unresolved = [s for s in sources if s.get("stability") == "url" and s["id"] in cited_by_public]
    if unresolved:
        out += [
            "",
            "## Known weaknesses in this register",
            "",
            "These are cited by a public document but exist only as web pages, so the",
            "evidence can change or vanish without notice. Each says why no durable",
            "copy was used; `accessed` records when it was last read.",
            "",
        ]
        for s in unresolved:
            why = " ".join(str(s.get("url_only_because", "")).split())
            out.append(f"- **`{s['id']}`** (accessed {s.get('accessed')}) — {why}")

    out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the view is stale")
    args = parser.parse_args(argv)

    reg = load()
    problems = validate(reg)
    if problems:
        print(f"evidence register: {len(problems)} problem(s)", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    rendered = render(reg)
    if args.check:
        current = VIEW.read_text() if VIEW.exists() else ""
        if current != rendered:
            print(
                "docs/references.md is stale. Regenerate it and commit:\n"
                "  python scripts/evidence/render.py",
                file=sys.stderr,
            )
            return 1
        print(f"evidence register: valid, view current ({len(reg.get('sources') or [])} sources)")
        return 0

    VIEW.write_text(rendered)
    print(f"wrote {VIEW.relative_to(ROOT)} ({len(reg.get('sources') or [])} sources)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
