# Limitations

An honest account of what Engin has and has not been shown to do. This page
exists from the first release and is updated as validation progresses.

## Validation status

**Most results published here come from a mechanistic simulator, not from real
fermentation campaigns.** A coefficient of determination measured against the
simulator that produced the data demonstrates that the code runs. It does not
demonstrate that the method works on real bioprocess data.

**Tier 3 is now measured.** [Calibration on real production
data](methods/real-data-calibration.md) reports coverage on 406 erythromycin
batches from a working plant: the intervals cover at close to their nominal rate,
and the forecasts they wrap are close to uninformative. Both halves are published,
because the first without the second would be the more flattering and less true
account.

Validation is structured in five tiers, each reported with what it does and does
not establish:

| Tier | Source | Establishes | Does not establish |
|---|---|---|---|
| 1 | Engin's own simulator | the loop works end to end | anything about real data — the model is validated against its own assumptions |
| 2 | An independent simulator | not overfitted to our own model's quirks | real-world behaviour |
| 3 | Real industrial data | survives real noise, missingness, scale change | in-domain performance; cost coupling, where data is normalised |
| 4 | In-domain literature DoE | the actual product claim | generalisation beyond small, heterogeneous samples |
| 5 | Partner campaign data | end-to-end value | — not yet available |

Current status is recorded in [Benchmarks](benchmarks.md).

## Known constraints

- **No public corpus of in-domain microbial *design-of-experiments* data with absolute titers exists**, which limits tier 4 and is a constraint on the field rather than on this project alone. **Corrected 2026-08-10:** this sentence used to do more work than it could carry. Real, industrial, in-domain microbial process data *does* exist publicly and permissively — the [erythromycin fermentation dataset](https://doi.org/10.5281/zenodo.14619074) is 406 production batches sampled hourly, CC-BY-4.0, with a product-potency target. What it is not is *designed* variation: process conditions were recorded, not varied to explore a design space. So tier 4 remains open and tier 3 does not, and the earlier phrasing implied a scarcity that was broader than the facts.
- **Cost coupling is demonstrated on mechanistic grounds.** No public dataset found supports validating cost-per-kilogram predictions end to end.
- **Calibrated intervals degrade out of distribution.** Coverage is reported for out-of-distribution cases rather than omitted.

## Ingest confidence is not calibrated

The schema-inference score reported by `engin_core.loaders` is an **ordinal
heuristic, not a calibrated probability.** A 0.9 means "matched a known alias
and the units agree"; it does not mean the mapping is right nine times in ten.
Nothing has been measured against a corpus of labelled exports, because no such
corpus exists here yet — the same data problem as tier 3–4 above.

This is called out rather than left implicit because on a project whose argument
is calibrated uncertainty, a number named "confidence" that has not been
calibrated is the easiest thing to over-read. Use it to rank what to review
first, not to decide what needs no review.

## Techno-economic constraints

Two limitations of the cost head are specific enough to state plainly. Both are
pinned as tests, so they cannot drift silently — if either test starts failing,
the situation has improved and this page is what should be updated.

- **The bundled simulator cannot reproduce industrial COGS structure.** At the
  cost model's default substrate price ($0.55/kg, glucose-scale) and this simulator's <!-- not-a-claim: our own model default, set in tea.py -->
  substrate-to-product ratio at 1–2 L scale, raw material lands at roughly **2%** <!-- not-a-claim: measured on our own simulator; pinned in test_tea.py -->
  of modelled cost, where the literature has substrate cost as a dominant term
  set by yield — "more than 50% of the total costs" for commodity chemicals
  ([Konzock & Nielsen 2024](https://doi.org/10.1016/j.tibtech.2024.04.007)).
  <!-- ref: 2024-konzock-try-costs -->
  That $0.55 is a model default rather than a quoted market rate: no open,
  citable price series for bulk industrial glucose was found, and the trade
  sources that carry one are paywalled. Reaching a comparable cost share here
  would require substrate priced near $28/kg, which is a fiction rather than a
  feedstock. The default was kept and the
  modelled process is therefore facility- and downstream-dominated. **The
  consequence is concrete: the yield lever — the one that dominates real COGS — is
  nearly invisible here.** Arguing about industrial economics needs a
  representative process, not this one.

- **Cost-optimal and titer-optimal designs coincide on this simulator**, so the
  practical payoff of optimizing net $/kg cannot be demonstrated with what ships.
  Titer and yield are positively correlated in the simulator, and the yield term is
  too small a share to move the optimum even where they differ. Showing that a cost
  objective picks a *different* design needs a process where pushing titer costs
  yield or rate — a data problem, not a modelling one.

The second point is a limitation of the **demonstration**, not of the decision
behind it: optimizing net cost per kilogram rather than titer rests on the
argument in [Decisions](decisions.md) (`D13`), which does not depend on this
simulator.

## Reporting a limitation we have missed

<https://github.com/enginbio/engin-suite/issues/new>
