"""Adapter from this stage's ranked routes into the suite's handoff vocabulary.

``engin_core.handoff`` defines what a stage [3] ranking looks like to the rest of the
funnel; this module is the only thing that produces one.
"""

from __future__ import annotations

from engin_core import HostDecision, RankedRoute, RouteRanking

from .rank import PathwayRanker
from .schema import Route


def to_ranking(
    ranker: PathwayRanker,
    routes: list[Route],
    host: HostDecision | None = None,
) -> RouteRanking:
    """Distil ``routes`` scored by ``ranker`` into the stage [3] handoff object.

    Requires a calibrated ranker — :meth:`engin_graph.GraphRanker.half_width`, which
    ``PathwayRanker`` inherits, raises otherwise, and
    that is the intended failure. A ranking crossing a stage boundary without an interval
    is exactly what the handoff vocabulary exists to prevent.

    The upstream ``host`` is **recorded, not applied**. ``lo``/``hi`` stay precisely the
    split-conformal bounds the ranker produced, because widening them here would leave a
    number that is no longer conformal under a field name asserting that it is. The funnel
    inflates once, downstream, in :func:`engin_core.process_brief`, which is why
    ``host_confidence`` is carried rather than consumed here.
    """
    if not routes:
        raise ValueError("cannot build a RouteRanking from an empty route list")

    mean = ranker.predict(routes)
    hw = ranker.half_width()  # constant-width for this head; raises if uncalibrated

    return RouteRanking(
        routes=[
            RankedRoute(
                route_id=r.route_id,
                manufacturability=float(m),
                lo=float(m - hw),
                hi=float(m + hw),
            )
            for r, m in zip(routes, mean, strict=True)
        ],
        conditioned_on_host=host.host if host is not None else None,
        host_confidence=host.confidence if host is not None else None,
    )
