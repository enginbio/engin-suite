"""The ingest layer against a real vendor export, measured rather than assumed.

``loaders.py`` shipped with an explanation for why it has no vendor profiles:
the header spellings, delimiters and encodings *"cannot be reasoned out"*, so
*"vendor profiles land when someone has the actual files."* That premise was
false when it was written. `JuBiotech/detl` has committed six real DASGIP/DASware
exports as test fixtures since 2022, and DASGIP is Eppendorf's line -- one of the
four vendors #19 names.

This script is the first measurement of :func:`engin_core.loaders.infer_columns`
against a real vendor export by anyone.

**Run it yourself:**

    python benchmarks/dasware_ingest.py

## Why this does not go through ``engin_core.datasets``

Three reasons, and the licence one is the reason to read before vendoring.

**detl is AGPL-3.0 and Engin is Apache-2.0 (`D3`).** Nothing here copies detl's
code or redistributes its fixtures: the file is fetched at run time, cached
outside the tree, and never committed -- the same rule `D12` applies to data. What
this script takes from the file is *facts about how Eppendorf spells a header*,
and facts carry no copyright. That reasoning is not a lawyer's, and a cautious
maintainer could reasonably decline to read an AGPL repository's fixtures at all
before writing a parser for the same format. **What is not defensible is vendoring
the fixtures or lifting detl's parser.** If a well-meaning PR proposes either,
this paragraph is the answer.

**It is a test fixture, not a dataset.** The registry describes things you would
train or validate on, with a licence and a checksum verified against a
publisher's. A vendor's file-format sample is neither.

**And the point is the format, not the numbers.** Nothing downstream consumes
what this reads.

## What it measures

Two things, in order, because the second is meaningless without the first:

1. **Can the file be read at all?** ``infer_columns`` takes a ``DataFrame``, so
   everything upstream of that is assumed. On this file the assumption fails.
2. **Given a DataFrame, what does the loader make of the columns?** detl's own
   parser is the label for what a correct answer looks like.

The result is not a calibration. Six files from one vendor is a first
measurement, and ``docs/limitations.md`` should keep saying the confidence score
is an ordinal heuristic.
"""

from __future__ import annotations

import io
import os
import re
import urllib.request
from pathlib import Path

import pandas as pd

from engin_core.loaders import infer_columns, register_alias

FIXTURE_URL = (
    "https://raw.githubusercontent.com/JuBiotech/detl/main/tests/testfiles/v4_20180726.Control.csv"
)
"""A real DASGIP/DASware v4 Control export, ~1.2 MB.

The smallest of detl's six on purpose -- the v5 long export is 76 MB and shows
nothing this one does not.
"""

CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "engin" / "dasware"
"""Outside the repository. Nothing fetched here is ever committed."""

ENCODING = "latin-1"
"""Not a guess: UTF-8 raises on this file. See :func:`step_1_can_pandas_read_it`."""

SECTION = re.compile(r'^\s*"?\[(?P<name>[^\]]+)\]"?\s*$')


def fetch_fixture() -> Path:
    """Download the export if it is not already cached. Never committed."""
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / "v4_20180726.Control.csv"
    if not path.exists():
        print(f"fetching {FIXTURE_URL}")
        urllib.request.urlretrieve(FIXTURE_URL, path)  # noqa: S310 - pinned https URL
    return path


def sections(lines: list[str]) -> tuple[dict[str, tuple[int, int]], int]:
    """``({section name: (body start, body end)}, header count)``.

    The count is returned separately because names repeat -- ``[Unit]`` and
    ``[Requirements]`` appear once per setup inside the trailing ``[Fb-Pro]``
    configuration block -- so ``len()`` of the mapping understates the file.
    The ``[TrackData*]`` names this script reads are unique.
    """
    starts = [(m.group("name"), i) for i, ln in enumerate(lines) if (m := SECTION.match(ln))]
    out: dict[str, tuple[int, int]] = {}
    for pos, (name, i) in enumerate(starts):
        end = starts[pos + 1][1] if pos + 1 < len(starts) else len(lines)
        out[name] = (i + 1, end)
    return out, len(starts)


def read_block(lines: list[str], span: tuple[int, int]) -> pd.DataFrame:
    """One ``[TrackData*]`` section as a frame. The header row is the section's first."""
    start, end = span
    return pd.read_csv(io.StringIO("\n".join(lines[start:end]).strip()), sep=";", quotechar='"')


def step_1_can_pandas_read_it(path: Path) -> None:
    print("=" * 76)
    print("1. Can the file be read at all?")
    print("=" * 76)
    for kwargs in ({}, {"sep": ";"}, {"sep": ";", "encoding": ENCODING}):
        label = ", ".join(f"{k}={v!r}" for k, v in kwargs.items()) or "defaults"
        try:
            frame = pd.read_csv(path, **kwargs)
        except Exception as exc:  # noqa: BLE001 - reporting, not handling
            print(f"   read_csv({label}) -> {type(exc).__name__}: {str(exc)[:88]}")
        else:
            print(f"   read_csv({label}) -> {frame.shape}")
    print()
    print("   Three separate obstacles, none of which a caller can guess:")
    print("   * UTF-8 raises -- the file is latin-1, and degC and microsiemens are")
    print("     the bytes that break it")
    print("   * the delimiter is ';'")
    print("   * it is not a table. It is an INI-style container of sections.")


def step_2_container_shape(found: dict[str, tuple[int, int]], headers: int) -> list[str]:
    print()
    print("=" * 76)
    print("2. What shape is it?")
    print("=" * 76)
    tracks = [n for n in found if n.startswith("TrackData") and n != "TrackData"]
    print(f"   {headers} section headers ({len(found)} distinct names)")
    print(f"   {len(tracks)} per-vessel time-series blocks: {tracks}")
    print()
    print("   The run axis is the *section*, not a column. A 4-vessel DASGIP run")
    print("   produces four blocks in one file, and the convention's (run, time)")
    print("   layout has nowhere to get the run identifier from.")
    return tracks


def step_3_infer(frame: pd.DataFrame) -> None:
    print()
    print("=" * 76)
    print("3. Given a DataFrame, what does infer_columns make of it?")
    print("=" * 76)
    report = infer_columns(frame)
    print(f"   orientation  : {report.orientation}")
    print(f"   run_column   : {report.run_column!r}")
    print(f"   time_column  : {report.time_column!r}")
    print(f"   mapped       : {len(report.mapped)} / {len(report.guesses)}")
    print(f"   unmapped     : {len(report.unmapped)}")
    print()
    for guess in report.mapped:
        print(f"   -> {guess.confidence:.2f}  {guess.source!r} -> {guess.channel}")
        print(f"      evidence: {guess.evidence}")
    print()
    print("   Every other column -- pH, DO, temperature, agitation, gas flow, volume,")
    print("   OTR, CTR, RQ, four feed rates and four feed totals -- is unmapped.")


def step_4_the_one_hit_is_wrong(frame: pd.DataFrame) -> None:
    print()
    print("=" * 76)
    print("4. The one mapped column, examined")
    print("=" * 76)
    roles: dict[str, set[str]] = {}
    for column in frame.columns:
        # `Unit 1.XCO2 1.Out [%]` -> base `XCO2 1` -> `XCO2`: the trailing number
        # is the vessel, repeated inside the channel name.
        if m := re.match(r"Unit \d+\.(.+?)\.(PV|SP|Out)\b", column):
            roles.setdefault(re.sub(r"\s*\d+$", "", m.group(1)), set()).add(m.group(2))
    print("   The file marks every channel with a role suffix:")
    for base, seen in sorted(roles.items()):
        print(f"      {base:8} {sorted(seen)}")
    print()
    print("   PV = process value (a measurement).  SP = setpoint.  Out = controller")
    print("   output. pH, DO and T carry all three. XO2 and XCO2 carry ONLY .Out --")
    print("   there is no .PV for either, because on this rig they are the gas-mixing")
    print("   station's commanded inlet composition, not an exhaust measurement.")
    print()
    for column in ("Unit 1.XO2 1.Out [%]", "Unit 1.XCO2 1.Out [%]"):
        if column in frame:
            series = frame[column]
            print(f"      {column:26} median {series.median():6.2f}  max {series.max():6.2f}")
    print()
    print("   So `offgas_co2` -- which the convention defines as measured exhaust")
    print("   composition -- was matched to a controller output, at 0.65, on the")
    print("   evidence 'header contains an alias'. That evidence is a substring hit")
    print("   on 'co2'. It cannot distinguish a measurement from an actuator command,")
    print("   and the file states the difference in every header.")
    print()
    print("   Net: 1 of 40 columns mapped, and the 1 is a false positive.")


def step_5_the_time_axis(frame: pd.DataFrame) -> None:
    print()
    print("=" * 76)
    print("5. The time axis, and a 24x error waiting to happen")
    print("=" * 76)
    stamps = pd.to_datetime(frame["Timestamp"])
    wall_hours = (stamps.max() - stamps.min()).total_seconds() / 3600
    duration = frame["Duration"].max()
    print(f"   wall-clock span : {wall_hours:.2f} h")
    print(f"   Duration span   : {duration:.4f}")
    print(f"   ratio           : {wall_hours / duration:.2f}")
    print()
    print("   `Duration` is in DAYS. It carries no unit in its header, and `day` is")
    print("   not in the loader's unit vocabulary at all.")
    print()
    print("   The loader picked `Timestamp` -- wall-clock -- as the time column,")
    print("   because it is a TIME_ALIASES hit and comes first. `Duration`, the")
    print("   elapsed axis the convention actually wants, was reported unmapped.")
    print("   Whoever fixes that by hand will map it to `time` and inherit hours.")


def step_6_can_register_alias_fix_it(lines: list[str], found: dict[str, tuple[int, int]]) -> None:
    print()
    print("=" * 76)
    print("6. Can register_alias() close the gap, as the docstring promises?")
    print("=" * 76)
    first = read_block(lines, found["TrackData1"])
    for channel, spelling in (
        ("ph", "ph1"),
        ("do", "do1"),
        ("temperature", "t1"),
        ("agitation", "n1"),
        ("airflow", "f1"),
        ("volume", "v1"),
        ("rq", "rq1"),
    ):
        register_alias(channel, spelling)
    naive = infer_columns(first)
    print(f"   a. the obvious spellings ('pH1', 'DO1', 'T1', ...): {len(naive.mapped)} / 40 mapped")
    print("      They never fire. The matcher compares against the whole header --")
    print("      'Unit 1.pH1.PV' folds to 'unit1ph1pv' -- and containment needs an")
    print("      alias of 4+ characters, so 'ph1' and 'rq1' are below the floor.")
    print()
    register_alias("ph", "pH1.PV")
    print(f"   b. the full dotted spelling ('pH1.PV'): {len(infer_columns(first).mapped)} / 40")
    second = read_block(lines, found["TrackData2"])
    mapped_v2 = [g.source for g in infer_columns(second).mapped]
    print(f"   c. ...and on vessel 2, that same alias maps: {mapped_v2}")
    print("      It does not carry. Vessel 2 spells it 'Unit 2.pH2.PV'.")
    print()
    pairs = set()
    for name, span in found.items():
        if name.startswith("TrackData") and name != "TrackData":
            for column in read_block(lines, span).columns:
                if m := re.match(r"Unit (\d+)\.(.+?)(?: \[.*\])?$", column):
                    pairs.add((m.group(1), m.group(2)))
    print(f"   d. aliases needed to cover THIS ONE 4-vessel file: {len(pairs)}")
    print()
    print("   That is the finding. A vendor profile is not a row in ALIASES -- it is")
    print("   a header grammar. This header glues three orthogonal facts together")
    print("   (vessel, channel, role) and the matcher treats headers as flat names,")
    print("   so the documented escape hatch does not reach this file.")


def main() -> None:
    path = fetch_fixture()
    lines = path.read_bytes().decode(ENCODING).splitlines()
    found, headers = sections(lines)

    step_1_can_pandas_read_it(path)
    step_2_container_shape(found, headers)
    frame = read_block(lines, found["TrackData1"])
    print(f"\n   [TrackData1] parsed by hand -> {frame.shape[0]} rows x {frame.shape[1]} cols")
    step_3_infer(frame)
    step_4_the_one_hit_is_wrong(frame)
    step_5_the_time_axis(frame)
    step_6_can_register_alias_fix_it(lines, found)

    print()
    print("=" * 76)
    print("Summary: what this file costs the loader")
    print("=" * 76)
    print("   read the file                     no  (encoding, delimiter, sections)")
    print("   find the runs                     no  (runs are sections, not a column)")
    print("   find the elapsed-time axis        no  (picked wall-clock; Duration is days)")
    print("   map the channels                  1 / 40, and that one is wrong")
    print("   fixable by register_alias()       no  (needs a header grammar)")


if __name__ == "__main__":
    main()
