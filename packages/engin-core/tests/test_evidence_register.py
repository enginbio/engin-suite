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


def test_docstring_refs_are_scanned_too(tmp_path, monkeypatch):
    """A ``ref:`` in a docstring, with no leading ``#``, must still resolve.

    Regression test for a real blind spot. The pattern required a ``#``, so a
    docstring ``ref:`` in gp.py named a source id that had never been registered
    while this check reported every ref resolving. **A guard that passes for the
    wrong reason is worse than no guard**, because the pass gets taken as
    evidence — which is precisely what happened for a day.
    """
    pkg = tmp_path / "packages" / "p" / "src" / "p"
    pkg.mkdir(parents=True)
    (pkg / "m.py").write_text('"""Doc.\n\n    ref: 1999-nobody-nothing\n    """\n')
    monkeypatch.setattr(check_mod, "ROOT", tmp_path)
    bad = check_mod.scan_code({"sources": [{"id": "2024-someone-thing"}]})
    assert bad and bad[0][2] == "1999-nobody-nothing"


# --- retracted-claim checker (scripts/evidence/check_corrections.py) ---------

_NOTICE = (
    "> **Withdrawn justification, kept because the error is instructive.** This decision\n"
    'previously read: *"Recovery cost is set upstream by the strain and the broth, and an\n'
    'optimizer chasing titer alone will therefore move the real objective backwards."*\n'
)


def _corrections_module():
    import importlib.util

    path = REPO / "scripts" / "evidence" / "check_corrections.py"
    spec = importlib.util.spec_from_file_location("check_corrections", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_a_retracted_claim_republished_is_caught(tmp_path):
    """The failure this exists for: a correction that reached one document only."""
    cm = _corrections_module()
    cores = cm.retracted_phrases(_NOTICE)
    assert cores, "the notice should yield a retracted phrase"

    doc = tmp_path / "guide.md"
    doc.write_text(
        "# Cost\n\nRecovery cost is set upstream by the strain and the broth, and an\n"
        "optimizer chasing titer alone will therefore move the real objective backwards.\n"
    )
    assert cm.scan([doc], cores)


def test_a_retracted_claim_cannot_vouch_for_itself(tmp_path):
    """Regression: context vocabulary must never overlap the claims themselves.

    The first version of the checker treated the word "backwards" as evidence
    that surrounding prose was *discussing* a retraction. That word is in the
    retracted claim, so a planted claim suppressed its own detection and the
    check passed while republishing it. Words about the act of correcting only.
    """
    cm = _corrections_module()
    assert not cm.DISCUSSING.search("move the real objective backwards")
    assert not cm.DISCUSSING.search("that mechanism was wrong")
    assert cm.DISCUSSING.search("this bullet previously read")


def test_quoting_a_retraction_is_allowed(tmp_path):
    """A correction notice quotes what it retracts. That is the house style."""
    cm = _corrections_module()
    cores = cm.retracted_phrases(_NOTICE)
    doc = tmp_path / "decisions.md"
    doc.write_text(
        "# Decisions\n\nCorrected 2026-08-10: this decision previously read\n"
        '"Recovery cost is set upstream by the strain and the broth, and an\n'
        'optimizer chasing titer alone will therefore move the real objective backwards."\n'
    )
    assert not cm.scan([doc], cores)


def test_the_explicit_opt_out_marker_works(tmp_path):
    cm = _corrections_module()
    cores = cm.retracted_phrases(_NOTICE)
    doc = tmp_path / "audit.md"
    doc.write_text(
        "<!-- quotes-retracted: this document is the audit that found it -->\n\n"
        "Recovery cost is set upstream by the strain and the broth, and an\n"
        "optimizer chasing titer alone will therefore move the real objective backwards.\n"
    )
    assert not cm.scan([doc], cores)


# --- execution-cache churn (scripts/evidence/check_cache_churn.py) -----------
#
# The classification these assert is the whole check. Calling a real cache update
# "churn" is the dangerous direction: it would have someone drop a refresh the
# published site needs (D20), so every column is pinned, not just `accessed`.


def _churn_module():
    import importlib.util

    path = REPO / "scripts" / "evidence" / "check_cache_churn.py"
    spec = importlib.util.spec_from_file_location("check_cache_churn", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cache_db(path, *, accessed="2026-08-01 00:00:00", created="2026-07-01 00:00:00", data="{}"):
    """A minimal database with jupyter-cache's schema and one row per table."""
    import sqlite3

    con = sqlite3.connect(path)
    con.executescript(
        "create table settings (pk integer primary key, key varchar(36), value json);"
        "create table nbproject (pk integer primary key, uri varchar(255),"
        " read_data json, assets json, exec_data json, created datetime, traceback text);"
        "create table nbcache (pk integer primary key, hashkey varchar(255),"
        " uri varchar(255), description varchar(255), data json,"
        " created datetime, accessed datetime);"
    )
    con.execute(
        "insert into nbproject values (1, 'docs/page.md', '{}', '[]', null, ?, null)", (created,)
    )
    con.execute(
        "insert into nbcache values (1, 'abc123', 'docs/page.md', '', ?, ?, ?)",
        (data, created, accessed),
    )
    con.commit()
    con.close()
    return path


def test_a_touched_timestamp_is_churn(tmp_path):
    """The observed case: a build that executes nothing still moves `accessed`."""
    cc = _churn_module()
    base = _cache_db(tmp_path / "base.db")
    head = _cache_db(tmp_path / "head.db", accessed="2026-08-30 12:00:00")
    verdict, changed = cc.compare(base, head)
    assert verdict == cc.TIMESTAMP_ONLY
    assert changed == {("nbcache", "accessed")}


def test_an_identical_cache_is_not_reported(tmp_path):
    cc = _churn_module()
    base = _cache_db(tmp_path / "base.db")
    head = _cache_db(tmp_path / "head.db")
    assert cc.compare(base, head)[0] == cc.IDENTICAL


@pytest.mark.parametrize(
    "kwargs",
    [
        {"data": '{"outputs": ["new"]}'},  # a cell produced different output
        {"created": "2026-08-30 12:00:00"},  # a record was rewritten, not just read
    ],
)
def test_a_real_cache_update_is_never_called_churn(tmp_path, kwargs):
    """The false positive that would matter: dropping a refresh the site needs."""
    cc = _churn_module()
    base = _cache_db(tmp_path / "base.db")
    head = _cache_db(tmp_path / "head.db", **kwargs)
    assert cc.compare(base, head)[0] == cc.SUBSTANTIVE


def test_a_timestamp_riding_along_with_a_real_change_is_substantive(tmp_path):
    """`accessed` moves on every build, so it will accompany genuine updates."""
    cc = _churn_module()
    base = _cache_db(tmp_path / "base.db")
    head = _cache_db(
        tmp_path / "head.db", accessed="2026-08-30 12:00:00", data='{"outputs": ["new"]}'
    )
    assert cc.compare(base, head)[0] == cc.SUBSTANTIVE


def test_a_new_cache_row_is_substantive(tmp_path):
    """A re-executed notebook adds a row; the real build does exactly this."""
    import sqlite3

    cc = _churn_module()
    base = _cache_db(tmp_path / "base.db")
    head = _cache_db(tmp_path / "head.db")
    con = sqlite3.connect(head)
    con.execute(
        "insert into nbcache values (2, 'def456', 'docs/two.md', '', '{}', ?, ?)", ("x", "y")
    )
    con.commit()
    con.close()
    assert cc.compare(base, head)[0] == cc.SUBSTANTIVE


def test_an_unreadable_database_is_never_called_churn(tmp_path):
    """Fail toward keeping the commit, not toward discarding it."""
    cc = _churn_module()
    base = _cache_db(tmp_path / "base.db")
    head = tmp_path / "not-a-database.db"
    head.write_bytes(b"certainly not sqlite")
    assert cc.compare(base, head)[0] == cc.SUBSTANTIVE
