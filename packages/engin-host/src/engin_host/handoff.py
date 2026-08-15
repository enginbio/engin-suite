"""Adapter from this stage's native scores into the suite's handoff vocabulary.

``engin_core.handoff`` defines what a stage [4] decision looks like to the rest of the
funnel; this module is the only thing that produces one. It is kept out of ``scoring``
deliberately: that module is about ranking hosts, this one is about crossing a stage
boundary, and a change to the handoff contract should not have to touch the MCDA.
"""

from __future__ import annotations

import numpy as np
from engin_core import HostDecision, prob_at_least

from .schema import HostScore, KnowledgeBase


def decision_confidence(chosen: HostScore, runner_up: HostScore | None) -> float:
    """``P(chosen really outranks runner_up)`` under independent normals.

    ``HostDecision.confidence`` is specified to fall both when the top hosts are a close
    call and when the knowledge base is thin. Both behaviours fall out of one expression
    rather than needing a blended heuristic: the score difference is distributed
    ``N(s1 - s2, sqrt(sd1**2 + sd2**2))``, so ``P(difference > 0)``

    - falls toward 0.5 as the top two converge (numerator -> 0), and
    - falls toward 0.5 as the KB thins (both sds grow, so the denominator does).

    With no runner-up this is 1.0: the chosen host is trivially the best *feasible*
    option when it is the only feasible option. That is a statement about the absence of
    a rival and not about whether the host is any good — ``score`` and ``band90`` carry
    that, and they are what stays honest when the KB is illustrative (#146).
    """
    if runner_up is None:
        return 1.0
    sd = float(np.hypot(chosen.sd, runner_up.sd))
    margin = np.array([chosen.score - runner_up.score], float)
    return float(prob_at_least(margin, np.array([sd]), 0.0)[0])


def to_decision(
    scores: list[HostScore],
    kb: KnowledgeBase | None = None,
    n_drivers: int = 3,
) -> HostDecision:
    """Distil ranked ``scores`` into the stage [4] handoff object.

    ``scores`` is taken as :func:`engin_host.score` returns it — feasible hosts first,
    then by score descending — so the decision is simply the first entry.

    ``alternatives`` lists only rivals *in the same feasibility class*. A feasible host
    and an infeasible one are not alternatives to each other in any sense a downstream
    stage can use, and mixing them would let an infeasible host contest the confidence.

    ``kb`` is optional and supplies ``capability_profile``. Without it the profile is
    left empty rather than filled with the per-capability *contributions*, which are
    weighted by the query and would be a different quantity wearing the same name.
    """
    if not scores:
        raise ValueError("cannot build a HostDecision from an empty score list")

    chosen = scores[0]
    rivals = [s for s in scores[1:] if s.feasible == chosen.feasible]

    profile: dict[str, float] = {}
    if kb is not None:
        host = next((h for h in kb.hosts if h.name == chosen.host), None)
        if host is not None:
            profile = dict(host.caps)

    return HostDecision(
        host=chosen.host,
        feasible=chosen.feasible,
        score=chosen.score,
        band90=chosen.band90,
        confidence=decision_confidence(chosen, rivals[0] if rivals else None),
        key_drivers=[c for c, _ in chosen.contributions[:n_drivers]],
        alternatives=[s.host for s in rivals],
        capability_profile=profile,
    )
