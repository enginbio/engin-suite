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

CHECKER = REPO / "scripts" / "evidence" / "check_claims.py"
_cspec = importlib.util.spec_from_file_location("evidence_check", CHECKER)
check_mod = importlib.util.module_from_spec(_cspec)
_cspec.loader.exec_module(check_mod)


def scan_text(tmp_path, text, register=None):
    doc = tmp_path / "doc.md"
    doc.write_text(text)
    return check_mod.scan(doc, register or {})


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


# ------------------------------------------------- the uncited-claim gate (#80)


def test_the_corpus_currently_passes():
    """Tier A is clean. If this fails, a claim was added without evidence."""
    assert check_mod.main([]) == 0


def test_a_claim_about_the_world_is_caught(tmp_path, monkeypatch):
    monkeypatch.setattr(check_mod, "ROOT", tmp_path)
    findings = scan_text(tmp_path, "Media is roughly 35-50% of fermentation COGS.")
    assert findings and "no source" in findings[0][2]


def test_a_bare_count_is_not_a_claim(tmp_path, monkeypatch):
    """Counts of our own things are checkable by looking, not by citing."""
    monkeypatch.setattr(check_mod, "ROOT", tmp_path)
    assert scan_text(tmp_path, "The suite has 237 tests across six packages.") == []


def test_a_nominal_level_is_not_a_claim(tmp_path, monkeypatch):
    """'a 90% interval' says what we asked for, not what anyone measured."""
    monkeypatch.setattr(check_mod, "ROOT", tmp_path)
    assert scan_text(tmp_path, "The interval keeps reporting 90% coverage either way.") == []


def test_code_blocks_are_not_scanned(tmp_path, monkeypatch):
    monkeypatch.setattr(check_mod, "ROOT", tmp_path)
    assert scan_text(tmp_path, "```\nshare = 0.42  # 42% of cost\n```") == []


def test_a_footnote_anywhere_in_the_paragraph_clears_it(tmp_path, monkeypatch):
    """Prose is hard-wrapped; demanding same-line citation would make it worse."""
    monkeypatch.setattr(check_mod, "ROOT", tmp_path)
    text = "Media is roughly 35-50% of fermentation COGS,\nwhich is a lot [^2024-someone-thing]."
    assert scan_text(tmp_path, text) == []


def test_the_escape_hatch_works_and_carries_a_reason(tmp_path, monkeypatch):
    monkeypatch.setattr(check_mod, "ROOT", tmp_path)
    text = "Raw material lands at 2% here. <!-- not-a-claim: measured on our simulator -->"
    assert scan_text(tmp_path, text) == []


def test_a_ref_to_an_unknown_source_is_caught(tmp_path, monkeypatch):
    monkeypatch.setattr(check_mod, "ROOT", tmp_path)
    findings = scan_text(
        tmp_path,
        "Something costly. <!-- ref: 1999-nobody-nothing -->",
        {"sources": [{"id": "2024-someone-thing"}]},
    )
    assert any("unknown source id" in f[2] for f in findings)


def test_code_refs_must_resolve(tmp_path, monkeypatch):
    """A `# ref:` naming a source that is not registered looks like provenance
    and resolves to nothing — the same failure as an uncited number, one layer
    down."""
    pkg = tmp_path / "packages" / "p" / "src" / "p"
    pkg.mkdir(parents=True)
    (pkg / "m.py").write_text("# implements D13; ref: 1999-nobody-nothing\n")
    monkeypatch.setattr(check_mod, "ROOT", tmp_path)
    bad = check_mod.scan_code({"sources": [{"id": "2024-someone-thing"}]})
    assert bad and bad[0][2] == "1999-nobody-nothing"


def test_a_known_code_ref_passes(tmp_path, monkeypatch):
    pkg = tmp_path / "packages" / "p" / "src" / "p"
    pkg.mkdir(parents=True)
    (pkg / "m.py").write_text("# implements D13; ref: 2024-someone-thing\n")
    monkeypatch.setattr(check_mod, "ROOT", tmp_path)
    assert check_mod.scan_code({"sources": [{"id": "2024-someone-thing"}]}) == []
