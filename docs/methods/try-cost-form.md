# The published TRY equation, checked against our own cost model

Bhagwat et al. (2026) fit minimum product selling price across the titer–rate–yield
landscape of 32 biomanufacturing facilities and report one equation captures it at
R² 0.992–1.000.[^2026-bhagwat-try-unifying-equation] At fixed productivity it reduces to

$$\text{cost} = a + \frac{b}{Y} + \frac{c}{T} + \frac{d}{YT}$$

`engin_core.tea.ParametricCostModel` was built independently of that work, from
equipment-cost correlations. This page asks whether it lands on the same surface.

```{note}
**Not computed at docs build.** The numbers come from a committed script:

    cd packages/engin-core
    python benchmarks/try_cost_form.py

It needs no network and no dataset — the cost model is analytic — so it runs in
seconds and anyone can check the table below.
```

## It fits, and one term is an identity rather than a resemblance

| fit over 6,000 design points | R² |
|---|---|
| $a + b/Y + c/T + d/(YT)$ | **0.9992** |
| $a + b/Y + c/T$ | 0.9977 |

That sits inside the range the paper reports for its own 32 configurations. The
cross-term buys 0.0015 of R², matching their finding that the interaction
contributes only a few percent.

More than a fit: **the yield term is exactly the paper's $b/Y$**, with
$b = \texttt{substrate\_usd\_per\_kg}$. Comparing `cost_breakdown`'s `raw_material`
against $0.55/Y$ point by point, the largest discrepancy across 6,000 designs is
`3.6e-15` — floating-point noise. Substrate cost per kilogram *recovered* is
substrate price divided by yield, by construction.

## What the 6,000 points are, and are not

The grid samples titer **independently** of the design knobs, so it spans
(yield, titer) pairs the simulator cannot produce — the reported yield range runs
to `9.7 g/g`, which no fermentation reaches and mass balance forbids. That is the
right way to characterise a cost *surface*, which is a function of two arguments
and is what the paper fits, and it is the wrong thing to quote as a reachable
range.

Measured properly — 40,000 random designs plus all 32 corners of the design
space, taking each design's own simulated titer — **reachable yield is 0.22–0.69
g/g**, and within a fixed titer band about 1.8×. <!-- not-a-claim: measured on our own simulator -->

The distinction matters for the claim below. Yield genuinely is *not* slaved to
titer — 1.8× of spread at fixed titer is real, and it is what makes the lever <!-- not-a-claim: measured on our own simulator -->
representable at all. But it is a factor of two, not the order of magnitude the
grid's range suggests, and the raw-material term it moves is a small share of
this vessel's cost.

## A high R² here is not evidence the structures agree

The row above is the one most worth reading carefully, because on its own it
overstates. #304 asked for a precondition to be checked **before** the grid is
trusted: the closed form holds only where recovery does not vary substantially
with yield, titer or productivity. Engin's does vary — `downstream` is
`downstream_base_usd_per_kg × (T_ref / T) ** 0.55` — and **no term of
`a + b/Y + c/T + d/(YT)` has that shape.** That check was not run when the fit
above was first published here.

Run now, it changes what the R² means. The test is not goodness of fit, which
four free parameters can buy over a bounded titer range; it is whether the fit
recovers a coefficient already known from algebra. `b` *must* equal
`substrate_usd_per_kg`, because `raw_material` is that identity to `3.6e-15`.
Sweeping the downstream exponent isolates the cause:

| downstream exponent | in the form? | R² | fitted `b` | vs the true 0.55 |
|---|---|---|---|---|
| 0.0 | yes — it is the constant `a` | 1.000000 | 0.550 | 1.0× |
| 1.0 | yes — it is `c/T` | 1.000000 | 0.550 | 1.0× |
| **0.55 (shipped)** | **no** | 0.999157 | **1.930** | **3.5×** |

<!-- not-a-claim: measured on our own cost model by benchmarks/try_cost_form.py -->

When the downstream term is expressible in the form, the fit is **exact** and `b`
comes back to four decimals. At the shipped exponent R² still reads 0.999 while
`b` is wrong by three and a half times. The free parameters are absorbing a power
law, and R² is measuring the flexibility of the form rather than agreement with
it.

**The earlier attribution was also wrong.** The 1.93 was noted when this page was
first written and put down to collinearity — 1/Y and 1/T correlate at +0.87, so a
global fit identifies `b` and `c` poorly. That is real but it is not the cause:
the collinearity is unchanged at exponent 0.0 and 1.0, where `b` recovers
exactly. The un-representable term is what moves it.

What survives is narrower and still worth having: the **yield** term is the
paper's `b/Y` identically, and the **facility** term is `c/T` identically. Two of
Engin's three terms are the published form. The third is not, and the aggregate
R² conceals that rather than showing it.

## What this corrects

```{important}
**Yield is not missing from this cost model, and it is not slaved to titer.**
[#304](https://github.com/enginbio/engin-suite/issues/304) reads
`break_even`'s docstring — *"yield is `titer * volume / substrate`"* — as showing
that yield is "a derived quantity algebraically slaved to titer, not an axis
anything can be optimized along". That is true **at a fixed design point**, which is
the situation `break_even` is in and why it has nothing to solve for. It is not true
across design points, which is the space the recommender searches.

Measured: holding titer in 58–62 g/L, the reachable yield spans **0.215 to 2.827 g/g
— a 13× range** — because the feed knobs move substrate independently of titer.

What *is* true is weaker and different: over the whole space $1/Y$ and $1/T$
correlate at **+0.87**, so a global fit identifies $b$ and $c$ poorly (it returns
$b = 1.93$ where the algebra says 0.55). Correlated, not degenerate.

And the reason the lever looks invisible is the parameterisation, not the structure:
**raw material is 1.8% of cost at the median design** (range 0.1–4.8%), against 48%
facility and 50% downstream. `tea.py`'s existing comment, which attributes the
invisibility to this vessel's scale, is closer to right than the structural reading.
```

## Relative importance: the form agrees, the balance does not

The paper's `RI_MPSP` compares **an improvement of 0.01 g/g in yield against 1 g/L in
titer**, as $\log_{10}$ of the ratio of cost saved.[^2026-bhagwat-try-unifying-equation] Those step sizes are part of the
definition — a per-unit derivative ratio sits two decades away and is not the same
quantity. On their steps, ours:

| yield ↓ / titer → | 20 g/L | 40 g/L | 80 g/L | 120 g/L |
|---|---|---|---|---|
| 0.1 g/g | −1.14 | −0.59 | −0.04 | 0.28 |
| **0.2 g/g** | **−1.72** | −1.17 | **−0.62** | −0.30 |
| 0.4 g/g | −2.31 | −1.76 | −1.21 | −0.89 |
| 0.8 g/g | −2.91 | −2.36 | −1.81 | −1.49 |

**Both of the paper's directions hold**: RI rises with titer and falls with yield —
the opposite of the intuitive guess, and easy to invert when quoting.

**The level does not.** Their worked example (TAL from dextrose monohydrate, yield
0.2 g/g) is **0.11 at 20 g/L and 1.28 at 80 g/L**[^2026-bhagwat-try-unifying-equation]; ours at the same points are
**−1.72 and −0.62**. They report yield leading across 71–95% of each
space[^2026-bhagwat-try-unifying-equation]; we get
1 of 16 cells. On this parameterisation **titer dominates where their facilities say
yield does.**

```{warning}
**An earlier draft of this page reported agreement here, and it was an artifact.**
Computing RI as a per-unit derivative ratio rather than on the paper's 0.01 g/g and
1 g/L steps shifts every cell up by two decades, which turned −1.72 into +0.28 and
made it look close to their 0.11. Same surface, wrong yardstick. The numbers above
are on their convention.
```

### The gap is the facility term, not the yield term

The obvious explanation is product economics — Engin's defaults price a high-value
product (`downstream_base_usd_per_kg` is 46) while TAL from dextrose is a commodity.
That explanation is testable and it is **mostly wrong**: cutting downstream cost
46-fold, to \$1/kg, moves RI at (0.2 g/g, 20 g/L) from −1.72 to only −1.60. <!-- not-a-claim: measured on our own cost model by benchmarks/try_cost_form.py -->

What sets the level is the **facility** term. It is
$1000 \cdot t_{\text{end}} \cdot c_{\text{reactor}} / T$ — the vessel volume cancels —
and at Engin's default bench vessel, 48 h at \$0.045/L/h, that is \$2160 per (g/L)
per kg. It swamps the titer derivative, so titer wins almost everywhere regardless of
what downstream costs.

So this is a statement about Engin's cost *parameterisation*, not about its structure:
the surface is the published one, and the coefficients are those of a bench vessel
running a high-value product, which is a different economic regime from the 32
production facilities the paper fits. `D13`'s selling-price continuum predicts exactly
this kind of divergence; what is new is that it can now be seen as a number.

## What this does not settle

The four-term form holds **at fixed productivity**. The paper's general equation has
productivity-dependent coefficients and divides by recovery, and Engin cannot vary
productivity independently anyway: `design_context` returns
`reactor_L_h = final_volume * t_end` with `t_end` fixed by the vessel config, so rate
is titer over a constant. Quoting the four-term version without that condition drops
the R from TRY.

Whether `ParametricCostModel` should take an explicit `(yield, titer)` pair rather
than deriving substrate from the knobs is a modelling decision, not a defect, and it
is still open on [#304](https://github.com/enginbio/engin-suite/issues/304).

[^2026-bhagwat-try-unifying-equation]: Bhagwat, Rao, Zhao, Singh & Guest, *A unifying equation for fermentation sustainability across the titer-rate-yield landscape*, Nature Communications 17:8655 (2026), [10.1038/s41467-026-75285-1](https://doi.org/10.1038/s41467-026-75285-1). CC BY 4.0.

## Related

- [Cost and techno-economics](../guides/cost.md) — the model this page checks
- [Benchmarks](../benchmarks.md) — the other reproducible numbers
- [Real-data calibration](real-data-calibration.md) — the same discipline on the forecast side
