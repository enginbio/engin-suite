---
file_format: mystnb
kernelspec:
  name: python3
  display_name: Python 3
  language: python
---

# Forecasting titer

You have a handful of runs and a decision to make. This page is the walkthrough:
what to type, what comes back, and what it is safe to conclude.

It is deliberately **not** the theory page. [Conformal
calibration](../methods/conformal-calibration.md) shows *why* the naive interval
fails and by how much; this one assumes you accept that and want the working
loop. Where the two overlap, that page is canonical.

Every number below is computed when these docs are built, on the bundled
simulator. Nothing is quoted from a previous run, and nothing here is a claim
about your process.

## 1. Fit from the runs you have

```{code-cell} python
import numpy as np

from engin_core.gp import fit_gp, split_conformal_multiplier, smallest_calibration_set
from engin_core.simulator import simulate_unit

NOMINAL = 0.90
rng = np.random.default_rng(0)

# A 24-run DoE over the five process knobs, with realistic assay noise.
U = rng.random((24, 5))
y_true = simulate_unit(U)
y_obs = np.maximum(y_true + rng.normal(0, 0.05 * y_true + 0.4), 0.0)

print(f"{len(U)} runs, titer {y_obs.min():.1f}-{y_obs.max():.1f} g/L")
```

Twenty-four runs is a real campaign, not a toy one. It is also *small*, and the
rest of this page is mostly about what small costs you.

**Hold some of it back.** The model cannot audit itself: an interval built from
residuals the model already fitted is optimistic by construction, which is the
failure the methods page measures.

```{code-cell} python
# 10 calibration points, not 8. Section 3 explains why that is not a free
# choice: at 90% the floor is 9, and below it the level is unavailable.
tr, ca = slice(0, 14), slice(14, 24)
gp = fit_gp(U[tr], y_obs[tr], seed=0)

mean_ca, sd_ca = gp.predict(U[ca], include_noise=True)
print(f"fitted on {tr.stop - tr.start}, calibrating on {ca.stop - ca.start}")
```

## 2. Turn the posterior into an interval you can quote

`split_conformal_multiplier` returns a single number `q`: the interval is
`mean ± q·sd`, and `q` is chosen so that it covered at the nominal rate on data
the model never saw.

```{code-cell} python
import warnings

# Captured rather than left to stderr purely so this page's output is
# reproducible -- the raw warning carries a per-process temp path, and these
# docs are checked by re-executing them and diffing against the committed run.
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    q = split_conformal_multiplier(y_obs[ca], mean_ca, sd_ca, level=NOMINAL)

gp.q90 = q                      # the wrapper carries it for downstream consumers
print(f"conformal multiplier q = {q:.2f}   (a Gaussian 90% would use 1.64)")
print(f"it also warned: {str(caught[0].message)[:96]} ...")

# The interval is mean +/- q*sd. Use the total predictive sd: you are predicting
# an assay result, and the assay has noise in it.
#
# Predict on designs the model has never seen -- not on the calibration set,
# which set q and would flatter the result.
Xs = rng.random((4, 5))
mean_s, sd_s = gp.predict(Xs, include_noise=True)
lo, hi = mean_s - q * sd_s, mean_s + q * sd_s
truth = simulate_unit(Xs)

for i in range(len(Xs)):
    covered = "yes" if lo[i] <= truth[i] <= hi[i] else "NO"
    print(f"new design {i}: {lo[i]:6.1f} - {hi[i]:6.1f} g/L   true {truth[i]:6.1f}   covered: {covered}")
```

That is the whole mechanism. `q` is not a modelling choice you tune; it is
measured, and if the model is overconfident `q` comes back large and the interval
gets wider. Wider is the honest response to a bad model, not a bug.

**Two things in that output are worth stopping on.**

*It warned you without being asked.* Ten calibration points is above the floor,
so you get a real multiplier — but the library still says the realised coverage
could land anywhere in roughly 0.74–0.99. That is section 3's point, and it
arrives unprompted rather than waiting to be looked up. Silence it with
`warn_below_slack=None` only once you have decided it does not matter to you.

*One interval has a negative lower bound.* Titer cannot be negative, and
`mean ± q·sd` does not know that. The interval is symmetric because the
calibration procedure is; it is not a physical statement about the process. For a
design the model is very unsure about, read the lower bound as "could be near
zero" and treat the width, not the endpoint, as the information.

## 3. The part nobody tells you: your calibration set has a floor

Split conformal takes the `ceil((n+1)·level)`-th smallest calibration score. That
index has to exist. Below a certain size, **the level you asked for is not
available at any price**:

```{code-cell} python
for level in (0.80, 0.90, 0.95, 0.99):
    print(f"{level:.0%} interval needs at least {smallest_calibration_set(level):>3} calibration points")
```

Read that against a 24-run campaign. A 90% interval is comfortable. A 95% one
consumes most of your data. **A 99% interval is not something you can have** —
not because the code refuses, but because the arithmetic has no quantile to take.

Ask for it anyway and `split_conformal_multiplier` warns and falls back to the
widest interval the calibration set can justify. That is honest, and it is *not*
the level you asked for.

```{code-cell} python
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    split_conformal_multiplier(y_obs[ca], mean_ca, sd_ca, level=0.99)
    print(str(caught[0].message)[:200], "...")
```

**Even above the floor, the level is a target rather than a promise for your
particular split.** Coverage conditional on one calibration set is a draw from a
Beta distribution, so a small set buys a wide range of possible realised
coverages:

```{code-cell} python
from engin_core.gp import conformal_coverage_interval

for n_cal in (9, 20, 50, 406):
    lo_c, mean_c, hi_c = conformal_coverage_interval(n_cal, level=NOMINAL)
    print(f"n={n_cal:>3}: realised coverage lands in {lo_c:.2f}-{hi_c:.2f} (central 90%)")
```

The nominal rate is what you get *on average over calibration sets*. With ten
points you are drawing one sample from a broad distribution -- which is exactly
what the warning in section 2 was telling you. This is the
strongest practical argument for spending runs on calibration, and it is why the
number is reported rather than hidden.

## 4. When the guarantee stops applying

Conformal coverage rests on **exchangeability** — that the run you are predicting
is drawn like the runs you calibrated on. Three ways that breaks in a real
campaign, in rough order of how often they bite:

- **You moved the process.** A new feed strategy, a different vessel, a strain
  change. The calibration set describes the old process.
- **You are extrapolating.** Predicting outside the region your DoE covered.
  [Out-of-distribution behaviour](../methods/out-of-distribution.md) measures what
  that costs here.
- **Time.** Seasonal raw-material variation, drift in an assay. Splitting a
  campaign at random hides this; splitting it chronologically does not.

Conformal methods are actively used for uncertainty quantification in biological
systems and are well suited to the sample sizes those experiments produce — a
2025 study evaluates jackknife-based conformal algorithms on nonlinear ODE models
of biological dynamics across 10 to 100 sample
points.[^2025-portela-conformal-dynamic-biology] Its authors are equally explicit
about the boundary: their intervals cover *"only for observed variables at
observed time points"* and cannot speak to unobserved states or future times.
The same caution applies here.

[^2025-portela-conformal-dynamic-biology]: Portela, Banga & Matabuena, *Conformal prediction for uncertainty quantification in dynamic biological systems*, PLOS Computational Biology 21(5), 2025. [doi:10.1371/journal.pcbi.1013098](https://doi.org/10.1371/journal.pcbi.1013098)

```{admonition} What transferred to real data, and what did not
:class: important

On 406 industrial erythromycin batches, split-conformal coverage came out at
**0.877** against a nominal 0.90 — the calibration held. The forecast it wraps
did not: **R² 0.104** on the same run. <!-- not-a-claim: our own benchmark, see the benchmarks page -->

Both halves are published, because a calibrated interval around an uninformative
forecast is still honest and still nearly useless for ranking designs. See
[Benchmarks](../benchmarks.md) and [Calibration on real production
data](../methods/real-data-calibration.md).
```

## 5. Choosing what to run next

```{code-cell} python
from engin_core.recommend import recommend_batch

X, mean, sd, ei = recommend_batch(gp, best_y=float(y_obs.max()), k=4, seed=0)
for i in range(len(X)):
    print(f"design {i}: predicted {mean[i]:5.1f} +/- {sd[i]:4.1f} g/L, EI {ei[i]:.3f}")
```

The recommender maximizes expected improvement over the incumbent and applies a
diversity filter, so a batch is not four variations on the current best — and it
will not re-propose a design you have already run.

```{admonition} A textbook baseline beats this, and it is on the front page
:class: warning

Sequential response surface methodology — Box–Wilson, as actually practised —
leads Engin's GP+EI at every one of ten rounds and wins on **20 of 20 seeds** on
an identical budget. <!-- not-a-claim: measured on our own simulator; see the benchmarks page -->

If you are optimizing a process today and want the best answer rather than the
calibrated one, fit a response surface. Engin's contribution is the interval, and
the interval is the part that transferred to real data. [Benchmarks](../benchmarks.md)
carries both results in the same table.
```

## Where to go next

- [Conformal calibration](../methods/conformal-calibration.md) — why the naive interval fails, measured
- [Out-of-distribution](../methods/out-of-distribution.md) — where coverage degrades and by how much
- [Limitations](../limitations.md) — the five-tier validation status, and what each tier does not establish
- [Data formats](data-formats.md) — getting your runs in, if they are currently a vendor export
