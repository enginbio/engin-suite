# 0009 — A vendor profile is a convention gap, not a parser abstraction

**Status:** Accepted (2026-08-16)

## Context

`#19` asks for vendor profiles for Sartorius, Eppendorf, Applikon and Benchling exports. The
obvious reading is "write four parsers", and the obvious blocker was access to real files. Both
turned out to be wrong.

### What the first real file did

`JuBiotech/detl` has committed six real DASGIP/DASware exports as test fixtures since
2022.[^2026-jubiotech-detl] Run against one of them, `engin_core.loaders` mapped **1 of 40
columns, and that one is a false positive**: `XCO2 1.Out` is a controller output and was matched
to `offgas_co2`, the convention's *measured exhaust* channel, on a substring hit for "co2".
<!-- not-a-claim: measured against this repository's own loader; benchmarks/dasware_ingest.py reproduces it -->

Before that it failed three times over — the file is latin-1, semicolon-delimited, and not a
table at all but INI-style sections whose `[TrackData*]` blocks are the runs.

### Why more aliases cannot fix it

A DASGIP header glues **three orthogonal facts into one dotted string**:

```
Unit 1.pH1.PV     →   vessel 1  ·  channel pH  ·  role = measured value
```

`ALIASES` matches substrings against a folded whole header, so the obvious spellings (`pH1`,
`RQ1`) fall below `MIN_CONTAINED_ALIAS` and never fire; the full dotted spelling `pH1.PV` maps
vessel 1 and does not carry to vessel 2, which spells it `Unit 2.pH2.PV`. Covering that one
four-vessel file takes **156 aliases**.
<!-- not-a-claim: counted against this repository's own alias table -->

That four-character floor is not a bug. It was added after short aliases produced four confident
false mappings on the erythromycin data. It is doing its job here and the file is still
unreadable.

### What the landscape shows

Three findings, checked rather than recalled, and each one narrows the design space.

**1. Nobody has a header-grammar DSL. The serious efforts hand-write parsers.**
Benchling's `allotropy` is the most credible attempt in this space — MIT, Allotrope-backed, and
the reference implementation for converting instrument output to the Allotrope Simple
Model.[^2026-benchling-allotropy] Its architecture is **one bespoke Python package per
instrument** (`{vendor}_parser.py`, `{vendor}_structure.py`, `constants.py`), not a declarative
grammar, across 54 parser packages. The project's published cost is 20–30 hours for a simple
instrument and 40–60 for a complex one. `detl` and `bletl` are likewise
hand-written.[^2022-osthege-bletl]

So a profile-as-grammar would be inventing an abstraction the field has not found necessary,
which `D9` says not to do.

**2. There is no target model to adopt: ASM has no bioreactor schema.**
The shipped ASM schema families cover the analyzers that sit *around* a bioreactor —
`metabolite-analyzer`, `solution-analyzer`, `bga`, `ph`, `cell-counting`, `plate-reader` — and
include **nothing for a cultivation time series**. The two nearest parsers, NovaBio Flex2 and
Roche Cedex BioHT, are offline sample analyzers rather than bioreactor
controllers.[^2026-benchling-allotropy]

**3. MIFE/MIFD cannot express it either, for two separate reasons.**
The fermentation-specific standard models **experiment-level metadata only** — no channels, no
timestamped sequences — and its parameter fields are a flat list that does not distinguish a
measured value from a setpoint.[^2026-georgakilas-mife-mifd] This extends `D11`'s finding that
MIFE is a reporting checklist rather than a data structure: it is also silent on the exact
distinction this problem turns on.

### The reframing those three produce

Line the DASGIP header's three axes up against the convention Engin already publishes:

| axis | in the convention today? |
|---|---|
| vessel | **yes** — the `run` dimension |
| channel | **yes** — `engin_core.convention.CHANNELS` |
| role — measured value / setpoint / controller output | **no** |

Two of three already exist. The missing one is not a vendor quirk: **process value, setpoint and
controller output are standard process-control vocabulary**, used across ISA-88/ISA-95, OPC-UA,
and every distributed control system and historian. DASGIP is spelling a universal concept, and
Engin's convention has no word for it.

So `#19` is a **convention gap wearing a vendor-parser costume**, and that is what makes the
false-positive class structural rather than a review failure. With no role concept, mapping an
actuator command onto a measured channel is a mapping the type system permits and the evidence
string cannot describe.

## Decision

**Two parts, and the second is deliberately incomplete.**

1. **`role` becomes a first-class concept in the data convention** — `D11` territory, "a thin
   versioned convention over xarray and pandas" — using process-control vocabulary rather than
   any vendor's spelling. A column that is a setpoint or a controller output is representable
   as such, and mapping one onto a measured channel becomes impossible to express rather than
   possible-but-discouraged.

2. **Vendor readers are ordinary code, not instances of a profile grammar.** A DASGIP reader is
   a function that yields `(run, channel, role, values)`; its sectioned-INI parsing, latin-1
   decoding and semicolon delimiter are that reader's business and are not abstracted. This is
   the shape the field converged on independently three times.

### The encoding, and the two alternatives rejected

`role` is a **per-variable attribute** — `ds["x"].attrs["role"]` — defaulting to `measured`,
validated exactly the way `units` already is. Convention version **0.2**.

**Rejected: a `role` coordinate or dimension.** It reads as the tidy answer and it is not.
Most channels have no setpoint and no controller output — `titer`, `biomass`, `our` never do —
so a role dimension is mostly empty, and every existing variable's shape changes to carry it.
That breaks consumers to represent absence.

**Rejected: a suffix convention on the variable name** (`ph`, `ph.sp`, `ph.out`). It matches how
vendors spell it, which is its only real advantage. It makes meaning depend on parsing a string,
and the convention already had a place for per-variable metadata that does not.

The attribute wins on three counts that the others cannot match: it is **sparse by construction**
(a role exists only where it was recorded), it **changes no array shape**, and it makes
0.1 data valid 0.2 data — absent `role` means `measured`, which is what every dataset written
before roles existed already was. **Variable names stay free**; when two roles of one channel
coexist they must differ, but the name is a label and `role` is the meaning.

The unsafe direction is the other one — an unlabelled actuator column counting as a measurement —
and that is what the category-error rule below is for.

## Consequences

- The false-positive class that `#19` surfaced is now **checkable rather than reviewable**. A
  registered channel name at a non-measured role is an error with its own code
  (`channel-name-at-non-measured-role`), so the `XCO2 1.Out` mapping fails validation instead of
  passing silently.
- **No migration.** 0.1 data is valid 0.2 data; what 0.2 rejects is a claim 0.1 had no way to
  make.
- An unregistered name may hold any role, which is the point: a column that genuinely *is* an
  actuator signal becomes representable. Only claiming a *channel's* name for one is refused.
- Vendor coverage stays expensive — the field's own estimate is tens of hours per instrument, and
  nothing here changes that. What changes is that the cost buys a reader rather than 156 alias
  rows.
- **A strategic consequence worth stating.** The leading standard in this space has a
  bioreactor-shaped hole: ASM models the analyzers and not the cultivation, and MIFE/MIFD models
  the experiment and not the time series. `D11` says standard-hood, if it comes, comes from the
  convention being the obvious way to do this. That hole is where it would come from.
- Nothing here licenses vendoring `detl`'s fixtures or lifting its parser. It is AGPL-3.0 against
  this project's Apache-2.0 (`D3`), and it carries a CLA, so contributing spellings upstream is a
  costed choice rather than a courtesy. Observed header spellings are facts rather than
  copyrightable expression.

## Related

- [`#19`](https://github.com/enginbio/engin-suite/issues/19) — the issue this records a decision for
- [`#116`](https://github.com/enginbio/engin-suite/issues/116) — the measurement against a real DASGIP export
- [Vendor-export ingest](../methods/vendor-export-ingest.md) — the full report
- [Data convention](../design/data-convention.md) — what `role` would be added to
- [ADR 0002](0002-light-default-dependency-path.md) — the light default path a reader must not break

[^2026-jubiotech-detl]: See the [evidence register](../references.md).
[^2026-benchling-allotropy]: See the [evidence register](../references.md).
[^2022-osthege-bletl]: See the [evidence register](../references.md).
[^2026-georgakilas-mife-mifd]: See the [evidence register](../references.md).
