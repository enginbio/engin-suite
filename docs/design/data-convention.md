# Design note: the bioprocess data convention

**Status:** the absence claim behind this component **did not survive review.**
**Last searched:** 2026-08-13 · **Re-check:** 2027-08 · Implements `D11`, `D23`.

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
| `cf_xarray` | Rejected on evaluation: its vocabulary is geoscience-specific and reports `n/a` across bioprocess channels. Cited in the register. |
| `frictionless` | Rejected on evaluation: `field_confidence` is a type-casting tolerance, not semantic confidence, and it maps nothing to a domain vocabulary. Cited in the register. |
| SBML | Wrong layer — kinetic model representation, not experimental data layout. Relevant to the simulator instead. |
| AnnData | Wrong domain, right shape. The pattern worth imitating, not the schema. |

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
