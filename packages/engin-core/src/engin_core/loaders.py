"""Ingest: get a messy export to the convention, and say how sure you are.

Implements the loader half of **D11** (:mod:`engin_core.convention` is the other
half). D11's claim is that this is the real contribution -- unglamorous,
genuinely hard, and not already built. That claim was tested before this module
was written, and survives:

- **frictionless** infers schemas, but its ``field_confidence`` is a *type-casting
  tolerance* -- nine integers and one string in a column makes it an integer at
  the 0.9 default. It answers "is this column numeric", not "is this column
  titer, in grams per litre". It maps nothing to a domain vocabulary.
- **pandas** reads the file. Everything after that is the problem.

So what is built here is the semantic step: map the headers a bioreactor or a
spreadsheet actually produced onto the convention's channels, extract units from
wherever they were hiding, and **report a per-column confidence rather than
raising**. A loader that rejects a real export is a loader nobody uses twice.

## What "confidence" means here, precisely

It is an **ordinal heuristic score, not a calibrated probability.** A 0.9 means
"matched a known alias exactly and the units agree"; it does not mean nine times
in ten this mapping is right, because nothing has been measured against labelled
exports. On a project whose entire argument is calibrated uncertainty, that
distinction has to be stated rather than assumed -- so the score is documented as
a ranking aid for a human review pass, and
:attr:`InferenceReport.needs_review` exists to make that pass cheap.

Calibrating it needs a corpus of real vendor exports with known-correct mappings,
which is the same data problem as D12 tier 3-4.

## Why there are no vendor-specific parsers here

#19 names Sartorius, Eppendorf, Applikon and Benchling exports. Writing parsers
for those from memory of what such a file looks like would be inventing a format
and calling it support -- and the header spellings, delimiters and encodings are
exactly the details that cannot be reasoned out. :data:`ALIASES` is therefore
seeded with spellings that are *generic* (``OD600``, ``DO(%)``, ``Feed Rate``),
and :func:`register_alias` exists so a real file can teach the loader without a
code change. Vendor profiles land when someone has the actual files.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

from engin_core.convention import (
    CHANNELS,
    RUN_DIM,
    TIME_DIM,
    Finding,
    stamp,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    import pandas as pd
    import xarray as xr

Orientation = Literal["endpoint", "long", "wide", "unknown"]

MIN_CONTAINED_ALIAS = 4
"""Shortest alias allowed to match by being *contained* in a header.

Three characters is too permissive on real headers: `rq` and `our` and `ph` are
all real channels, and a three-letter alias found inside a longer header is as
often coincidence as signal. Exact matches are unaffected -- a two-character
header still maps if it is a known spelling in its own right.
"""

ALIASES: dict[str, tuple[str, ...]] = {
    "titer": ("titer", "titre", "product", "product_conc", "producttiter", "conc_product"),
    "biomass": ("biomass", "dcw", "dryweight", "od600", "od", "cellmass", "x"),
    "substrate": ("substrate", "glucose", "glc", "carbonsource", "s"),
    "volume": ("volume", "workingvolume", "broth_volume", "v"),
    "feed_rate": ("feedrate", "feed", "feedflow", "substratefeed"),
    "mu": ("mu", "growthrate", "specificgrowthrate"),
    # "o2" is deliberately an alias of both `do` and `offgas_o2`: a bare O2 column
    # is genuinely ambiguous between dissolved and exhaust oxygen, and resolving it
    # by fiat would be a confident wrong answer. It scores low and names both.
    "do": ("do", "do2", "o2", "dissolvedoxygen", "po2", "pdo"),
    "ph": ("ph", "phvalue"),
    "temperature": ("temperature", "temp", "t"),
    "agitation": ("agitation", "stirrer", "stirrerspeed", "rpm", "impeller"),
    "airflow": ("airflow", "gasflow", "aeration", "air"),
    "offgas_co2": ("co2", "offgasco2", "exhaustco2", "xco2"),
    "offgas_o2": ("o2", "offgaso2", "exhausto2", "xo2"),
    "our": ("our", "oxygenuptakerate", "our_rate"),
    "cer": ("cer", "co2evolutionrate", "carbondioxideevolutionrate"),
    "rq": ("rq", "respiratoryquotient"),
    "kla": ("kla", "klaa", "masstransfercoefficient"),
}
"""Header spellings that map onto a convention channel.

Deliberately generic. Extend with :func:`register_alias` from a real file rather
than by guessing at a vendor's wording.
"""

RUN_ALIASES: tuple[str, ...] = (
    "runid",
    "run",
    "runname",
    "batch",
    "batchid",
    "experiment",
    "experimentid",
    "vessel",
    "reactor",
    "culture",
    "sampleid",
)
"""Header spellings that identify the run a row belongs to."""

TIME_ALIASES: tuple[str, ...] = (
    "time",
    "hh",
    "timeh",
    "elapsedtime",
    "processtime",
    "age",
    "eft",
    "duration",
    "timestamp",
    "hours",
)
"""Header spellings for the within-run time axis."""

_UNIT_PATTERNS = (
    re.compile(r"\[([^\[\]]{1,20})\]\s*$"),  # Titer [g/L]
    re.compile(r"\(([^()]{1,20})\)\s*$"),  # Titer (g/L)
    re.compile(r"_in_([A-Za-z0-9_/%]{1,20})$"),  # titer_in_g_per_L
)

_UNIT_WORDS = {
    "g_per_l": "g/L",
    "gperl": "g/L",
    "g_l": "g/L",
    "gl": "g/L",
    "mg_per_l": "mg/L",
    "per_h": "1/h",
    "perh": "1/h",
    "1_h": "1/h",
    "h": "h",
    "hr": "h",
    "hours": "h",
    "min": "min",
    "pct": "%",
    "percent": "%",
    "c": "degC",
    "degc": "degC",
    "celsius": "degC",
    "rpm": "rpm",
    "vvm": "vvm",
    "l": "L",
    "l_per_h": "L/h",
    "lperh": "L/h",
}
"""Unit spellings that appear in headers, mapped to convention unit strings."""


def _normalize(text: str) -> str:
    """Fold a header to a comparison key: lowercase, alphanumerics only."""
    return re.sub(r"[^a-z0-9]", "", str(text).lower())


def register_alias(channel: str, *spellings: str) -> None:
    """Teach the loader header spellings seen in a real file.

    Raises for an unknown channel: a typo here would silently produce a mapping
    that never fires, which is worse than a failed import.
    """
    if channel not in CHANNELS:
        raise KeyError(f"{channel!r} is not a registered channel; known: {sorted(CHANNELS)}")
    ALIASES[channel] = tuple(dict.fromkeys(ALIASES.get(channel, ()) + tuple(spellings)))


class ColumnGuess(BaseModel):
    """What one source column was taken to be, and on what grounds.

    ``confidence`` is an ordinal heuristic (see the module docstring), not a
    calibrated probability. ``evidence`` is the sentence a reviewer reads to
    decide whether to accept the mapping.
    """

    source: str
    channel: str | None = None
    units: str | None = None
    units_assumed: bool = False
    """True when the header carried no units and the convention's default was
    filled in. Tracked separately from ``confidence``, which is about *which
    channel this is* -- a header spelled exactly like the canonical channel name
    is not a worse identification for failing to repeat its units."""

    confidence: float = Field(0.0, ge=0.0, le=1.0)
    evidence: str = ""
    alternatives: list[str] = Field(default_factory=list)

    contested: bool = False
    """Another column claims the same channel, so this mapping is *not* applied.

    Renaming two columns to one name silently destroys one of them. When a real
    dataset offers four aeration-rate columns -- total, air, O2 and CO2 -- the
    loader cannot know which is *the* airflow, and picking by confidence would be
    arbitrary when they all score alike. Both keep their original names, the
    suggestion stays visible here, and a finding names the competition.
    """

    @property
    def mapped(self) -> bool:
        """Identified *and* usable: a contested guess is reported, not applied."""
        return self.channel is not None and not self.contested


class InferenceReport(BaseModel):
    """The result of looking at a table: what it seems to be, and how sure.

    Nothing here raises. A column that could not be mapped is reported, not
    dropped, because the person reading the report is the one who knows what
    ``AUX2_raw`` was.
    """

    orientation: Orientation = "unknown"
    guesses: list[ColumnGuess] = Field(default_factory=list)
    run_column: str | None = None
    time_column: str | None = None
    notes: list[Finding] = Field(default_factory=list)
    review_threshold: float = 0.7

    @property
    def mapped(self) -> list[ColumnGuess]:
        return [g for g in self.guesses if g.mapped]

    @property
    def unmapped(self) -> list[ColumnGuess]:
        return [g for g in self.guesses if not g.mapped]

    @property
    def needs_review(self) -> list[ColumnGuess]:
        """Mapped columns whose evidence was weak enough to be worth a human's eye."""
        return [g for g in self.mapped if g.confidence < self.review_threshold]

    def mapping(self) -> dict[str, str]:
        """``{source column: channel}`` for the columns that were mapped."""
        return {g.source: g.channel for g in self.mapped if g.channel}

    def units(self) -> dict[str, str]:
        """``{channel: units}`` for mapped columns whose units were determined."""
        return {g.channel: g.units for g in self.mapped if g.channel and g.units}

    def summary(self) -> str:
        n_map, n_un, n_rev = len(self.mapped), len(self.unmapped), len(self.needs_review)
        return (
            f"{self.orientation} table: {n_map} column(s) mapped, {n_un} unmapped, "
            f"{n_rev} below the {self.review_threshold:g} review threshold"
        )


def _extract_units(header: str) -> tuple[str, str | None]:
    """Split a header into ``(name_part, units)``.

    Units hide in brackets (``Titer [g/L]``), parentheses (``Titer (g/L)``) or a
    suffix (``titer_g_per_L``). Returns the header unchanged and ``None`` when
    nothing unit-shaped is present.
    """
    text = str(header).strip()
    for pattern in _UNIT_PATTERNS:
        match = pattern.search(text)
        if match:
            raw = match.group(1).strip()
            name = text[: match.start()].strip(" _-")
            return name, _canonical_unit(raw)

    # Trailing token that is itself a known unit spelling: titer_g_per_L, do_pct
    parts = re.split(r"[_\-\s]+", text)
    for take in (3, 2, 1):
        if len(parts) > take:
            tail = "_".join(parts[-take:]).lower()
            if tail in _UNIT_WORDS:
                return "_".join(parts[:-take]), _UNIT_WORDS[tail]
    return text, None


def _canonical_unit(raw: str) -> str | None:
    """Map a unit as written in a header onto the convention's spelling."""
    key = re.sub(r"[^a-z0-9/%]", "", raw.lower())
    direct = {
        "g/l": "g/L",
        "gl": "g/L",
        "mg/l": "mg/L",
        "1/h": "1/h",
        "h-1": "1/h",
        "1/hr": "1/h",
        "%": "%",
        "pct": "%",
        "c": "degC",
        "degc": "degC",
        "°c": "degC",
        "rpm": "rpm",
        "vvm": "vvm",
        "l": "L",
        "l/h": "L/h",
        "h": "h",
        "hr": "h",
        "min": "min",
    }
    if key in direct:
        return direct[key]
    if key in _UNIT_WORDS:
        return _UNIT_WORDS[key]
    return raw.strip() or None


def _match_channel(name_part: str) -> tuple[str | None, float, str, list[str]]:
    """Map a header's name part to a channel: ``(channel, confidence, why, others)``."""
    key = _normalize(name_part)
    if not key:
        return None, 0.0, "empty header", []

    if key in CHANNELS:
        return key, 1.0, f"header is the canonical channel name {key!r}", []

    exact = [ch for ch, spellings in ALIASES.items() if key in map(_normalize, spellings)]
    if len(exact) == 1:
        return exact[0], 0.9, f"header matches a known alias for {exact[0]!r}", []
    if len(exact) > 1:
        return (
            exact[0],
            0.4,
            f"header is ambiguous between {exact}; took the first",
            exact[1:],
        )

    # Containment, in one direction only and with a length floor.
    #
    # The reverse direction -- treating a header as an abbreviation *inside* a
    # longer alias -- was tried and removed. On the first real dataset it mapped
    # `our` to substrate via "carbonSOURce", `ht` to biomass via "dryweigHT",
    # `fi` to mu via "speciFIc" and `te` to titer via "tITEr`. Four confident-
    # looking guesses, all coincidence. A short header appearing somewhere inside
    # a long word is not evidence about what the column means.
    partial = [
        ch
        for ch, spellings in ALIASES.items()
        if any(len(s) >= MIN_CONTAINED_ALIAS and _normalize(s) in key for s in spellings)
    ]
    if len(partial) == 1:
        return partial[0], 0.6, f"header contains an alias for {partial[0]!r}", []
    if len(partial) > 1:
        return partial[0], 0.35, f"header partially matches {partial}; took the first", partial[1:]

    return None, 0.0, "no alias matched", []


def _find_special(columns: list[str], aliases: tuple[str, ...]) -> str | None:
    """First column whose header matches one of ``aliases``, exact match preferred."""
    normalized = {c: _normalize(_extract_units(c)[0]) for c in columns}
    for column, key in normalized.items():
        if key in aliases:
            return column
    for column, key in normalized.items():
        if any(a in key for a in aliases if len(a) >= 4):
            return column
    return None


def infer_columns(df: pd.DataFrame, *, review_threshold: float = 0.7) -> InferenceReport:
    """Work out what each column of a table is, without changing anything.

    Reports rather than raises. Inspect :attr:`InferenceReport.needs_review` and
    :attr:`InferenceReport.unmapped` before trusting a mapping.
    """
    columns = [str(c) for c in df.columns]
    report = InferenceReport(review_threshold=review_threshold)

    report.run_column = _find_special(columns, RUN_ALIASES)
    report.time_column = _find_special(columns, TIME_ALIASES)
    report.orientation = "long" if report.time_column else "endpoint"

    for column in columns:
        if column in (report.run_column, report.time_column):
            continue

        name_part, units = _extract_units(column)
        channel, confidence, evidence, alternatives = _match_channel(name_part)
        units_assumed = False

        if channel and units:
            # Units that agree are genuine evidence the *channel* guess is right:
            # a column called "Titre" reading in g/L is more likely titer than not.
            # Units that disagree are reported, never silently converted.
            expected = CHANNELS[channel].units
            if units == expected:
                confidence = min(1.0, confidence + 0.05)
                evidence += f"; units {units!r} agree with the convention"
            else:
                evidence += f"; units {units!r} differ from the convention's {expected!r}"
        elif channel and not units:
            # Absence of units is not evidence against the channel, so it costs no
            # confidence -- it is recorded on units_assumed instead.
            evidence += "; no units in the header, so the convention's default is assumed"
            units = CHANNELS[channel].units
            units_assumed = True

        report.guesses.append(
            ColumnGuess(
                source=column,
                channel=channel,
                units=units,
                units_assumed=units_assumed,
                confidence=round(confidence, 3),
                evidence=evidence,
                alternatives=alternatives,
            )
        )

    # Two columns renamed to one name destroys one of them, and pandas does it
    # without complaint -- a real dataset with four aeration-rate columns lost all
    # four this way before this check existed. Contested channels are reported and
    # left alone rather than resolved by guessing.
    claims: dict[str, list[ColumnGuess]] = {}
    for guess in report.guesses:
        if guess.channel:
            claims.setdefault(guess.channel, []).append(guess)
    for channel, competitors in claims.items():
        if len(competitors) < 2:
            continue
        sources = [g.source for g in competitors]
        for guess in competitors:
            guess.contested = True
            guess.evidence += f"; contested by {len(competitors) - 1} other column(s)"
        report.notes.append(
            Finding(
                level="error",
                code="contested-channel",
                target=channel,
                message=f"{len(competitors)} columns all look like {channel!r}: {sources}. "
                "None was applied -- renaming them all to one name would silently "
                "discard every one but the last.",
                suggestion="decide which is the channel and rename it yourself, or "
                "register_alias() the others to channels of their own; they are carried "
                "through under their original names either way",
            )
        )

    if report.run_column is None:
        report.notes.append(
            Finding(
                level="warning",
                code="no-run-column-found",
                target="<table>",
                message="no column looked like a run identifier, so rows cannot be tied "
                "to the runs they came from",
                suggestion=f"pass run_column= explicitly, or rename the column to {RUN_DIM!r}",
            )
        )
    if report.needs_review:
        weak = ", ".join(f"{g.source!r}->{g.channel}" for g in report.needs_review)
        report.notes.append(
            Finding(
                level="info",
                code="low-confidence-mappings",
                target="<table>",
                message=f"mapped on weak evidence: {weak}",
                suggestion="check these against the source file; the score is a heuristic "
                "ranking aid, not a calibrated probability",
            )
        )
    for guess in report.unmapped:
        report.notes.append(
            Finding(
                level="info",
                code="unmapped-column",
                target=guess.source,
                message=f"{guess.source!r} did not match any known channel ({guess.evidence})",
                suggestion="register_alias() it if it is a channel under another name; "
                "otherwise it is carried through untouched",
            )
        )

    return report


def load_endpoints(
    df: pd.DataFrame,
    *,
    run_column: str | None = None,
    rename: bool = True,
    review_threshold: float = 0.7,
) -> tuple[pd.DataFrame, InferenceReport]:
    """Bring an endpoint DoE table onto the convention.

    Returns the frame with mapped columns renamed to their channels (unmapped
    columns are carried through untouched) and the report that says what was
    done. Pass ``rename=False`` to inspect the report without touching the data.
    """
    report = infer_columns(df, review_threshold=review_threshold)
    if run_column is not None:
        report.run_column = run_column
        report.notes = [n for n in report.notes if n.code != "no-run-column-found"]

    out = df.copy()
    if rename:
        mapping = report.mapping()
        if report.run_column:
            mapping[report.run_column] = "run_id"
        out = out.rename(columns=mapping)
    return out, report


def load_timeseries(
    df: pd.DataFrame,
    *,
    run_column: str | None = None,
    time_column: str | None = None,
    review_threshold: float = 0.7,
) -> tuple[xr.Dataset, InferenceReport]:
    """Turn a long-format table of runs over time into a conforming Dataset.

    Expects one row per (run, time) and one column per channel -- the shape a
    bioreactor export arrives in. The result has dims ``(run, time)``, units in
    each variable's attrs, and the convention version stamped on it.

    Raises :class:`ValueError` only when the table cannot be reshaped at all --
    no run or time column. Everything else is reported.
    """
    import pandas as pd

    report = infer_columns(df, review_threshold=review_threshold)
    run_col = run_column or report.run_column
    time_col = time_column or report.time_column
    report.run_column, report.time_column = run_col, time_col
    report.orientation = "long"

    if run_col is None or time_col is None:
        missing = "run" if run_col is None else "time"
        raise ValueError(
            f"cannot reshape to (run, time): no {missing} column found. "
            f"Columns were {list(map(str, df.columns))}. Pass {missing}_column= explicitly."
        )

    mapping = report.mapping()
    frame = df.rename(columns={**mapping, run_col: RUN_DIM, time_col: TIME_DIM})

    value_columns = [c for c in frame.columns if c not in (RUN_DIM, TIME_DIM)]
    numeric = [c for c in value_columns if pd.api.types.is_numeric_dtype(frame[c])]
    dropped = sorted(set(value_columns) - set(numeric))
    if dropped:
        report.notes.append(
            Finding(
                level="warning",
                code="non-numeric-columns-dropped",
                target="<table>",
                message=f"non-numeric columns not carried onto the Dataset: {dropped}",
                suggestion="parse them to numbers first, or keep them as per-run metadata; "
                "a Dataset variable has to be an array",
            )
        )

    indexed = frame.set_index([RUN_DIM, TIME_DIM])[numeric]
    if indexed.index.duplicated().any():
        n = int(indexed.index.duplicated().sum())
        indexed = indexed[~indexed.index.duplicated(keep="first")]
        report.notes.append(
            Finding(
                level="warning",
                code="duplicate-run-time-rows",
                target="<table>",
                message=f"{n} row(s) repeated a (run, time) pair; kept the first of each",
                suggestion="aggregate replicates before loading if that is not what you want",
            )
        )

    ds = indexed.to_xarray()

    units = report.units()
    for name in ds.data_vars:
        if str(name) in units:
            ds[name].attrs["units"] = units[str(name)]
    if TIME_DIM in ds.coords:
        _, time_units = _extract_units(time_col)
        ds[TIME_DIM].attrs["units"] = time_units or "h"
        if time_units is None:
            report.notes.append(
                Finding(
                    level="warning",
                    code="time-units-assumed",
                    target=time_col,
                    message=f"no units in the time header {time_col!r}; assumed hours",
                    suggestion="rename the column to carry them, e.g. 'time (h)', or set "
                    'ds.time.attrs["units"] yourself',
                )
            )

    return stamp(ds), report
