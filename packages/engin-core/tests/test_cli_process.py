"""`engin-process` at the command line. Kept small: every run simulates and fits a GP."""

from __future__ import annotations

import json

import pytest

from engin_core.cli import main

pytest.importorskip("yaml", reason="project files need the [cli] extra")

# Deliberately tiny -- this test is about the command, not about the modelling.
GOOD = """\
target: a test molecule
process:
  n_runs: 12
  batch_size: 2
  seed: 0
  reactor:
    v0: 1.0
    vmax: 2.5
    t_end: 24.0
"""


def _write(tmp_path, text):
    p = tmp_path / "project.yaml"
    p.write_text(text)
    return str(p)


def test_a_valid_project_recommends_a_batch(tmp_path, capsys):
    assert main(["--config", _write(tmp_path, GOOD)]) == 0
    out = capsys.readouterr().out
    assert "next 2 runs" in out
    assert "feed_rate" in out


def test_the_configured_vessel_is_the_one_reported(tmp_path, capsys):
    """The whole point of #142 reaching the CLI: a user's own vessel, not ours."""
    cfg = _write(tmp_path, GOOD.replace("v0: 1.0", "v0: 5.0").replace("vmax: 2.5", "vmax: 12.0"))
    assert main(["--config", cfg, "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["reactor"]["v0"] == 5.0
    assert payload["reactor"]["vmax"] == 12.0


def test_cost_is_the_default_objective(tmp_path, capsys):
    """D13 in the user-facing surface: cost unless explicitly asked otherwise."""
    assert main(["--config", _write(tmp_path, GOOD), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["objective"] == "net_usd_per_kg"
    assert "expected_cost_reduction_usd_per_kg" in payload["recommended"][0]


def test_titer_flag_switches_to_the_baseline_objective(tmp_path, capsys):
    assert main(["--config", _write(tmp_path, GOOD), "--titer", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["objective"] == "titer_g_L"
    assert "expected_improvement_g_L" in payload["recommended"][0]


def test_output_says_the_runs_were_simulated(tmp_path, capsys):
    """This stage cannot read a real run history yet. Saying so is not optional."""
    main(["--config", _write(tmp_path, GOOD)])
    assert "simulated" in capsys.readouterr().out.lower()


def test_a_run_is_reproducible(tmp_path, capsys):
    cfg = _write(tmp_path, GOOD)
    main(["--config", cfg, "--json"])
    first = capsys.readouterr().out
    main(["--config", cfg, "--json"])
    assert capsys.readouterr().out == first


def test_missing_section_says_which_one(tmp_path, capsys):
    assert main(["--config", _write(tmp_path, "target: x\n")]) == 2
    assert "no 'process:' section" in capsys.readouterr().err
