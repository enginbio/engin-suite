"""The Engin data convention: a thin, versioned layer over xarray and pandas.

Implements **D11**. Engin defines **no bespoke data container**. Time-series runs
are :class:`xarray.Dataset`\\ s; endpoint design-of-experiments data is a
:class:`pandas.DataFrame`. What is versioned here is a *convention* over those --
dimension and coordinate names, unit attributes, metadata attachment points --
and a validator that reports how far a dataset sits from it.

## Why a convention rather than a type

The design constraint this has to satisfy is that **another tool must be able to
read and write this format without depending on Engin at all**. A type we own
fails that constraint the moment anyone has to reimplement it; a convention over
structures that already have readers and writers satisfies it by construction.
A conforming dataset written by Engin is an ordinary netCDF file, and a
conforming dataset can be produced by anything that can write one.

The precedent is climate science, which layered CF conventions onto netCDF rather
than inventing an array format. This module borrows CF's *mechanism* -- meaning
carried in ``attrs`` as ``units`` / ``standard_name`` / ``long_name`` -- without
borrowing its vocabulary, which is about latitude and cell measures and has
nothing to say about a bioreactor.

## What the validator is for, and what it deliberately is not

It **reports**; it does not raise, and it does not repair. Bioprocess data
arrives from vendor exports that nobody designed for interchange, so a validator
whose only verdict is "rejected" would be a wall in front of the ingest layer
rather than a guide through it. Every finding names the thing it saw, why the
convention wants otherwise, and what would fix it. :attr:`ConventionReport.ok`
is a summary for tests and CI, not a gate the library enforces on users.

xarray validates none of this itself -- it accepts any string as ``units`` -- so
the job is real.

## Units

Units are strings in ``attrs["units"]``, written the way pint parses them
(``"g/L"``, ``"1/h"``, ``"degC"``, ``"rpm"``). Dimensionless quantities are
``"1"``. Where pint is installed the validator parses them; where it is not, it
falls back to comparing against the expected unit string for known channels and
says so in the report rather than silently skipping the check.

One domain unit needs defining: ``vvm`` (gas volumes per liquid volume per
minute) is standard in fermentation and absent from pint's registry. See
:func:`register_domain_units`.

## A note on the endpoint case

``DataFrame.attrs`` does **not** survive a CSV round-trip. Units for endpoint
data therefore cannot live there if they are to reach anyone; they belong in a
sidecar passed alongside the frame (:func:`validate_endpoints`), or in a format
that carries metadata. This is a property of pandas, not a choice made here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:  # pragma: no cover - import-time typing only
    import pandas as pd
    import xarray as xr

CONVENTION_VERSION = "0.1"
"""Version of the convention itself. Written into ``Dataset.attrs`` so a reader
can tell which rules a file was produced under. Bumped when the rules change,
independently of the package version."""

CONVENTION_ATTR = "engin_convention"
"""Dataset-level attribute carrying :data:`CONVENTION_VERSION`."""

RUN_DIM = "run"
"""Canonical dimension for independent fermentation runs."""

TIME_DIM = "time"
"""Canonical dimension for within-run sampling. A coordinate with a ``units``
attribute -- elapsed time, not wall clock, because runs are compared to each
other rather than to a calendar."""

DOMAIN_UNITS: tuple[str, ...] = ("vvm = liter / liter / minute",)
"""Units standard in fermentation that pint does not ship. Applied by
:func:`register_domain_units`."""


class Channel(BaseModel):
    """One known measurement channel: its canonical name and expected units.

    The registry is a *recommendation*, not a closed vocabulary. An unrecognised
    channel is reported at ``info`` level, never as an error -- a convention that
    refuses to carry a measurement it has not heard of would be useless on the
    first real dataset.
    """

    name: str
    units: str
    description: str


CHANNELS: dict[str, Channel] = {
    c.name: c
    for c in (
        Channel(name="titer", units="g/L", description="product concentration in broth"),
        Channel(name="biomass", units="g/L", description="dry cell weight"),
        Channel(name="substrate", units="g/L", description="limiting substrate concentration"),
        Channel(name="volume", units="L", description="working volume"),
        Channel(name="feed_rate", units="L/h", description="feed addition rate"),
        Channel(name="mu", units="1/h", description="specific growth rate"),
        Channel(name="do", units="%", description="dissolved oxygen, percent of saturation"),
        Channel(name="ph", units="1", description="pH, dimensionless by convention"),
        Channel(name="temperature", units="degC", description="broth temperature"),
        Channel(name="agitation", units="rpm", description="impeller speed"),
        Channel(name="airflow", units="vvm", description="gas flow per volume per minute"),
        Channel(name="offgas_co2", units="%", description="exhaust CO2 fraction"),
        Channel(name="offgas_o2", units="%", description="exhaust O2 fraction"),
    )
}
"""Known channels. Extend by registering rather than editing: unknown names are
carried, not rejected."""

Level = Literal["error", "warning", "info"]


class Finding(BaseModel):
    """One observation about a dataset, with the fix that would resolve it.

    ``suggestion`` is mandatory in spirit: a finding a reader cannot act on is a
    complaint rather than a report.
    """

    level: Level
    code: str
    target: str
    message: str
    suggestion: str

    def __str__(self) -> str:  # pragma: no cover - convenience only
        return f"[{self.level}] {self.target}: {self.message} -- {self.suggestion}"


class ConventionReport(BaseModel):
    """What a dataset looks like against the convention.

    ``ok`` means no ``error``-level findings. Warnings and info are expected on
    real data and do not make a dataset unusable.
    """

    convention_version: str = CONVENTION_VERSION
    findings: list[Finding] = Field(default_factory=list)
    checked_units_with_pint: bool = False

    @property
    def ok(self) -> bool:
        return not any(f.level == "error" for f in self.findings)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "warning"]

    def summary(self) -> str:
        """One line, for logs and test failure messages."""
        n_e, n_w = len(self.errors), len(self.warnings)
        n_i = len(self.findings) - n_e - n_w
        verdict = "conforms" if self.ok else "does not conform"
        return (
            f"{verdict} to engin convention {self.convention_version}: "
            f"{n_e} error(s), {n_w} warning(s), {n_i} note(s)"
        )


def register_domain_units(registry: Any | None = None) -> bool:
    """Teach pint the fermentation units it does not ship (currently ``vvm``).

    Returns ``False`` when pint is not installed, so callers can degrade rather
    than depend on it. Safe to call repeatedly; redefinitions are ignored.
    """
    try:
        import pint
    except ImportError:
        return False

    reg = registry if registry is not None else pint.get_application_registry()
    for definition in DOMAIN_UNITS:
        name = definition.split("=", 1)[0].strip()
        if not hasattr(reg, name):
            reg.define(definition)
    return True


def _parse_units(units: str) -> tuple[bool, str]:
    """``(parsed_ok, detail)``. Detail carries the reason when parsing fails."""
    try:
        import pint
    except ImportError:  # pragma: no cover - exercised via checked_units_with_pint
        return True, "pint not installed"

    register_domain_units()
    reg = pint.get_application_registry()
    try:
        reg.Unit(units)
    except Exception as exc:  # noqa: BLE001 - pint raises several unrelated types
        return False, type(exc).__name__
    return True, ""


def _pint_available() -> bool:
    try:
        import pint  # noqa: F401
    except ImportError:
        return False
    return True


def validate_timeseries(ds: xr.Dataset) -> ConventionReport:
    """Check a time-series Dataset against the convention.

    Expects dims ``(run, time)``, one data variable per channel, ``units`` in
    each variable's ``attrs``, and :data:`CONVENTION_ATTR` on the Dataset.
    Nothing is modified.
    """
    report = ConventionReport(checked_units_with_pint=_pint_available())
    add = report.findings.append

    declared = ds.attrs.get(CONVENTION_ATTR)
    if declared is None:
        add(
            Finding(
                level="warning",
                code="missing-convention-attr",
                target="<dataset>",
                message=f"no {CONVENTION_ATTR!r} attribute, so a reader cannot tell "
                "which version of the convention this was written under",
                suggestion=f'set ds.attrs["{CONVENTION_ATTR}"] = "{CONVENTION_VERSION}"',
            )
        )
    elif str(declared) != CONVENTION_VERSION:
        add(
            Finding(
                level="info",
                code="convention-version-mismatch",
                target="<dataset>",
                message=f"written under convention {declared!r}; this is {CONVENTION_VERSION!r}",
                suggestion="check the changelog for the rules that changed between them",
            )
        )

    if RUN_DIM not in ds.dims:
        add(
            Finding(
                level="error",
                code="missing-run-dim",
                target="<dataset>",
                message=f"no {RUN_DIM!r} dimension; runs are what makes this a campaign "
                "rather than a single trace",
                suggestion=f"rename the run axis to {RUN_DIM!r}, or expand_dims({RUN_DIM!r}) "
                "for a single run",
            )
        )
    if TIME_DIM not in ds.dims:
        add(
            Finding(
                level="error",
                code="missing-time-dim",
                target="<dataset>",
                message=f"no {TIME_DIM!r} dimension",
                suggestion=f"rename the sampling axis to {TIME_DIM!r}",
            )
        )
    elif TIME_DIM not in ds.coords:
        add(
            Finding(
                level="error",
                code="time-not-a-coordinate",
                target=TIME_DIM,
                message="time is a dimension without a coordinate, so sample spacing is unknown "
                "and runs sampled at different rates cannot be aligned",
                suggestion="assign elapsed times, e.g. ds = ds.assign_coords(time=hours)",
            )
        )
    elif "units" not in ds[TIME_DIM].attrs:
        add(
            Finding(
                level="warning",
                code="time-missing-units",
                target=TIME_DIM,
                message="time coordinate has no units, and hours-vs-minutes is not inferable "
                "from the values",
                suggestion='set ds.time.attrs["units"] = "h"',
            )
        )

    if not ds.data_vars:
        add(
            Finding(
                level="error",
                code="no-data-variables",
                target="<dataset>",
                message="no data variables; there is nothing to interpret",
                suggestion="add one data variable per measured channel",
            )
        )

    for name, var in ds.data_vars.items():
        target = str(name)
        units = var.attrs.get("units")
        known = CHANNELS.get(target)

        if units is None:
            expected = f' (this convention expects "{known.units}")' if known else ""
            add(
                Finding(
                    level="error",
                    code="missing-units",
                    target=target,
                    message=f"no units attribute{expected}",
                    suggestion=f'set ds["{target}"].attrs["units"] = '
                    f'"{known.units if known else "<unit>"}"',
                )
            )
        else:
            parsed, detail = _parse_units(str(units))
            if not parsed:
                add(
                    Finding(
                        level="error",
                        code="unparseable-units",
                        target=target,
                        message=f"units {units!r} could not be parsed ({detail})",
                        suggestion="use a pint-parseable string, e.g. 'g/L', '1/h', 'degC'; "
                        "dimensionless quantities are '1'",
                    )
                )
            elif known and str(units) != known.units:
                add(
                    Finding(
                        level="warning",
                        code="unexpected-units",
                        target=target,
                        message=f"{target!r} is in {units!r}; this convention records it "
                        f"in {known.units!r} ({known.description})",
                        suggestion=f"convert to {known.units!r}, or rename the variable if it "
                        "measures something else",
                    )
                )

        if known is None:
            add(
                Finding(
                    level="info",
                    code="unregistered-channel",
                    target=target,
                    message=f"{target!r} is not a registered channel, so it is carried "
                    "without interpretation",
                    suggestion="fine as-is; register it if it is common enough that other "
                    "datasets will use the same name",
                )
            )

        missing_dims = [d for d in (RUN_DIM, TIME_DIM) if d in ds.dims and d not in var.dims]
        if missing_dims:
            add(
                Finding(
                    level="warning",
                    code="unexpected-variable-dims",
                    target=target,
                    message=f"dims {tuple(str(d) for d in var.dims)} omit {tuple(missing_dims)}",
                    suggestion="per-run constants are fine on (run,) alone; check this is "
                    "deliberate rather than a collapsed axis",
                )
            )

    return report


def validate_endpoints(
    df: pd.DataFrame,
    units: dict[str, str] | None = None,
    *,
    run_column: str = "run_id",
) -> ConventionReport:
    """Check an endpoint design-of-experiments table against the convention.

    ``units`` is a sidecar mapping column name to unit string, passed separately
    because ``DataFrame.attrs`` is lost on a CSV round-trip -- if it is omitted,
    the frame's own ``attrs["units"]`` is used, with a note that it will not
    survive being written out.
    """
    report = ConventionReport(checked_units_with_pint=_pint_available())
    add = report.findings.append

    sidecar = units
    if sidecar is None:
        sidecar = dict(df.attrs.get("units", {}))
        if sidecar:
            add(
                Finding(
                    level="warning",
                    code="units-in-frame-attrs",
                    target="<frame>",
                    message="units were read from DataFrame.attrs, which pandas drops when "
                    "the frame is written to CSV",
                    suggestion="carry them alongside the frame instead, and pass them as the "
                    "units= argument",
                )
            )

    if run_column not in df.columns:
        add(
            Finding(
                level="error",
                code="missing-run-column",
                target=run_column,
                message=f"no {run_column!r} column, so rows cannot be tied back to the runs "
                "they came from",
                suggestion=f"add a {run_column!r} column of stable run identifiers",
            )
        )
    elif df[run_column].duplicated().any():
        n = int(df[run_column].duplicated().sum())
        add(
            Finding(
                level="warning",
                code="duplicate-run-ids",
                target=run_column,
                message=f"{n} duplicated run id(s); endpoint data is one row per run",
                suggestion="aggregate replicates, or make the identifier unique per row",
            )
        )

    if not sidecar:
        add(
            Finding(
                level="warning",
                code="no-units-sidecar",
                target="<frame>",
                message="no units given for any column, so numbers are uninterpretable "
                "outside the session that produced them",
                suggestion='pass units={"titer": "g/L", ...}',
            )
        )

    for column in df.columns:
        if column == run_column:
            continue
        name = str(column)
        known = CHANNELS.get(name)
        unit = sidecar.get(name)

        if unit is None:
            if known:
                add(
                    Finding(
                        level="warning",
                        code="missing-units",
                        target=name,
                        message=f"{name!r} is a known channel but has no unit given",
                        suggestion=f'add "{name}": "{known.units}" to the units mapping',
                    )
                )
            continue

        parsed, detail = _parse_units(str(unit))
        if not parsed:
            add(
                Finding(
                    level="error",
                    code="unparseable-units",
                    target=name,
                    message=f"units {unit!r} could not be parsed ({detail})",
                    suggestion="use a pint-parseable string, e.g. 'g/L'; dimensionless is '1'",
                )
            )
        elif known and str(unit) != known.units:
            add(
                Finding(
                    level="warning",
                    code="unexpected-units",
                    target=name,
                    message=f"{name!r} is in {unit!r}; this convention records it "
                    f"in {known.units!r}",
                    suggestion=f"convert to {known.units!r}, or rename the column",
                )
            )

    unknown_units = sorted(set(sidecar) - set(map(str, df.columns)))
    if unknown_units:
        add(
            Finding(
                level="warning",
                code="units-for-absent-columns",
                target="<frame>",
                message=f"units given for columns not present: {unknown_units}",
                suggestion="drop them, or check for a typo against the frame's column names",
            )
        )

    return report


def stamp(ds: xr.Dataset) -> xr.Dataset:
    """Return ``ds`` with the convention version recorded in its attrs.

    A shallow copy -- the input is not modified. This is the only writing this
    module does, and it writes one attribute.
    """
    out = ds.copy()
    out.attrs[CONVENTION_ATTR] = CONVENTION_VERSION
    return out
