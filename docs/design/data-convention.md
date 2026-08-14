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

## Where this leaves the component

Reclassified `bespoke-unjustified`. Not because the convention is wrong — it may well
survive as the array-layout complement to a metadata standard that does not specify
in-memory layout — but because that positioning currently exists in a vault note rather
than in code, and an unevidenced "we're compatible" is exactly what this register is for
catching.

**What would settle it:** generate the data model, JSON Schema and validators from the
published LinkML spec, and state precisely which MIFE terms the convention's channel
registry corresponds to. `D11`'s own reasoning already points there — it converts the
headline task from design to code generation, and inherits future revisions for free.

Timing favours it. The standard is months post-publication, so real adoption is near
zero: a well-designed, institutionally backed standard with no tooling yet is the best
position to arrive in. Too early is guesswork; too late and someone else is its
reference implementation.

## Related

- `D11` — the convention decision · `D9` — compose, don't reimplement
- [References](../references.md) — the register rows behind every claim here
