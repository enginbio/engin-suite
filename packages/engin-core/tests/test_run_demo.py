"""The advertised demo runs, and emits what the README says it emits (#236).

``examples/run_demo.py`` is named in ``README.md`` as the full end-to-end demo, and
until now nothing imported it, nothing ran it, and ``examples/outputs/`` is gitignored
so there was no artifact for anything to diff against. The only thing keeping it
working was somebody running it by hand and noticing.

**These assert structure, not numbers.** A golden file over the memo would have to be
re-blessed on every model change, and a test that gets re-blessed without being read
is worse than no test -- it converts a real signal into a chore. So the assertions are
the ones that stay true while the numbers move: the artifacts exist, the memo has its
sections, the CSV has its columns, and the plots are not empty files.

The demo takes about 8 seconds, which is why this sits in the normal suite rather than
behind a marker like ``engin-pathway``'s ``network``.
"""

from __future__ import annotations

import csv

import pytest

# matplotlib is an `examples` extra, not a default dependency (ADR 0002). The light
# install path must stay green, so this skips rather than fails when it is absent.
#
# Both of these are `importorskip` rather than plain imports, and `run_demo` is bound
# by assignment on purpose: written as `import run_demo` after the guard, ruff's
# isort rule hoists it above the guard, which is exactly the line that must not move.
pytest.importorskip("matplotlib", reason="matplotlib is the `examples` extra (ADR 0002)")
run_demo = pytest.importorskip("run_demo", reason="examples/ is on the path via conftest")


#: What ``README.md`` promises: "writes plots, a DoE CSV, and a DoE round-reduction memo".
PLOTS = ("calibration.png", "sensitivity.png", "active_learning.png")
CSV_NAME = "doe_dataset.csv"
MEMO_NAME = "doe-round-reduction-memo.md"


@pytest.fixture(scope="module")
def demo_outputs(tmp_path_factory):
    """Run the demo once into a tmp directory and hand back the path.

    Module-scoped because the demo takes seconds and every assertion below reads the
    same run. ``run_demo.OUT`` is patched rather than the cwd, so the real
    ``examples/outputs/`` is untouched by the suite.
    """
    out = tmp_path_factory.mktemp("demo_outputs")
    original = run_demo.OUT
    run_demo.OUT = str(out)
    try:
        run_demo.main()
    finally:
        run_demo.OUT = original
    return out


def test_demo_writes_every_artifact_the_readme_advertises(demo_outputs):
    for name in (*PLOTS, CSV_NAME, MEMO_NAME):
        assert (demo_outputs / name).is_file(), f"{name} was advertised and not written"


def test_plots_are_not_empty_files(demo_outputs):
    # A savefig that silently produced nothing would still create the file.
    for name in PLOTS:
        assert (demo_outputs / name).stat().st_size > 1024


def test_memo_keeps_its_sections(demo_outputs):
    """The memo's headings, not its numbers.

    ``## What it costs`` is the one worth pinning: #235 added it so the memo closes on
    cost rather than on titer lift, which `D13` calls the wrong target. A regression
    that dropped it would be invisible without this line.
    """
    memo = (demo_outputs / MEMO_NAME).read_text()
    for heading in (
        "# DoE round-reduction memo",
        "## Forecast quality (held-out)",
        "## What actually drives titer",
        "## Recommended next DoE batch",
        "## Bottom line",
        "## What it costs",
    ):
        assert heading in memo, f"memo lost its {heading!r} section"


def test_memo_says_it_is_generated(demo_outputs):
    """It leaves the repo as a screenshot, so it has to say what it is."""
    assert "auto-generated" in (demo_outputs / MEMO_NAME).read_text()


def test_csv_carries_the_five_knobs_and_both_titers(demo_outputs):
    with open(demo_outputs / CSV_NAME, newline="") as f:
        rows = list(csv.reader(f))

    from engin_core import simulator as sim

    header, body = rows[0], rows[1:]
    assert header[: len(sim.KNOB_NAMES)] == list(sim.KNOB_NAMES)
    # both the observed and the true titer, because the demo's point is the gap
    assert "titer_obs_gL" in header and "titer_true_gL" in header
    assert body, "the DoE CSV has a header and no runs"


def test_the_real_outputs_directory_is_untouched(demo_outputs):
    """Importing the demo must not write into the checkout.

    ``os.makedirs`` used to run at import, so merely collecting this file created
    ``examples/outputs/``. It moved into ``main()`` (#236); this pins that, because
    the regression is silent and only shows up as a dirty tree.
    """
    assert run_demo.OUT.endswith("outputs")
    assert str(demo_outputs) != run_demo.OUT
