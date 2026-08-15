# The ingest layer against a real vendor export

Every claim about the ingest layer before this one was measured against files this
project wrote. This page is the first measurement against a **real DASGIP/DASware
export** — Eppendorf's bioreactor line, one of the four vendors [#19][issue-19] names.

The result is bad, and specific. It is published because a loader that fails on the
first real file it meets is worth knowing about before someone else finds out.

```{note}
**The numbers on this page are not computed when the docs build.** Producing them
means downloading a file from a third party, and a documentation build that depends
on someone else's server being up is a build that breaks for unrelated reasons.

They come from a committed script instead, and you can run it yourself:

    python benchmarks/dasware_ingest.py

It fetches the export at run time and caches it outside the repository. Nothing is
redistributed with Engin.
```

## The premise that was wrong

`loaders.py` shipped with an explanation for why it has no vendor profiles: the header
spellings, delimiters and encodings *"are exactly the details that cannot be reasoned
out"*, so *"vendor profiles land when someone has the actual files."*

The first half is right, and this page is evidence for it. **The second half was false
when it was written.** [`JuBiotech/detl`][detl] — a DASware parser out of
Forschungszentrum Jülich — has committed six real DASGIP exports as test fixtures since
2022, ranging from 1.2 MB to 76 MB, including separate DO and pH calibration exports.
The files were public the whole time.

## What was measured

The smallest of detl's six fixtures, `v4_20180726.Control.csv` — a real *B. subtilis*
fermentation, four vessels, 22.8 hours, logged once a minute.

Two questions, in order, because the second is meaningless without the first.

### 1. Can the file be read at all?

`infer_columns` takes a `DataFrame`, so everything upstream of that is assumed. Here the
assumption fails three separate times:

| Attempt | Result |
|---|---|
| `read_csv(path)` | `UnicodeDecodeError` — the file is **latin-1**; `°C` and `µS` are the bytes that break it |
| `read_csv(path, sep=";")` | Same — the delimiter was never the first problem |
| `read_csv(path, sep=";", encoding="latin-1")` | `ParserError: Expected 7 fields in line 28, saw 33` |

The third failure is the structural one. **This is not a table.** It is an INI-style
container: **47 section headers**, of which the time series occupy four —
`[TrackData1]` through `[TrackData4]`, one per vessel — alongside instrument metadata,
a calibration block, an event log and a trailing configuration document.

**So the run axis is the *section*, not a column.** A four-vessel DASGIP run is four
runs in one file, and the convention's `(run, time)` layout has nowhere to get a run
identifier from. `infer_columns` reports `run_column: None` and a finding saying rows
cannot be tied to the runs they came from — which is correct, and is as far as it can get.

### 2. Given a DataFrame, what does the loader make of the columns?

Extracting `[TrackData1]` by hand gives 1371 rows × 41 columns. Handing that to
`infer_columns`:

| | |
|---|---|
| Columns mapped | **1 of 40** |
| Of which correct | **0** |
| Run column found | no |
| Elapsed-time axis found | no |

The single mapped column is `Unit 1.XCO2 1.Out [%]` → `offgas_co2`, at 0.65, on the
evidence *"header contains an alias for `offgas_co2`"*.

## The one hit is a false positive, and why that is the interesting part

This file marks every channel with a **role suffix**, and states it in every header:

| Role | Meaning | Channels carrying it here |
|---|---|---|
| `.PV` | process value — a measurement | pH, DO, T, F, FA–FD, V, VA–VD, N, Level, Torque |
| `.SP` | setpoint | pH, DO, T, FA–FD |
| `.Out` | controller output | pH, DO, T, F, **XO2**, **XCO2** |

`XO2` and `XCO2` carry **only** `.Out`. There is no `.PV` for either. On this rig they
are the gas-mixing station's commanded **inlet** composition — `XO2 1.Out` sits at a
median of 19.63% and a maximum of 20.71%, blending down from air — and the convention
defines `offgas_co2` as measured **exhaust** composition.
<!-- ref: 2026-jubiotech-detl -->  <!-- both figures are read off the fixture by
     benchmarks/dasware_ingest.py; they describe that file, not the field -->

Settling the vendor semantics beyond doubt needs Eppendorf's documentation, and this
page does not claim to have done that. **But the defect does not depend on it.** The
loader arrived at its answer by substring-matching `co2`, and its evidence sentence —
the sentence a reviewer is meant to read before accepting a mapping — carries no
information about whether the column is a measurement, a setpoint or an actuator
command. The file states that difference in every header. The loader has no concept of
it.

Meanwhile the quantities that *are* derived from exhaust gas here — `OTR`, `CTR` and
`RQ` — went unmapped, `RQ` included, though `rq` is a registered channel.

## A 24× error waiting to happen

The file carries two time columns. The loader picked the wrong one, and the right one is
in units it does not know.

| Column | What it is | Loader's verdict |
|---|---|---|
| `Timestamp` | wall-clock datetime | **chosen** as the time column |
| `Duration` | elapsed time, **in days** | unmapped |

Measured over this run: 22.83 wall-clock hours against a `Duration` span of 0.9521 — a
ratio of **23.98**. `Duration` carries no unit in its header, and `day` is not in the
loader's unit vocabulary at all.

`Duration` is the elapsed axis the convention wants. Whoever maps it by hand will get
hours, and every run will be twenty-four times too short. Nothing in the current
report would warn them.

## `register_alias()` does not reach this file

The module docstring offers `register_alias()` as the reason vendor profiles are cheap:
*"a real file can teach the loader without a code change."* Measured against this file,
it cannot.

| What was tried | Result |
|---|---|
| The obvious spellings — `pH1`, `DO1`, `T1`, `N1`, `F1`, `V1`, `RQ1` | **no change.** They never fire |
| The full dotted spelling — `pH1.PV` | maps, on **vessel 1 only** |
| The same alias against `[TrackData2]` | **does not carry.** Vessel 2 spells it `Unit 2.pH2.PV` |
| Aliases needed to cover this one four-vessel file | **156** |

The obvious spellings fail for a reason worth stating: the matcher compares against the
whole header, so `Unit 1.pH1.PV` folds to `unit1ph1pv`, and containment requires an alias
of at least four characters — `ph1` and `rq1` are below the floor. That floor is not a
bug. It was added deliberately after short aliases produced four confident false mappings
on the erythromycin dataset. It is doing its job here and the file is still unreadable.

**This is the finding that matters.** A DASGIP header glues three orthogonal facts into
one dotted string — *vessel*, *channel*, *role* — and the loader treats headers as flat
names. **A vendor profile is not a row in `ALIASES`. It is a header grammar.** The
documented escape hatch is real for a spreadsheet with an unusual spelling of `OD600`,
and it does not reach a vendor's instrument export.

## What this does and does not license

**It does not calibrate the confidence score.** Six files from one vendor is not a
labelled corpus, and [Limitations](../limitations.md) still says the score is an ordinal
heuristic. Reading this page as "the loader has now been measured, so the number means
something" would be the exact over-read that page exists to prevent. This is a first
measurement, on one file, from one vendor.

**It does replace a guess with a number.** The honest description of the ingest layer
today is: it handles tabular exports whose headers name their channels, and it has been
measured against one real instrument export, where it mapped one column of forty and got
that one wrong.

## Licence boundary — read before vendoring anything

**`detl` and `bletl` are AGPL-3.0. Engin is Apache-2.0 (`D3`).**

Nothing here copies detl's code or redistributes its fixtures. The file is fetched at run
time, cached outside the repository, and never committed — the same rule `D12` applies to
data. What this measurement takes from the file is *facts about how a vendor spells a
header*, and facts are not copyrightable expression.

That reasoning is a maintainer's, not a lawyer's, and a more cautious position — declining
to read an AGPL repository's fixtures at all before writing a parser for the same format —
is defensible. **What is not defensible is vendoring the fixtures or lifting the parser.**
If a well-meaning pull request proposes either, this section is the answer.

`detl` also carries a CLA, so contributing observed spellings back is a deliberate choice
with a cost attached, not a courtesy.

## Related

- [Data formats guide](../guides/data-formats.md) — what the loader does handle
- [The data convention](../design/data-convention.md) — the near-miss table, including the
  parser-side candidates this measurement added
- [Limitations](../limitations.md) — why the confidence score is still uncalibrated
- [#19][issue-19] — vendor profiles; its stated blocker was this page's starting point

[detl]: https://github.com/JuBiotech/detl
[issue-19]: https://github.com/enginbio/engin-suite/issues/19
