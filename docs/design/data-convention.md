# Design note: the bioprocess data convention

**Status:** the absence claim behind this component **did not survive review.**
**Last searched:** 2026-08-14 · **Re-check:** 2027-02 · Implements `D11`, `D23`.

This note exists because `D23` holds absence claims to the highest bar in the scheme. A
package saying *"no community standard exists"* is making a claim about the field, not
about itself — and "nobody has built this" is the most self-serving sentence available
to a project like this one.

So it gets checked. This one failed.

## What was claimed

The component register recorded the data convention as `standard_impl: none exists`.
The reasoning in `D11` was sound as far as it went: don't invent a bespoke container,
use xarray and pandas as they are, and publish a thin versioned convention over them.

## What the search found

**A standard exists**, is peer-reviewed, and is closer to this project's needs than
anything the convention was designed against.

**MIFE and MIFD** — *Minimum information for fermentation experiments and devices*
(Georgakilas et al., *GigaScience* 15, giag038, 2026;
[doi:10.1093/gigascience/giag038](https://doi.org/10.1093/gigascience/giag038)) — come
out of the EU BioIndustry4.0 work via UNLOCK/IBISBA. They are ISA-derived, carry a
LinkML schema, are deposited in BioPortal, and integrate with FAIR Data Station and
FAIRDOM-SEEK.

**Every knob in this project's simulator maps to an existing MIFE slot** — feed rate,
feed start, feed concentration, induction timing, initial substrate — and, less
obviously, so do the downstream ones `D13`'s cost model needs (harvest flow rate and
weight, `purification_method`).

### Near-misses, and why each was rejected

| Candidate | Verdict |
|---|---|
| **MIFE / MIFD** | **Not a near-miss. The standard.** Adopt. |
| **PREFER** | **Monitor, do not adopt yet** — and report the MIFE relationship upstream. See below. |
| `cf_xarray` | Rejected on evaluation: its vocabulary is geoscience-specific and reports `n/a` across bioprocess channels. Cited in the register. |
| `frictionless` | Rejected on evaluation: `field_confidence` is a type-casting tolerance, not semantic confidence, and it maps nothing to a domain vocabulary. Cited in the register. |
| SBML | Wrong layer — kinetic model representation, not experimental data layout. Relevant to the simulator instead. |
| AnnData | Wrong domain, right shape. The pattern worth imitating, not the schema. |
| `detl` | **Parser-side, and it exists.** DASGIP/DASware only, no vocabulary layer. Not composable: **AGPL-3.0**. See below. |
| `bletl` | Parser-side. BioLector I/Pro only, no vocabulary layer, peer-reviewed. Also **AGPL-3.0**. |
| `allotropy` | Closest existing implementation of the *architecture*, MIT, ~60 parsers — and **zero bioreactor parsers**. Rejected on scope, kept as precedent. |

### The near-miss table had no parser rows, on a component whose contribution is a parser

Added 2026-08-14 (#116). `D11` calls the ingest layer *"the real contribution"*, and every row
above it is schema-side — MIFE, `cf_xarray`, `frictionless`, SBML, AnnData. **The parser half was
never searched.** That is a defect in the table rather than in the claim, and the distinction
matters:

**The absence claim survives, narrowed.** `D11`'s claim has two conjuncts — *arbitrary vendor
bioreactor exports*, mapped onto *a domain vocabulary* — and no candidate found meets both.
`detl` and `bletl` are bioreactor parsers with no vocabulary layer and one vendor each;
`allotropy` has the vocabulary layer and no bioreactor parsers. The defensible sentence is
therefore "no open-source layer maps *arbitrary* bioreactor exports onto a *domain vocabulary*",
and that is what the register now says.

**What the search actually found is more interesting than an absence.** Two single-vendor
parsers out of Forschungszentrum Jülich, 8 stars each, one peer-reviewed, both in maintenance
mode. The niche is not contested — it is **abandoned in place**. People did build exactly this,
for one vendor each, and then stopped, because nobody funds the cross-vendor mapper. That is a
better argument for `D11` than "nobody thought of it", and it is true.

**`D9` does not require composing with them.** Both are AGPL-3.0 against this project's
Apache-2.0 (`D3`), so composition is not available on any terms this project can accept. Saying
so explicitly is better than leaving `D9` ambiguous here. The full licence boundary — including
why observing a header spelling is a fact rather than expression, and why the fixtures and the
parser must not be vendored — is in
[the ingest measurement](../methods/vendor-export-ingest.md).

**And detl's fixtures cost this project a published claim.** `loaders.py` explained its lack of
vendor profiles by saying they *"land when someone has the actual files"* — while six real
DASGIP exports had been sitting in detl's test directory since 2022. Running the loader against
one is [the first measurement it has had](../methods/vendor-export-ingest.md), and it mapped 1
of 40 columns with that one wrong.

### PREFER, and what the re-check date missed

**PREFER** — *An Ontology for the PREcision FERmentation Community*
([arXiv 2602.16755](https://doi.org/10.48550/arXiv.2602.16755), Amigó et al., DTU Biosustain
and UCSD, submitted 2026-02-18) — is a BFO-aligned ontology covering the whole precision
fermentation process, reusing ChEBI, PATO, IAO, BAO and RO. Its author list includes Lars K.
Nielsen and Bernhard Ø. Palsson.

It was six months old when the search above ran, and the search missed it. That is the finding
worth recording first, ahead of any verdict about the ontology itself.

**The verdict is monitor, on two grounds and one caution.**

It is a *different layer*, not a competitor. MIFE/MIFD is a minimum-information checklist with
a LinkML schema — what fields must accompany an experiment. PREFER is a semantic ontology —
what the terms mean and how they relate. A project can hold both, and they are more plausibly
complementary than rival. Nothing here displaces the decision to adopt MIFE.

And there is no adoption evidence yet: a preprint, a repository with 4 stars and 34 open
issues. The base rate for "prestigious authors publish a vocabulary" → "field adopts the
vocabulary" is poor, and adopting on the strength of an author list would be the same class of
reasoning error this note exists to record.

The caution runs the other way. `D11` chose MIFE over inventing a format precisely to avoid
*"two half-adopted standards and an unmaintained converter"* — and **PREFER does not cite MIFE
or MIFD.** That was checked rather than assumed: the full text of the v1 PDF returns zero hits
for MIFE, MIFD, "Minimum Information", MIAPPE and MIBBI, in body and references alike. So the
fragmentation `D11` named is visible in the field right now, one layer up.

**What follows is an upstream report, not an adoption.** This note already commits to the
posture — *being the reference implementation means contributing findings back* — and now has a
second occasion to act on it, alongside the MIFE channel gaps below. Engin checked all 17 of
its channels against the MIFE slot index on 2026-08-13, which makes it one of the few parties
holding information both efforts would want.

```{note}
**Open question for the founder, deliberately not resolved here.** `D23` sets the re-check
cadence for absence claims at annual, and `DECISIONS.md` is canonical, so this note does not
change it. But annual looks like the wrong clock for a *standards* claim specifically: a
vocabulary layer consolidates once, and eighteen months of latency is enough to arrive after
someone else is its reference implementation. This note's own re-check is pulled in to
**2027-02** on that reasoning. Whether the rule generalises is `D23`'s to decide.
```

## The uncomfortable part

**This project's own canonical decision record already knew.** The vault's `D11` entry
names MIFE and MIFD, verifies them, and resolves to *adopt rather than compete* — on
the reasoning that where a standard exists the durable position is the reference
implementation, since a competing format mostly yields two half-adopted standards and
an unmaintained converter.

Meanwhile the public register went on saying the slot was empty.

That is the third instance in a week of a correction living in one canonical document
and not reaching another — after a withdrawn `D13` justification that three published
documents kept asserting, and a cost figure the repo dropped that the vault kept for two
days. **The failure is never the original error. It is that fixing one document is taken
for fixing the claim.**

## Where the boundary actually falls

**Positioned in code as of 2026-08-13**: `engin_core.convention.MIFE_SLOTS` maps every
registered channel to its MIFE slot or to a documented gap, and tests fail if a channel
is added without a verdict. That is what moved this row off `bespoke-unjustified` — an
unevidenced "we're compatible" is exactly what the register exists to catch.

Of 17 channels, **9 map to MIFE and 8 are gaps**, and the split is not arbitrary.

| | |
|---|---|
| **MIFE owns** the controlled conditions and provenance | `feed_flow_rate`, `agitation_rate`, `aeration_rate`, `temperature`, `pH`, `pO2`, `volume`, `concentration` — plus the downstream slots `D13` needs |
| **This convention adds** measured and derived time series | `our`, `cer`, `rq`, `kla`, `mu`, `biomass`, `offgas_o2`, `offgas_co2` |

Checked against the published slot index on 2026-08-13: MIFE defines no slot for the
metabolic rates, for kLa, for specific growth rate, or for biomass during cultivation —
`sample_dry_mass` is a *sample* property, not a cultivation channel. And
`gas_input_composition` describes the gas going **in**, so exhaust composition has no
home either.

**Those are precisely the channels a real industrial export forced into this registry and
a simulator never needed.** The erythromycin dataset arrived with OUR, CER, RQ and kLa
because a working plant measures its exhaust gas; Engin's own simulator has none, which
is why the vocabulary was missing until real data landed. That the standard has the same
shape of gap is the more interesting observation, and it is worth reporting upstream —
being the reference implementation means contributing findings back, not just consuming
the schema.

## Still outstanding

Generating the data model, JSON Schema and validators from the published LinkML spec.
`D11`'s reasoning points there — it converts the headline task from design to code
generation and inherits future revisions free. **Note one thing found while checking:**
the schema documentation site does not link a downloadable LinkML or JSON Schema
artifact from its home view, so "generate from the spec" needs the artifact located
before it can be planned rather than assumed.

Timing favours it. The standard is months post-publication, so real adoption is near
zero: a well-designed, institutionally backed standard with no tooling yet is the best
position to arrive in. Too early is guesswork; too late and someone else is its
reference implementation.

## Related

- `D11` — the convention decision · `D9` — compose, don't reimplement
- [References](../references.md) — the register rows behind every claim here
