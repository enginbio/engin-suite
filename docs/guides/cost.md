---
file_format: mystnb
kernelspec:
  name: python3
  display_name: Python 3
  language: python
---

# Cost and techno-economics

You have a process and a price to hit. This page is the walkthrough: what to
type, what comes back, and what it is safe to conclude.

It is deliberately **not** the worked example. [The techno-economic case
study](../case-studies/techno-economic-analysis.md) walks one campaign end to
end and closes on what it does and does not establish; this page assumes you want
the loop against your own numbers. Where they overlap, the case study is where the
argument lives.

Every number below is computed when these docs are built, on the bundled
simulator. Nothing is quoted from a previous run, and **nothing here is a claim
about your process** — no public dataset found supports validating cost-per-kg
end to end, which [Limitations](../limitations.md) records as an open gap.

## 1. Cost a design, with an interval

Cost rides on a titer forecast, so you need a fitted model first. Everything in
[Forecasting titer](forecasting.md) applies unchanged.

```{code-cell} python
import numpy as np
from engin_core import fit_gp, simulate_unit
from engin_core.tea import CostParameters, cost_summary

rng = np.random.default_rng(7)
U = rng.random((40, 5))                       # 40-run DoE over the process knobs
y = simulate_unit(U) + rng.normal(0, 1.5, 40)  # with assay noise
gp = fit_gp(U, y, seed=0)

best = int(np.argmax(y))
c = cost_summary(gp, U[[best]])[0]
print(f"expected   ${c.expected_usd_per_kg:.2f}/kg")
print(f"90% range  ${c.lower_usd_per_kg:.2f} - ${c.upper_usd_per_kg:.2f}")
print(f"P(clears ${c.target_usd_per_kg:.0f}/kg) = {c.prob_meets_target:.2f}")
```

`CostSummary` has **no bare `cost` field**, deliberately. Cost is a non-linear
function of an uncertain titer, so a point estimate hides both the spread and its
skew.

## 2. Ask the question backwards

`cost_summary` answers *given this process, what does it cost*. The question you
probably arrived with is the other one: **I have a price to hit — what would have
to be true?**

```{code-cell} python
from engin_core.tea import break_even

for target in (200.0, 40.0, 5.0):
    be = break_even(U[[best]], params=CostParameters(target_usd_per_kg=target), gp=gp)
    titer = f"{be.value:.1f} g/L" if be.value is not None else "unreachable"
    reach = f"{be.prob_reaching:.2f}" if be.prob_reaching is not None else "n/a"
    print(f"  ${target:>6.0f}/kg  ->  {titer:>14}   reachable={be.reachable!s:<5} P(reach)={reach}")
```

**Two of those rows are a "no", and they are different nos.**

- `reachable=True` with `P(reach)=0.00` — the price *is* clearable at some titer,
  and this process will not get there. That is a process problem.
- `reachable=False` — **no titer in the searched bracket clears it at all**,
  because fixed facility and recovery burden do not vanish however much product
  you make. That is a business-model problem, and no amount of strain engineering
  fixes it.

Conflating them is how a techno-economic analysis becomes wishful. Pass `gp=` to
get `P(reach)`; without it you get the root and no opinion on whether you will
hit it.

```{note}
There is **no interval on the break-even titer**, and that is not an omission.
It is the inverse of a fixed cost curve at a fixed design point — a deterministic
root, identical for every posterior draw. The uncertainty that exists is whether
you reach it, which is what `P(reach)` reports.
```

## 3. Read the interval: it tracks the curve, not the model

This is the part most likely to change how you read a cost forecast.

```{code-cell} python
mean, sd = gp.predict(U)
summaries = cost_summary(gp, U)
width = np.array([s.upper_usd_per_kg - s.lower_usd_per_kg for s in summaries])

print(f"  corr(interval width, GP sd)   = {np.corrcoef(width, sd)[0, 1]:+.2f}")
print(f"  corr(interval width, 1/titer) = {np.corrcoef(width, 1 / mean)[0, 1]:+.2f}")
print()
for i in np.argsort(mean)[:: max(len(mean) // 4, 1)][:4]:
    s = summaries[i]
    w = s.upper_usd_per_kg - s.lower_usd_per_kg
    print(f"  titer {mean[i]:5.1f} g/L   cost ${s.expected_usd_per_kg:7.2f}/kg   "
          f"90% width ${w:6.2f}  ({w / s.expected_usd_per_kg:.0%} of the estimate)")
```

The model's titer uncertainty is nearly flat across these designs. The cost
interval is not, because cost is non-linear in titer: near the bottom of the
curve, small titer errors are large cost errors.

**The practical consequence: a low-titer process has a cost estimate you cannot
plan against, and no model improvement fixes it — you have to move the titer.**

```{warning}
This interval is **propagated, not conformal.** It carries the GP's titer
posterior through the cost model. Calibrating it would need held-out *cost*
observations from a costed campaign nobody has run. The titer intervals in
[Forecasting titer](forecasting.md) are conformal; these are not, and on this
project those words are not interchangeable.
```

## 4. Inspect the breakdown before believing the total

```{code-cell} python
from engin_core.tea import ParametricCostModel

model = ParametricCostModel()
bd = model.cost_breakdown(np.array([mean[best]]), U[[best]])
total = sum(float(np.atleast_1d(v)[0]) for k, v in bd.items() if k != "total")
for name, value in bd.items():
    v = float(np.atleast_1d(value)[0])
    share = "" if name == "total" else f"   ({v / total:.1%})"
    print(f"  {name:<14} ${v:>8.2f}/kg{share}")
```

If raw material comes back as a small share and you work on commodity chemicals,
that should stop you. The defaults encode a **specialty product**, and the cost
split slides with selling price — see the note at the foot of this page.
[Limitations](../limitations.md) records the consequence plainly: **the yield
lever, the one that dominates real COGS, is nearly invisible at these defaults.**

`capital` reads zero until you describe a production scale.

## 5. Use your own vessel and economics

Every number above came from defaults that are almost certainly not yours.

```{code-cell} python
from engin_core.simulator import ReactorConfig
from engin_core.tea import PurityGrade, purity_dsp_multiplier

params = CostParameters(
    substrate_usd_per_kg=0.55,          # what you pay for feedstock
    target_usd_per_kg=200.0,            # the price you need to beat
)
vessel = ReactorConfig(v0=1.0, vmax=2.5, t_end=48.0)

for grade in PurityGrade:
    print(f"  {grade.value:<10} downstream multiplier x{purity_dsp_multiplier(grade):.2f}")
```

**Purity is not a correction, it is most of the answer** when downstream is half
the cost. Comparing two processes at different specifications compares nothing.

```{warning}
**The capital correlation extrapolates silently.** `ProductionScale` prices
bioreactors from a correlation stated over 0.33–200 m³, and outside that range it
returns numbers without warning — `0.1 m³` is 100 L, a pilot vessel somebody would
plausibly type in. It also covers **bioreactors only**, so the capital figure is a
floor rather than an estimate, and the correlation is borrowed from animal cell
culture. All three are recorded in [Limitations](../limitations.md); knowing the
range is currently your job.
```

## Why net $/kg rather than titer

**Titer is one of three cost centres, and which one dominates tracks the
product's value, not the process.** Downstream processing runs 45–92% of
production cost for biopharmaceuticals against a typical 20–40% for bulk
fermentation products, and the relative DSP contribution rises with selling price
— roughly 15% for ethanol at ~$0.5/kg up to 60–70% for
enzymes.[^2011-straathof-downstream-costs] **Purity moves it as much as product
class does**: crude penicillin G and crude lipase sit near 25%, while purified and
formulated versions of the same products land nearer 50–55%.

A single-metric objective cannot track a weighting that slides along a continuum
like that. Net $/kg can. See `D13` in [Decisions](../decisions.md).

[^2011-straathof-downstream-costs]: Straathof, *The Proportion of Downstream Costs in Fermentative Production Processes*, Comprehensive Biotechnology (2011), pp. 811–814. [doi:10.1016/B978-0-08-088504-9.00492-X](https://doi.org/10.1016/B978-0-08-088504-9.00492-X)

```{note}
**Corrected 2026-08-13.** This section previously read: *"recovery cost is
determined upstream — by titer, strain and broth composition — but incurred
downstream. An optimizer maximizing titer can therefore move the true objective
backwards."* That mechanism is backwards — higher titer *reduces* downstream cost,
because there is less water to remove — and `D13` withdrew it on 2026-08-10. This
page went on asserting it for three days **while citing `D13` as its authority**.
The decision survived; only its old reasoning did not.
```

## Where to go next

- [Techno-economic case study](../case-studies/techno-economic-analysis.md) — one campaign, worked end to end
- [Forecasting titer](forecasting.md) — the titer model this rides on
- [Limitations](../limitations.md) — every assumption the cost head rests on
- [Decisions](../decisions.md) — `D13`, the objective decision itself
