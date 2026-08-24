"""engin-host: chassis / host-selection decision engine.

Stage [4] of the engin strain-to-scale suite. Given a target molecule's capability
profile, score candidate microbial hosts with an explainable rationale, an honest
confidence band, and hard-constraint flags. A thin domain layer over ``engin_core``'s
uncertainty vocabulary.
"""

from __future__ import annotations

from .handoff import decision_confidence, to_decision
from .kb import CAPABILITIES, default_kb
from .memo import render_memo
from .schema import Host, HostQuery, HostScore, KnowledgeBase, QpsRecord, QpsStatus
from .scoring import prob_meets, score

__version__ = "0.1.1"

__all__ = [
    "Host",
    "KnowledgeBase",
    "HostQuery",
    "HostScore",
    "QpsRecord",
    "QpsStatus",
    "default_kb",
    "CAPABILITIES",
    "score",
    "prob_meets",
    "render_memo",
    "to_decision",
    "decision_confidence",
    "__version__",
]
