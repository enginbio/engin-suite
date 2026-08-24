"""Illustrative host-capability knowledge base.

A small, deliberately-illustrative first pass (values in [0,1], higher = more
capable) with a per-cell confidence (data completeness / consensus). In
production these come from curated literature + per-host models with citations
(the M1 milestone); here they exist to prove the scoring / uncertainty /
attribution loop end to end. See ../README.md for provenance caveats.

Every cell is ``provenance="illustrative"`` by default (see
:class:`~engin_host.schema.Host`), so the status now travels with the number
rather than living only in this docstring.

**``gras`` was a capability here until 2026-08-23 and is now retired** (ADR 0010,
#146). Regulatory status is carried instead by ``Host.qps`` -- EFSA QPS at species
level, printed by ``render_memo`` and ignored by ``scoring``. The reasoning is
preserved below because it is why the column could not simply be sourced, and it
is the argument anyone proposing to re-add a regulatory *score* has to answer.

It looked like the easy one -- a regulatory-status question with a citable answer
-- and it is not, because GRAS is not a property of an organism. Checked against
FDA on 2026-08-16:

- A GRAS conclusion attaches to a **substance under specific conditions of
  use**, not to a production organism. The inventory reads *"pepsin A from
  Komagataella phaffii DFB-002"*, *"egg-white protein from K. phaffii
  GSD-1235"*, *"Bacillus subtilis SG188"* -- substance, strain, and use.
- It is **strain-specific**. `B. subtilis` SG188 and `B. subtilis` PLSSC are
  separate notices. "B. subtilis is 0.85 GRAS" corresponds to no citable fact.
- FDA does **not approve** GRAS notices. It issues a "no questions" letter and
  states it has not made its own determination, so even a per-substance cell
  cannot honestly be labelled an approval.

So a scalar per organism cannot be given a ``sources.yaml`` id without
laundering an editorial judgement into a citation, which is the failure `D23`
exists to prevent. A sourceable encoding would be a *count or list of accepted
notices naming that organism as the production organism*, which is a different
field with a different meaning -- and that is a schema decision, not a lookup.
Recorded on #146 and #22.
"""

from __future__ import annotations

from .schema import Host, KnowledgeBase, QpsRecord

# `gras` is not sourceable as written, and the follow-up found out why. #188
# established that a GRAS conclusion attaches to a substance under specific
# conditions of use rather than to an organism, so this scalar cannot carry a
# `sources.yaml` id. ADR 0010 answers the encoding question that left open:
#
#   * EFSA's QPS list *is* organism-level -- status is granted at the species
#     level, with qualifications, and is CC BY 4.0 on the Knowledge Junction.
#     That is the citable per-host regulatory fact. # ref: 2026-efsa-qps-list
#   * The FDA inventory has no production-organism field at all, so a per-host
#     US number would be our own extraction wearing a citation.
#     # ref: 2026-fda-gras-inventory
#
# The concrete symptom, if you want one before reading the ADR: `E. coli` scores
# 0.50 below and CHO 0.30, but E. coli is *excluded from QPS by name* while CHO
# was never in scope. The column orders "assessed and refused" above "not
# applicable", which is not a quantity that has an axis.
#
# ADR 0010 is **accepted**, and it sequences the change: drop `gras` from the
# weighted sum, add the QPS status as a field `render_memo` *prints* and scoring
# ignores, and defer ranking on it to #22. Read that consequence before wiring
# the status into `scoring.py` -- "E. coli: excluded" shown without a target
# market is a misleading number replacing a meaningless one, and QPS is about
# food and feed, not about the detergent enzyme someone is actually making.
CAPABILITIES: list[str] = [
    "secretion",
    "glyco",
    "titer",
    "speed",
    "tools",
    "scaleup",
    "cost",
    "smallmol",
    "protein",
]

# host -> capability values (illustrative; higher = better/more-capable)
_CAPS: dict[str, list[float]] = {
    "E. coli": [0.30, 0.05, 0.80, 0.95, 0.98, 0.90, 0.90, 0.80, 0.80],
    "S. cerevisiae": [0.50, 0.40, 0.75, 0.70, 0.90, 0.85, 0.85, 0.85, 0.70],
    "P. pastoris": [0.85, 0.50, 0.85, 0.60, 0.75, 0.80, 0.80, 0.60, 0.85],
    "B. subtilis": [0.90, 0.10, 0.70, 0.85, 0.70, 0.75, 0.85, 0.60, 0.70],
    "CHO (mammalian)": [0.80, 0.95, 0.50, 0.20, 0.60, 0.70, 0.30, 0.20, 0.95],
    "Cell-free (TXTL)": [0.20, 0.20, 0.30, 0.98, 0.60, 0.30, 0.20, 0.50, 0.60],
}
# confidence in each cell (0..1); lower for less-characterized hosts / harder caps
_CONF: dict[str, list[float]] = {
    "E. coli": [0.90, 0.90, 0.80, 0.90, 0.95, 0.90, 0.90, 0.85, 0.85],
    "S. cerevisiae": [0.85, 0.70, 0.80, 0.85, 0.90, 0.85, 0.85, 0.85, 0.80],
    "P. pastoris": [0.80, 0.60, 0.75, 0.80, 0.70, 0.75, 0.75, 0.60, 0.80],
    "B. subtilis": [0.80, 0.70, 0.70, 0.80, 0.70, 0.70, 0.75, 0.60, 0.70],
    "CHO (mammalian)": [0.80, 0.90, 0.70, 0.80, 0.70, 0.70, 0.70, 0.60, 0.90],
    "Cell-free (TXTL)": [0.60, 0.50, 0.60, 0.80, 0.60, 0.50, 0.55, 0.50, 0.60],
}


#: EFSA QPS status per host (ADR 0010). Read from the CC BY 4.0 Knowledge Junction
#: list -- "Appendix E, Updated list of QPS recommended biological agents, PS 24" --
#: not from the EFSA Journal article, which is CC BY-ND and from which a machine-
#: readable table would be a derivative work. Qualifications are verbatim.
#: Verified against the source 2026-08-23.  # ref: 2026-efsa-qps-list
_QPS: dict[str, QpsRecord] = {
    "E. coli": QpsRecord(
        status="excluded",
        taxonomic_unit="Escherichia coli",
        source="2026-efsa-qps-list",
        note=(
            "On the list's 'Excluded from QPS' sheet: 'Many strains of E. coli are "
            "pathogens for humans and animals. ... The Panel decided to exclude this "
            "species from future QPS evaluations.' Assessed and refused, which is a "
            "different thing from never having been in scope -- and note what it does "
            "NOT mean: QPS is about intentional addition to food or feed, so this says "
            "nothing about E. coli as a chassis for an enzyme or a pharmaceutical "
            "intermediate, which is most of what it is used for."
        ),
    ),
    "S. cerevisiae": QpsRecord(
        status="listed",
        taxonomic_unit="Saccharomyces cerevisiae",
        qualifications=[
            "When used as active agents (viable cells): Absence of resistance to "
            "antimycotics used for medical treatment of yeast infections in cases where "
            "viable cells are added to the food or feed chain."
        ],
        source="2026-efsa-qps-list",
    ),
    "P. pastoris": QpsRecord(
        status="listed",
        taxonomic_unit="Komagataella phaffii",
        source="2026-efsa-qps-list",
        note=(
            "Listed with no qualification, which is why `qualifications` is empty rather "
            "than absent -- the empty list is the fact. Filed under the current name; "
            "'P. pastoris' is this KB's colloquial label for the same species."
        ),
    ),
    "B. subtilis": QpsRecord(
        status="listed",
        taxonomic_unit="Bacillus subtilis",
        qualifications=[
            "The strains should not harbour any acquired antimicrobial resistance genes "
            "to clinically relevant antimicrobials."
        ],
        source="2026-efsa-qps-list",
    ),
    "CHO (mammalian)": QpsRecord(
        status="out_of_scope",
        note=(
            "QPS covers microorganisms intentionally added to food or feed. A mammalian "
            "cell line is not one, so there is no status to report -- which is the "
            "distinction the retired `gras` scalar destroyed by scoring CHO 0.30 below "
            "E. coli's 0.50."
        ),
    ),
    "Cell-free (TXTL)": QpsRecord(
        status="out_of_scope",
        note="A cell-free extract is not an organism, so the scheme does not reach it.",
    ),
}


def default_kb() -> KnowledgeBase:
    """Build the illustrative :class:`KnowledgeBase`."""
    hosts = [
        Host(
            name=name,
            caps=dict(zip(CAPABILITIES, _CAPS[name], strict=True)),
            conf=dict(zip(CAPABILITIES, _CONF[name], strict=True)),
            qps=_QPS[name],
        )
        for name in _CAPS
    ]
    return KnowledgeBase(capabilities=CAPABILITIES, hosts=hosts, sd_scale=0.35)
