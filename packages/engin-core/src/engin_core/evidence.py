"""Per-run evidence report: what a run assumed, rested on, and has not shown (#145).

The evidence discipline in this repository — ``sources.yaml``, the claim checker,
published corrections, honest baselines, the tiered-validation table — is enforced in
CI for *the project's own* claims. None of it was reachable for a *user's* run. This
module is that machinery pointed outward: the same four questions, answered per run,
for the numbers a user is about to put in front of somebody else.

## The shape, and why each section is not optional

A report has six sections, and :meth:`EvidenceReport.to_markdown` emits all six even
when one is empty, because a missing section reads as "not applicable" when what it
usually means is "nobody supplied it":

1. **Inputs and assumptions**, with defaults flagged *as* defaults. This is the section
   with a track record: the shipped :class:`~engin_core.tea.CostParameters` described a
   product class no document declared, and a report that printed those six numbers back
   at their author would have surfaced it years earlier (#122). Pydantic's
   ``model_fields_set`` is what makes the flagging honest rather than a convention —
   it records what the caller actually passed, not what happens to differ from a default.
2. **Provenance chain** — ``ProcessBrief.provenance`` finally has a consumer.
3. **Uncertainty, by kind.** A conformal interval and a propagated one are different
   objects and this project refuses to print them in the same typeface. See
   :class:`IntervalKind`.
4. **What this does not establish** — the ``D12`` tier, carrying that tier's published
   limitation verbatim.
5. **Baseline comparison** — the dumb heuristic and its number.
6. **Reproducibility stamp** — versions, seeds, dataset manifest digests.

## Why this can ship before the tools are validated

``D24`` holds visibility until the tools are validated on real data. An artefact whose
fourth section is *what this does not establish* does not overclaim by construction, so
it is publishable on the near side of that bar rather than the far side.

## What this module does not do

It does not compute anything. Every number in a report is one the caller already had;
this assembles them and refuses to let the awkward ones be dropped. That is deliberate —
a reporting layer that recomputed its inputs could disagree with the run it describes.
"""

from __future__ import annotations

import json
import platform
from enum import Enum, IntEnum
from importlib import metadata
from typing import Any

from pydantic import BaseModel, Field

from .handoff import ProcessBrief
from .tea import CostParameters, CostSummary

__all__ = [
    "Assumption",
    "Baseline",
    "EvidenceReport",
    "IntervalClaim",
    "IntervalKind",
    "ReproStamp",
    "ValidationTier",
    "assumptions_from",
    "report",
]


# --------------------------------------------------------------------- tiers


class ValidationTier(IntEnum):
    """``D12``'s five validation tiers.

    The ``does not establish`` text is the load-bearing half and is reproduced from
    ``docs/limitations.md`` rather than paraphrased, so a run's report says exactly what
    the published table says. ``tests/test_evidence_report.py`` asserts the two agree.
    """

    OWN_SIMULATOR = 1
    INDEPENDENT_SIMULATOR = 2
    REAL_INDUSTRIAL = 3
    IN_DOMAIN_DOE = 4
    PARTNER_CAMPAIGN = 5

    @property
    def source(self) -> str:
        return _TIERS[self][0]

    @property
    def establishes(self) -> str:
        return _TIERS[self][1]

    @property
    def does_not_establish(self) -> str:
        return _TIERS[self][2]


_TIERS: dict[ValidationTier, tuple[str, str, str]] = {
    ValidationTier.OWN_SIMULATOR: (
        "Engin's own simulator",
        "the loop works end to end",
        "anything about real data — the model is validated against its own assumptions",
    ),
    ValidationTier.INDEPENDENT_SIMULATOR: (
        "An independent simulator",
        "not overfitted to our own model's quirks",
        "real-world behaviour",
    ),
    ValidationTier.REAL_INDUSTRIAL: (
        "Real industrial data",
        "survives real noise, missingness, scale change",
        "in-domain performance; cost coupling, where data is normalised; behaviour "
        "under temporal drift — the split is random, not chronological",
    ),
    ValidationTier.IN_DOMAIN_DOE: (
        "In-domain literature DoE",
        "the actual product claim",
        "generalisation beyond small, heterogeneous samples",
    ),
    ValidationTier.PARTNER_CAMPAIGN: (
        "Partner campaign data",
        "end-to-end value",
        "— not yet available",
    ),
}


# ---------------------------------------------------------------- components


class IntervalKind(str, Enum):
    """How an interval earned its width. The distinction this project will not blur.

    ``cost_summary``'s docstring already draws the line — "the interval is an empirical
    quantile of the propagated samples, not a conformal one" — and a report that printed
    a cost band beside a conformal band without saying which was which would undo that
    care at the exact moment a reader is most likely to quote the number.
    """

    CONFORMAL = "conformal"
    """Split-conformal bounds. Coverage has been *measured*, and the measurement is
    published — the only kind this project calls calibrated."""

    PROPAGATED = "propagated"
    """A credible interval under the model, obtained by pushing a posterior through a
    cost model or an inflation factor. No coverage guarantee stands behind it."""

    HEURISTIC = "heuristic"
    """A width produced by a rule with neither a coverage measurement nor a posterior —
    e.g. ``inflate_uncertainty``'s ``2 - confidence`` factor."""


class IntervalClaim(BaseModel):
    """One reported interval, tagged with what kind of interval it is."""

    quantity: str
    lower: float
    upper: float
    kind: IntervalKind
    level: float | None = None
    """Nominal level, where one applies. ``None`` for a half-width with no level."""

    basis: str = ""
    """One sentence on where the width came from. Printed verbatim."""

    @property
    def width(self) -> float:
        return self.upper - self.lower


class Assumption(BaseModel):
    """One input, and whether the caller chose it or inherited it."""

    name: str
    value: Any
    is_default: bool
    note: str = ""

    @property
    def marker(self) -> str:
        return "default" if self.is_default else "set by caller"


class Baseline(BaseModel):
    """The simpler thing this run says it beats, and what that thing scored.

    ``engin_value`` is optional because the honest-baselines principle is satisfied by
    reporting the baseline's number even when the comparison has not been run — the
    unrun comparison is itself the finding, and ``docs/benchmarks.md`` marks several.
    """

    name: str
    metric: str
    baseline_value: float | None = None
    engin_value: float | None = None
    source: str = ""
    note: str = ""

    @property
    def engin_wins(self) -> bool | None:
        """``None`` when either side is missing — deliberately not ``False``."""
        if self.baseline_value is None or self.engin_value is None:
            return None
        return self.engin_value > self.baseline_value


class ReproStamp(BaseModel):
    """What somebody else needs to get this number again.

    #125 recorded that per-result seeds and versions are promised on published results
    and carried by none of them. The same plumbing serves both, so this is deliberately
    shaped like something the benchmarks page could also emit.
    """

    python: str = ""
    packages: dict[str, str] = Field(default_factory=dict)
    seeds: dict[str, int] = Field(default_factory=dict)
    dataset_manifests: dict[str, str] = Field(default_factory=dict)
    """Dataset name -> sha256, from ``engin_core.datasets.manifest_for``."""


_STAMPED_PACKAGES = ("engin-core", "numpy", "scipy", "scikit-learn", "pydantic")


def _package_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    for name in _STAMPED_PACKAGES:
        try:
            out[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            # A bare checkout with no install: absent is the honest entry, not a guess.
            out[name] = "not installed (running from source)"
    return out


# ------------------------------------------------------------------- report


class EvidenceReport(BaseModel):
    """A run's evidence trail, renderable for a person or for a machine."""

    title: str = "Engin run report"
    tier: ValidationTier
    assumptions: list[Assumption] = Field(default_factory=list)
    provenance: str = ""
    intervals: list[IntervalClaim] = Field(default_factory=list)
    baselines: list[Baseline] = Field(default_factory=list)
    repro: ReproStamp = Field(default_factory=ReproStamp)
    notes: list[str] = Field(default_factory=list)

    def to_json(self, *, indent: int = 2) -> str:
        """The machine-readable form. Enum values serialise to their names/values."""
        return json.dumps(json.loads(self.model_dump_json()), indent=indent)

    def to_markdown(self) -> str:
        """The human-readable form. All six sections, always."""
        out: list[str] = [f"# {self.title}", ""]

        out += ["## 1. Inputs and assumptions", ""]
        if self.assumptions:
            out += ["| Input | Value | Source |", "|---|---|---|"]
            for a in self.assumptions:
                note = f" — {a.note}" if a.note else ""
                out.append(f"| `{a.name}` | {a.value} | {a.marker}{note} |")
            n_default = sum(a.is_default for a in self.assumptions)
            if n_default:
                out += [
                    "",
                    f"{n_default} of {len(self.assumptions)} inputs are defaults. "
                    "Defaults describe a product class; check it is yours.",
                ]
        else:
            out.append("_No inputs recorded._")
        out.append("")

        out += ["## 2. Provenance", ""]
        out.append(f"`{self.provenance}`" if self.provenance else "_No funnel chain recorded._")
        out.append("")

        out += ["## 3. Uncertainty", ""]
        if self.intervals:
            out += ["| Quantity | Interval | Level | Kind |", "|---|---|---|---|"]
            for i in self.intervals:
                level = f"{i.level:.0%}" if i.level is not None else "—"
                out.append(
                    f"| {i.quantity} | {i.lower:.4g} – {i.upper:.4g} | "
                    f"{level} | **{i.kind.value}** |"
                )
            out.append("")
            for i in self.intervals:
                if i.basis:
                    out.append(f"- **{i.quantity}** — {i.basis}")
        else:
            out.append("_No intervals recorded._")
        out.append("")

        out += [
            "## 4. What this does not establish",
            "",
            f"**Validation tier {int(self.tier)} — {self.tier.source}.**",
            "",
            f"- Establishes: {self.tier.establishes}",
            f"- Does **not** establish: {self.tier.does_not_establish}",
            "",
        ]

        out += ["## 5. Baseline comparison", ""]
        if self.baselines:
            out += ["| Baseline | Metric | Baseline | Engin | Verdict |", "|---|---|---|---|---|"]
            for b in self.baselines:
                wins = b.engin_wins
                verdict = "not compared" if wins is None else ("Engin" if wins else "**baseline**")
                bv = "—" if b.baseline_value is None else f"{b.baseline_value:.4g}"
                ev = "—" if b.engin_value is None else f"{b.engin_value:.4g}"
                out.append(f"| {b.name} | {b.metric} | {bv} | {ev} | {verdict} |")
        else:
            out.append(
                "_No baseline supplied._ Every claim in this project is reported against "
                "the simpler thing it says it beats; a run without one has not met that bar."
            )
        out.append("")

        out += ["## 6. Reproducibility", ""]
        if self.repro.python:
            out.append(f"- Python: `{self.repro.python}`")
        for name, ver in self.repro.packages.items():
            out.append(f"- `{name}`: {ver}")
        for name, seed in self.repro.seeds.items():
            out.append(f"- seed `{name}`: {seed}")
        for name, digest in self.repro.dataset_manifests.items():
            out.append(f"- dataset `{name}`: sha256 `{digest}`")
        if not (self.repro.python or self.repro.packages or self.repro.seeds):
            out.append("_No reproducibility stamp recorded._")
        out.append("")

        if self.notes:
            out += ["## Notes", ""] + [f"- {n}" for n in self.notes] + [""]

        return "\n".join(out)


def assumptions_from(params: CostParameters) -> list[Assumption]:
    """Flatten :class:`~engin_core.tea.CostParameters` into flagged assumptions.

    ``model_fields_set`` is the whole trick: it holds the fields the caller actually
    passed, so a value that *coincides* with the default is still marked as set by the
    caller. That is the honest reading — the question this section answers is "did
    anybody think about this number", not "does it differ from ours".
    """
    out: list[Assumption] = []
    explicit = params.model_fields_set
    for name, value in params.model_dump().items():
        if name == "scale":
            continue
        out.append(Assumption(name=name, value=value, is_default=name not in explicit))
    scale = params.scale
    if scale is None:
        out.append(
            Assumption(
                name="scale",
                value=None,
                is_default="scale" not in explicit,
                note="no production scale set — costs price the bench vessel, not a plant",
            )
        )
    else:
        scale_explicit = scale.model_fields_set
        for name, value in scale.model_dump().items():
            out.append(
                Assumption(
                    name=f"scale.{name}",
                    value=value,
                    is_default=name not in scale_explicit,
                )
            )
    return out


def report(
    *,
    tier: ValidationTier,
    params: CostParameters | None = None,
    brief: ProcessBrief | None = None,
    cost: CostSummary | None = None,
    cost_level: float = 0.90,
    baselines: list[Baseline] | None = None,
    seeds: dict[str, int] | None = None,
    dataset_manifests: dict[str, str] | None = None,
    title: str = "Engin run report",
    notes: list[str] | None = None,
) -> EvidenceReport:
    """Assemble a run report from the objects a run already produced.

    Every argument is optional except ``tier``, and that asymmetry is the point: a
    report with no cost model and no funnel chain is still a legitimate artefact, but a
    report that does not say which validation tier it corresponds to is the thing this
    module exists to prevent.

    The interval kinds are assigned here rather than supplied by the caller, because
    they are properties of the code that produced each number and not of the run:
    ``cost_summary`` returns propagated quantiles, and ``ProcessBrief.uncertainty`` is a
    heuristic inflation of a conformal half-width. Neither is a judgement call.
    """
    intervals: list[IntervalClaim] = []
    if cost is not None:
        intervals.append(
            IntervalClaim(
                quantity="cost (USD/kg)",
                lower=cost.lower_usd_per_kg,
                upper=cost.upper_usd_per_kg,
                kind=IntervalKind.PROPAGATED,
                level=cost_level,
                basis=(
                    "an empirical quantile of the propagated samples, not a conformal "
                    "one. Conformal calibration would need held-out cost observations, "
                    "which require a costed campaign nobody has run."
                ),
            )
        )
    if brief is not None:
        intervals.append(
            IntervalClaim(
                quantity="manufacturability (half-width)",
                lower=brief.expected_manufacturability - brief.uncertainty,
                upper=brief.expected_manufacturability + brief.uncertainty,
                kind=IntervalKind.HEURISTIC,
                basis=(
                    "the pathway stage's conformal half-width multiplied by "
                    "`inflate_uncertainty`'s `2 - confidence` factor. Wider than a "
                    "calibrated interval by construction; nothing has checked its coverage."
                ),
            )
        )

    notes = list(notes or [])
    if cost is not None and cost.prob_meets_target is not None:
        notes.append(
            f"P(clears {cost.target_usd_per_kg:g} USD/kg) = {cost.prob_meets_target:.2f}, "
            "under the same propagated samples as the cost interval above."
        )

    return EvidenceReport(
        title=title,
        tier=tier,
        assumptions=assumptions_from(params) if params is not None else [],
        provenance=brief.provenance if brief is not None else "",
        intervals=intervals,
        baselines=list(baselines or []),
        repro=ReproStamp(
            python=platform.python_version(),
            packages=_package_versions(),
            seeds=dict(seeds or {}),
            dataset_manifests=dict(dataset_manifests or {}),
        ),
        notes=notes,
    )
