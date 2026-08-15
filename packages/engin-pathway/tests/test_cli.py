"""`engin-pathway` at the command line, and the disclosure it must never drop."""

from __future__ import annotations

import json

import pytest

from engin_pathway.cli import main

pytest.importorskip("yaml", reason="project files need the [cli] extra")

STEP = "{g_thermo: 0.8, g_enzyme: 0.7, g_cofactor: 0.9, g_tox: 0.95, g_expr: 0.6}"

GOOD = f"""\
target: a test molecule
pathway:
  routes:
    - id: route-A
      steps:
        - {STEP}
        - {STEP}
    - id: route-B
      steps:
        - {STEP}
"""


def _write(tmp_path, text):
    p = tmp_path / "project.yaml"
    p.write_text(text)
    return str(p)


def test_a_valid_project_ranks_every_route(tmp_path, capsys):
    assert main(["--config", _write(tmp_path, GOOD)]) == 0
    out = capsys.readouterr().out
    assert "route-A" in out and "route-B" in out


def test_synthetic_training_is_disclosed_every_run(tmp_path, capsys):
    """The model is trained on this package's own generator when the user has no
    labels. Ranking real candidates against a model of a different world is the
    single most misleading thing this command can do, so the warning is pinned."""
    main(["--config", _write(tmp_path, GOOD)])
    out = capsys.readouterr().out
    assert "synthetic" in out.lower()
    assert "#124" in out and "#140" in out


def test_json_records_what_the_model_was_trained_on(tmp_path, capsys):
    assert main(["--config", _write(tmp_path, GOOD), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["trained_on"] == "synthetic generator"
    assert payload["n_labelled_supplied"] == 0
    assert len(payload["ranking"]) == 2


def test_overlapping_intervals_are_called_out(tmp_path, capsys):
    """Two near-identical routes must not be presented as a ranked winner."""
    main(["--config", _write(tmp_path, GOOD)])
    assert "overlap" in capsys.readouterr().out.lower()


def test_ranking_is_ordered_best_first(tmp_path, capsys):
    main(["--config", _write(tmp_path, GOOD), "--json"])
    ranking = json.loads(capsys.readouterr().out)["ranking"]
    scores = [r["manufacturability"] for r in ranking]
    assert scores == sorted(scores, reverse=True)


def test_a_run_is_reproducible(tmp_path, capsys):
    cfg = _write(tmp_path, GOOD)
    main(["--config", cfg, "--json", "--seed", "3"])
    first = capsys.readouterr().out
    main(["--config", cfg, "--json", "--seed", "3"])
    assert capsys.readouterr().out == first


# ------------------------------------------------------- failures, not tracebacks


def test_missing_section_says_which_one(tmp_path, capsys):
    assert main(["--config", _write(tmp_path, "target: x\n")]) == 2
    assert "no 'pathway:' section" in capsys.readouterr().err


def test_a_wrong_step_key_names_the_five_expected(tmp_path, capsys):
    bad = """\
pathway:
  routes:
    - id: r1
      steps:
        - {g_thermo: 0.8, g_enzyme: 0.7, g_cofactor: 0.9, g_tox: 0.95, typo: 0.6}
"""
    assert main(["--config", _write(tmp_path, bad)]) == 2
    err = capsys.readouterr().err
    assert "r1" in err
    assert "g_expr" in err  # tells them the key they were missing
    assert "Traceback" not in err


def test_an_out_of_range_feature_is_refused(tmp_path, capsys):
    bad = """\
pathway:
  routes:
    - id: r1
      steps:
        - {g_thermo: 5.0, g_enzyme: 0.7, g_cofactor: 0.9, g_tox: 0.95, g_expr: 0.6}
"""
    assert main(["--config", _write(tmp_path, bad)]) == 2
    assert "Traceback" not in capsys.readouterr().err
