# Case study: process development

**The reader.** You run process development on a fed-batch fermentation. You have
historical runs, a limited number of bioreactor slots this month, and a decision
to make about which conditions to try next. You want to know whether a forecast
you did not produce yourself can be trusted enough to spend those slots on.

This is that question, worked end to end with commands you can run. Every number
below came out of a run rather than a draft.

```{admonition} There is a seam in the middle of this study, and it is deliberate
:class: important

The first half runs on **406 real production batches**. The second half runs on
**this project's simulator**, because it has to: a recommendation asks *what
would happen at a condition nobody has run*, and a fixed historical dataset
cannot answer that. `benchmark.py --multi-round` refuses the real-data flag for
the same reason.

So the calibration evidence below is real and the recommendation demonstration is
not. The join is marked where it happens. Do not carry the credibility of the
first half into the second — that is the specific mistake this page is arranged
to prevent.
```

## Part 1 — can I trust the interval? (real data)

```bash
cd packages/engin-core
python examples/quickstart_real_data.py
```

Five steps. Each is a thing that goes wrong in practice.

### The data arrives with its provenance attached

406 erythromycin batches from a working pharmaceutical plant, CC-BY-4.0, fetched
from Zenodo. <!-- ref: 2025-zenodo-erythromycin-efp --> The file is
checksum-verified against the publisher's own md5, and a JSON manifest is written
beside it recording the URL, the licence, both checksums and a UTC timestamp.

This matters for a reason specific to your job: **an audit six months from now
asks which file a number came from.** The manifest answers it. If you have ever
tried to reconstruct why a forecast said what it said, you already know why this
is step one rather than a footnote.

### The ingest layer tells you what it does not know

```text
50,536 rows x 27 columns
long table: 4 column(s) mapped, 21 unmapped, 0 below the 0.7 review threshold
run column : batch_id
time column: hh  (orientation: long)
```
<!-- not-a-claim: output of our own loader on this file -->

**Four columns out of twenty-five.** `our`, `cer`, `rq` and `kla` are standard
bioprocess abbreviations and map cleanly; the other twenty-one are unglossed
plant abbreviations and the loader **carries them through under their original
names rather than guessing.**

That is the honest behaviour and it is worth dwelling on, because the tempting
alternative is worse. This dataset has already produced confident false mappings
here — `our` once matched a substrate channel through the substring
`carbonsource`. A loader that guessed would have handed you a tidy table with the
wrong columns in it, and nothing downstream would have complained.
[Vendor-export ingest](../methods/vendor-export-ingest.md) reports the same layer
measured against a DASGIP export, where it did much worse.

### The forecast is calibrated, and the calibration is measured

```text
405 batches, 23 process features each
conformal multiplier at 90%: 1.730  (Gaussian would use 1.645)
empirical coverage : 0.802   (nominal 0.9)
R^2                : -0.151
mean interval width: 1269
```
<!-- not-a-claim: measured on our own run of the shipped example -->

Read those four lines in order, because the story is in the pairing.

**The multiplier is wider than the textbook one.** Split conformal measured the
residuals this model actually made on a calibration split it never trained on,
and concluded the Gaussian 1.645 was too narrow. The interval you get is worse
looking than the naive one, on purpose.

**Coverage lands near nominal.** 0.802 on one split of 81 test batches, which
carries roughly ±0.03 of binomial noise; averaged over five seeds it is **0.877**
against a nominal 0.90.
<!-- not-a-claim: measured on our own run; the five-seed table is in methods/real-data-calibration.md -->
[Calibration on real production data](../methods/real-data-calibration.md) has
the full table. **This is the one thing on this page that is evidence about the
real world.**

**And the forecast inside those intervals is close to uninformative.** R² is
negative — it is nearly predicting the mean, and the intervals are wide enough to
cover it anyway.

```{admonition} A model can be well calibrated and still not know much
:class: warning

Those two results are not in tension and reporting only the first would be the
flattering lie. Calibration says *the interval means what it says*. It does not
say *the interval is narrow enough to act on*. On this task, ours is not.

If you take one thing from this page, take that pairing. A vendor quoting
coverage without an accuracy number beside it has told you nothing about whether
the tool will help you.
```

## The seam

Everything above used runs somebody already did. The next question — *which
conditions should we try next month* — cannot be answered from them, because it
asks about conditions nobody ran.

**Below this line the data is simulated.** The machinery is the same; the
evidence is not.

## Part 2 — what should I run next? (simulator)

```bash
engin-host --init project.yaml   # writes a commented starter file
engin-process --config project.yaml
```

The starter file describes your vessel and your economics in plain language. Edit
it, then:

```text
vessel: 1 L -> 2.5 L over 48 h   (40 simulated runs)

best cost so far : $50/kg  [$47, $52] (90%)
clears $200/kg target with probability 1.00

next 4 runs, by expected cost reduction:
  1. E[saving]=$3/kg   feed_rate=0.0585  feed_start=4.25  Sf=447  induction_time=8.4   S0=21.2
  2. E[saving]=$2/kg   feed_rate=0.0512  feed_start=3.26  Sf=439  induction_time=8.23  S0=28.9
  3. E[saving]=$2/kg   feed_rate=0.0586  feed_start=4.02  Sf=425  induction_time=9.43  S0=6.95
  4. E[saving]=$2/kg   feed_rate=0.0571  feed_start=5.05  Sf=430  induction_time=7.36  S0=27.1
```
<!-- not-a-claim: output of our own CLI on the starter project file -->

Four runs, ranked by **expected cost reduction** rather than expected titer —
`D13`, the decision this project is most willing to look bad for.

### Run the comparison it invites

`--titer` switches the objective, and the result is the most useful thing on this
page for deciding whether to believe any of it:

```text
next 4 runs, by expected improvement in titer:
  1. E[gain]=4.75 g/L   feed_rate=0.0585  feed_start=4.25  Sf=447  induction_time=8.4   S0=21.2
  2. E[gain]=2.82 g/L   feed_rate=0.0512  feed_start=3.26  Sf=439  induction_time=8.23  S0=28.9
```
<!-- not-a-claim: output of our own CLI on the starter project file -->

**Identical designs, in identical order.** On the bundled simulator the cost
objective and the titer objective pick the same batch, so `D13`'s whole argument
buys you nothing here — and this is not a surprise, it is
[a limitation already on the record](../limitations.md): titer and yield are
positively correlated in this simulator and raw material is a small share of
modelled cost, so the yield term cannot move the optimum. Both facts are pinned
as tests.

Showing that a cost objective picks a *different* design needs a process where
pushing titer costs yield or rate. That is a data problem, not a modelling one,
and it is open.

## The artifact

```bash
python examples/run_demo.py     # writes outputs/doe-round-reduction-memo.md
```

A memo with forecast quality, what drives titer, the recommended batch, a cost
bottom line with an interval, and a Tier 1 banner saying its runs came from a
simulator. That banner is there because this is the page most likely to leave as
a screenshot.

It is honest in a way worth noticing: it reports whether the two cost intervals
overlap, and at the demo's sample size **they do**, so it says the cost ranking is
not decisive. A memo that only read well when the answer was flattering would be
worth less than no memo.

## What this case study establishes, and what it does not

| | |
|---|---|
| **Established** | The intervals cover at close to their stated rate on real production batches this model never saw. The ingest layer reports what it could not map instead of guessing. The provenance trail survives to an audit. |
| **Not established** | That the forecast is *accurate* enough to act on — on this task it is not. That coverage holds under temporal drift; the split is random, not chronological ([#173](https://github.com/enginbio/engin-suite/issues/173)). That the cost objective picks different designs from a titer objective — on this simulator it does not. Anything at all about scale: the simulator has no oxygen state ([#190](https://github.com/enginbio/engin-suite/issues/190)). |

**The honest summary for someone deciding whether to spend bioreactor slots on
this:** the uncertainty machinery works and is measured. The forecast it wraps is
not yet good on public data. Those are separate questions and this project reports
them separately, which is the whole argument — you are being handed a calibrated
interval, not a promise.

## Related

- [Quickstart](../quickstart.md) — the same first half, as a how-to
- [Calibration on real production data](../methods/real-data-calibration.md) — the full coverage table
- [Limitations](../limitations.md) — what has and has not been shown
- [Benchmarks](../benchmarks.md) — including where simpler methods beat this one
