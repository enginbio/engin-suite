# Limitations

An honest account of what Engin has and has not been shown to do. This page
exists from the first release and is updated as validation progresses.

## Validation status

**Most results published here come from a mechanistic simulator, not from real
fermentation campaigns.** A coefficient of determination measured against the
simulator that produced the data demonstrates that the code runs. It does not
demonstrate that the method works on real bioprocess data.

**Tier 3 is now measured.** [Calibration on real production
data](methods/real-data-calibration.md) reports coverage on 406 erythromycin
batches from a working plant: the intervals cover at close to their nominal rate,
and the forecasts they wrap are close to uninformative. Both halves are published,
because the first without the second would be the more flattering and less true
account.

**Measured under a random split, which bounds what it establishes.** The batches
are time-ordered production history and the benchmark permutes them, so the result
is marginal coverage under exchangeability — real noise, real missingness, real
feature distributions, but no test of temporal drift. That page states the
protocol and why it matters.

Validation is structured in five tiers, each reported with what it does and does
not establish:

| Tier | Source | Establishes | Does not establish |
|---|---|---|---|
| 1 | Engin's own simulator | the loop works end to end | anything about real data — the model is validated against its own assumptions |
| 2 | An independent simulator | not overfitted to our own model's quirks | real-world behaviour |
| 3 | Real industrial data | survives real noise, missingness, scale change | in-domain performance; cost coupling, where data is normalised; **behaviour under temporal drift** — the split is random, not chronological |
| 4 | In-domain literature DoE | the actual product claim | generalisation beyond small, heterogeneous samples |
| 5 | Partner campaign data | end-to-end value | — not yet available |

Current status is recorded in [Benchmarks](benchmarks.md).

## Known constraints

- **No public corpus of *process-condition* design-of-experiments data with absolute titers exists**, which limits tier 4. **Corrected 2026-08-10:** this sentence used to do more work than it could carry. Real, industrial, in-domain microbial process data *does* exist publicly and permissively — the [erythromycin fermentation dataset](https://doi.org/10.5281/zenodo.14619074) is 406 production batches sampled hourly, CC-BY-4.0, with a product-potency target. What it is not is *designed* variation: process conditions were recorded, not varied to explore a design space. So tier 4 remains open and tier 3 does not, and the earlier phrasing implied a scarcity that was broader than the facts.

  **Narrowed again 2026-08-16, and the claim is weaker than it looked.** It used
  to say *in-domain*, which reads as any microbial DoE and is false on that
  reading. "In-domain" here means Engin's actual design space, which is process
  conditions — `feed_rate`, `feed_start`, `Sf`, `induction_time`, `S0`. A
  design-of-experiments over gene targets is not an input this model can consume.
  Two public multi-cycle campaigns were searched and each falsifies a *different*
  half of the sentence, which is the only reason it survives:

  | Campaign | Designed variation | Response | Why it does not falsify |
  |---|---|---|---|
  | [JBEI isoprenol CRISPRi](https://doi.org/10.1038/s41467-025-66304-8) — 6 DBTL cycles, ART-guided | sgRNA combinations over gene targets, ~800,000-combination space | **absolute titer, mg/L** | designed variation is genetic, not process conditions |
  | [JBEI flaviolin media optimization](https://doi.org/10.1038/s42003-025-08039-2) — 3 campaigns, LHS then ART | **media components** — genuinely process inputs | Abs340, which the paper itself calls a *titer proxy* | the response is not an absolute titer |

  Read the table honestly: the flaviolin campaigns are designed variation over
  process inputs across multiple cycles, and they fail this claim on the assay
  alone. **The absence is one measurement away from not existing**, so it is not
  the field-wide scarcity the earlier wording implied — it is a narrow and
  possibly temporary gap. Searched 2026-08-16; if you know of a counterexample,
  [open an issue](https://github.com/enginbio/engin-suite/issues) — that is the
  contribution this page most wants. Tracked in
  [#174](https://github.com/enginbio/engin-suite/issues/174).
- **Cost coupling is demonstrated on mechanistic grounds.** No public dataset found supports validating cost-per-kilogram predictions end to end.
- **Calibrated intervals degrade out of distribution.** Coverage is reported for out-of-distribution cases rather than omitted.

## The simulator has no oxygen, so scale is inert

Added 2026-08-18 ([#190](https://github.com/enginbio/engin-suite/issues/190)).
Until then this page contained **zero** occurrences of oxygen, kLa, OTR or
aeration, <!-- not-a-claim: grep count over this file before this section --> which
on a page this specific about the 2% raw-material share and the 1-of-40 ingest <!-- not-a-claim: both figures are this page's own, cited in their own sections -->
failure was the conspicuous silence rather than an omission.

`engin_core.simulator` integrates the state vector `[X, S, P, V]` — biomass,
substrate, product, volume. There is no dissolved-oxygen state, no kLa, no oxygen
uptake rate and no overflow-metabolism branch.

**The consequence is an algebraic identity, not a fidelity quibble.** Every
concentration equation in `_rhs` depends on volume only through the dilution term
`F/V`, and the feeding switch is `V < vmax`. Scaling `v0`, `vmax` and `feed_rate`
by a common factor leaves `F/V` and the switch times unchanged, so `X`, `S` and
`P` are *pointwise identical* and only `V` scales. **Varying the vessel changes
nothing about the predicted titer.**

Measured across six random designs, bench vessel against scaled vessel:

| scale factor | vessel | largest titer difference |
|---|---|---|
| 10× | 25 L | 6.0e-07 g/L |
| 1,000× | 2,500 L | 6.3e-07 g/L |
| 10,000× | 25,000 L | 7.2e-07 g/L |
| 100,000× | 250,000 L | 4.9e-07 g/L |

The residual does not grow with scale, and it tracks the integrator: at
`rtol=1e-9` it falls to 2.5e-09 and at `rtol=1e-12` to 1.8e-12.
<!-- not-a-claim: measured on our own simulator, reproduced by benchmarks/scale_invariance.py -->
So it is RK45 truncation error, not a scale effect — **the invariance is exact and
the table is measuring the solver.**

This makes one sentence in the code false, and it has been corrected:
`ReactorConfig` said that "a scale-up question usually varies the second while
holding the first", and varying precisely those parameters is provably a no-op.

Two further consequences of the same omission:

- **`feed_rate` has no feasibility ceiling.** The only limits are the knob bound
  and the `vmax` volume cap, neither of which is physical. With all five knobs at
  their upper bounds the simulator reports peak biomass of **124 g/L DCW in a 1 L vessel**, <!-- not-a-claim: measured on our own simulator; reproduced by benchmarks/scale_invariance.py -->
  and across 3,000 random designs **9.9%** exceed 100 g/L, <!-- not-a-claim: measured on our own simulator; reproduced by benchmarks/scale_invariance.py -->
  with no penalty of any kind. That is deep inside the high-cell-density regime
  the oxygen-transfer literature is entirely about.
- **The interior optimum is partly an artifact of the knob bounds.** Across the
  top 40 of 3,000 random designs, mean unit-cube coordinates are `feed_rate` 0.89
  and `Sf` 0.91 — pinned near their upper bounds.
  <!-- not-a-claim: measured on our own simulator; reproduced by benchmarks/scale_invariance.py -->
  Raise the bound and the optimum follows.

**Why this is the omission that matters.** Oxygen transfer is, in the standard
review of the subject, "often the rate-limiting step" in aerobic bioprocesses, and
predicting kLa is called a crucial step in bioreactor design and
scale-up.[^2009-garcia-ochoa-otr-scaleup] Because kLa is set by power input,
gas flow and broth properties rather than by volume, transfer capacity does not
arrive free with a bigger vessel — which is the reason scale-up is hard, and
exactly what a model without an oxygen state cannot represent.

The coupling this model is missing is also specific rather than diffuse. In
high-cell-density culture the substrate feed rate must be adapted to the cells'
changing capability to avoid overfeeding and inhibitory by-products, and
heterologous protein production itself *lowers* the maximal specific oxygen uptake
rate.[^2014-schaepe-overfeeding] So in a real vessel `induction_time` tightens the
feasible `feed_rate`; here the two knobs are independent by construction.

**What this does and does not invalidate.** The GP, the conformal calibration, the
recommender and the sensitivity readout are unaffected — they are claims about
learning a response surface from data, and they are measured against real
production data in [Calibration on real production
data](methods/real-data-calibration.md). What is not supported is any statement
that varying *scale* in this simulator tells you something about scale. Tier 1 and
tier 2 in the table above were always "the loop works end to end"; this section
says which specific question the bundled simulator cannot be asked.

Adding the missing physics — a dissolved-oxygen state, a kLa correlation and an
overflow branch — is a modelling project with its own validation burden, and it is
tracked on [#190](https://github.com/enginbio/engin-suite/issues/190) rather than
done quietly here.

[^2009-garcia-ochoa-otr-scaleup]: Garcia-Ochoa & Gomez, *Bioreactor scale-up and oxygen transfer rate in microbial processes: an overview*, Biotechnology Advances 27(2) (2009) 153–176. [doi:10.1016/j.biotechadv.2008.10.006](https://doi.org/10.1016/j.biotechadv.2008.10.006).

[^2014-schaepe-overfeeding]: Schaepe, Kuprijanov, Simutis & Lübbert, *Avoiding overfeeding in high cell density fed-batch cultures of E. coli during the production of heterologous proteins*, Journal of Biotechnology 192 Pt A (2014) 146–153. [doi:10.1016/j.jbiotec.2014.09.002](https://doi.org/10.1016/j.jbiotec.2014.09.002).

## Ingest confidence is not calibrated

The schema-inference score reported by `engin_core.loaders` is an **ordinal
heuristic, not a calibrated probability.** A 0.9 means "matched a known alias
and the units agree"; it does not mean the mapping is right nine times in ten.
It has not been measured against a corpus of labelled exports, and no such
corpus exists here — the same data problem as tier 3–4 above.

This is called out rather than left implicit because on a project whose argument
is calibrated uncertainty, a number named "confidence" that has not been
calibrated is the easiest thing to over-read. Use it to rank what to review
first, not to decide what needs no review.

**Updated 2026-08-14: one real export has now been measured, and it went badly.**
This section used to add that nothing had been measured *because no corpus
exists*, which quietly implied nothing could be. Real DASGIP/DASware exports were
public in [`detl`](https://github.com/JuBiotech/detl)'s test fixtures the whole
time. Run against one, the loader mapped **1 of 40 columns and that one was
wrong**, having first failed three times to read the file at all —
[the full report](methods/vendor-export-ingest.md).

One file from one vendor calibrates nothing, so the paragraph above stands
unchanged: the score is still an ordinal heuristic and should still be read as
one. What has changed is that the gap is now measured rather than asserted, and
the first measurement says the honest description of the ingest layer is
narrower than "handles messy exports" — it handles *tabular* exports whose
headers name their channels.

## Techno-economic constraints

Two limitations of the cost head are specific enough to state plainly. Both are
pinned as tests, so they cannot drift silently — if either test starts failing,
the situation has improved and this page is what should be updated.

- **The bundled simulator cannot reproduce industrial COGS structure.** At the
  cost model's default substrate price ($0.55/kg, glucose-scale) and this simulator's <!-- not-a-claim: our own model default, set in tea.py -->
  substrate-to-product ratio at 1–2 L scale, raw material lands at roughly **2%** <!-- not-a-claim: measured on our own simulator; pinned in test_tea.py -->
  of modelled cost.

  **Corrected 2026-08-18: this bullet compared against the wrong end of the
  continuum (#122).** It read that raw material lands at 2% "where the literature
  has substrate cost as a dominant term set by yield — 'more than 50% of the total
  costs' for commodity chemicals"
  ([Konzock & Nielsen 2024](https://doi.org/10.1016/j.tibtech.2024.04.007)).
  <!-- ref: 2024-konzock-try-costs -->
  But `D13`'s other citation says the split **slides with selling price**, and the
  cost model's defaults encode a **$200/kg specialty product**, not a commodity.
  Straathof puts downstream at ~15% for ethanol at ~$0.5/kg against 45–92% for
  biopharmaceuticals; a $200/kg product is not supposed to have commodity cost
  structure, so being downstream-dominated here is predicted rather than anomalous.
  <!-- ref: 2011-straathof-downstream-costs -->

  The gap is still real — 2% sits below the 15–60% carbohydrate-feedstock range
  Straathof reports across every process he analysed
  <!-- ref: 2011-straathof-downstream-costs --> — but **its size cannot be
  stated while the product class is undeclared**, because the figure it should be
  compared against is a function of that class.
  That $0.55 is a model default rather than a quoted market rate: no open,
  citable price series for bulk industrial glucose was found, and the trade
  sources that carry one are paywalled. Reaching a comparable cost share here
  would require substrate priced near $28/kg, which is a fiction rather than a
  feedstock. The default was kept and the
  modelled process is therefore facility- and downstream-dominated. **The
  consequence is concrete: the yield lever — the one that dominates real COGS — is
  nearly invisible here.** Arguing about industrial economics needs a
  representative process, not this one.

- **Cost-optimal and titer-optimal designs coincide on this simulator**, so the
  practical payoff of optimizing net $/kg cannot be demonstrated with what ships.
  Titer and yield are positively correlated in the simulator, and the yield term is
  too small a share to move the optimum even where they differ. Showing that a cost
  objective picks a *different* design needs a process where pushing titer costs
  yield or rate — a data problem, not a modelling one.

The second point is a limitation of the **demonstration**, not of the decision
behind it: optimizing net cost per kilogram rather than titer rests on the
argument in [Decisions](decisions.md) (`D13`), which does not depend on this
simulator.

### The capital correlation is borrowed from a different cell type

Added 2026-08-17 with the production-scale term
([#143](https://github.com/enginbio/engin-suite/issues/143) piece 1). `ProductionScale`
prices capital with Humbird's piecewise bioreactor correlation and capital charge
factor.[^2021-humbird-scaleup-economics] **That work is about animal cell culture.**

What is being borrowed is the price of a vessel — ASME BPE, 316L stainless,
CIP/SIP, full-vacuum design — which is standard bioprocess hardware rather than
anything specific to animal cells, and that is the argument for using it. It
remains an argument. No source found establishes that the correlation transfers
to microbial fermentation, and this page should not be read as claiming one does.
The same paper's cell-type-specific conclusions are deliberately **not** carried
over.

Two consequences worth stating rather than leaving implicit:

- **Bioreactors only.** Minor process equipment, buildings and utilities are
  outside the term. The capital number is a floor, not an estimate.
- **The correlation is stated over 0.33–200 m³.** Outside that range the code
  extrapolates without warning, because the source gives no basis for choosing a
  warning threshold and inventing one would be the same error the term was built
  to avoid.

[^2021-humbird-scaleup-economics]: Humbird, *Scale-up economics for cultured meat*, Biotechnology and Bioengineering 118(8) (2021). [doi:10.1002/bit.27848](https://doi.org/10.1002/bit.27848). CC BY 4.0.

### Downstream cost does not see what is in the broth

Recovery cost is a function of titer, and since
[#17](https://github.com/enginbio/engin-suite/issues/17) of product
specification. It is **not** a function of broth composition — biomass load,
whether the product is secreted or intracellular, or an impurity burden. None of
those enters the cost path, and
[#15](https://github.com/enginbio/engin-suite/issues/15) tracks the gap.

This is a limitation of the **evidence**, not an oversight. A literature pass on
2026-08-17 looked for something citable and did not find it:

- **Biomass load.** The closest candidate varies biomass density (4.2–50 g/L),
  expression level and production scale together across its
  scenarios,[^2025-fdh-fermentation-tea] so its cost differences cannot be
  attributed to biomass load.
- **Secreted versus intracellular.** The literature is consistent and
  qualitative — secretion "avoids the costly lysis step" — with no costed
  comparison found for a comparable product.
- **An impurity proxy.** Nothing was found to calibrate one against, and the
  bundled simulator surfaces nothing about broth contents to attach it to.

The honest reading is that secreted-versus-intracellular is not a coefficient at
all: it adds or removes a unit operation, so it changes the shape of the model
rather than one of its numbers. A plausible continuous correlation invented here
would be exactly the unevidenced number `CONTRIBUTING` rule 1 rejects, so the
term stays absent and the issue stays open.

[^2025-fdh-fermentation-tea]: *Techno-economic analysis of industrial-scale fermentation for formate dehydrogenase (FDH) production*, Bioresources and Bioprocessing 12 (2025). [doi:10.1186/s40643-025-00985-3](https://doi.org/10.1186/s40643-025-00985-3). CC BY 4.0.

## Reporting a limitation we have missed

<https://github.com/enginbio/engin-suite/issues/new>
