"""Typed schema for the host-selection engine (pydantic).

A curated host-capability knowledge base + a query = a ranked, explainable host
recommendation with a confidence band. Pydantic validates the data (values and
confidences in [0, 1], every host covering every capability) so a malformed KB
fails loudly at load time rather than silently skewing a recommendation.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field, model_validator


class Host(BaseModel):
    """One microbial host: capability values and per-capability confidence.

    ``caps[c]`` in [0, 1] is how capable the host is on capability ``c`` (higher =
    better); ``conf[c]`` in [0, 1] is our confidence in that value (data
    completeness / consensus). Low confidence widens the recommendation's band.
    """

    name: str
    caps: dict[str, float] = Field(..., description="capability -> value in [0,1]")
    conf: dict[str, float] = Field(..., description="capability -> confidence in [0,1]")

    @model_validator(mode="after")
    def _check(self) -> Host:
        if set(self.caps) != set(self.conf):
            raise ValueError(f"host {self.name!r}: caps and conf must cover the same keys")
        for d, label in ((self.caps, "caps"), (self.conf, "conf")):
            for k, v in d.items():
                if not 0.0 <= v <= 1.0:
                    raise ValueError(f"host {self.name!r}: {label}[{k!r}]={v} not in [0,1]")
        return self


class KnowledgeBase(BaseModel):
    """A set of hosts scored over a shared list of capabilities."""

    capabilities: list[str]
    hosts: list[Host]
    sd_scale: float = Field(0.35, description="maps (1 - confidence) -> capability sd")

    @model_validator(mode="after")
    def _check(self) -> KnowledgeBase:
        caps = set(self.capabilities)
        if len(caps) != len(self.capabilities):
            raise ValueError("duplicate capability names")
        for h in self.hosts:
            if set(h.caps) != caps:
                missing = caps ^ set(h.caps)
                raise ValueError(f"host {h.name!r} capabilities differ from KB: {missing}")
        return self

    def matrices(self) -> tuple[list[str], NDArray[np.float64], NDArray[np.float64]]:
        """Return ``(names, C, S)``: capability matrix and capability-sd matrix.

        ``S = (1 - conf) * sd_scale`` turns confidence into a standard deviation.
        """
        names = [h.name for h in self.hosts]
        C = np.array([[h.caps[c] for c in self.capabilities] for h in self.hosts])
        conf = np.array([[h.conf[c] for c in self.capabilities] for h in self.hosts])
        S = (1.0 - conf) * self.sd_scale
        return names, C, S


class HostQuery(BaseModel):
    """A target profile: how much each capability matters, and hard requirements.

    ``weights[c] >= 0`` is the importance of capability ``c`` (renormalized to sum
    to 1 at scoring time). ``hard[c] = thr`` flags any host whose ``caps[c] < thr``
    as infeasible (e.g. glycosylation in a prokaryote), demoting it below all
    feasible hosts regardless of score.
    """

    weights: dict[str, float]
    hard: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check(self) -> HostQuery:
        for c, w in self.weights.items():
            if w < 0:
                raise ValueError(f"weight[{c!r}]={w} must be >= 0")
        if sum(self.weights.values()) <= 0:
            raise ValueError("weights must not be all zero")
        return self


class HostScore(BaseModel):
    """A scored host: suitability, uncertainty band, drivers, and flags."""

    host: str
    score: float
    sd: float
    band90: float  # 1.645 * sd, a 90% half-width
    contributions: list[tuple[str, float]]  # top per-capability contributions
    flags: list[str]  # hard-constraint violations
    feasible: bool
