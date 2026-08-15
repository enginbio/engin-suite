"""`engin-host` at the command line: exit codes, JSON, and readable failures."""

from __future__ import annotations

import json

import pytest

from engin_host.cli import main

pytest.importorskip("yaml", reason="project files need the [cli] extra")

GOOD = """\
target: a test molecule
host:
  weights: {secretion: 1.0, titer: 1.0}
  hard: {secretion: 0.40}
"""


def _write(tmp_path, text, name="project.yaml"):
    p = tmp_path / name
    p.write_text(text)
    return str(p)


def test_a_valid_project_succeeds(tmp_path, capsys):
    assert main(["--config", _write(tmp_path, GOOD)]) == 0
    out = capsys.readouterr().out
    assert "Host recommendation" in out
    assert "a test molecule" in out
    assert "confidence" in out


def test_output_discloses_the_illustrative_knowledge_base(tmp_path, capsys):
    """The KB is 60 hand-assigned values (#146). A CLI that printed a ranking without
    saying so would be the most likely place for that to get lost."""
    main(["--config", _write(tmp_path, GOOD)])
    assert "illustrative" in capsys.readouterr().out.lower()


def test_json_output_is_machine_readable(tmp_path, capsys):
    assert main(["--config", _write(tmp_path, GOOD), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["decision"]["host"]
    assert 0.0 <= payload["decision"]["confidence"] <= 1.0
    assert payload["kb_provenance"] == "illustrative"
    assert payload["ranking"]


def test_init_writes_a_file_that_the_tool_can_then_read(tmp_path, capsys):
    dest = tmp_path / "new.yaml"
    assert main(["--init", str(dest)]) == 0
    assert dest.is_file()
    capsys.readouterr()
    assert main(["--config", str(dest)]) == 0


def test_init_refuses_to_overwrite(tmp_path, capsys):
    dest = tmp_path / "exists.yaml"
    dest.write_text("target: mine\n")
    assert main(["--init", str(dest)]) == 1
    assert "not overwriting" in capsys.readouterr().err
    assert dest.read_text() == "target: mine\n"  # untouched


# ------------------------------------------------------- failures, not tracebacks


def test_no_config_is_a_usage_error(capsys):
    assert main([]) == 2
    assert "--init" in capsys.readouterr().err


def test_missing_file_reports_a_sentence(tmp_path, capsys):
    assert main(["--config", str(tmp_path / "absent.yaml")]) == 2
    err = capsys.readouterr().err
    assert "no project file" in err
    assert "Traceback" not in err


def test_missing_section_says_which_one(tmp_path, capsys):
    assert main(["--config", _write(tmp_path, "target: x\n")]) == 2
    assert "no 'host:' section" in capsys.readouterr().err


def test_unknown_capability_lists_the_known_ones(tmp_path, capsys):
    cfg = _write(tmp_path, "host:\n  weights: {nonsense: 1.0}\n")
    assert main(["--config", cfg]) == 2
    err = capsys.readouterr().err
    assert "nonsense" in err
    assert "secretion" in err  # tells them what is available


def test_malformed_yaml_reports_a_sentence(tmp_path, capsys):
    cfg = _write(tmp_path, "host:\n  weights: {titer: -5.0}\n")
    assert main(["--config", cfg]) == 2
    assert "Traceback" not in capsys.readouterr().err
