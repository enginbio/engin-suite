---
file_format: mystnb
kernelspec:
  name: python3
  display_name: Python 3
  # `language` is load-bearing, not decoration. With execution ON (CI) the kernel
  # reports it; with execution OFF (Read the Docs, D20) there is no kernel, and
  # without it myst-nb emits "No source code lexer found for notebook cell N" for
  # every cell -- which fail_on_warning turns into a failed RTD build while CI
  # stays green.
  language: python
---

# Data formats and conventions

Engin introduces **no bespoke data container**. Time-series runs are
[xarray](https://docs.xarray.dev/) Datasets; endpoint design-of-experiments data
is a pandas DataFrame. Your data is not locked inside Engin, and there is no new
type to learn.

What *is* versioned is a thin **convention** over those structures — which
dimensions things live on, where units go, where metadata attaches — plus a
validator that tells you how far a dataset sits from it.

```{note}
The convention lives in the optional `io` extra, since the modelling path does
not need xarray or pandas:

    pip install "engin-core[io]"
```

## Why a convention and not a format

The constraint that shaped this: **another tool must be able to read and write
this without depending on Engin at all.** A type we own fails that the moment
somebody has to reimplement it. A convention over structures that already have
readers and writers satisfies it by construction — a conforming dataset is an
ordinary netCDF file.

The precedent is climate science, which layered CF conventions onto netCDF
rather than inventing an array format. This borrows CF's *mechanism* — meaning
carried in `attrs` as `units` and friends — without its vocabulary, which is
about latitude and cell measures and has nothing to say about a bioreactor.

See `D11` in [Decisions](../decisions.md), including the two superseded versions
of this decision and why each was wrong.

## Time series

Dimensions `(run, time)`, one data variable per measured channel, units in each
variable's `attrs`, and the convention version on the Dataset:

```{code-cell} python
import numpy as np
import xarray as xr
from engin_core.convention import stamp, validate_timeseries

rng = np.random.default_rng(0)
n_run, n_time = 3, 12

ds = xr.Dataset(
    data_vars={
        "titer":   (("run", "time"), rng.random((n_run, n_time)) * 40, {"units": "g/L"}),
        "biomass": (("run", "time"), rng.random((n_run, n_time)) * 20, {"units": "g/L"}),
        "mu":      (("run", "time"), rng.random((n_run, n_time)) * 0.35, {"units": "1/h"}),
    },
    coords={
        "run":  ("run", [f"R{i:02d}" for i in range(n_run)]),
        "time": ("time", np.arange(float(n_time)), {"units": "h"}),
    },
)

report = validate_timeseries(stamp(ds))
print(report.summary())
```

`time` is **elapsed** time, not wall clock — runs are compared to each other
rather than to a calendar.

## The validator reports, it does not reject

Real bioprocess data arrives from vendor exports that nobody designed for
interchange. A validator whose only verdict is "rejected" would be a wall in
front of the ingest layer rather than a guide through it. So every finding names
what it saw and what would fix it:

```{code-cell} python
broken = ds.copy()
del broken["titer"].attrs["units"]
broken["mu"].attrs["units"] = "per hour-ish"
broken["fluorescence"] = (("run", "time"), np.zeros((n_run, n_time)), {"units": "1"})

report = validate_timeseries(broken)
print(report.summary())
for finding in report.findings:
    print(f"  {finding}")
```

Note what is *not* an error there. An unregistered channel is carried without
interpretation — a convention that refused to hold a measurement it had not
heard of would be useless on the first real dataset. A unit that parses but
isn't the one we record in is a warning, because it is convertible.

`report.ok` means no error-level findings. It is a summary for your tests and
CI, not a gate the library enforces on you.

## Endpoint DoE tables

One row per run, a `run_id` column, and units passed **alongside** the frame:

```{code-cell} python
import pandas as pd
from engin_core.convention import validate_endpoints

doe = pd.DataFrame({
    "run_id":    ["R00", "R01", "R02"],
    "feed_rate": [0.1, 0.2, 0.3],
    "titer":     [30.0, 35.0, 28.0],
})

report = validate_endpoints(doe, units={"titer": "g/L", "feed_rate": "L/h"})
print(report.summary())
```

Units are a separate argument rather than `DataFrame.attrs` for a blunt reason:
**pandas drops `.attrs` when you write a CSV.** Units stored there vanish on the
way to the person you sent the file to. This is a property of pandas rather than
a choice made here, and it is pinned as a test so that if it ever changes, the
convention gets simplified rather than the rule quietly outliving its reason.

## Units

Unit strings are written the way [pint](https://pint.readthedocs.io/) parses
them — `"g/L"`, `"1/h"`, `"degC"`, `"rpm"` — and dimensionless quantities are
`"1"`. With pint installed the validator parses them, so a typo is caught rather
than carried.

One domain unit needs teaching: `vvm`, gas volumes per liquid volume per minute,
is standard in fermentation and absent from pint's registry.
`register_domain_units()` defines it, and the validator calls it for you.

## Registered channels

Known channel names and the units the convention records them in:

```{code-cell} python
from engin_core.convention import CHANNELS

for channel in CHANNELS.values():
    print(f"  {channel.name:14s} {channel.units:6s}  {channel.description}")
```

This is a recommendation, not a closed vocabulary. Channels outside it are
carried as-is.

## Getting messy data onto the convention

Nobody's export arrives conforming. `engin_core.loaders` maps the headers a
bioreactor or a spreadsheet actually produced onto the convention's channels,
pulls units out of wherever they were hiding, and **reports what it did rather
than raising**:

```{code-cell} python
import pandas as pd
from engin_core.loaders import load_endpoints

messy = pd.DataFrame({
    "Batch":        ["B1", "B2"],
    "Titre (g/L)":  [30.0, 31.5],
    "OD600":        [4.1, 4.4],
    "O2 (%)":       [21.0, 20.8],
    "AUX2_raw":     [0.11, 0.09],
})

tidy, report = load_endpoints(messy)
print(report.summary())
print()
for guess in report.guesses:
    mapped = guess.channel or "—"
    print(f"  {guess.source:14s} -> {mapped:10s} {guess.confidence:>4}  {guess.evidence}")
```

`AUX2_raw` is reported, not dropped — the person reading knows what it was, and
the loader does not. It survives into the returned frame untouched.

### Confidence is a heuristic, not a calibration

```{warning}
The score is an **ordinal ranking aid, not a calibrated probability.** A 0.9
means "matched a known alias and the units agree" — it does *not* mean nine
times in ten the mapping is right, because nothing has been measured against
labelled exports. Calibrating it needs a corpus of real files with known-correct
mappings, which is the same data problem as `D12` tier 3–4.
```

Use it to decide *what to look at first*:

```{code-cell} python
for guess in report.needs_review:
    print(f"  check {guess.source!r}: {guess.evidence}")
    if guess.alternatives:
        print(f"    could also be: {guess.alternatives}")
```

Ambiguity is preserved rather than resolved by fiat. A bare `O2` column is
genuinely ambiguous between dissolved and exhaust oxygen, so it scores low and
names both candidates instead of picking one confidently.

### Long tables to Datasets

A long export — one row per run per timepoint — reshapes to the convention in
one call:

```{code-cell} python
from engin_core.loaders import load_timeseries
from engin_core.convention import validate_timeseries

rows = [
    {"Batch": run, "Time (h)": float(t), "Titer (g/L)": 10.0 + t, "OD600": 2.0 + t}
    for run in ("R00", "R01")
    for t in range(4)
]

ds, load_report = load_timeseries(pd.DataFrame(rows))
print(load_report.summary())
print(validate_timeseries(ds).summary())
print(ds)
```

The result conforms, so the loader and the validator agree — which is the point
of having both.

`load_timeseries` raises in exactly one case: there is no run or time column, so
there is nothing to reshape onto. Everything else is a report.

### Teaching it your headers

```{code-cell} python
from engin_core.loaders import infer_columns, register_alias

register_alias("titer", "prod_a")
print(infer_columns(pd.DataFrame({"PROD_A": [1.0]})).guesses[0].evidence)
```

### On vendor-specific loaders

There are none yet, deliberately. Writing a Sartorius or Benchling parser from a
general impression of what such a file looks like would be inventing a format
and calling it support — delimiters, encodings and header spellings are exactly
what cannot be reasoned out. The alias table is seeded with generic spellings,
and `register_alias` lets a real file teach the loader without a code change.
Vendor profiles land when someone has the actual files.

## Related

- [Limitations](../limitations.md) — what has and has not been validated
- [Decisions](../decisions.md) — `D11` for the convention, `D12` for data policy
