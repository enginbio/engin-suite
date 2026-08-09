"""Illustrative host-capability knowledge base.

A small, deliberately-illustrative first pass (values in [0,1], higher = more
capable) with a per-cell confidence (data completeness / consensus). In
production these come from curated literature + per-host models with citations
(the M1 milestone); here they exist to prove the scoring / uncertainty /
attribution loop end to end. See ../README.md for provenance caveats.
"""

from __future__ import annotations

from .schema import Host, KnowledgeBase

CAPABILITIES: list[str] = [
    "secretion",
    "glyco",
    "titer",
    "speed",
    "tools",
    "scaleup",
    "cost",
    "gras",
    "smallmol",
    "protein",
]

# host -> capability values (illustrative; higher = better/more-capable)
_CAPS: dict[str, list[float]] = {
    "E. coli": [0.30, 0.05, 0.80, 0.95, 0.98, 0.90, 0.90, 0.50, 0.80, 0.80],
    "S. cerevisiae": [0.50, 0.40, 0.75, 0.70, 0.90, 0.85, 0.85, 0.95, 0.85, 0.70],
    "P. pastoris": [0.85, 0.50, 0.85, 0.60, 0.75, 0.80, 0.80, 0.70, 0.60, 0.85],
    "B. subtilis": [0.90, 0.10, 0.70, 0.85, 0.70, 0.75, 0.85, 0.85, 0.60, 0.70],
    "CHO (mammalian)": [0.80, 0.95, 0.50, 0.20, 0.60, 0.70, 0.30, 0.30, 0.20, 0.95],
    "Cell-free (TXTL)": [0.20, 0.20, 0.30, 0.98, 0.60, 0.30, 0.20, 0.40, 0.50, 0.60],
}
# confidence in each cell (0..1); lower for less-characterized hosts / harder caps
_CONF: dict[str, list[float]] = {
    "E. coli": [0.90, 0.90, 0.80, 0.90, 0.95, 0.90, 0.90, 0.80, 0.85, 0.85],
    "S. cerevisiae": [0.85, 0.70, 0.80, 0.85, 0.90, 0.85, 0.85, 0.90, 0.85, 0.80],
    "P. pastoris": [0.80, 0.60, 0.75, 0.80, 0.70, 0.75, 0.75, 0.65, 0.60, 0.80],
    "B. subtilis": [0.80, 0.70, 0.70, 0.80, 0.70, 0.70, 0.75, 0.75, 0.60, 0.70],
    "CHO (mammalian)": [0.80, 0.90, 0.70, 0.80, 0.70, 0.70, 0.70, 0.70, 0.60, 0.90],
    "Cell-free (TXTL)": [0.60, 0.50, 0.60, 0.80, 0.60, 0.50, 0.55, 0.50, 0.50, 0.60],
}


def default_kb() -> KnowledgeBase:
    """Build the illustrative :class:`KnowledgeBase`."""
    hosts = [
        Host(
            name=name,
            caps=dict(zip(CAPABILITIES, _CAPS[name], strict=True)),
            conf=dict(zip(CAPABILITIES, _CONF[name], strict=True)),
        )
        for name in _CAPS
    ]
    return KnowledgeBase(capabilities=CAPABILITIES, hosts=hosts, sd_scale=0.35)
