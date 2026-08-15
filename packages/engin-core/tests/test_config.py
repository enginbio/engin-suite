"""The project file: what it accepts, what it refuses, and that the starter parses."""

from __future__ import annotations

import pytest

from engin_core.config import ProjectConfig, load_project, starter_yaml

yaml = pytest.importorskip("yaml", reason="project files need the [cli] extra")


def _write(tmp_path, text: str):
    p = tmp_path / "project.yaml"
    p.write_text(text)
    return p


# ------------------------------------------------------------ the starter file


def test_starter_file_actually_parses():
    """`--init` writes this. If it drifts from the schema the first run of the first
    command a new user types fails, which is the worst place to have a bug."""
    project = ProjectConfig.model_validate(yaml.safe_load(starter_yaml()))
    assert project.host is not None
    assert project.pathway is not None
    assert project.process is not None


def test_starter_file_round_trips_through_the_loader(tmp_path):
    p = _write(tmp_path, starter_yaml())
    project = load_project(p)
    assert project.target
    assert project.host.weights
    assert len(project.pathway.routes) >= 2
    assert project.process.reactor.v0 > 0


def test_starter_pathway_steps_carry_every_feature():
    """The commented example teaches the vocabulary, so it must use all of it."""
    project = ProjectConfig.model_validate(yaml.safe_load(starter_yaml()))
    expected = {"g_thermo", "g_enzyme", "g_cofactor", "g_tox", "g_expr"}
    for route in project.pathway.routes:
        for step in route.steps:
            assert set(step) == expected


# ------------------------------------------------------------------- sections


def test_every_section_is_optional(tmp_path):
    project = load_project(_write(tmp_path, "target: just a name\n"))
    assert project.host is None and project.pathway is None and project.process is None


def test_process_defaults_to_the_bundled_vessel_and_economics(tmp_path):
    project = load_project(_write(tmp_path, "process: {}\n"))
    assert project.process.reactor.v0 == 1.0
    assert project.process.cost.target_usd_per_kg == 200.0


def test_process_reactor_is_a_real_reactor_config(tmp_path):
    project = load_project(_write(tmp_path, "process:\n  reactor:\n    v0: 5.0\n    vmax: 12.0\n"))
    assert (project.process.reactor.v0, project.process.reactor.vmax) == (5.0, 12.0)


def test_an_incoherent_vessel_is_rejected_through_the_project_file(tmp_path):
    """ReactorConfig's own validation must not be bypassed by coming in via YAML."""
    with pytest.raises(ValueError, match="vmax"):
        load_project(_write(tmp_path, "process:\n  reactor:\n    v0: 10.0\n    vmax: 2.0\n"))


# ------------------------------------------------------------------ rejection


def test_missing_file_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="no project file"):
        load_project(tmp_path / "absent.yaml")


def test_a_non_mapping_file_is_an_error(tmp_path):
    with pytest.raises(ValueError, match="mapping at the top level"):
        load_project(_write(tmp_path, "- just\n- a list\n"))


def test_unknown_top_level_keys_are_refused(tmp_path):
    """A typo'd section name must not be silently ignored -- the user would think the
    stage ran on their settings when it ran on defaults."""
    with pytest.raises(ValueError, match="hostt|extra"):
        load_project(_write(tmp_path, "hostt:\n  weights: {titer: 1.0}\n"))


def test_empty_host_weights_are_refused(tmp_path):
    with pytest.raises(ValueError, match="at least one capability"):
        load_project(_write(tmp_path, "host:\n  weights: {}\n"))


def test_all_zero_host_weights_are_refused(tmp_path):
    with pytest.raises(ValueError, match="not be all zero"):
        load_project(_write(tmp_path, "host:\n  weights: {titer: 0.0}\n"))


def test_negative_host_weight_is_refused(tmp_path):
    with pytest.raises(ValueError, match=">= 0"):
        load_project(_write(tmp_path, "host:\n  weights: {titer: -1.0}\n"))


def test_a_route_needs_at_least_one_step(tmp_path):
    with pytest.raises(ValueError):
        load_project(_write(tmp_path, "pathway:\n  routes:\n    - id: r1\n      steps: []\n"))


def test_yaml_is_loaded_safely(tmp_path):
    """A project file is data. It must not be able to construct Python objects."""
    p = _write(tmp_path, "target: !!python/object/apply:os.system ['echo pwned']\n")
    with pytest.raises(Exception):  # noqa: B017 - any refusal is the point
        load_project(p)
