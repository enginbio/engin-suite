# Quickstart

From a spreadsheet of real production runs to a calibrated forecast, in about
five minutes of wall time and one command.

**This uses a published industrial dataset, not this project's simulator** — 406
erythromycin batches from a working pharmaceutical plant, CC-BY-4.0. That
distinction is the whole point: a quickstart written against our own simulator
would demonstrate that the code runs, which was never in doubt.

```bash
git clone https://github.com/enginbio/engin-suite
cd engin-suite
pip install -r requirements-dev.txt
cd packages/engin-core && python examples/quickstart_real_data.py
```

The first run downloads 8 MB and caches it. Most of the elapsed time is fitting
the Gaussian process.
<!-- ref: 2025-zenodo-erythromycin-efp -->


```{note}
Engin is **not on PyPI** — see [Install](install.md). Clone and install from
source.
```

## What it does, and why each step exists

### 1. Fetch, with the licence and provenance attached

```python
from engin_core.datasets import describe, fetch, manifest_for

print(describe("erythromycin-efp"))
(path,) = fetch("erythromycin-efp")
record = manifest_for(path)
```

The download is checksum-verified **against the publisher's own md5**, and a
JSON provenance manifest is written beside the file recording where it came
from, when, and under what licence. Any number you compute afterwards can be
traced to a specific byte sequence obtained on a given day.

`fetch` will also refuse a dataset whose licence forbids commercial use, because
Engin is Apache-2.0 and its users are commercial by assumption. Try
`fetch("indpensim")` to see that happen.

### 2. Ask what the columns are, and get an honest answer

```python
from engin_core.loaders import infer_columns

report = infer_columns(df)
print(report.summary())
```

```text
long table: 4 column(s) mapped, 21 unmapped, 0 below the 0.7 review threshold
run column : batch_id
time column: hh  (orientation: long)

  our -> our   1.0     cer -> cer   1.0
  rq  -> rq    1.0     kla -> kla   1.0
```

Four columns map at full confidence. **Twenty-one do not, and are carried
through under their original names** rather than dropped or guessed at — this
dataset's headers are unglossed abbreviations, and inventing meanings for them
is exactly the failure the confidence report exists to prevent.

### 3. Reshape onto the convention

```python
from engin_core.loaders import load_timeseries

ds, load_report = load_timeseries(df, run_column="batch_id", time_column="elapsed_h")
```

```text
dims: {'run': 406, 'time': 154}  variables: 25
  [warning] non-numeric columns not carried onto the Dataset: ['date']
  [warning] 156 row(s) repeated a (run, time) pair; kept the first of each
```

The result is an ordinary xarray Dataset on dims `(run, time)` with units in
`attrs` — no Engin-specific type, and another tool can read it without this
library installed. See [Data formats](guides/data-formats.md).

```{admonition} Two things real data made us handle
:class: tip

**`hh` is an absolute process hour, not elapsed time.** Batches begin anywhere
between hour 30 and hour 83, so each is aligned to its own start first. Skipping
this produces empty windows rather than an error.

**156 rows repeat a `(run, time)` pair**, which pandas will not put in an xarray
index. A first draft of this example did the reshape by hand and crashed on it;
`load_timeseries` keeps the first of each and says so. The library step is there
because it handles what the obvious two lines do not.
```

### 4. Fit, calibrate, forecast

Predict each batch's final potency from its first 72 hours, with a split-conformal
interval:

```python
gp = fit_gp(U[train], y[train], seed=0)
mc, sdc = gp.predict(U[calib], include_noise=True)
q = split_conformal_multiplier(y[calib], mc, sdc, level=0.90)
mean, sd = gp.predict(U[test], include_noise=True)
```

```text
 batch    actual  forecast          90% interval  covered
     0     10667     10886  [   10228,    11544]     True
     1     11050     10695  [   10043,    11347]     True
     2     10905     11080  [   10452,    11708]     True
     3     10966     11072  [   10437,    11707]     True
     4     11612     10872  [   10241,    11504]    False
```

### 5. Read it honestly — the part that matters

```text
empirical coverage : 0.802   (nominal 0.9)
R^2                : -0.151
mean interval width: 1269
```

**The calibration transfers — to held-out batches from this plant.** Averaged
over five seeds, coverage is 0.877 against a nominal 0.90 on batches the model
was not fitted on. The single split above carries roughly ±0.03 of binomial
noise, so do not read its third decimal — [the methods
page](methods/real-data-calibration.md) has the full table.

Two limits on what that sentence claims. The held-out batches come from the
**same plant** the model trained on, so this is not cross-plant transfer, which
is tested at no tier. And the split is random rather than chronological, over a
dataset that is time-ordered production history, so it does not establish that
the intervals hold on *next month's* batches — see
[#173](https://github.com/enginbio/engin-suite/issues/173) and the methods page.

**The forecast does not.** R² near zero means the model is close to predicting
the mean, and the intervals are wide enough to cover it anyway.

```{warning}
**A model can be well calibrated and still not know much.** Coverage says the
intervals are honest about the model's ignorance. It says nothing about whether
the model knows anything, which is why every number here is reported beside an
R² and a width.
```

That is a genuine limitation of this baseline rather than of the dataset —
adding early potency to the features roughly doubles R², and the dataset's own
authors report considerably better prediction using an architecture built for the
purpose. Engin's *calibration* transfers to real data; its *modelling*, pointed
naively at a task it was not designed for, does not.

## If you would rather not write Python

There is a command-line path, and it is deliberately **not** a second route to this
page's result. Each stage ships a console script that reads one `project.yaml`:

```bash
engin-host --init project.yaml   # writes a commented starter file to edit
engin-host     --config project.yaml   # [4] which chassis?
engin-pathway  --config project.yaml   # [3] which route?
engin-process  --config project.yaml   # [1] what to run next?
```

The starter file is the useful part if you are new: it names every input in plain
language and says which numbers are your judgement rather than something computed.

**What it does not do is this page.** `engin-process` has no way to read your run
history — its project file has no data section, and it *simulates* runs from the
vessel you describe. So it exercises the same recommender against a model of your
process, not against measurements of it, and none of the fetch, column-inference or
provenance machinery above is on that path. Reading your own runs from the CLI is
tracked in [#141](https://github.com/enginbio/engin-suite/issues/141).

That distinction is the same one this page opens with, so it is worth stating twice:
a result computed from a simulator shows the code runs, and a result computed from
406 real batches shows something else. The CLI is the fastest way to see what
questions the tool asks. This page is the way to see whether its answers hold up.

## Where to go next

- [Install](install.md) — the full command set for the CLI above
- [Data formats](guides/data-formats.md) — the convention and the ingest layer
- [Conformal calibration](methods/conformal-calibration.md) — why the interval is built this way
- [Out-of-distribution](methods/out-of-distribution.md) — where the intervals stop holding
- [Limitations](limitations.md) — what has and has not been shown
