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


def _same_shape(a, b, path=""):
    """Keys, order and structure, ignoring numeric values. Returns a complaint or None."""
    if isinstance(a, dict):
        if not isinstance(b, dict) or list(a) != list(b):
            return f"{path or '<root>'}: keys or key order differ -- {list(a)} vs {list(b)}"
        return next((c for k in a if (c := _same_shape(a[k], b[k], f"{path}.{k}"))), None)
    if isinstance(a, list):
        if not isinstance(b, list) or len(a) != len(b):
            return f"{path}: length differs -- {len(a)} vs {len(b)}"
        return next(
            (
                c
                for i, (u, v) in enumerate(zip(a, b, strict=True))
                if (c := _same_shape(u, v, f"{path}[{i}]"))
            ),
            None,
        )
    if isinstance(a, bool) or not isinstance(a, float | int):
        return None if a == b else f"{path}: {a!r} vs {b!r}"
    return None  # numbers are compared separately, with a tolerance


def _numbers(x, path=""):
    """Every number in the payload, by path."""
    if isinstance(x, dict):
        return {k: v for key, sub in x.items() for k, v in _numbers(sub, f"{path}.{key}").items()}
    if isinstance(x, list):
        return {k: v for i, sub in enumerate(x) for k, v in _numbers(sub, f"{path}[{i}]").items()}
    if isinstance(x, bool) or not isinstance(x, float | int):
        return {}
    return {path: float(x)}


def test_a_run_is_reproducible(tmp_path, capsys):
    """Same config and seed, same answer -- to the precision anyone acts on.

    **This used to assert byte-identical stdout**, which is strictly stronger than
    the property the name claims and than anything a caller relies on. It flaked once
    in `minimum-versions` CI on the last two digits of two floats -- around 1e-13
    relative, which is floating-point associativity rather than anything the seed
    controls, on a pull request that touched nothing on this path (#293).

    The suspected mechanism is threaded BLAS partitioning a reduction differently
    between calls. **That is unconfirmed**: on this machine at current dependency
    versions the output is byte-identical over twelve consecutive runs and across
    `OMP_NUM_THREADS` of 1, 4 and 8. The fix does not depend on the cause, because
    the assertion was wrong either way.

    What is checked instead is strictly more of what the name claims and strictly
    less of what it does not: the same keys in the same order -- the byte-level
    regression actually worth catching, now checked directly rather than as a side
    effect of comparing strings -- and every number equal to a tolerance far tighter
    than any decision anyone makes on these outputs.
    """
    cfg = _write(tmp_path, GOOD)
    main(["--config", cfg, "--json"])
    first = json.loads(capsys.readouterr().out)
    main(["--config", cfg, "--json"])
    second = json.loads(capsys.readouterr().out)

    assert (complaint := _same_shape(first, second)) is None, complaint

    a, b = _numbers(first), _numbers(second)
    assert list(a) == list(b)
    for key, value in a.items():
        assert value == pytest.approx(b[key], rel=1e-9, abs=1e-12), key


def test_missing_section_says_which_one(tmp_path, capsys):
    assert main(["--config", _write(tmp_path, "target: x\n")]) == 2
    assert "no 'process:' section" in capsys.readouterr().err
