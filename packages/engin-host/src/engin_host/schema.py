"""Typed schema for the host-selection engine (pydantic).

A curated host-capability knowledge base + a query = a ranked, explainable host
recommendation with a confidence band. Pydantic validates the data (values and
confidences in [0, 1], every host covering every capability) so a malformed KB
fails loudly at load time rather than silently skewing a recommendation.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field, model_validator

Provenance = Literal["illustrative", "sourced"]
"""Where a capability value came from.

``illustrative`` is the default because it is what the shipped knowledge base
actually is -- sixty hand-assigned numbers, disclosed as such in the module
docstring, the package README and its CLAUDE.md.

The point of making it a field rather than prose is that **prose does not survive
a function boundary**. ``score()`` returns a value to two decimals with a
confidence band; a caller printing that, or feeding it into a memo, a CLI or a
``HostDecision``, has no way to know the inputs were invented. Each hop moves the
caveat one step further from the number. See #146.
"""


class Host(BaseModel):
    """One microbial host: capability values and per-capability confidence.

    ``caps[c]`` in [0, 1] is how capable the host is on capability ``c`` (higher =
    better); ``conf[c]`` in [0, 1] is our confidence in that value (data
    completeness / consensus). Low confidence widens the recommendation's band.

    ``provenance[c]`` says whether that value was sourced or invented, and
    ``sources[c]`` carries the ``sources.yaml`` id when it was sourced.

    **``conf`` and ``provenance`` are different quantities and are deliberately
    separate fields.** A cell can have high confidence and no source -- today most
    do, which reads as an evidence claim while being an editorial one. Collapsing
    them would hide exactly the thing this distinction exists to expose.
    """

    name: str
    caps: dict[str, float] = Field(..., description="capability -> value in [0,1]")
    conf: dict[str, float] = Field(..., description="capability -> confidence in [0,1]")
    provenance: dict[str, Provenance] = Field(
        default_factory=dict,
        description="capability -> 'illustrative' (default) or 'sourced'",
    )
    sources: dict[str, str] = Field(
        default_factory=dict,
        description="capability -> sources.yaml id; required where provenance is 'sourced'",
    )

    def provenance_of(self, capability: str) -> Provenance:
        """Provenance for one capability, defaulting to ``illustrative``.

        Defaulting rather than requiring the key means an existing knowledge base
        is correctly labelled with no edits, and a *new* cell cannot claim to be
        sourced by being forgotten.
        """
        return self.provenance.get(capability, "illustrative")

    @model_validator(mode="after")
    def _check(self) -> Host:
        if set(self.caps) != set(self.conf):
            raise ValueError(f"host {self.name!r}: caps and conf must cover the same keys")
        for d, label in ((self.caps, "caps"), (self.conf, "conf")):
            for k, v in d.items():
                if not 0.0 <= v <= 1.0:
                    raise ValueError(f"host {self.name!r}: {label}[{k!r}]={v} not in [0,1]")
        for key in (*self.provenance, *self.sources):
            if key not in self.caps:
                raise ValueError(f"host {self.name!r}: unknown capability {key!r}")
        # A cell claiming to be sourced must say what sourced it. Without this the
        # enum can drift from the register and "sourced" becomes an assertion
        # rather than a pointer -- the failure D23 exists to prevent.
        for cap, prov in self.provenance.items():
            if prov == "sourced" and not self.sources.get(cap):
                raise ValueError(
                    f"host {self.name!r}: {cap!r} is marked sourced but carries no sources.yaml id"
                )
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
    """A scored host: suitability, uncertainty band, drivers, and flags.

    ``provenance`` is the **worst** provenance among the weighted capabilities that
    produced this score, not an average. One invented input is enough to make the
    output not a sourced number, and reporting the majority case would let a single
    unsourced cell hide behind nine sourced ones.
    """

    host: str
    score: float
    sd: float
    band90: float  # 1.645 * sd, a 90% half-width
    contributions: list[tuple[str, float]]  # top per-capability contributions
    flags: list[str]  # hard-constraint violations
    feasible: bool
    provenance: Provenance = "illustrative"
    unsourced: list[str] = Field(
        default_factory=list,
        description="weighted capabilities behind this score that are not sourced",
    )
