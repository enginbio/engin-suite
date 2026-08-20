# Case study: techno-economic analysis

**The reader.** You build cost models. Somebody has handed you a fermentation
process and asked whether it can hit a price, or handed you a price and asked
what process would clear it. You already know the hard part of your job is not
arithmetic — it is knowing which numbers in a model are load-bearing and which
are placeholders someone typed once.

So this study leads with that, rather than closing on it.

```{admonition} Everything below runs on this project's simulator
:class: important

Unlike [the process-development study](process-development.md), there is no
real-data half here. No public dataset found supports validating
cost-per-kilogram predictions end to end, which
[Limitations](../limitations.md) records as an open gap.

What follows demonstrates that the cost machinery works and shows you where its
numbers come from. It is **not** evidence that those numbers are right for your
process.
```

## Start with the question backwards

`cost_summary` answers *given this process, what does it cost*. That is rarely the
question an analyst arrives with. The real one is: **I have a molecule, a target
price, and no process yet — what would have to be true?**

```python
from engin_core.tea import break_even, CostParameters

be = break_even(design, params=CostParameters(target_usd_per_kg=40.0), gp=gp)
```

Run across a range of targets against a 40-run campaign:

```text
   target      break-even titer   reachable   P(reach)
  $200/kg              17.9 g/L        True       1.00
   $60/kg              80.2 g/L        True       0.98
   $40/kg             137.6 g/L        True       0.00
   $20/kg             362.9 g/L        True       0.00
    $5/kg                     —       False          —
```
<!-- not-a-claim: measured on our own simulator and cost model, seed 7 -->

**The $40/kg row is the one to read twice.** `reachable=True` and
`P(reach)=0.00` are not a contradiction — they are two different answers to two
different questions, and conflating them is how a TEA becomes wishful:

- **`reachable`** is a statement about the *cost curve*: is there any titer in the
  searched bracket at which this process clears $40/kg? Yes — 137.6 g/L. <!-- not-a-claim: measured on our own simulator and cost model, seed 7 -->
- **`P(reach)`** is a statement about *this process*: will it get there? Under the
  fitted posterior, no.

So $40/kg is not impossible in principle and is not happening with this campaign.
The $5/kg row is the other kind of no: **no titer anywhere in the bracket clears
it**, because fixed facility and recovery burden do not go away no matter how much
product you make.

```{admonition} There is no interval on the break-even titer, on purpose
:class: note

You might expect one, and #143 asked for one. It does not exist: the break-even
titer is the inverse of a *fixed* cost curve at a *fixed* design point, so it is a
deterministic root. Inverting each posterior draw returns the same number every
time.

The uncertainty that genuinely exists is the other half — whether the process
reaches that titer — and that is what `P(reach)` reports. A synthetic interval
around the root would have looked more rigorous and meant nothing.
```

## The interval is driven by the curve, not by the model

This is the result most likely to change how you read a cost forecast, and it is
not obvious.

```text
 titer g/L   GP sd  cost $/kg   90% width   width as % of cost
       9.3    2.46     362.76      298.51                82.3%
      17.7    2.24     198.29       68.76                34.7%
      43.7    2.07      95.40       11.91                12.5%
      69.3    2.23      66.76        5.43                 8.1%
```
<!-- not-a-claim: measured on our own simulator and cost model, seed 7 -->

The GP's titer uncertainty is **almost flat** across these designs — about 2.1 to
2.5 g/L throughout. The cost interval is not: it goes from 8% of the estimate <!-- not-a-claim: measured on our own simulator and cost model, seed 7 -->
to 82%. <!-- not-a-claim: measured on our own simulator and cost model, seed 7 -->

Across the whole campaign:

```text
correlation(interval width, GP sd)   = +0.32
correlation(interval width, 1/titer) = +0.95
```
<!-- not-a-claim: measured on our own simulator and cost model, seed 7 -->

**Cost is a non-linear function of titer**, so the same titer uncertainty maps to
a wildly different cost spread depending on where you sit on the curve. Near the
bottom, small titer errors are enormous cost errors.

The practical consequence for your job: **a low-titer process has a cost estimate
you cannot plan against**, and no amount of model improvement fixes it — you have
to move the titer. That is also why this library propagates the posterior by Monte
Carlo rather than pushing a point estimate through the cost model: a point
estimate at 9.3 g/L would have quoted $363/kg with no indication that the <!-- not-a-claim: measured on our own simulator and cost model, seed 7 -->
honest range is nearly three hundred dollars wide.

## What the numbers rest on

Ask any cost model for its breakdown before you believe its total.

```text
cost breakdown at 85.5 g/L:
  raw_material    $  1.57/kg   ( 2.8%)
  facility        $ 25.26/kg   (44.2%)
  downstream      $ 30.29/kg   (53.0%)
  capital         $  0.00/kg   ( 0.0%)
```
<!-- not-a-claim: measured on our own simulator and cost model, seed 7 -->

**Raw material is under 3% and downstream plus facility is 97%.** <!-- not-a-claim: measured on our own simulator and cost model, seed 7 --> If you work
on commodity chemicals that number should stop you: the literature has substrate
cost as a dominant term for commodities. <!-- ref: 2024-konzock-try-costs --> [Limitations](../limitations.md) explains why
this is predicted rather than anomalous — the defaults encode a **$200/kg
specialty product**, and the cost split slides with selling price — and also
records the consequence honestly: **the yield lever, the one that dominates real
COGS, is nearly invisible here.**

`capital` reads $0.00 because no `ProductionScale` was configured. Configure one
and it prices bioreactors from a published correlation — *borrowed from animal
cell culture*, which [Limitations](../limitations.md) flags as an argument rather
than an established transfer, and which covers **bioreactors only**, so the
capital number is a floor rather than an estimate.

### Where it will extrapolate without telling you

The capital correlation is stated over 0.33–200 m³. Outside that range it keeps
returning numbers:

```text
     0.1 m3  ->  $    278,000     no warning
    0.33 m3  ->  $    810,131     no warning
   200.0 m3  ->  $  6,940,000     no warning
  2000.0 m3  ->  $ 62,200,000     no warning
```
<!-- not-a-claim: measured on our own cost model -->

**0.1 m³ is 100 L — a pilot vessel somebody would plausibly type in**, and it is
below the correlation's stated floor. [Limitations](../limitations.md) records
that the extrapolation is silent and why no warning threshold was invented: the
source gives no basis for choosing one. Knowing the range is currently your job,
so it is stated here at the point you would trip over it.

## Purity changes the answer, and it is an input

Recovery cost is a function of titer and, since
[#17](https://github.com/enginbio/engin-suite/issues/17), of product
specification:

```text
crude      dsp multiplier x1.00
purified   dsp multiplier x3.32
```
<!-- not-a-claim: our own cost model's parameters -->

Since downstream is 53% of modelled cost above, moving from crude to purified is <!-- not-a-claim: measured on our own simulator and cost model, seed 7 -->
not a correction — it is most of the answer. An analyst comparing two processes at
different specifications is comparing nothing.

**What it does not see is what is in the broth.** Not biomass load, not
secreted-versus-intracellular, not impurity burden.
[#15](https://github.com/enginbio/engin-suite/issues/15) tracks that gap, and
[Limitations](../limitations.md) records why it is a limitation of the *evidence*:
a literature pass found no costed comparison to calibrate a coefficient against,
and secretion changes the *shape* of the model — it adds or removes a unit
operation — rather than one of its numbers.

## What this study establishes, and what it does not

| | |
|---|---|
| **Established** | The cost head inverts cleanly and distinguishes "no titer clears this price" from "this process will not reach that titer". The propagated interval widens where the cost curve is steep, which is where a point estimate is most misleading. The breakdown is inspectable, so you can see what the total rests on. |
| **Not established** | That any of these numbers match your process — no public dataset found supports validating cost-per-kg end to end. The interval is **propagated, not conformal**: calibrating it needs held-out *cost* observations from a campaign nobody has run. Capital transfers from animal cell culture to microbial fermentation. Anything about scale — the simulator has no oxygen state ([#190](https://github.com/enginbio/engin-suite/issues/190)), so vessel size is inert. |

**The honest summary for an analyst:** this is a probabilistic TEA whose
assumptions are enumerated and whose failure modes are written down, wired to a
calibrated titer posterior rather than a point estimate. That is worth something
on its own — it is a structure you can substitute your own coefficients into. It
is not a validated cost model for your molecule, and nothing here should be quoted
as one.

## Related

- [Process development](process-development.md) — the same engine, forecasting rather than costing
- [Limitations](../limitations.md) — the full list of what the cost head rests on
- [Decisions](../decisions.md) — `D13`, why the objective is net $/kg rather than titer
