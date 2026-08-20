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
methods/vendor-export-ingest
case-studies/process-development
case-studies/techno-economic-analysis
benchmarks
contributing-a-benchmark
limitations
ecosystem
references
```

```{toctree}
:hidden:
:caption: Project

governance
biosecurity
contributing
decisions
design/data-convention
design/host-selection
adr/index
```

**Open tooling for bioprocess forecasting and scale-up economics.**

Turn a handful of fermentation runs into a titer forecast with honest uncertainty, a recommendation for what to run next, and a probabilistic cost-per-kilogram read that accounts for recovery.<sup>\*</sup>

:::{dropdown} <sup>\*</sup> Pre-1.0 — the calibration is measured on real production data, and nearly everything else is not
:animate: fade-in-slide-down

The conformal intervals have been tested against 406 erythromycin batches from a
working pharmaceutical plant, and they cover at close to their nominal rate. The
forecasts they wrap are close to uninformative on that data. Both halves are
published, because the first without the second would be the more flattering and
the less true account.

Everything else — the next-batch recommender, the optimization comparisons,
pathway ranking — comes from a mechanistic simulator, not from real fermentation
campaigns. That is a genuine limitation, not a formality: see
[Limitations](limitations) for the five-tier validation status and
[Benchmarks](benchmarks) for exactly what has and has not been run.

This caveat is repeated on the pages where it actually bites, rather than only
here — a reader about to trust a number should meet it there.
:::

## Start where you are

Pick the row that describes you. The decisions are the same either way; what changes is how much is explained on the way in.

::::::{tab-set}

:::::{tab-item} New to this
:sync: new

You have a molecule and a hypothesis, and you want to know what the questions even are.

**If you would rather not write Python, start here:**

```bash
engin-host --init project.yaml
```

That writes a commented file naming every input each stage takes, in plain language —
what `secretion` weighs, what `g_thermo` means, and which numbers are your judgement
rather than something computed. Edit it, then run whichever stage you have filled in
(`engin-host`, `engin-pathway`, `engin-process`). Each prints its own caveats on exit.
See [Install](install.md) for the full command set.

**If you would rather see it work on real data**, start with
**[Quickstart](quickstart)** — 406 batches from a working plant to a calibrated
forecast. It is a Python script, and it is the honest one: the CLI simulates your runs
from the vessel you describe, while the quickstart uses measurements somebody actually
took.

Then come back for the decision you are facing.

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item-card} What should I make?
Ranking candidate molecules by cost interval is **not built**. Tracked in
[#176](https://github.com/enginbio/engin-suite/issues/176); today the target is an input you supply.
:::

:::{grid-item-card} Which host?
:link: design/host-selection
:link-type: doc

Scoring chassis against a production requirement, with a confidence band and hard-constraint flags.
:::

:::{grid-item-card} Will my process get there?
:link: quickstart
:link-type: doc

A titer forecast with a calibrated interval from a small number of runs, and what to run
next — worked end to end on real batches, including where the forecast is weak.
:::

:::{grid-item-card} What will it cost?
Cost per kilogram as a distribution, including recovery. The **guide is unwritten**; what
the model does and does not capture is in
[Limitations](limitations), and the API is in [`engin_core.tea`](api/index).
:::

::::
:::::

:::::{tab-item} I have a process
:sync: practitioner

You have runs, a vocabulary, and a specific question. Straight to it:

::::{grid} 1 1 2 2
:gutter: 2

:::{grid-item-card} The API
:link: api/index
:link-type: doc

Every public entry point, with the [stability guarantee](api-stability) that says what may change.
:::

:::{grid-item-card} Getting your data in
:link: guides/data-formats
:link-type: doc

The ingest layer, vendor exports, and the [data convention](design/data-convention) underneath.
:::

:::{grid-item-card} What has actually been measured
:link: benchmarks
:link-type: doc

Including the baselines that beat us, in the same table as the ones that don't.
:::

:::{grid-item-card} What to use instead
:link: ecosystem
:link-type: doc

Ten capability areas Engin deliberately does not build, with licences and dead ends.
:::

::::
:::::

:::::{tab-item} Scaling up
:sync: scale

**This is the least complete path, and saying so is more useful than a card that implies otherwise.**

The bundled simulator has no oxygen state, so it is exactly scale-invariant — every scale-up artifact it produces is vacuous with respect to scale. That is documented rather than worked around.

- **[Limitations](limitations)** — the five-tier validation status and what each tier does not establish
- **[Cost and techno-economics](guides/cost)** — capital, batch scheduling and recovery, which *are* modelled
- Break-even inversion — *"what titer must I hit to clear a price?"* — is tracked in [#143](https://github.com/enginbio/engin-suite/issues/143)
:::::

::::::

## How the stages fit together

Each stage hands the next its **decision and its uncertainty**, so an unresolved
choice early on widens the interval later rather than disappearing.

```{raw} html
<svg viewBox="0 0 720 208" role="img" aria-labelledby="funnel-t funnel-d"
     style="width:100%;height:auto;max-width:44rem;margin:0.5rem 0;color:inherit">
  <title id="funnel-t">The strain-to-scale funnel</title>
  <desc id="funnel-d">Four stages left to right. Target: you supply it; ranking
  candidates is proposed in issue 176 and is not built. Stage 4, host selection,
  emits a HostDecision carrying a confidence. Stage 3, pathway ranking, emits a
  RouteRanking with conformal bounds. Stage 1, process, emits a ProcessBrief and a
  cost per kilogram. A band beneath widens left to right: a low-confidence host
  multiplies the downstream half-width by two minus confidence.</desc>

  <g fill="none" stroke="currentColor" stroke-width="1.5">
    <rect x="11"  y="26" width="158" height="72" rx="6" stroke-dasharray="5 4" opacity="0.55"/>
    <rect x="191" y="26" width="158" height="72" rx="6"/>
    <rect x="371" y="26" width="158" height="72" rx="6"/>
    <rect x="551" y="26" width="158" height="72" rx="6"/>
  </g>

  <g fill="currentColor" font-size="13" font-weight="600">
    <text x="90"  y="50" text-anchor="middle" opacity="0.65">target</text>
    <text x="270" y="50" text-anchor="middle">[4] host</text>
    <text x="450" y="50" text-anchor="middle">[3] pathway</text>
    <text x="630" y="50" text-anchor="middle">[1] process</text>
  </g>

  <g fill="currentColor" font-size="10.5" opacity="0.8">
    <text x="90"  y="70" text-anchor="middle" opacity="0.75">you supply this</text>
    <text x="90"  y="85" text-anchor="middle" opacity="0.75">ranking it: not built</text>
    <text x="270" y="70" text-anchor="middle">which organism</text>
    <text x="270" y="85" text-anchor="middle">engin-host</text>
    <text x="450" y="70" text-anchor="middle">which route</text>
    <text x="450" y="85" text-anchor="middle">engin-pathway</text>
    <text x="630" y="70" text-anchor="middle">vessel, $/kg</text>
    <text x="630" y="85" text-anchor="middle">engin-core</text>
  </g>

  <g stroke="currentColor" stroke-width="1.5" fill="none">
    <path d="M169 62 H185" opacity="0.55"/><path d="M180 57 l6 5 -6 5" opacity="0.55"/>
    <path d="M349 62 H365"/><path d="M360 57 l6 5 -6 5"/>
    <path d="M529 62 H545"/><path d="M540 57 l6 5 -6 5"/>
  </g>

  <g fill="currentColor" font-size="9.5" opacity="0.7" font-style="italic">
    <text x="357" y="118" text-anchor="middle">HostDecision</text>
    <text x="537" y="118" text-anchor="middle">RouteRanking</text>
  </g>

  <path d="M191 168 L709 152 V190 L191 178 Z" fill="currentColor" opacity="0.14"/>
  <g fill="currentColor" font-size="10.5">
    <text x="191" y="200" opacity="0.8">uncertainty compounds &#8594;</text>
    <text x="709" y="200" text-anchor="end" opacity="0.8">half-width &#215; (2 &#8722; confidence)</text>
  </g>
</svg>
```

**The dashed box is the honest part.** `target` is an input you supply — the
config file says of it, *"labels the output; nothing computes from it."* Ranking
candidate molecules is [proposed](https://github.com/enginbio/engin-suite/issues/176)
and not built, so the funnel starts one stage later than a tidier diagram would
suggest.

The widening band is `inflate_uncertainty`: a host chosen with confidence 0.5
multiplies the pathway stage's half-width by 1.5 before the process stage sees it.
That propagated width is **not** a calibrated interval, and
[`ProcessBrief`](api/index) says so.

## Why this exists

Practitioners describe rebuilding the same foundational software at company after company, because that software is either trade secret or has never existed. Engin makes that layer public infrastructure, so a team starts where the last one finished. Everything here is free, and always will be.

:::{dropdown} Why that claim is stated as testimony rather than as a finding
:animate: fade-in-slide-down

That is testimony rather than a survey, and it is stated as such deliberately — this project's whole argument is that an uncalibrated claim should be labelled as one.

Large companies hold an advantage over small ones for no better reason than having already built the basic tooling. Removing that asymmetry is the point; see [Governance](governance) for how the project is run and [Decisions](decisions) for why it is free.
:::

## What makes it different

::::{grid} 1 1 3 3
:gutter: 3

:::{grid-item-card} Calibrated, not confident
Take a Gaussian process's own uncertainty, multiply by 1.645, call it a 90% interval — and it covers barely more than half the time. Engin uses split-conformal calibration and reports honest coverage, [including where it degrades](methods/out-of-distribution).
:::

:::{grid-item-card} Optimizes cost, not titer
Titer captures one of three cost centres, and which one dominates depends on the product — downstream for high-value low-titer products, raw material for bulk ones. So the recommender optimizes net $/kg. This makes Engin look *worse* on the metric everyone reports, deliberately.
:::

:::{grid-item-card} Composes, doesn't replace
MAPIE cross-checks the conformal intervals; BioSTEAM backs techno-economics as an optional extra. BayBE and COBRApy are *not* dependencies — they are why parts of the roadmap stay unbuilt (`D9`). Your data stays in xarray and pandas. The [ecosystem map](ecosystem) says where to go for everything Engin deliberately doesn't build.
:::

::::

## Honest baselines

**A textbook response surface method beats us, and it is on the front page rather than in a footnote.** Sequential RSM leads at every one of ten rounds and wins on 20 of 20 seeds against multi-round Engin on an identical budget.

A benchmark suite that always favours its author is worthless, and we would rather you trusted the ones we do win.

:::{dropdown} The full comparison, and which baselines are still unbuilt
:animate: fade-in-slide-down

The commitment is that every claim is benchmarked against the simpler thing it says it beats — plain DoE/RSM for optimization, BioSTEAM for techno-economics, step-count heuristics for pathway ranking, "just use *E. coli*" for host selection.

**Two of those are implemented today** — RSM for optimization, and step-count for pathway ranking. BioSTEAM and "just use *E. coli*" are not built. That sentence used to be written as though all four were, and then as though three were; naming them rather than counting them is so the next drift shows up in the diff instead of hiding inside a number. [Benchmarks](benchmarks) marks which is which, because a page promising honest baselines is the last place to overstate what has been run.

**The first real baseline beat us, twice.** A textbook response surface proposes better designs than Engin's GP with expected improvement on 18 of 20 seeds — and its OLS prediction interval lands closer to nominal coverage than our conformal one, 17% narrower. <!-- not-a-claim: measured on our own simulator; see the benchmarks page --> Both results are at the top of the [benchmarks](benchmarks) page rather than in a footnote, with what they do and don't settle.

**Then it beat us again, on the comparison we said would be fairer.** One round favours pure exploitation, so the obvious defence was that expected improvement pays its exploration back later. Sequential response surface methodology — Box–Wilson, the way it is actually practised — against multi-round Engin on an identical budget says otherwise: RSM leads at every one of ten rounds and wins on 20 of 20 seeds. The exploration does pay back part of the gap, and never closes it. That is on the benchmarks page too.

Cases where a simpler baseline wins are published in the same table as the wins.
:::

## Install

**Not released on PyPI** — and `pip install engin-core` will *appear* to work.
Four names are registered as empty placeholder reservations, so that command
installs a stub containing nothing. See [Install](install). From source:

```bash
git clone https://github.com/enginbio/engin-suite
cd engin-suite && pip install -r requirements-dev.txt
```

Requires Python 3.10+. See [Install](install) for extras and the reasoning.

## Contributing

Two things help most: **real fermentation data** or pointers to public datasets, and **benchmarks where Engin loses**. See [Contributing](contributing).

Questions, results and "does this apply to my process?" belong in
[Discussions](https://github.com/enginbio/engin-suite/discussions); defects and
specific changes belong in
[Issues](https://github.com/enginbio/engin-suite/issues). If a number on this
site looks wrong, either is the right place — the whole argument here is that the
claims are checkable.

The project has one maintainer and is [open to co-founders](governance).

---

Apache-2.0. No contributor licence agreement — [deliberately](governance), because it means this code can never be relicensed away from you.
