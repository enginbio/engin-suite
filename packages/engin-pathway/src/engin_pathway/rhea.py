"""Fetch a reaction from Rhea by identifier (#140 item 3, partially).

## What this is not

#140 item 3 asks for ``Route`` construction "from a pathway identifier". **This
does not do that, and the reason is worth stating rather than leaving as an
absence: no licence-clean source has the pathway structure.**

#209 concluded "build traversal against Rhea" on licence grounds, and that
conclusion was about licences only. Checked against the Rhea API on 2026-08-18, a
reaction record carries ``id``, ``equation``, ``balanced``, ``status``,
``transport`` and ``comment`` -- and querying its ``pathway``, ``metacyc``,
``kegg`` and ``reaction-xref`` columns returns **empty**. Rhea is a curated
*reaction* database. It has no routes and no pathway cross-references to borrow
them from.

The sources that *do* carry pathway structure are the ones #209 ruled out: KEGG
requires a commercial licence, MetaCyc requires a subscription, and MetaNetX
aggregates both so a wholesale pull inherits their terms.

**So traversal is blocked on licensing, not unbuilt.** Every licence-clean source
lacks routes; every source with routes lacks a usable licence. That is a fact
about the field rather than about this package, and it will not be fixed by
writing more code here.

## What this is

The half that *is* reachable. A user who knows which reactions their route
comprises can name them by Rhea identifier instead of typing equations, and
:func:`step_for_rhea_id` runs each through the #206 bridge so ``g_thermo`` is
measured and marked. That removes the hand-transcription, which is where the
typos live; it does not discover the route for you.

## One caveat, because it is the same shape as a bug this project has already had

Rhea's ``equation`` is **compound names**, not identifiers -- "pentanamide + H2O =
pentanoate + NH4(+)". eQuilibrator parses that (its ChEBI identifiers, oddly, are
*not* in the compound cache and raise), which means the match is by name. A name
match can silently find the wrong compound, in the way ``XCO2 1.Out`` silently
matched ``offgas_co2`` in #206.

The guard is the same one: :func:`~engin_pathway.thermo_bridge.dg_for_reaction`
refuses an unbalanced reaction, and a mis-matched compound will usually fail to
balance. "Usually" is doing real work in that sentence -- it is a mitigation, not
a proof, and a route assembled this way deserves a reading before it is trusted.
"""

from __future__ import annotations

import urllib.parse
import urllib.request
from typing import Any

from .schema import Step

__all__ = [
    "RHEA_TSV_ENDPOINT",
    "USER_AGENT",
    "RheaLookupError",
    "reaction_equation",
    "step_for_rhea_id",
]

USER_AGENT = "engin-pathway (https://github.com/enginbio/engin-suite)"
"""Sent on every request. Rhea 403s the default ``Python-urllib`` agent, and
naming the caller is the polite half of that anyway."""

RHEA_TSV_ENDPOINT = "https://www.rhea-db.org/rhea/"
"""Rhea's REST endpoint. CC BY 4.0, and the only route-adjacent source that
permits commercial use in as many words -- see #209 and the register row
``2026-rhea-license``."""


class RheaLookupError(LookupError):
    """Raised when an identifier returns no reaction, rather than returning None.

    A silent ``None`` here would flow into a Step builder and produce a route with
    a hole in it.
    """


def reaction_equation(rhea_id: str, *, timeout: float = 30.0) -> str:
    """The reaction equation for ``rhea_id``, e.g. ``"RHEA:10000"``.

    Returns the compound-name form, which is what eQuilibrator can parse -- see
    the module docstring on why the ChEBI identifiers Rhea also publishes are not
    usable for this.
    """
    ident = rhea_id if rhea_id.upper().startswith("RHEA:") else f"RHEA:{rhea_id}"
    query = urllib.parse.urlencode(
        {"query": ident, "columns": "rhea-id,equation", "format": "tsv", "limit": "1"}
    )
    # A User-Agent is required, not cosmetic: Rhea returns 403 to the default
    # `Python-urllib/3.x`. #209 recorded that its licence page does the same to
    # some agents, and this module was written without applying that -- the first
    # network test failed on exactly the 403 already in the register.
    request = urllib.request.Request(
        f"{RHEA_TSV_ENDPOINT}?{query}",
        headers={"User-Agent": USER_AGENT, "Accept": "text/plain"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")

    rows = [line for line in body.splitlines() if line.strip()]
    if len(rows) < 2:  # header only
        raise RheaLookupError(f"Rhea returned no reaction for {ident!r}")
    fields = rows[1].split("\t")
    if len(fields) < 2 or not fields[1].strip():
        raise RheaLookupError(f"Rhea returned no equation for {ident!r}")
    return fields[1].strip()


def step_for_rhea_id(
    rhea_id: str,
    *,
    g_enzyme: float,
    g_cofactor: float,
    g_tox: float,
    g_expr: float,
    cc: Any | None = None,
    timeout: float = 30.0,
) -> tuple[Step, tuple[float, float]]:
    """A :class:`Step` for one Rhea reaction, with ``g_thermo`` measured.

    The other four features are required, for the reason given in
    :func:`~engin_pathway.thermo_bridge.step_from_reaction`: a step whose
    ``g_thermo`` is measured and whose rest are invented is not a measured step,
    and this function does not get to hide that by defaulting them.

    Needs the ``[thermo]`` extra for the energy, and network access for Rhea.
    """
    from .thermo_bridge import step_from_reaction

    return step_from_reaction(
        reaction_equation(rhea_id, timeout=timeout),
        g_enzyme=g_enzyme,
        g_cofactor=g_cofactor,
        g_tox=g_tox,
        g_expr=g_expr,
        cc=cc,
    )
