"""Typed schema for protein design campaigns (pydantic).

Validates loudly at the boundary, because the failure mode this prevents is quiet:
a campaign assembled from a spreadsheet with one variant of the wrong length, or a
fitness on a different scale than the rest, will train a model that looks fine and
ranks wrongly.

The vocabulary is deliberately small — ``Variant`` (a sequence, optionally measured),
``Campaign`` (a set of measured variants), ``ScoredDesign`` (a prediction with its
uncertainty). Everything the three faces exchange is one of these.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field, field_validator, model_validator

# The 20 canonical amino acids, in a fixed order the featurizer depends on.
AMINO_ACIDS: str = "ACDEFGHIKLMNPQRSTVWY"
AA_INDEX: dict[str, int] = {a: i for i, a in enumerate(AMINO_ACIDS)}


class Variant(BaseModel):
    """One protein variant: a sequence, optionally with a measured fitness.

    ``fitness`` is the assay readout, normalized to [0, 1] by the caller so that
    campaigns from different assays can be compared. ``None`` means unmeasured — a
    candidate we want to *predict*, not train on.
    """

    variant_id: str
    sequence: str
    fitness: float | None = None

    @field_validator("sequence")
    @classmethod
    def _check_sequence(cls, v: str) -> str:
        if not v:
            raise ValueError("sequence must be non-empty")
        bad = sorted(set(v) - set(AMINO_ACIDS))
        if bad:
            raise ValueError(
                f"sequence contains non-canonical residues {bad}; expected only {AMINO_ACIDS}"
            )
        return v

    @model_validator(mode="after")
    def _check_fitness(self) -> Variant:
        if self.fitness is not None and not 0.0 <= self.fitness <= 1.0:
            raise ValueError(
                f"fitness must be normalized to [0,1] or None; got {self.fitness}. "
                "Normalize per-assay before building a Campaign."
            )
        return self

    @property
    def length(self) -> int:
        return len(self.sequence)


class Campaign(BaseModel):
    """A set of measured variants of equal length — the training substrate.

    Equal length is enforced because the default featurizer is positional. Indel
    libraries need an alignment-aware featurizer, which is out of scope at M0; the
    error says so rather than silently truncating.
    """

    campaign_id: str
    variants: list[Variant] = Field(..., min_length=1)

    @model_validator(mode="after")
    def _check_uniform(self) -> Campaign:
        lengths = {v.length for v in self.variants}
        if len(lengths) > 1:
            raise ValueError(
                f"all variants must share a length; got {sorted(lengths)}. "
                "Indel libraries need an alignment-aware featurizer (not supported at M0)."
            )
        ids = [v.variant_id for v in self.variants]
        if len(set(ids)) != len(ids):
            raise ValueError("variant_id values must be unique within a campaign")
        return self

    @property
    def length(self) -> int:
        return self.variants[0].length

    @property
    def n_measured(self) -> int:
        return sum(v.fitness is not None for v in self.variants)

    def measured(self) -> list[Variant]:
        """Only the variants carrying a fitness value."""
        return [v for v in self.variants if v.fitness is not None]

    def sequences(self) -> list[str]:
        return [v.sequence for v in self.variants]

    def fitness_array(self) -> NDArray[np.float64]:
        """Fitness of every variant; raises if any is unmeasured."""
        if self.n_measured != len(self.variants):
            raise ValueError(
                "campaign contains unmeasured variants; call measured() first "
                "or build a campaign of measured variants only"
            )
        return np.array([v.fitness for v in self.variants], float)


class ScoredDesign(BaseModel):
    """A prediction for one design: value, calibrated interval, and threshold prob.

    There is deliberately no bare ``score`` field. A consumer that wants a point
    estimate has to read ``predicted``, next to the interval that qualifies it —
    which is the whole trust proposition of the suite.
    """

    variant_id: str
    sequence: str
    predicted: float
    lower: float
    upper: float
    prob_above_threshold: float | None = None

    @model_validator(mode="after")
    def _check_interval(self) -> ScoredDesign:
        if self.lower > self.upper:
            raise ValueError(f"lower {self.lower} exceeds upper {self.upper}")
        if self.prob_above_threshold is not None:
            if not 0.0 <= self.prob_above_threshold <= 1.0:
                raise ValueError("prob_above_threshold must be in [0,1]")
        return self

    @property
    def interval_width(self) -> float:
        return self.upper - self.lower
