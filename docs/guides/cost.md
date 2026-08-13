# Cost and techno-economics

```{warning}
Not yet written. The techno-economic head is under construction.
```

Will cover: producing a probabilistic cost-per-kilogram estimate, why the
recommender optimizes net cost rather than titer, and how recovery cost is
modelled.

The short version of the second point: **titer is one of three cost centres, and
which one dominates is a property of the product, not of the process.**
Downstream processing is reported at 45–92% of production cost for
biopharmaceuticals against 20–40% for bulk fermentation products, where raw
material — governed by *yield*, which titer does not capture — takes the larger
share instead.[^2011-straathof-downstream-costs] A single-metric objective cannot
track a weighting that moves by product class; net $/kg can. See `D13` in
[Decisions](../decisions.md).

[^2011-straathof-downstream-costs]: Straathof, *The Proportion of Downstream Costs in Fermentative Production Processes*, Comprehensive Biotechnology (2011). [doi:10.1016/B978-0-08-088504-9.00492-X](https://doi.org/10.1016/B978-0-08-088504-9.00492-X) — these figures come from the chapter's abstract; it is paywalled and its underlying tables have not been read.

```{note}
**Corrected 2026-08-13.** This section previously read: *"recovery cost is
determined upstream — by titer, strain and broth composition — but incurred
downstream. An optimizer maximizing titer can therefore move the true objective
backwards."* That mechanism is backwards — higher titer *reduces* downstream cost,
because there is less water to remove — and `D13` withdrew it on 2026-08-10. This
page went on asserting it for three days **while citing `D13` as its authority**.
The decision survived; only its old reasoning did not.
```
