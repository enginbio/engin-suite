# Limitations

An honest account of what Engin has and has not been shown to do. This page
exists from the first release and is updated as validation progresses.

## Validation status

**Results published so far come from a mechanistic simulator, not from real
fermentation campaigns.** A coefficient of determination measured against the
simulator that produced the data demonstrates that the code runs. It does not
demonstrate that the method works on real bioprocess data.

Validation is structured in five tiers, each reported with what it does and does
not establish:

| Tier | Source | Establishes | Does not establish |
|---|---|---|---|
| 1 | Engin's own simulator | the loop works end to end | anything about real data — the model is validated against its own assumptions |
| 2 | An independent simulator | not overfitted to our own model's quirks | real-world behaviour |
| 3 | Real industrial data, other domain | survives real noise, missingness, scale change | in-domain performance; cost coupling, where data is normalised |
| 4 | In-domain literature DoE | the actual product claim | generalisation beyond small, heterogeneous samples |
| 5 | Partner campaign data | end-to-end value | — not yet available |

Current status is recorded in [Benchmarks](benchmarks.md).

## Known constraints

- **No public corpus of in-domain microbial design-of-experiments data with absolute titers exists.** This limits tier 4 and is a constraint on the field, not only on this project.
- **Cost coupling is demonstrated on mechanistic grounds.** No public dataset found supports validating cost-per-kilogram predictions end to end.
- **Calibrated intervals degrade out of distribution.** Coverage is reported for out-of-distribution cases rather than omitted.

## Reporting a limitation we have missed

<https://github.com/enginbio/engin-suite/issues/new>
