"""Multi-criteria host scoring with uncertainty propagation and flags.

A weighted-sum MCDA over the capability matrix. Two things make it more than a
spreadsheet:

1. **Uncertainty is first-class.** Each capability carries a sd (from KB
   confidence); for a weighted sum of independent terms the score variance is
   ``(S**2) @ (w**2)`` exactly (linear error propagation), giving a 90% band that
   widens honestly where the KB is thin.
2. **Hard constraints demote, not just penalize.** A host that fails a hard
   requirement (e.g. glycosylation in a prokaryote) is flagged infeasible and
   ranked below every feasible host regardless of raw score.

The uncertainty primitive ``P(score >= threshold)`` is reused from ``engin_core``
so the whole suite shares one calibrated-uncertainty vocabulary.
"""

from __future__ import annotations

import numpy as np
from engin_core import prob_at_least

from .schema import HostQuery, HostScore, KnowledgeBase

GAUSS_90 = 1.645


def score(kb: KnowledgeBase, query: HostQuery, top_k: int = 3) -> list[HostScore]:
    """Rank hosts for ``query``. Returns feasible hosts first, then by score desc."""
    unknown = set(query.weights) - set(kb.capabilities)
    if unknown:
        raise KeyError(f"query weights reference unknown capabilities: {sorted(unknown)}")
    names, C, S = kb.matrices()
    w = np.array([query.weights.get(c, 0.0) for c in kb.capabilities], float)
    w = w / w.sum()  # renormalize to a convex weighting

    scores = C @ w  # weighted suitability
    sd = np.sqrt((S**2) @ (w**2))  # linear error propagation
    contrib = C * w[None, :]  # per-capability contribution

    by_name = {h.name: h for h in kb.hosts}
    # Capabilities that actually move this score. A zero-weighted capability is not
    # an input, so an unsourced value there should not make the output unsourced.
    weighted = [c for c, wc in zip(kb.capabilities, w, strict=True) if wc > 0]

    out: list[HostScore] = []
    for i, name in enumerate(names):
        flags = []
        for c, thr in query.hard.items():
            j = kb.capabilities.index(c)
            if C[i, j] < thr:
                flags.append(f"{c} {C[i, j]:.2f} < required {thr:.2f}")
        top = sorted(zip(kb.capabilities, contrib[i], strict=True), key=lambda kv: -kv[1])

        host = by_name[name]
        # A hard constraint reads a capability even at zero weight, so it is an
        # input to feasibility and belongs in the provenance too.
        considered = sorted(set(weighted) | set(query.hard))
        unsourced = [c for c in considered if host.provenance_of(c) != "sourced"]

        out.append(
            HostScore(
                host=name,
                score=float(scores[i]),
                sd=float(sd[i]),
                band90=float(GAUSS_90 * sd[i]),
                contributions=[(c, float(v)) for c, v in top[:top_k]],
                flags=flags,
                feasible=not flags,
                provenance="illustrative" if unsourced else "sourced",
                # Carried through for the memo to print. Deliberately absent from
                # every expression above: ADR 0010 sequences display before scoring,
                # and ranking on QPS needs a target market first (#22).
                qps=host.qps,
                unsourced=unsourced,
            )
        )
    out.sort(key=lambda d: (not d.feasible, -d.score))
    return out


def prob_meets(hostscore: HostScore, threshold: float) -> float:
    """``P(true suitability >= threshold)`` for a host, via engin-core's primitive."""
    return float(prob_at_least(np.array([hostscore.score]), np.array([hostscore.sd]), threshold)[0])
