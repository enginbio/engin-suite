# Cost and techno-economics

```{warning}
Not yet written. The techno-economic head is under construction.
```

Will cover: producing a probabilistic cost-per-kilogram estimate, why the
recommender optimizes net cost rather than titer, and how recovery cost is
modelled.

The short version of the second point: **titer is one of three cost centres, and
which one dominates tracks the product's value, not the process.** Downstream
processing runs 45–92% of production cost for biopharmaceuticals against a
typical 20–40% for bulk fermentation products, and the relative DSP contribution
rises with selling price — roughly 15% for ethanol at ~$0.5/kg up to 60–70% for
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
