"""Tests for the D23 evidence register validator.

Each test constructs a register that *should* fail and asserts it does. A
validator nobody has watched reject anything is a validator nobody has tested,
and this one guards the claim that every public citation resolves somewhere a
reader can go.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml", reason="PyYAML is declared in requirements-docs.txt")

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "evidence" / "render.py"

if not SCRIPT.exists():  # pragma: no cover - the suite also runs from a wheel
    pytest.skip("evidence renderer not present in this checkout", allow_module_level=True)

_spec = importlib.util.spec_from_file_location("evidence_render", SCRIPT)
render_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render_mod)


def source(**overrides):
    base = {
        "id": "2026-someone-thing",
        "title": "A thing",
        "authors": ["Someone"],
        "year": 2026,
        "venue": "Somewhere",
        "location": "https://doi.org/10.0000/x",
        "accessed": "2026-08-11",
        "stability": "doi",
        "type": "paper",
    }
    base.update(overrides)
    return base


def claim(**overrides):
    base = {
        "doc": "docs/benchmarks.md",
        "tier": "A",
        "source_id": "2026-someone-thing",
        "claim": "A specific sentence long enough to be a real claim about something.",
        "strength": "supports",
        "reviewed": "2026-08-11",
    }
    base.update(overrides)
    return base


def test_the_committed_register_is_valid():
    """The register that ships must pass its own rules."""
    assert render_mod.validate(render_mod.load()) == []


def test_committed_view_matches_the_register():
    """docs/references.md is generated; a stale view misreports the citations."""
    assert render_mod.main(["--check"]) == 0


def test_claim_citing_an_unknown_source_is_caught():
    """A citation pointing at nothing is worse than none: it reads as evidence."""
    problems = render_mod.validate({"sources": [source()], "claims": [claim(source_id="nope")]})
    assert any("unknown source id" in p for p in problems)


def test_public_citation_to_a_private_path_is_caught():
    """D23's single hard constraint."""
    problems = render_mod.validate(
        {"sources": [source(location="/Users/someone/obsidian/vaults/notes.md")], "claims": []}
    )
    assert any("private path" in p for p in problems)


def test_tier_a_citing_a_bare_url_is_caught():
    problems = render_mod.validate(
        {
            "sources": [source(stability="url", location="https://example.invalid")],
            "claims": [claim()],
        }
    )
    assert any("url_only_because" in p for p in problems)


def test_a_stated_reason_permits_a_web_only_source():
    """The exception exists, but it has to be said out loud rather than assumed."""
    problems = render_mod.validate(
        {
            "sources": [
                source(
                    stability="url",
                    location="https://example.invalid",
                    url_only_because="Library documentation; there is no paper.",
                )
            ],
            "claims": [claim()],
        }
    )
    assert problems == []


def test_thin_claim_text_is_caught():
    """'Background' is not a claim, and a register full of it evidences nothing."""
    problems = render_mod.validate({"sources": [source()], "claims": [claim(claim="background")]})
    assert any("too thin" in p for p in problems)


def test_bespoke_justified_without_evidence_is_caught():
    """'We looked and there was nothing' is a claim about the field."""
    problems = render_mod.validate(
        {
            "sources": [source()],
            "claims": [],
            "components": [
                {
                    "component": "Something hand-rolled",
                    "package": "engin-core",
                    "stance": "bespoke-justified",
                    "standard_impl": "none exists",
                    "evidence": [],
                }
            ],
        }
    )
    assert any("bespoke-justified with no evidence" in p for p in problems)


def test_duplicate_ids_are_caught():
    problems = render_mod.validate({"sources": [source(), source()], "claims": []})
    assert any("duplicate source id" in p for p in problems)


def test_vault_document_in_the_public_register_is_caught():
    """Tier B/C vault rows belong in sources.vault.yaml, sharing the id namespace."""
    problems = render_mod.validate(
        {"sources": [source()], "claims": [claim(doc="ventures/engin-vision.md")]}
    )
    assert any("belong in sources.vault.yaml" in p for p in problems)


def test_render_marks_contradicting_rows():
    """Those rows are the output the exercise exists to produce."""
    text = render_mod.render(
        {
            "sources": [source()],
            "claims": [claim(strength="contradicts")],
            "components": [],
        }
    )
    assert "**contradicts**" in text


def test_render_reports_how_many_components_are_audited():
    text = render_mod.render(
        {
            "sources": [],
            "claims": [],
            "components": [
                {"component": "a", "package": "p", "stance": "standard", "standard_impl": "x"},
                {"component": "b", "package": "p", "stance": "unaudited", "standard_impl": "?"},
            ],
        }
    )
    assert "1 of 2 audited" in text
