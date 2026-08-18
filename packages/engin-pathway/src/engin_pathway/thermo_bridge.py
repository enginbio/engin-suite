"""Reaction formula in, :class:`~engin_pathway.schema.Step` out (#140 item 3).

:mod:`engin_pathway.thermo` turns a Gibbs energy into ``g_thermo``. This turns a
*reaction* into one, by asking eQuilibrator for the energy first. It is the
half of #140 item 3 that makes ``g_thermo`` reachable without typing a number;
route ingest from a pathway database is deliberately not here.

## The guard this module exists for

**eQuilibrator returns a confident number for an unbalanced reaction.** Measured
on 2026-08-17, ``kegg:C00002 = kegg:C00008`` -- ATP to ADP with the phosphate and
water left out -- returns ``874.9 +/- 0.6 kJ/mol``. No exception, and the
uncertainty is *tight*, which reads as high confidence rather than as nonsense.

Through :func:`~engin_pathway.thermo.g_thermo` that becomes ``g_thermo`` of
essentially zero: the step is scored as thermodynamically impossible. So a user
who omits a cofactor does not get an error, they get a confident wrong ranking.

This module therefore **refuses an unbalanced reaction** rather than scoring it.
That is the same principle as the role check in ADR 0009 -- a plausible number
that means nothing is worse than a missing one, and the place to stop it is where
the meaning is known.

## Why the other four features have no defaults

:func:`step_from_reaction` requires ``g_enzyme``, ``g_cofactor``, ``g_tox`` and
``g_expr`` explicitly. It could default them to 0.5 and return a whole
:class:`Step`; it does not, because a step whose ``g_thermo`` is measured and
whose other four are invented is **not a measured step**, and defaulting would
hide exactly that. Same argument as the provenance work in ``engin-host`` (#146):
the status has to travel with the number.

## Installation

Needs the ``[thermo]`` extra. eQuilibrator is not a default dependency and not a
CI one -- its compound database is 1.34 GB (#205).
"""

from __future__ import annotations

from typing import Any

from .schema import Step
from .thermo import g_thermo, g_thermo_interval

__all__ = ["ThermoUnavailable", "UnbalancedReaction", "dg_for_reaction", "step_from_reaction"]


class UnbalancedReaction(ValueError):
    """Raised rather than scoring a reaction whose atoms do not balance.

    Carries the formula because the fix is almost always a missing cofactor, and
    the message is where someone will look for which one.
    """


class ThermoUnavailable(ImportError):
    """Raised when the ``[thermo]`` extra is not installed."""


def _component_contribution() -> Any:
    """Import eQuilibrator lazily, with an error that says what to install.

    Lazy because importing it is not free and because this package must remain
    importable without the extra -- every other module here has to keep working
    on a default install.
    """
    try:
        from equilibrator_api import ComponentContribution
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ThermoUnavailable(
            "reaction thermodynamics needs the optional extra: "
            "pip install 'engin-pathway[thermo]'. Note it downloads a 1.34 GB "
            "compound database on first use."
        ) from exc
    return ComponentContribution()


def dg_for_reaction(formula: str, cc: Any | None = None) -> tuple[float, float]:
    """``(dG'^o, sd)`` in kJ/mol for a reaction formula, e.g. ``"kegg:C00002 + ..."``.

    Pass ``cc`` to reuse a :class:`ComponentContribution`; constructing one loads
    the compound database and takes tens of seconds, so a caller scoring a route
    should build it once.

    Raises :class:`UnbalancedReaction` if the atoms do not balance -- see the
    module docstring for why that is a refusal rather than a warning.
    """
    cc = cc if cc is not None else _component_contribution()
    reaction = cc.parse_reaction_formula(formula)
    if not reaction.is_balanced():
        raise UnbalancedReaction(
            f"reaction does not balance: {formula!r}. eQuilibrator will still "
            f"return a Gibbs energy for it, with a tight-looking uncertainty, and "
            f"that number is meaningless -- a missing cofactor or water is the "
            f"usual cause. Balance it rather than scoring it."
        )
    measurement = cc.standard_dg_prime(reaction)
    return float(measurement.value.magnitude), float(measurement.error.magnitude)


def step_from_reaction(
    formula: str,
    *,
    g_enzyme: float,
    g_cofactor: float,
    g_tox: float,
    g_expr: float,
    cc: Any | None = None,
) -> tuple[Step, tuple[float, float]]:
    """A :class:`Step` whose ``g_thermo`` is measured, plus its one-sigma bounds.

    The other four features are **required keyword arguments with no defaults**.
    They are still expert judgement, and this signature makes that impossible to
    forget: you cannot obtain a Step from this function without stating them.

    Returns the interval alongside the Step because :class:`Step` has nowhere to
    put it. ``g_thermo`` is a point in the schema, and the uncertainty
    eQuilibrator supplies would otherwise be discarded at the boundary -- which
    on this project is worth handing back rather than dropping.
    """
    dg, sd = dg_for_reaction(formula, cc=cc)
    low, high = g_thermo_interval(dg, sd)
    step = Step(
        features={
            "g_thermo": float(g_thermo(dg)),
            "g_enzyme": g_enzyme,
            "g_cofactor": g_cofactor,
            "g_tox": g_tox,
            "g_expr": g_expr,
        },
        # Only g_thermo came from a source. Marking it is what stops this mixed
        # step reading as a fully measured one downstream (#140 item 4) -- the
        # gap this function opened when it shipped without the field.
        measured=frozenset({"g_thermo"}),
    )
    return step, (float(low), float(high))
