---
sd_hide_title: true
---

# Engin

```{toctree}
:hidden:
:caption: Getting started

quickstart
install
```

```{toctree}
:hidden:
:caption: Guides

guides/forecasting
guides/cost
guides/data-formats
```

```{toctree}
:hidden:
:caption: Reference

api/index
api-stability
methods/conformal-calibration
methods/out-of-distribution
methods/real-data-calibration
benchmarks
limitations
```

```{toctree}
:hidden:
:caption: Project

governance
biosecurity
contributing
decisions
adr/index
```

# Engin

**Open tooling for bioprocess forecasting and scale-up economics.**

Turn a handful of fermentation runs into a titer forecast with honest uncertainty, a recommendation for what to run next, and a probabilistic cost-per-kilogram read that accounts for recovery.

```{warning}
**Pre-1.0, and validated on synthetic data so far.**

Results below come from a mechanistic simulator, not from real fermentation
campaigns. That is a genuine limitation, not a formality — see
[Limitations](limitations) and [Benchmarks](benchmarks) for exactly what has
and has not been demonstrated. Real-data validation is the project's current
priority.
```

## Why this exists

Every bioprocess company rebuilds the same foundational software, because that software is either trade secret or has never existed. Large companies hold an advantage over small ones for no better reason than having already built the basic tooling.

Engin makes that layer public infrastructure, so a team starts where the last one finished. Everything here is free, and always will be.

## What makes it different

::::{grid} 1 1 3 3
:gutter: 3

:::{grid-item-card} Calibrated, not confident
Most bioprocess optimizers return point predictions or intervals that are quietly overconfident. Engin uses split-conformal calibration and reports honest coverage — including when it degrades.
:::

:::{grid-item-card} Optimizes cost, not titer
Recovery cost is determined upstream but paid downstream, so maximizing titer can move the real objective backwards. The recommender optimizes net $/kg. This makes Engin look *worse* on the metric everyone reports, deliberately.
:::

:::{grid-item-card} Composes, doesn't replace
Built on BayBE, BioSTEAM, COBRApy and MAPIE rather than reimplementing them. Your data stays in xarray and pandas — no bespoke container to learn, and nothing locked inside Engin.
:::

::::

## Start here

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} Quickstart
:link: quickstart
:link-type: doc

From a spreadsheet of runs to a calibrated forecast in under ten minutes.
:::

:::{grid-item-card} Benchmarks
:link: benchmarks
:link-type: doc

How Engin performs against plain DoE, BayBE and BioSTEAM — including where it loses.
:::

::::

## Install

**Not on PyPI yet** — no distribution name is registered to this project, so
`pip install engin-core` fetches nothing today. From source:

```bash
git clone https://github.com/enginbio/engin-suite
cd engin-suite && pip install -r requirements-dev.txt
```

Requires Python 3.10+. See [Install](install) for extras and the reasoning.

## Honest baselines

Every claim on this site is benchmarked against the simpler thing it says it beats — plain DoE/RSM for optimization, BioSTEAM for techno-economics, step-count heuristics for pathway ranking, "just use *E. coli*" for host selection.

Cases where a simpler baseline wins are published in the same table as the wins. A benchmark suite that always favours its author is worthless, and we would rather you trusted the ones we do win.

## Contributing

Two things help most: **real fermentation data** or pointers to public datasets, and **benchmarks where Engin loses**. See [Contributing](contributing).

The project has one maintainer and is [open to co-founders](governance).

---

Apache-2.0. No contributor licence agreement — [deliberately](governance), because it means this code can never be relicensed away from you.
