"""Techno-economic head: a calibrated titer posterior in, a cost distribution out.

Implements **D8** (the cost model is public) and **D13** (the objective is net cost
per kilogram, not titer).  # ref: 2024-konzock-try-costs

## What this module is, and deliberately is not

**It is the coupling.** Monte-Carlo techno-economic analysis is a solved, tooled
problem — BioSTEAM does it natively, and SuperPro Designer with Crystal Ball has for
years. Rebuilding that would be reinventing a wheel, which `D9` forbids. What is
genuinely underexplored is using a *calibrated machine-learning posterior* as the
uncertainty source, rather than hand-specified parameter distributions. That seam is
what lives here.

**It is not a process simulator.** :class:`ParametricCostModel` is a transparent
three-term caricature for the default light path. For real numbers, install the
``tea`` extra and use :class:`BioSteamCostModel`, which drives an actual flowsheet.
The two share the :class:`CostModel` protocol, so everything above them — posterior
propagation, cost-space acquisition, the recommender — is backend-agnostic.

## Why the cost centres are split this way

The parametric model follows the **TRY** framing, in which the three process metrics
map to three cost centres:

| Metric | Cost centre | Typical share of precision-fermentation COGS |
|---|---|---|
| **yield** | raw material / media | dominant; >50% for commodities [1] |
| **rate** | facility, reactor occupancy | sets reactor scale [1] |
| **titer** | downstream processing | sets separation burden [1] |

[1] Konzock & Nielsen, *TRYing to evaluate production costs in microbial
biotechnology*, Trends in Biotechnology (2024), doi:10.1016/j.tibtech.2024.04.007.
The mapping is theirs; titer is "an integrative metric [that] does not say much
about either the performance of the cell factory or the fermentation process".
An earlier version of this table gave a 35-50 / 20-25 / 15-20 split. Those
figures were not sourceable and are gone -- see D13.

**These defaults describe a product class, and it is worth saying which.** A
$200/kg target against a $46/kg recovery cost at a 40 g/L reference titer is
**specialty / enzyme-class economics**. It is not ethanol, and it is not a
biopharmaceutical either. Nothing in this module said so until 2026-08-18, which
made the comparison below hard to read (#122).

**The simulator understates raw material, but by less than this docstring used to
claim.** With glucose at ~$0.55/kg and this simulator's substrate-to-product ratio
of ~3.6 kg/kg at 1–2 L scale, raw material lands near **2%** of modelled cost.
Reaching a *commodity* share would require substrate at roughly **$28/kg**, which
is not a feedstock, it is a fiction.

**But a commodity share is the wrong benchmark for these defaults, and comparing
against it was a category error.** This paragraph used to read "not the dominant
share the literature describes", citing Konzock's ">50% of the total costs ... for
commodity products such as ethanol". `D13`'s other citation says the split *slides
with selling price*: Straathof puts downstream at roughly 15% for ethanol at
~$0.5/kg, rising to 60-70% for enzymes and 45-92% for biopharmaceuticals against
20-40% for bulk products. **A $200/kg product is not supposed to have commodity
cost structure.** Being downstream-dominated at that price point is the predicted
behaviour, not the anomaly.

**The gap is real and smaller than stated.** 2% still sits below the 15-60%
carbohydrate-feedstock range Straathof reports across every process he analysed,
so the simulator does understate feedstock even for a specialty product. What
cannot be stated is *by how much*, because the number it should be compared
against is a function of the product class -- which is `D13`'s own argument, and
is why declaring the class above is a prerequisite rather than a nicety.

The consequence for optimization is unchanged: **the yield lever is nearly
invisible on this simulator**, so cost optimization here is driven by the other
two terms. Anyone using this to argue about industrial economics needs a
representative process, not this one.

**Yield is not an input here, and that was argued rather than overlooked (#304).**
The proposal was to give this model an explicit yield axis, on the reading that
yield is "algebraically slaved to titer, not an axis anything can be optimized
along". That reading holds at a *fixed design point* -- which is where
:func:`break_even` stands, and why its docstring is right -- and not across design
points, which is the space :func:`recommend_batch_by_cost` searches. Measured over
40,000 random designs plus all 32 corners, reachable yield is 0.22-0.69 g/g and
varies about 1.8x within a fixed titer band. <!-- not-a-claim: measured on our own simulator -->

So the lever is representable already. What the model lacks is a yield *parameter*,
and adding one would let a caller name a ``(titer, yield)`` pair no design realises
-- turning ``cost_per_kg`` from "what this candidate costs" into "what this
hypothetical costs". The first is what an acquisition function needs. The second is
what a fitted *surface* needs, and ``benchmarks/try_cost_form.py`` already provides
it by sampling the two independently, which is why its yield range runs far past
anything the simulator produces.

The identity that makes both true: ``raw_material`` **is**
``substrate_usd_per_kg / yield``, exactly. This model is already parameterised by
yield; it simply reaches it through the design point rather than through an
argument.

**Note the sign on titer, because an earlier version of this module had it backwards.**
Higher titer *reduces* downstream cost — less water to remove, smaller equipment,
fewer unit operations. It does not raise it. The reason titer is nonetheless the wrong
optimization target is that it is an *integrative* metric, inflatable by running
longer or at higher biomass, and it says nothing about the raw-material cost that
dominates. See `D13` in ``DECISIONS.md``, including the withdrawn justification.
"""

from __future__ import annotations

from enum import Enum
from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import ArrayLike, NDArray
from pydantic import BaseModel, Field
from scipy.optimize import brentq

from .gp import GP, prob_at_least
from .recommend import _is_far_enough
from .simulator import DEFAULT_REACTOR, ReactorConfig, unit_to_physical

__all__ = [
    "CostParameters",
    "ProductionScale",
    "bioreactor_direct_cost_usd",
    "capital_charge_factor",
    "annual_capital_charge_usd",
    "capital_cost_per_batch_usd",
    "PurityGrade",
    "purity_dsp_multiplier",
    "CostModel",
    "ParametricCostModel",
    "BioSteamCostModel",
    "CostSummary",
    "design_context",
    "cost_samples",
    "cost_summary",
    "BreakEven",
    "break_even",
    "expected_cost_reduction",
    "recommend_batch_by_cost",
]


# --------------------------------------------------------------------- context


def design_context(
    U: ArrayLike, config: ReactorConfig | None = None
) -> dict[str, NDArray[np.float64]]:
    """Quantities that follow from the design point alone, with no simulation.

    Substrate fed and final volume are fixed by the knobs, which is what lets cost be
    evaluated for a *candidate* design rather than only for one already run — and
    therefore what lets cost sit inside an acquisition function.

    ``config`` defaults to the bundled vessel. Passing the same config used for the
    simulation is what keeps the cost denominated in the user's own reactor.

    **The fed volume is capped at ``config.vmax``**, because that is what
    :func:`~engin_core.simulate` does — feeding stops once the vessel is
    full. *(Corrected 2026-08-15: this previously integrated the feed over the whole
    run with no cap, so for aggressive-feed designs it reported a volume the vessel
    could not hold — 3.700 L against a 2.5 L working volume at the extreme, on 15 of
    40 sampled designs.* <!-- not-a-claim: measured on our own simulator --> *The
    effect on cost per kilogram was near zero, because ``final_volume_L`` divides out
    of both the facility and raw-material terms; the defect was that two parts of one
    package disagreed about how much liquid was in the vessel, which would bite
    differently once ``vmax`` became a user setting.)*
    """
    cfg = config or DEFAULT_REACTOR
    phys = np.atleast_2d(unit_to_physical(U, cfg))
    feed_rate, feed_start, Sf, _induction, S0 = (phys[:, i] for i in range(5))

    uncapped = feed_rate * np.maximum(cfg.t_end - feed_start, 0.0)
    fed_volume = np.minimum(uncapped, max(cfg.vmax - cfg.v0, 0.0))
    final_volume = cfg.v0 + fed_volume
    return {
        "substrate_fed_g": S0 * cfg.v0 + fed_volume * Sf,
        "final_volume_L": final_volume,
        "reactor_L_h": final_volume * cfg.t_end,
    }


# ---------------------------------------------------------------- cost models


class ProductionScale(BaseModel):
    """Plant scale, and the capital recovery that follows from it (#143 piece 1).

    **Opt-in.** :class:`CostParameters` leaves this ``None``, in which case the cost
    model behaves exactly as it did before and every previously published number is
    unchanged. Setting it adds a capital term the flat ``reactor_usd_per_L_h`` rate
    cannot express, because that rate is linear in volume and capital is not.

    Everything here is Humbird (2021), which is the correlation #143 said had to be
    sourced before any code.  # ref: 2021-humbird-scaleup-economics

    **The issue asked for a scale exponent and the source does not have one.** The
    published correlation is *piecewise linear with an intercept*:

        TDC[$k] = 30.7 * V + 800     (V >= 0.33 m3)
        TDC[$k] = 2285 * V + 49.5    (V <  0.33 m3)

    The economy of scale is real but it lives in that fixed 800 and in a direct-cost
    factor that falls from 12.1x at 1 m3 to 1.8x at 200 m3 — not in a six-tenths
    exponent. Fitting an exponent to it would have been a plausible functional form
    invented here, which is what CONTRIBUTING rule 1 rejects and what this field set
    exists to avoid.

    **What does not transfer, stated rather than smoothed over.** The correlation is
    developed for animal cell culture. The *vessel* it prices is standard bioprocess
    hardware — ASME BPE, 316L, CIP/SIP, full-vacuum design — which is why it is used
    here for microbial fermentation, but that transfer is an argument, not a
    measurement, and no source establishes it. The cell-type-specific conclusions in
    the same paper (the CO2-inhibition ceiling, the 20 m3 optimum) are **not** carried
    over. See ``docs/limitations.md``.
    """

    working_volume_m3: float = Field(..., gt=0)
    """Production vessel working volume. Distinct from ``ReactorConfig.vmax``, which
    is the *simulated* vessel — the whole point of #143 is that the two differ."""

    n_vessels: int = Field(1, ge=1)
    """Production bioreactors in the facility. Capital is per vessel; a train of small
    vessels and one large vessel cost differently, which is the comparison this
    enables."""

    batches_per_year: float = Field(..., gt=0)
    """Completed batches per vessel per year. Turns a capital stock into a per-batch
    charge, and is where turnaround and downtime enter."""

    capital_charge_rate: float = Field(0.075, gt=0, lt=1)
    """Discount rate ``i`` in the capital charge factor. Humbird's 7.5%, described
    there as a common value for food manufacturing facilities."""

    capital_lifetime_years: int = Field(10, ge=1)
    """Amortization period ``n``. Humbird's 10 years, same basis."""

    indirect_cost_factor: float = Field(0.6, ge=0)
    """Engineering and construction fees applied to total direct cost."""

    contingency_factor: float = Field(0.15, ge=0)
    """Contingency applied to total plant cost to reach total capital investment."""


def bioreactor_direct_cost_usd(working_volume_m3: float) -> float:
    """Total direct cost of one installed bioreactor, from Humbird (2021) Equation 9.

    Piecewise linear in volume, in 2020-ish USD. Reproduces that paper's own cost
    table to within about 10% across 1-200 m3, which is the range it is stated over;
    outside it this is extrapolation and the caller is not warned, because the paper
    gives no basis for a warning threshold.

    # ref: 2021-humbird-scaleup-economics
    """
    v = float(working_volume_m3)
    if v <= 0:
        raise ValueError(f"working_volume_m3 must be positive, got {working_volume_m3}")
    thousands = 30.7 * v + 800.0 if v >= 0.33 else 2285.0 * v + 49.5
    return thousands * 1_000.0


def capital_charge_factor(rate: float = 0.075, years: int = 10) -> float:
    """Annual capital charge as a fraction of total capital investment.

    Humbird (2021) Equation 10, ``i / (1 - (1 + i)^-n)`` — the standard capital
    recovery factor. At the defaults (7.5%, 10 years) this is about 0.15/y, the
    figure that paper uses.

    # ref: 2021-humbird-scaleup-economics
    """
    if not 0.0 < rate < 1.0:
        raise ValueError(f"rate must be in (0, 1), got {rate}")
    if years < 1:
        raise ValueError(f"years must be >= 1, got {years}")
    return rate / (1.0 - (1.0 + rate) ** -years)


def annual_capital_charge_usd(scale: ProductionScale) -> float:
    """Annualized capital cost of the production bioreactors.

    The chain is Humbird's: total direct cost -> total plant cost (indirect factor)
    -> total capital investment (contingency) -> annual charge (capital charge
    factor). Bioreactors only — minor process equipment, buildings and utilities are
    out of scope here and their absence is a floor on the number, not a rounding
    error.

    # ref: 2021-humbird-scaleup-economics
    """
    direct = bioreactor_direct_cost_usd(scale.working_volume_m3) * scale.n_vessels
    total_plant = direct * (1.0 + scale.indirect_cost_factor)
    total_capital = total_plant * (1.0 + scale.contingency_factor)
    ccf = capital_charge_factor(scale.capital_charge_rate, scale.capital_lifetime_years)
    return total_capital * ccf


def capital_cost_per_batch_usd(scale: ProductionScale) -> float:
    """Annual capital charge apportioned over a year of batches."""
    return annual_capital_charge_usd(scale) / (scale.batches_per_year * scale.n_vessels)


class PurityGrade(str, Enum):
    """Product specification, as a cost axis (#17).

    Demirel's argument is that the field's systematic error is purifying to
    pharmaceutical grade for commodity products that do not need it. The cost
    model could not express that at all, because specification entered nowhere.

    **Two grades exist here, and that is a statement about the evidence rather
    than a simplification for convenience.** Straathof names exactly two points
    for the same molecules at the same scale; a third grade would be a number
    somebody made up.  # ref: 2011-straathof-downstream-costs
    """

    CRUDE = "crude"
    """Recovered but not purified or formulated -- Straathof's crude penicillin G
    and crude lipase, near 25% DSP share of production cost."""

    PURIFIED = "purified"
    """Purified and formulated. Straathof puts the same products near the 50-55%
    range at this specification."""


#: DSP share of total production cost at each grade (Straathof 2011). The
#: purified figure is the midpoint of the published 50-55% range.
_DSP_SHARE: dict[PurityGrade, float] = {
    PurityGrade.CRUDE: 0.25,
    PurityGrade.PURIFIED: 0.525,
}


def purity_dsp_multiplier(
    grade: PurityGrade | str,
    crude_share: float = _DSP_SHARE[PurityGrade.CRUDE],
    purified_share: float = _DSP_SHARE[PurityGrade.PURIFIED],
) -> float:
    """Multiplier on the downstream term for ``grade``, relative to crude.

    **Straathof reports shares of production cost, not $/kg**, so the conversion
    is explicit rather than a rescaling. For a fixed upstream cost ``U``, a DSP
    share ``s`` implies ``DSP = U * s / (1 - s)``; the multiplier between two
    grades is the ratio of those. From 25% to the published 50-55% range that is
    **3.0x to 3.7x**, and 3.3x at the midpoint.

    The held-fixed assumption is load-bearing and deliberate: purifying further
    adds unit operations to the same fermentation, so upstream cost is what stays
    put. Holding *total* cost fixed instead gives 2.1x and would be wrong, because
    it assumes purification is free in aggregate.

    **Calibrated for bulk and intermediate-scale products; it does not transfer
    to affinity-purified ones.** A 2025 techno-economic study of formate
    dehydrogenase -- a His-tagged enzyme where IMAC resin is 65% of variable
    operating cost -- reports crude-to-pure ratios of 13x to 43x across its
    scenarios, an order of magnitude above this figure.
    # ref: 2025-fdh-fermentation-tea
    For that product class pass explicit shares, or set
    ``purity_multiplier_override`` on :class:`CostParameters`. One global constant
    would be wrong for one class or the other, which is why there is not one.

    # ref: 2011-straathof-downstream-costs
    """
    grade = PurityGrade(grade)
    for name, share in (("crude_share", crude_share), ("purified_share", purified_share)):
        if not 0.0 < share < 1.0:
            raise ValueError(f"{name} must be a share in (0, 1), got {share}")
    if grade is PurityGrade.CRUDE:
        return 1.0
    return (purified_share / (1.0 - purified_share)) / (crude_share / (1.0 - crude_share))


class CostParameters(BaseModel):
    """Illustrative cost structure. Values are a caricature, not a real process.

    Data rather than constants, so substituting your own economics is a keyword
    argument and a sensitivity sweep is a loop.
    """

    substrate_usd_per_kg: float = Field(0.55, gt=0)
    """Media cost, glucose-scale. The *yield* lever — dominant in real COGS, but see
    the module docstring: it is nearly invisible at this simulator's scale."""

    reactor_usd_per_L_h: float = Field(0.045, gt=0)
    """Vessel occupancy — capital recovery, utilities, labour. The *rate* lever."""

    downstream_base_usd_per_kg: float = Field(46.0, gt=0)
    """Recovery cost at the reference titer. The *titer* lever."""

    downstream_reference_titer_g_L: float = Field(40.0, gt=0)
    """Titer at which the base downstream cost applies. Set near the simulator's
    median so the reference is a real operating point rather than an arbitrary one."""

    downstream_titer_exponent: float = Field(0.55, ge=0)
    """How fast downstream cost *falls* as titer rises. Zero disables the effect."""

    target_usd_per_kg: float = Field(200.0, gt=0)
    """The bar a process must clear to be worth building."""

    scale: ProductionScale | None = None
    """Production scale and capital recovery (#143 piece 1). ``None`` keeps the
    pre-#143 behaviour exactly, so no previously published number moves; set it to
    price the plant rather than the bench vessel."""

    purity_grade: PurityGrade = PurityGrade.CRUDE
    """Product specification (#17). Defaults to ``CRUDE``, whose multiplier is
    1.0, so every previously published number is unchanged and setting this is
    the only way to move it."""

    purity_multiplier_override: float | None = Field(None, gt=0)
    """Use this multiplier instead of the Straathof-derived one. The escape hatch
    for product classes the default does not cover -- affinity-purified proteins
    sit an order of magnitude higher. See ``purity_dsp_multiplier``."""

    @property
    def purity_multiplier(self) -> float:
        """The multiplier actually applied to the downstream term."""
        if self.purity_multiplier_override is not None:
            return self.purity_multiplier_override
        return purity_dsp_multiplier(self.purity_grade)


@runtime_checkable
class CostModel(Protocol):
    """Maps a titer and a design point to a cost per kilogram.

    The seam that lets a parametric caricature and a BioSTEAM flowsheet be
    interchangeable everywhere above this line.
    """

    def cost_per_kg(self, titer_g_L: ArrayLike, U: ArrayLike) -> NDArray[np.float64]: ...


class ParametricCostModel:
    """Three-term TRY cost model. The light default — no extra dependencies."""

    def __init__(
        self,
        params: CostParameters | None = None,
        config: ReactorConfig | None = None,
    ) -> None:
        """``config`` is the vessel the design points are interpreted against.

        It is held on the instance rather than added to :class:`CostModel`, because that
        protocol is the seam a BioSTEAM flowsheet also has to fit, and a flowsheet owns
        its own geometry. Keeping the signature at ``(titer, U)`` leaves the two models
        interchangeable everywhere above this line.
        """
        self.params = params or CostParameters()
        self.config = config or DEFAULT_REACTOR

    def cost_per_kg(self, titer_g_L: ArrayLike, U: ArrayLike) -> NDArray[np.float64]:
        p = self.params
        titer = np.maximum(np.asarray(titer_g_L, float), 1e-6)
        ctx = design_context(U, self.config)

        product_kg = np.maximum(titer * ctx["final_volume_L"] / 1000.0, 1e-9)

        # yield lever: substrate bought per kilogram actually recovered
        raw_material = (ctx["substrate_fed_g"] / 1000.0) * p.substrate_usd_per_kg / product_kg
        # rate lever: vessel-hours per kilogram
        facility = ctx["reactor_L_h"] * p.reactor_usd_per_L_h / product_kg
        # titer lever: dilute broth means more volume to process per kilogram.
        # Falls with titer. The sign here is the one D13 originally had backwards.
        downstream = (
            p.downstream_base_usd_per_kg
            * ((p.downstream_reference_titer_g_L / titer) ** p.downstream_titer_exponent)
            * p.purity_multiplier
        )
        return raw_material + facility + downstream + self._capital(titer)

    def _capital(self, titer: NDArray[np.float64]) -> NDArray[np.float64]:
        """Annualized bioreactor capital per kilogram, or zero when scale is unset.

        The batch is priced at *production* scale rather than at the simulated
        vessel's: the design point fixes titer, and titer times the production
        working volume is what a plant batch yields. That substitution is the whole
        content of #143 piece 1 — without it, capital per kilogram at 2 L and at
        20 m3 differ only linearly, which is the failure mode the issue describes.
        """
        scale = self.params.scale
        if scale is None:
            return np.zeros_like(np.asarray(titer, float))
        # g/L * m3 * (1000 L/m3) / (1000 g/kg) == g/L * m3, in kg.
        batch_kg = np.maximum(np.asarray(titer, float) * scale.working_volume_m3, 1e-9)
        return capital_cost_per_batch_usd(scale) / batch_kg

    def cost_breakdown(self, titer_g_L: ArrayLike, U: ArrayLike) -> dict[str, NDArray[np.float64]]:
        """Per-centre costs, for checking the shares land where the literature says."""
        p = self.params
        titer = np.maximum(np.asarray(titer_g_L, float), 1e-6)
        ctx = design_context(U, self.config)
        product_kg = np.maximum(titer * ctx["final_volume_L"] / 1000.0, 1e-9)
        return {
            "raw_material": (ctx["substrate_fed_g"] / 1000.0) * p.substrate_usd_per_kg / product_kg,
            "facility": ctx["reactor_L_h"] * p.reactor_usd_per_L_h / product_kg,
            "downstream": p.downstream_base_usd_per_kg
            * ((p.downstream_reference_titer_g_L / titer) ** p.downstream_titer_exponent)
            * p.purity_multiplier,
            "capital": self._capital(titer),
        }


class BioSteamCostModel:
    """Cost from a BioSTEAM flowsheet. Requires the ``tea`` extra.

    Deliberately thin. BioSTEAM owns the process model and the economics; this class
    exists only to present them through :class:`CostModel` so the posterior-propagation
    machinery above is unchanged.

    **Not installed by default**, for two concrete reasons: BioSTEAM requires Python
    ≥ 3.12 while this package supports 3.10+, and it pulls roughly forty transitive
    dependencies including ``numba`` and ``thermo``. Keeping it optional preserves the
    light default path (ADR 0002) without giving up `D9` where it matters.

        pip install "engin-core[tea]"
    """

    def __init__(self, build_model, titer_parameter: str = "titer") -> None:
        """``build_model`` returns a configured ``biosteam.Model``.

        Injection is left to the caller because a flowsheet is domain-specific — there
        is no single fermentation-and-recovery train this library could presume.
        """
        try:
            import biosteam  # noqa: F401
        except ModuleNotFoundError as exc:  # pragma: no cover - depends on extra
            raise ModuleNotFoundError(
                "BioSteamCostModel needs the 'tea' extra: pip install 'engin-core[tea]'. "
                "Note BioSTEAM requires Python >= 3.12."
            ) from exc
        self._build_model = build_model
        self._titer_parameter = titer_parameter

    def cost_per_kg(self, titer_g_L: ArrayLike, U: ArrayLike) -> NDArray[np.float64]:
        """Evaluate the flowsheet at each titer, returning cost per kilogram.

        Uses BioSTEAM's ``Model.load_samples`` / ``evaluate`` path, which accepts
        externally generated sample arrays — the reason this coupling is possible at
        all rather than a fight with the tool.
        """
        titer = np.atleast_1d(np.asarray(titer_g_L, float))
        model = self._build_model(U)
        model.load_samples(titer.reshape(-1, 1))
        model.evaluate()
        return np.asarray(model.table.iloc[:, -1].to_numpy(), float)


# ------------------------------------------------------- posterior propagation


def cost_samples(
    gp: GP,
    U: ArrayLike,
    model: CostModel | None = None,
    n_samples: int = 2000,
    seed: int = 0,
) -> NDArray[np.float64]:
    """Monte-Carlo cost samples, propagating the GP's titer posterior into COGS.

    Returns ``(n_designs, n_samples)``. A point cost estimate hides that the titer it
    rests on is uncertain, and the hiding is not symmetric: cost is a non-linear
    function of titer, so the cost distribution is skewed even when the titer
    posterior is Gaussian.
    """
    model = model or ParametricCostModel()
    U = np.atleast_2d(np.asarray(U, float))
    mean, sd = gp.predict(U)
    rng = np.random.default_rng(seed)
    draws = np.maximum(rng.normal(mean[:, None], sd[:, None], size=(len(U), n_samples)), 1e-6)
    return np.array([model.cost_per_kg(draws[i], U[i]) for i in range(len(U))])


class CostSummary(BaseModel):
    """A cost forecast for one design. Deliberately has no bare ``cost`` field."""

    expected_usd_per_kg: float
    lower_usd_per_kg: float
    upper_usd_per_kg: float
    prob_meets_target: float
    target_usd_per_kg: float

    @property
    def interval_width(self) -> float:
        return self.upper_usd_per_kg - self.lower_usd_per_kg


def cost_summary(
    gp: GP,
    U: ArrayLike,
    model: CostModel | None = None,
    params: CostParameters | None = None,
    level: float = 0.90,
    n_samples: int = 2000,
    seed: int = 0,
) -> list[CostSummary]:
    """Per-design cost forecast: expectation, interval, and P(clears target).

    The interval is an **empirical quantile of the propagated samples, not a conformal
    one**. Conformal calibration would need held-out *cost* observations, which require
    a costed campaign nobody has run. Reported as what it is — a propagated credible
    interval under the model. Do not describe it as calibrated; that word is reserved
    here for intervals whose coverage has been checked.
    """
    p = params or CostParameters()
    samples = cost_samples(gp, U, model, n_samples=n_samples, seed=seed)
    lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2
    return [
        CostSummary(
            expected_usd_per_kg=float(row.mean()),
            lower_usd_per_kg=float(np.quantile(row, lo_q)),
            upper_usd_per_kg=float(np.quantile(row, hi_q)),
            prob_meets_target=float(np.mean(row <= p.target_usd_per_kg)),
            target_usd_per_kg=p.target_usd_per_kg,
        )
        for row in samples
    ]


# ----------------------------------------------------------------- acquisition


class BreakEven(BaseModel):
    """What would have to be true for a design to clear its price target (#143 piece 2).

    ``cost_summary`` answers "given this process, what does it cost". This answers
    the question the other way round, which is the one somebody deciding whether to
    start actually has: a molecule, a market price, and no process yet.
    """

    solve_for: str
    """Which quantity was inverted. Only ``"titer"`` today -- see :func:`break_even`."""

    target_usd_per_kg: float

    value: float | None
    """The break-even titer in g/L, or ``None`` when the target is unreachable
    anywhere in the searched range."""

    reachable: bool
    cost_at_value: float | None
    searched: tuple[float, float]
    """The bracket that was searched. Reported because "unreachable" is a statement
    about this interval, not about physics."""

    prob_reaching: float | None = None
    """``P(titer >= value)`` under the GP posterior, when a fitted model was given.
    **This is the uncertainty that exists here**, and it is not an interval on
    ``value`` -- see :func:`break_even`."""

    note: str = ""


def break_even(
    U: ArrayLike,
    model: CostModel | None = None,
    params: CostParameters | None = None,
    solve_for: str = "titer",
    bracket: tuple[float, float] = (0.1, 500.0),
    gp: GP | None = None,
    n_samples: int = 2000,
    seed: int = 0,
) -> BreakEven:
    """Invert the cost model: what titer would clear ``target_usd_per_kg``?

    A root-find over :meth:`CostModel.cost_per_kg`, which is monotone decreasing in
    titer for the shipped parametric model -- more product per batch spreads the
    same substrate, vessel-hours and recovery burden over more kilograms.

    **The interval this issue asked for does not exist, and that is worth stating
    rather than approximating.** #143 piece 2 specifies "an interval from the same
    propagated samples ``cost_summary`` already uses". Those samples vary exactly one
    thing: titer, drawn from the GP posterior. The break-even titer is the inverse of
    a *fixed* cost curve at a *fixed* design point, so it is a deterministic root --
    there is no distribution over it to summarise. Inverting each posterior draw
    returns the same number every time.

    The uncertainty that genuinely exists is the other half: whether the process
    reaches that titer. Pass ``gp`` and this reports ``prob_reaching``, computed from
    the same posterior, which is the honest counterpart and the exact inverse of
    ``CostSummary.prob_meets_target``.

    **Monotonicity is verified, not assumed.** :class:`CostModel` is a protocol, and
    :class:`BioSteamCostModel` drives a real flowsheet with no such guarantee. A root
    find that silently returns one of several roots is worse than one that refuses,
    so the bracket is scanned first and a non-monotone curve raises.

    **Only ``solve_for="titer"`` is available.** Not an oversight in either case:

    - ``"scale"`` is now representable -- :class:`ProductionScale` landed with #143
      piece 1 -- and inverting it is ordinary follow-up work rather than a blocked
      dependency. It is simply not done here, so it raises rather than pretending
      the axis does not exist.
    - ``"yield"`` has nothing to solve for. Substrate fed is fixed by the design
      knobs via :func:`design_context`, so yield is ``titer * volume / substrate``
      and inverting it at a fixed design *is* inverting titer. A separate
      ``solve_for="yield"`` would return the same root wearing a different label.

    Returns a :class:`BreakEven`. ``reachable=False`` means the target is not met
    anywhere in ``bracket`` -- a statement about the searched range, which is
    reported alongside, rather than about physics.
    """
    if solve_for != "titer":
        raise ValueError(
            f"solve_for={solve_for!r} is not available; only 'titer' is. "
            "'scale' is representable but not implemented here; 'yield' is "
            "degenerate with titer at a fixed design point (see the docstring)."
        )
    lo, hi = (float(b) for b in bracket)
    if not 0 < lo < hi:
        raise ValueError(f"bracket must satisfy 0 < lo < hi, got {bracket}")

    p = params or CostParameters()
    # `p` has to reach the *model*, not only the target. Building the default model
    # without it silently inverted a cost curve with default purity and no scale
    # while reporting the caller's target -- so purity_grade and scale changed
    # nothing, which is the bug `test_break_even_sees_purity_and_scale` now pins.
    # An explicitly supplied model owns its own parameters; `p` then contributes
    # only `target_usd_per_kg`, and it is the caller's job to keep the two aligned.
    model = model or ParametricCostModel(p)
    U = np.atleast_2d(np.asarray(U, float))
    if len(U) != 1:
        raise ValueError(f"break_even inverts one design at a time, got {len(U)}")
    target = p.target_usd_per_kg

    def cost_at(titer: float) -> float:
        return float(np.asarray(model.cost_per_kg(np.array([titer]), U)).ravel()[0])

    grid = np.geomspace(lo, hi, 64)
    costs = np.array([cost_at(t) for t in grid])
    if not np.all(np.diff(costs) < 1e-12):
        raise ValueError(
            "cost is not monotone decreasing in titer over the bracket, so a root "
            "find is not well posed. This holds for ParametricCostModel; a "
            "flowsheet-backed CostModel carries no such guarantee. Narrow the "
            "bracket or invert that model directly."
        )

    if costs[-1] > target:
        return BreakEven(
            solve_for=solve_for,
            target_usd_per_kg=target,
            value=None,
            reachable=False,
            cost_at_value=None,
            searched=(lo, hi),
            note=(
                f"cost stays above ${target:,.2f}/kg across the whole bracket "
                f"(${costs[-1]:,.2f}/kg even at {hi:g} g/L). Titer alone does not "
                "close this gap for this design."
            ),
        )
    if costs[0] <= target:
        return BreakEven(
            solve_for=solve_for,
            target_usd_per_kg=target,
            value=lo,
            reachable=True,
            cost_at_value=float(costs[0]),
            searched=(lo, hi),
            note=(
                f"the target is already met at the bottom of the bracket ({lo:g} g/L), "
                "so the break-even titer is at or below it rather than at this value."
            ),
        )

    root = float(brentq(lambda t: cost_at(t) - target, lo, hi, xtol=1e-6))
    out = BreakEven(
        solve_for=solve_for,
        target_usd_per_kg=target,
        value=root,
        reachable=True,
        cost_at_value=cost_at(root),
        searched=(lo, hi),
    )
    if gp is not None:
        mean, sd = gp.predict(U)
        out.prob_reaching = float(prob_at_least(mean, sd, root)[0])
        out.note = (
            "prob_reaching is P(titer >= break-even) under the GP posterior. It is "
            "the uncertainty that exists here; the break-even titer itself is a "
            "deterministic root, not a distribution."
        )
    return out


def expected_cost_reduction(
    gp: GP,
    U: ArrayLike,
    best_cost: float,
    model: CostModel | None = None,
    n_samples: int = 512,
    seed: int | None = 0,
) -> NDArray[np.float64]:
    """``E[max(best_cost - cost, 0)]`` — expected improvement in cost space.

    Monte Carlo rather than closed form: cost is a non-linear transform of titer, so
    the cost distribution is not Gaussian even when the titer posterior is, and the
    analytic EI formula does not apply.
    """
    samples = cost_samples(gp, U, model, n_samples=n_samples, seed=seed)
    return np.maximum(best_cost - samples, 0.0).mean(axis=1)


def recommend_batch_by_cost(
    gp: GP,
    best_cost: float,
    k: int = 8,
    pool: int = 4000,
    seed: int | None = None,
    min_dist: float = 0.15,
    model: CostModel | None = None,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Recommend the next ``k`` designs by expected *cost* reduction.

    `D13` in executable form. ``engin_core.recommend_batch`` maximizes titer; this
    maximizes economics.

    **Whether they disagree is an empirical question, not a given.** On the bundled
    mechanistic simulator they largely agree, because its titer-optimal designs also
    have high yield — see ``tests/test_tea.py``. The disagreement D13 anticipates
    needs a design space where pushing titer costs yield or rate.

    **``seed`` defaults to ``None``: a fresh candidate pool per call** (ADR 0011).
    Pass an int for a bit-reproducible recommendation. The old default of ``1``
    made the pool byte-identical every round, which capped a multi-round campaign
    at the best point in that one fixed lattice -- see :func:`engin_core.recommend_batch`.
    """
    rng = np.random.default_rng(seed)
    candidates = rng.random((pool, len(gp.ell)))
    acq = expected_cost_reduction(gp, candidates, best_cost, model, seed=seed)

    chosen: list[int] = []
    for idx in np.argsort(-acq):
        x = candidates[idx]
        if _is_far_enough(x, candidates, chosen, gp.X, min_dist):
            chosen.append(int(idx))
        if len(chosen) == k:
            break
    return candidates[chosen], acq[chosen]
