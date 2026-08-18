"""The eQuilibrator bridge (#140 item 3).

**Split deliberately into two halves.** The tests that need eQuilibrator skip
without it -- its compound database is 1.34 GB, so it is not a CI dependency
(#205) -- and everything that can be checked without it is checked without it, so
a default CI run still defends the parts that do not need the network.

The live half is marked so that what CI actually asserts is legible, rather than
implied by a green tick.
"""

from __future__ import annotations

import pytest

from engin_pathway.schema import FEATURES, Step
from engin_pathway.thermo_bridge import (
    ThermoUnavailable,
    UnbalancedReaction,
    dg_for_reaction,
    step_from_reaction,
)

_HAS_EQ = True
try:  # pragma: no cover - depends on whether the extra is installed
    import equilibrator_api  # noqa: F401
except ImportError:
    _HAS_EQ = False

needs_eq = pytest.mark.skipif(
    not _HAS_EQ, reason="needs the [thermo] extra (1.34 GB compound database)"
)

ATP_HYDROLYSIS = "kegg:C00002 + kegg:C00001 = kegg:C00008 + kegg:C00009"
UNBALANCED = "kegg:C00002 = kegg:C00008"  # ATP -> ADP, phosphate and water missing


# ---------------------------------------------------------- without the extra


def test_unbalanced_reaction_is_an_error_type_callers_can_catch():
    """It subclasses ValueError so existing handling still works, but is its own
    type so a caller can distinguish 'you gave me nonsense' from 'that is not a
    number'."""
    assert issubclass(UnbalancedReaction, ValueError)
    assert issubclass(ThermoUnavailable, ImportError)


def test_step_from_reaction_requires_the_other_four_features():
    """No defaults, on purpose: a Step whose g_thermo is measured and whose other
    four are invented is not a measured step, and a default would hide that."""
    with pytest.raises(TypeError):
        step_from_reaction(ATP_HYDROLYSIS)  # type: ignore[call-arg]


def test_the_module_imports_without_the_extra():
    """engin-pathway must stay importable on a default install."""
    from engin_pathway import thermo_bridge

    assert thermo_bridge.dg_for_reaction is dg_for_reaction


# ------------------------------------------------------------- with the extra


@needs_eq
def test_a_balanced_reaction_returns_energy_and_uncertainty():
    dg, sd = dg_for_reaction(ATP_HYDROLYSIS)
    assert dg == pytest.approx(-29.64, abs=0.5)
    assert 0.0 < sd < 5.0


@needs_eq
def test_an_unbalanced_reaction_is_refused_rather_than_scored():
    """The guard this module exists for.

    eQuilibrator returns 874.9 +/- 0.6 kJ/mol for this -- a confident-looking
    number with a tight uncertainty, which through g_thermo becomes ~0 and ranks
    the step as impossible. Refusing beats scoring it.
    """
    with pytest.raises(UnbalancedReaction, match="does not balance"):
        dg_for_reaction(UNBALANCED)


@needs_eq
def test_step_from_reaction_produces_a_valid_step_with_a_measured_g_thermo():
    step, (low, high) = step_from_reaction(
        ATP_HYDROLYSIS, g_enzyme=0.7, g_cofactor=0.6, g_tox=0.9, g_expr=0.8
    )
    assert isinstance(step, Step)
    assert set(step.features) == set(FEATURES)
    assert step.features["g_thermo"] > 0.9999
    assert low < step.features["g_thermo"] < high


@needs_eq
def test_the_uncertainty_is_handed_back_rather_than_dropped():
    """Step has nowhere to put an interval, so the boundary would otherwise
    discard what eQuilibrator supplied."""
    _, (low, high) = step_from_reaction(
        ATP_HYDROLYSIS, g_enzyme=0.5, g_cofactor=0.5, g_tox=0.5, g_expr=0.5
    )
    assert high > low
    assert (high - low) < 1e-4  # narrow here, but present
