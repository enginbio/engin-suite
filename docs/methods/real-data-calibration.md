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
variables averaged over the first N hours *of recorded fermentation*, predict the
batch's final potency. (Not the first N hours of the run — see the time-axis
correction below.) It
is a task practitioners genuinely want, and it exercises the machinery under
test: features to a scalar, with a calibrated interval.

## The result

| features | cutoff (record h) | n | n_cal | coverage | band it buys | width | R² |
|---|---|---|---|---|---|---|---|
| process only | 24 h | 406 | 81 | 0.917 | [0.868, 0.934] | 1569 | 0.023 |
| process only | 48 h | 406 | 81 | 0.893 | [0.868, 0.934] | 1480 | 0.025 |
| process only | 72 h | 405 | 81 | 0.877 | [0.867, 0.936] | 1337 | 0.104 |
| process + early potency | 24 h | 406 | 81 | 0.910 | [0.868, 0.934] | 1505 | 0.059 |
| process + early potency | 48 h | 406 | 81 | 0.912 | [0.868, 0.934] | 1521 | 0.113 |
| process + early potency | 72 h | 405 | 81 | 0.899 | [0.867, 0.936] | 1299 | **0.223** |

Nominal coverage is 0.90, averaged over five seeds.

```{important}
**Read each coverage against the band on its own row, not against 0.90** (#276).
That band is where a correctly calibrated method lands 90% of the time — so **every
row above is inside it**, and the spread from 0.877 to 0.917 is not evidence that any
configuration calibrates better than another.

**`n` is batches; `n_cal` is calibration points, and they are not the same
number.** The split is 60/20/20, so 406 batches buy 81 calibration points. This
page said "406 calibration points" until 2026-08-23 and published the much tighter
band that follows from it.

`n_cal` is computed per row rather than once, because it is
`int(0.8n) − int(0.6n)` on whatever survives the `isfinite` filter and each
configuration drops a different number of incomplete batches. On this dataset it
lands on 81 every time — including the 72 h rows where `n` is 405 — so the column
is constant here. That was checked rather than assumed.
```

```{note}
**Corrected 2026-08-29 (#306): the band was right about the wrong quantity.**
Until today this column read `[0.844, 0.950]` on every row, taken from
`conformal_coverage_interval`. That function is correct and its docstring is
explicit about what it describes — the coverage of **one fitted model against an
infinite test set**, conditional on its calibration set.

**The number beside it is not that.** Each row is the *mean over five re-splits* of
one dataset, each scored on ~82 held-out batches. Those differ in two directions at
once: averaging five re-splits shrinks the calibration-draw spread, and a finite
test set adds binomial spread the Beta ignores. Simulated at the realised split
sizes over 40,000 replicates:

| statistic | sd | its own central 90% | share inside the old `[0.844, 0.950]` |
|---|---|---|---|
| one seed | 0.046 | [0.817, 0.963] | 0.70 |
| **the five-seed mean actually printed** | **0.021** | **[0.868, 0.934]** | **0.99** |

So the old band was a **99% acceptance region wearing a 90% label**, and a
five-seed mean of 0.850 — a real miscalibration — would have passed it. That is
roughly a 1.6× loss of sensitivity in the one measurement standing between this
project and a false "the calibration holds" on real production data.

**The conclusion survives, with much less room than it looked.** All six rows are
still inside the corrected band, but the worst of them clears the lower edge by
**1.1 pp** rather than the 3.3 pp the old band implied.

**This page had the right number forty lines below the wrong one.** The #276 note
above already said the five-seed mean has a standard deviation of about 2.1 pp —
computed by the same simulation, by the same author, in the same week — while the
table kept the Beta. The band now comes from
`engin_core.gp.resampled_coverage_interval`, which describes the statistic a
benchmark actually reports, so the reporting site no longer has to reach for the
nearest available function.
```

```{note}
**Regenerated 2026-08-16 after fixing a leak, and the fix cut both ways.** The
benchmark used to scale features by `X.min(0)`/`X.max(0)` taken over the *whole*
dataset before splitting, which leaks the calibration and test range into the
fit. It now scales from the training split only.

**Coverage did not detectably move.** The six cells are paired — same seeds, same
permutations, same splits before and after, because `rng.permutation` is the first
draw from a fresh generator and the fix did not touch it — so the comparison to
make is the per-cell difference:

| cell | before | after | Δ |
|---|---|---|---|
| process only, 24 h | 0.890 | 0.917 | **+2.7 pp** |
| process only, 48 h | 0.893 | 0.893 | 0.0 pp |
| process only, 72 h | 0.886 | 0.877 | −0.9 pp |
| process + early potency, 24 h | 0.907 | 0.910 | +0.3 pp |
| process + early potency, 48 h | 0.905 | 0.912 | +0.7 pp |
| process + early potency, 72 h | 0.909 | 0.899 | −1.0 pp |

Mean Δ = **+0.3 pp**, 95% CI **[−1.1, +1.7]**, paired *t* = 0.54 on 5 df, *p* =
0.61. Three cells up, one flat, two down; a sign test and a Wilcoxon signed-rank
both give *p* = 1.0. Mean coverage went 0.898 → 0.901.

So the honest summary is that **the leak was real and worth fixing, and its effect
on coverage is too small for six cells to resolve** — if anything coverage moved
*up*, and the largest single move was over-coverage.

R² got **better**, and one value changed sign — process-only at 24 h was
**−0.030** and is now **+0.023**. That is the more suspicious direction, so it
is stated rather than absorbed: a self-critical number disappearing because of
our own change deserves more scrutiny, not less. The likely mechanism is that
global min/max scaling let a few extreme batches compress everything else toward
the middle of the unit cube, and `fit_gp`'s ARD kernel is initialised for
unit-cube inputs — training-split scaling gives the training data the full cube.
**That is a hypothesis, not a measurement**; nobody has run the ablation that
would settle it.

What does not change is the finding this page exists for. Process-only R² stays
near zero, the best figure is 0.223, and the intervals are still wide enough to
cover a near-mean predictor.
```

```{note}
**Corrected 2026-08-24 (#276).** The paragraph above used to read: *"Coverage got
**worse**, which is the direction a leakage fix should move it: the worst deviation
from nominal was 1.4 points and is now 2.3."* Both numbers are arithmetically right
and the inference from them is not.

**The statistic was unpaired, on paired data.** `max` over six cells of
|coverage − 0.90| compares each cell to a constant, so none of the shared
randomness cancels — and then `max` discards whatever pairing survived. Running the
paired comparison the design actually supports reverses the direction: coverage
moved *up* by 0.3 pp, at *p* = 0.61.

**It also read a coincidence as a mechanism.** With 81 calibration points, one
cell's five-seed mean coverage has a standard deviation of about **2.1 pp**
(40,000 replicates over exchangeable ranks, reproducing from the split sizes
alone). Against that, 1.4 pp and 2.3 pp are both ordinary distances from nominal,
and the move between them is well inside noise. What the page presented as a
methodological signature was the yardstick being too short to see.

**One claim from the scan is not reproduced here.** #276 puts the pre-fix
max-deviation at the 1st percentile of its null — *P* = 0.011. That figure holds
only if the six cells are independent, and they are not: they share the batches,
the seeds and the permutations. Simulating both ends of the dependence range gives
*P* = 0.013 for independent cells and *P* = 0.47 for perfectly correlated ones, and
the truth is somewhere between. **"A 1st-percentile fluke" is therefore not a
claim this page makes** — which changes nothing above, because the paired
statistic never needed it.
```

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

## What a random split cannot see

The table above splits uniformly at random, which is what split conformal guarantees
and what the split-protocol section below explains. A plant asks a narrower question: *will the interval hold on next
month's batches?* A random split cannot answer it, because it puts members of every
cohort on both sides.

Grouping the 406 batches by the month their record starts — the only provenance the
file carries — and holding one cohort out at a time:

| | coverage |
|---|---|
| random split, 5 seeds (as published above) | 0.893 |
| **leave-one-month-out, 12 cohorts** | **0.892** |

**The marginal number survives, and that is the honest headline.** Holding out a
whole cohort does not degrade average coverage at all.

The spread does not survive:

| cohort | n | coverage | z vs 0.90 |
|---|---|---|---|
| 2021-12 | 18 | 0.778 | −1.73 |
| 2022-01 | 46 | 0.957 | +1.29 |
| 2022-02 | 41 | 0.927 | +0.58 |
| **2022-03** | 37 | **0.703** | **−3.99** |
| 2022-04 | 35 | 0.914 | +0.28 |
| 2022-05 | 36 | 1.000 | +2.00 |
| 2022-06 | 36 | 0.806 | −1.88 |
| 2022-07 | 36 | 0.944 | +0.88 |
| 2022-08 | 36 | 0.861 | −0.78 |
| 2022-09 | 33 | 0.939 | +0.75 |
| 2022-10 | 38 | 0.947 | +0.97 |
| 2022-11 | 14 | 0.929 | +0.36 |

Cohort-to-cohort sd is **0.087** against the **0.055** that binomial noise alone
would produce — 1.6× wider. <!-- not-a-claim: measured by benchmarks/block_holdout_coverage.py --> One cohort, 2022-03, covers at **0.703**, which is four
binomial standard deviations low and not a small-sample artifact. A user running that
month would have had a 90% interval hold seven times in ten.

```{warning}
**This mixes two mechanisms and cannot separate them.** Monthly cohorts are
time-ordered, so a between-cohort offset and temporal drift
([#173](https://github.com/enginbio/engin-suite/issues/173)) are confounded here.
Nothing on this page distinguishes "the media lot changed" from "the process moved".

Separating them needs provenance the dataset does not carry — no media lot, no seed
train, no operator, no vessel. `engin_core.convention` gained
[`GROUPINGS`](../api/index) in 0.3 so a dataset *can* record it
([#310](https://github.com/enginbio/engin-suite/issues/310)); that is a field, not a
finding, and this table is the argument for wanting it rather than evidence of what
it would show.
```

Reproduce with `benchmarks/block_holdout_coverage.py`, same `cd` as above.

### The same experiment on the simulator, where the truth is known

The real-data table above cannot separate a cohort offset from drift, and cannot say
what a *known* block effect would do. The simulator can, and — contrary to
[#310](https://github.com/enginbio/engin-suite/issues/310)'s reading that tier 1
"provably cannot" exhibit this — **no simulator change was needed.** `simulate_unit`
takes a `kinetics` argument and `Kinetics` is a top-level export, so drawing one
`Kinetics` per group reproduces the structure directly:

```bash
cd packages/engin-core
python benchmarks/block_effect_synthetic.py
```

10 groups of 24 batches, nominal 0.90. `block_sd` is the spread of each group's
kinetic draw — a knob on a synthetic landscape, not an estimate of any plant's
variability:

| `block_sd` | random split | leave-one-group-out | group sd | vs binomial floor | worst group |
|---|---|---|---|---|---|
| 0.00 | 0.917 | 0.950 | 0.069 | 1.1× | 0.833 |
| 0.15 | 0.908 | 0.954 | 0.057 | 0.9× | 0.833 |
| 0.30 | 0.954 | 0.946 | 0.087 | 1.4× | 0.708 |
| 0.50 | 0.963 | 0.904 | 0.157 | **2.6×** | **0.542** |

<!-- not-a-claim: measured by benchmarks/block_effect_synthetic.py -->

**The mean never shows it.** Leave-one-group-out coverage stays near nominal at every
block strength, which is exactly what the 406 industrial batches show — 0.892 grouped
against 0.893 random. A marginal number cannot detect this, on real data or synthetic.

**The spread and the worst group are where it appears.** At the strongest block the
cohort-to-cohort sd is 2.6× the binomial floor and one group's 90% interval covers
**54%** of the time. <!-- not-a-claim: measured by benchmarks/block_effect_synthetic.py -->

The industrial cohorts sit at 1.6× their floor, between the 0.15 and 0.30 rows here. <!-- not-a-claim: both measured by our own benchmarks -->
That is a correspondence in magnitude and **not** evidence that the mechanism is the
same one — the simulator's block effect is a kinetic draw, while the plant's cohorts
confound lot, season and drift.

## Calibration transferred. Prediction did not.

**Coverage lands within about two points of nominal on real industrial data.**
That is the claim this project most needed to check and had not: the conformal
machinery, calibrated on a held-out split, produces intervals that cover at
roughly their stated rate on batches it was not fitted on.

That used to read *within about a point*, and the leakage fix above is what
widened it. The weaker sentence is the true one.

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
nominal, so the signal is there and window means are a poor way to reach it.

```{note}
**Corrected 2026-08-23 (#275).** This paragraph used to end: *"The authors who
published this dataset report considerably better prediction using a time-series
architecture built for the purpose."* That was a comparison, and there is no
comparison to make.

Their released code (`run_EFP.py`, `utils/metrics.py`) forecasts the target from
**48 hours of its own recent history, 12 hours ahead**. Engin's baseline predicts
a batch's outcome from process inputs. Those are different tasks, and the
repository computes **no R²** at all — its metrics are RSE, CORR, MAE, MSE, RMSE,
MAPE, MSPE, SMAPE and MASE. So "considerably better" had nothing to be better
*than*, on any shared number.

**And the paper itself has not been read here.** Neurocomputing 657 is paywalled;
Crossref, OpenAlex and Semantic Scholar all hold the record with a null abstract.
The correction rests on the authors' released code, which shows what that code
does and cannot rule out the paper reporting something else.
```

The honest summary is that Engin's *calibration* transfers to real data and its
*modelling*, pointed naively at a task it was not designed for, does not.

## Two things worth knowing if you run it

**The time axis starts late, and every batch is missing its head.** `hh` is
*per-batch fermentation time*, and each batch is aligned to its own first
observation before a window is taken. Getting that alignment wrong produces empty
feature windows rather than an error, which is how it was noticed.

```{warning}
**Corrected 2026-08-29 (#307): `hh` is not an absolute process hour.** This
paragraph, `quickstart.md`, `quickstart_real_data.py` and the benchmark all said it
was a plant clock, with batches beginning between hour 30 and 83. Measured on the
file itself (md5 `6f65e6af…`):

- **7,772 wall-clock timestamps carry more than one batch, and at every one of them
  the batches report different `hh`.** A plant-wide clock cannot take two values at
  one instant — the batches run in parallel.
- Correlation between a batch's first `hh` and its wall-clock start time is
  **−0.03**. A clock offset would be near +1.
- Within a batch, `hh` advances one per hour of `date`, and the `hh` span equals the
  wall-clock duration for every batch (both mean 125.9 h).

So the varying start is not a clock offset. It is where each batch's **record**
begins, and no record begins at zero — the minimum `hh` anywhere in the file is
**30**, mean final `hh` is 160.2, and the depositors describe ~154 h runs. The
inoculation and early growth phase is absent from this dataset, not summarised in
it.

**That changes what the `cutoff` column means**, which is why it is now labelled
*record hours* rather than plain hours. A "24 h" row is not a decision taken 24
hours into a fermentation: it is the first 24 hours *of available record*, which for
389 of 406 batches begins at fermentation hour 30–39 and for one begins at 83.
**This dataset cannot answer the 24-hours-into-the-run question at all.**

None of the published numbers move — the preprocessing is unchanged and the model
was always fitted to these windows. What was wrong is the description of what the
windows are.
```

### Would a common origin have been better? Measured, and no

The obvious remedy is to anchor every batch at the same fermentation hour —
`elapsed = hh - 30` — so a window covers the same band of the run for all of them.
That is more defensible in principle, and it is available as
`python benchmarks/real_data_coverage.py --alignment common`. It does not pay:

| features | cutoff | R² per-batch *(ships)* | R² common origin | n per-batch → common |
|---|---|---|---|---|
| process only | 24 h | **0.023** | −0.125 | 406 → 401 |
| process only | 48 h | **0.025** | 0.016 | 406 → 405 |
| process only | 72 h | **0.104** | 0.091 | 405 → 406 |
| process + early hx | 24 h | **0.059** | −0.032 | 406 → 401 |
| process + early hx | 48 h | 0.113 | **0.143** | 406 → 405 |
| process + early hx | 72 h | **0.223** | 0.134 | 405 → 406 |

<!-- not-a-claim: our own benchmark, five seeds, printed by real_data_coverage.py -->

**Worse in five of six, and negative in both feature sets at 24 h** — which is the
cutoff where the truncation bites hardest, because a common origin gives every
late-starting batch an empty window. The one win, `process + early hx` at 48 h, is
0.030 of R² and does not survive as a pattern.

**The two arms are not scored on the same batches**, which is why `n` is in the
table. A common origin drops batches whose record begins too late to fill a short
window, and admits one at 72 h that per-batch alignment drops for being too short.
So these R² columns are close to comparable rather than strictly so, and the 24 h
rows are the least comparable of them.

**Coverage is unaffected either way.** Every row of both arms lands inside its own
band, so this is a question about the forecast and not about the calibration —
which is the half of this page that transfers.

The alignment therefore stays as it is, on evidence rather than inertia
([#307](https://github.com/enginbio/engin-suite/issues/307)).

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

What remains is tier 4: *process-condition* design-of-experiments data with
absolute titers. This page used to call that "a genuine scarcity rather than an
oversight", which claimed more than the search supports. Public multi-cycle DoE
campaigns with absolute titers do exist — JBEI's isoprenol work is six ART-guided
cycles reporting mg/L — but they design over *gene targets*, not the process
knobs this model takes. The campaign that does design over process inputs,
JBEI's flaviolin media optimization, reports an absorbance proxy rather than a
titer. The gap is narrow and possibly temporary, not field-wide. See
[Limitations](../limitations.md) for the search trail.

## Related

- [Out-of-distribution](out-of-distribution.md) — where the intervals stop holding
- [Conformal calibration](conformal-calibration.md) — the method being tested here
- [Benchmarks](../benchmarks.md) — the datasets and how they are fetched
- [Limitations](../limitations.md) — validation status
