"""Inter-stage handoff contracts for the strain-to-scale suite.

Each stage of the funnel hands the next stage its **decision and its uncertainty**:

    host-selection  --HostDecision-->  pathway-ranking  --RouteRanking-->  process

These pydantic contracts live in ``engin_core`` (the shared dependency) so every
stage speaks the same vocabulary without depending on the others -- a consumer of
a :class:`HostDecision` needs neither ``engin_host`` nor ``engin_pathway`` installed.

The compounding-uncertainty thesis is made concrete by
:func:`inflate_uncertainty`: a *low-confidence* upstream decision **widens** the
downstream interval, so unresolved risk early in the funnel is not silently
dropped. The deep, learned conditioning (a host-conditioned manufacturability
model; a route-conditioned process design space) is a later milestone -- these
contracts + honest uncertainty propagation are the plumbing it will ride on.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class HostDecision(BaseModel):
    """Stage [4] output: the chosen chassis, why, and how sure we are.

    ``confidence`` in [0, 1] is (roughly) the probability the chosen host is truly
    the best *feasible* option — it should fall when the top hosts are a close call
    or the knowledge base is thin, and that fall must propagate downstream.
    """

    host: str
    feasible: bool
    score: float
    band90: float
    confidence: float = Field(..., ge=0.0, le=1.0)
    key_drivers: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    capability_profile: dict[str, float] = Field(default_factory=dict)


class RankedRoute(BaseModel):
    """One ranked route with a calibrated manufacturability interval."""

    route_id: str
    manufacturability: float
    lo: float
    hi: float

    @property
    def half_width(self) -> float:
        return 0.5 * (self.hi - self.lo)


class RouteRanking(BaseModel):
    """Stage [3] output: routes ranked by manufacturability, with intervals.

    ``conditioned_on_host`` / ``host_confidence`` record the upstream decision this
    ranking was produced under (``None`` if ranked host-agnostically).
    """

    routes: list[RankedRoute] = Field(..., min_length=1)
    conditioned_on_host: str | None = None
    host_confidence: float | None = None

    @property
    def top(self) -> RankedRoute:
        """The highest-manufacturability route."""
        return max(self.routes, key=lambda r: r.manufacturability)


class ProcessBrief(BaseModel):
    """Stage [1] input: what the process stage consumes to start optimizing.

    The chosen route, its expected manufacturability, and the uncertainty carried
    down the whole funnel (upstream host + pathway). ``provenance`` records the chain.

    ```{warning}
    ``uncertainty`` is a **propagated width, not a conformal one.** It is the pathway
    stage's calibrated half-width multiplied by :func:`inflate_uncertainty`'s
    ``2 - confidence`` factor, which is a heuristic with no coverage guarantee behind
    it. The product inherits the weaker of the two: it is wider than a calibrated
    interval by construction, and nothing here has checked what it covers.

    Use it to plan conservatively, not to state a coverage claim. "Calibrated" is
    reserved in this project for intervals whose coverage has been measured — the
    same distinction ``engin_core.tea.cost_summary`` draws for its cost interval.
    ```
    """

    route_id: str
    expected_manufacturability: float
    uncertainty: float  # propagated half-width (stage interval x upstream inflation)
    host: str | None = None
    provenance: str = ""


def inflate_uncertainty(half_width: float, upstream_confidence: float | None) -> float:
    """Widen ``half_width`` when the upstream decision is low-confidence.

    Factor ``2 - confidence``: confidence 1.0 -> unchanged; 0.5 -> ×1.5; 0.0 -> ×2.
    ``None`` (no upstream decision) leaves the width unchanged.
    """
    if upstream_confidence is None:
        return half_width
    c = min(max(upstream_confidence, 0.0), 1.0)
    return half_width * (2.0 - c)


def process_brief(ranking: RouteRanking) -> ProcessBrief:
    """Distil a :class:`RouteRanking` into the :class:`ProcessBrief` the process stage consumes.

    This is where the funnel's uncertainty compounds, and the only place it does.
    ``ProcessBrief.uncertainty`` is documented as including upstream inflation, and
    ``RouteRanking`` carries ``host_confidence`` for no other purpose, so the widening
    is applied here via :func:`inflate_uncertainty`.

    It is deliberately *not* applied earlier. ``RankedRoute.lo``/``hi`` are split-conformal
    bounds; widening them at the pathway stage would produce a number that is no longer
    conformal under a field name claiming it is. Keeping the stage interval calibrated and
    inflating once at the boundary keeps both quantities honest.

    *(Changed 2026-08-15: this previously passed ``top.half_width`` through uninflated,
    which left ``inflate_uncertainty`` with no callers anywhere in the suite and the
    "incl. upstream inflation" contract on ``ProcessBrief.uncertainty`` unmet.)*
    """
    top = ranking.top
    host = ranking.conditioned_on_host
    prov = "pathway"
    if host is not None:
        prov = f"host={host}(conf={ranking.host_confidence:.2f}) -> pathway"
    return ProcessBrief(
        route_id=top.route_id,
        expected_manufacturability=top.manufacturability,
        uncertainty=inflate_uncertainty(top.half_width, ranking.host_confidence),
        host=host,
        provenance=f"{prov} -> process",
    )
