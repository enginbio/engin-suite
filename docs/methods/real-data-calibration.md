# Calibration on real production data

Every coverage number published before this one was measured against Engin's own
simulator. That demonstrates the code runs; it is not evidence the method works.
This page is the first measurement against **406 erythromycin batches from a
working pharmaceutical plant**.

```{note}
**The numbers on this page are not computed when the docs build**, unlike the
rest of this documentation. Producing them means downloading 8 MB from a third
party, and a documentation build that depends on someone else's server being up
is a documentation build that breaks for reasons unrelated to the docs.

They come from a committed script instead, and you can run it yourself:

    cd packages/engin-core
    python benchmarks/real_data_coverage.py

It fetches the data through `engin_core.datasets`, which verifies the checksum
against the publisher's own and writes a provenance manifest beside the file.
```

## The task, and why it is not the one Engin was built for

Engin forecasts an outcome from a **design point**. This dataset is production
history: the process conditions were *recorded*, not chosen, so there is no
design space to explore. Calling it a design-of-experiments benchmark would be
the kind of overstatement this project keeps catching in itself.

The closest honest analogue is **early batch outcome prediction** — from process
variables averaged over the first N hours, predict the batch's final potency. It
is a task practitioners genuinely want, and it exercises the machinery under
test: features to a scalar, with a calibrated interval.

## The result

| features | cutoff | n | coverage | width | R² |
|---|---|---|---|---|---|
| process only | 24 h | 406 | 0.890 | 1487 | **−0.030** |
| process only | 48 h | 406 | 0.893 | 1582 | 0.015 |
| process only | 72 h | 405 | 0.886 | 1317 | 0.123 |
| process + early potency | 24 h | 406 | 0.907 | 1505 | 0.054 |
| process + early potency | 48 h | 406 | 0.905 | 1496 | 0.096 |
| process + early potency | 72 h | 405 | 0.909 | 1344 | **0.232** |

Nominal coverage is 0.90, averaged over five seeds.

### How the split is made, because it decides what the number means

Each seed draws a **uniformly random 60/20/20 split** into train, calibration and
test. The dataset it draws from is time-ordered production history, and the
permutation discards that order.

That measures **marginal coverage under exchangeability** — which is exactly what
split conformal guarantees, so the number is what it says it is. What it cannot
see is temporal drift, because a uniformly random permutation is precisely how
[the standard reference on non-exchangeable
conformal](https://doi.org/10.1214/23-aos2276) constructs the *exchangeable
control group* it compares a time-ordered split against.
<!-- ref: 2023-barber-beyond-exchangeability -->

So read the table as *these intervals are honest across this dataset*, and not as
*these intervals will hold on your plant's next batch*. The second is the
deployment question, and a random split is the one design that cannot answer it.
Tracked in
[#173](https://github.com/enginbio/engin-suite/issues/173), which also works out
that a single chronological re-split would be underpowered to settle it.

## Calibration transferred. Prediction did not.

**Coverage lands within about a point of nominal on real industrial data.** That
is the claim this project most needed to check and had not: the conformal
machinery, calibrated on a held-out split, produces intervals that cover at
roughly their stated rate on batches it was not fitted on.

**Not on a plant it has never seen** — this sentence used to say that, and it was
wrong in a way worth naming rather than quietly deleting. The model trains on
roughly 243 batches from *this same plant*; the held-out batches are held out of
training, not drawn from anywhere else. Cross-plant transfer is not tested at any
tier, and the earlier phrasing invited exactly that reading.

**R² is near zero.** With window-mean features, the model has almost no ability
to tell one batch's final potency from another's. It is close to predicting the
mean — and the intervals, being wide, cover it anyway.

Those two facts together are the point of this page:

```{warning}
**A model can be almost perfectly calibrated and nearly useless.** Coverage says
the intervals are honest about the model's ignorance. It says nothing about
whether the model knows anything.
```

That is the same lesson as
[the out-of-distribution page](out-of-distribution.md), which found coverage
recovering far from the training data because the intervals had grown large
enough to contain anything. There it was demonstrated on a simulator. Here it is
demonstrated on production data, which is a stronger place to demonstrate it.

## What this does not say about the dataset

The low R² is a statement about **this baseline**, not about the data. Adding
early potency to the features roughly doubles R² while coverage stays near
nominal, so the signal is there and window means are a poor way to reach it. The
authors who published this dataset report considerably better prediction using a
time-series architecture built for the purpose.

The honest summary is that Engin's *calibration* transfers to real data and its
*modelling*, pointed naively at a task it was not designed for, does not.

## Two things worth knowing if you run it

**The time axis is not elapsed time.** `hh` is an absolute process hour: batches
begin anywhere between hour 30 and hour 83. Every batch is aligned to its own
start before a window is taken. Getting this wrong produces empty feature
windows rather than an error, which is how it was noticed.

**Only one column is glossed.** `hx` is the target, confirmed from the dataset
authors' own code rather than inferred from its behaviour. The remaining 22
columns are unglossed abbreviations, and are used as features without
interpretation. That is legitimate for a forecast and would not be for any claim
about mechanism — no statement here depends on knowing what `phzx` or `btmt`
measures.

## Where this leaves the validation programme

This is `D12` **tier 3** — real data, industrial, and in-domain, though not
designed. It is one of the three things `D24` gates a visibility push on, and it
is now published, including the unflattering half.

What remains is tier 4: in-domain *design-of-experiments* data with absolute
titers, which is a genuine scarcity rather than an oversight. See
[Limitations](../limitations.md).

## Related

- [Out-of-distribution](out-of-distribution.md) — where the intervals stop holding
- [Conformal calibration](conformal-calibration.md) — the method being tested here
- [Benchmarks](../benchmarks.md) — the datasets and how they are fetched
- [Limitations](../limitations.md) — validation status
