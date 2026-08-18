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

**The bundled simulator cannot reproduce those shares, and that is worth knowing.**
With realistic media prices (glucose ~$0.55/kg) and this simulator's substrate-to-
product ratio of ~3.6 kg/kg at 1–2 L scale, raw material lands near **2%** of modelled
cost, not the dominant share the literature describes. Reaching a comparable
share would require pricing substrate at
roughly **$28/kg**, which is not a feedstock, it is a fiction.

So the defaults keep realistic unit costs and the modelled process is
facility- and downstream-dominated. The consequence is concrete: **the yield lever —
the one the literature says dominates real COGS — is nearly invisible on this
simulator**, so cost optimization here is driven by the other two terms. Anyone
using this to argue about industrial economics needs a representative process, not
this one.

**Note the sign on titer, because an earlier version of this module had it backwards.**
Higher titer *reduces* downstream cost — less water to remove, smaller equipment,
fewer unit operations. It does not raise it. The reason titer is nonetheless the wrong
optimization target is that it is an *integrative* metric, inflatable by running
longer or at higher biomass, and it says nothing about the raw-material cost that
dominates. See `D13` in ``DECISIONS.md``, including the withdrawn justification.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np
from numpy.typing import ArrayLike, NDArray
from pydantic import BaseModel, Field

from .gp import GP
from .simulator import DEFAULT_REACTOR, ReactorConfig, unit_to_physical

__all__ = [
    "CostParameters",
    "ProductionScale",
    "bioreactor_direct_cost_usd",
    "capital_charge_factor",
    "annual_capital_charge_usd",
    "capital_cost_per_batch_usd",
    "CostModel",
    "ParametricCostModel",
    "BioSteamCostModel",
    "CostSummary",
    "design_context",
    "cost_samples",
    "cost_summary",
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
    :func:`~engin_core.simulator.simulate` does — feeding stops once the vessel is
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


class CostParameters(BaseModel):
    """Illustrative cost structure. Values are a caricature, not a real process.

    Data rather than constants, so substituting your own economics is a keyword
    argument and a sensitivity sweep is a loop.
    """

    substrate_usd_per_kg: float = Field(0.55, gt=0)
    """Media cost, glucose-scale. The *yield* lever — dominant in real COGS, but see
    the module docstring: it is nearly invisible at this simulator's scale."""

    reactor_usd_per_L_h: float = Field(0.045, gt=0)
    """Vessel occupancy: capital recovery, utilities, labour. The *rate* lever."""

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
        downstream = p.downstream_base_usd_per_kg * (
            (p.downstream_reference_titer_g_L / titer) ** p.downstream_titer_exponent
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
            * ((p.downstream_reference_titer_g_L / titer) ** p.downstream_titer_exponent),
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


def expected_cost_reduction(
    gp: GP,
    U: ArrayLike,
    best_cost: float,
    model: CostModel | None = None,
    n_samples: int = 512,
    seed: int = 0,
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
    seed: int = 1,
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
    """
    rng = np.random.default_rng(seed)
    candidates = rng.random((pool, len(gp.ell)))
    acq = expected_cost_reduction(gp, candidates, best_cost, model, seed=seed)

    chosen: list[int] = []
    for idx in np.argsort(-acq):
        x = candidates[idx]
        if all(np.linalg.norm(x - candidates[j]) >= min_dist for j in chosen):
            chosen.append(int(idx))
        if len(chosen) == k:
            break
    return candidates[chosen], acq[chosen]
