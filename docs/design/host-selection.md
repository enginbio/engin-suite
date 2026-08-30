# Design note: host selection

**Status:** the absence claim **holds**, narrowed.
**Last searched:** 2026-08-13 · **Re-check:** 2027-08 · Implements `D23`, closes #107.

```{warning}
**The shipped capability numbers are illustrative, not sourced.** `engin-host`'s
knowledge base is 54 hand-assigned values carrying no citations, and
`Provenance` defaults to `"illustrative"` in the schema for exactly that reason
([#146](https://github.com/enginbio/engin-suite/issues/146)). The scoring
arithmetic over them is separately marked `bespoke-unjustified`
([#103](https://github.com/enginbio/engin-suite/issues/103)).

This note argues that **no published tool does this**. That is a claim about the
rest of the field, and it is not a claim that these particular scores are right.
Treat a ranking from the bundled KB as a worked example of the interface, not as
advice about a chassis.
```

`engin-host` scores candidate microbial chassis against a production requirement. Its
README claimed this was *"genuine whitespace"* with *"no standard commercial tool"* — an
absence claim, published, and never searched.

This is the search. Unlike [the data convention's](data-convention.md), which the same
procedure demolished on the same day, this one survives — but not in the form it was
stated.

## Why the bar is set here

`D23` holds absence claims to the highest standard in the scheme, because *"nobody has
built this"* is the most self-serving sentence available to a project like this one. The
base rate justifies the caution: **two absence claims were examined on 2026-08-13, and
the other was flatly wrong.** MIFE/MIFD had been published, and this project's own `D11`
already named it.

An unrecorded absence claim is unfalsifiable. This note exists so this one isn't.

## What was searched

Literature on chassis and host selection; PyPI for candidate distributions
(`chassis-selection`, `chassisdb`, `hostpicker`, `chassy` — all 404); and the
decision-support tooling named in current biomanufacturing reviews.

### Near-misses, and why each is not this

| Candidate | Why it isn't the tool |
|---|---|
| [Chan et al. 2025](https://doi.org/10.1021/acssynbio.5c00308), *Rethinking Microbial Chassis as a Design Variable* | Argues exactly that chassis should be a design variable rather than a default. **Motivates the tool; is not one.** |
| Broad-host-range expression platforms for chassis screening | **Wet-lab.** Answers the same question empirically — build the constructs, measure across hosts — rather than computationally. A genuine alternative, and a different kind of thing. |
| KEGG · MetaCyc · BRENDA | Hold the capability data. Do not score it against a production requirement. |
| Techno-economic and biositing tools | Address feedstock, siting and process economics — not host choice. |

## What changed in the claim

**The README said more than the search can support.** "No standard *commercial* tool" is
a statement about a vendor market, and a literature-and-package search cannot settle
that: vendor capability is frequently unpublished, and absence of evidence in the
literature is weak evidence about what sits inside a proprietary platform.

So the claim is narrowed to what is actually held: **no published tool scores candidate
chassis against a production requirement with calibrated uncertainty.** That is
falsifiable, it is what the search supports, and it is the claim the package can defend.

The broad-host-range screening platforms are worth naming rather than dismissing. If the
practical answer to "which chassis" is *build it in six and measure*, then a scoring tool
competes with an experiment, not with other software — and it has to be honest about
which is more informative. It usually isn't the model.

## Related

- `D9` — compose, don't reimplement · `D23` — the evidence register
- [#103](https://github.com/enginbio/engin-suite/issues/103) — the scoring arithmetic
  itself is `bespoke-unjustified` pending an MCDA-library evaluation. Separate question:
  this note is about whether the *capability* exists elsewhere, that one is about whether
  the *implementation* should be ours.
