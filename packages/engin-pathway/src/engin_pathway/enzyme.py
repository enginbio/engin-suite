"""``g_enzyme`` from UniProt kinetics -- and a precise account of what it is not.

`#140` item 2 asks for ``g_enzyme`` from a kcat/K_M source. **It cannot be
answered as asked from any licence-clean, anonymously-reachable source**, and the
measurement that establishes that is in this module's tests rather than in a
paragraph somebody wrote once.

## What the licence and access constraints leave

`#198` settled the licences: BRENDA is CC BY 4.0 and usable, SABIO-RK excludes use
"in connection with a product or service which is ... licensed", DLKcat and UniKP
ship no LICENSE at all, and CatPred is MIT while CatPred-DB mixes BRENDA and
SABIO-RK. That left BRENDA -- whose programmatic access is a SOAP endpoint behind
registration. **An adapter that needs an account is not one this package can
ship**, so the reachable licence-clean source is UniProt: CC BY 4.0, anonymous
HTTPS, and already the namespace `#214`'s Rhea identifiers join against.

## What UniProt actually carries, measured on 2026-08-20

``kineticParameters`` has exactly three keys: ``michaelisConstants``,
``maximumVelocities`` and ``note``. Across 500 reviewed entries carrying an EC
number:

===========================  ======
any kinetic parameters        29.8%
a K_M value                   29.0%
a Vmax value                  14.8%
neither                       70.2%
===========================  ======

**There is no kcat field.** kcat appears only inside free-text ``note`` values, in
about 7% of entries, phrased like ``"kcat is 43 min(-1)"``. Parsing turnover
numbers out of prose is the same failure shape as the ingest layer matching
``our`` to a substrate channel through the substring ``carbonsource`` -- it would
usually work and silently not work sometimes, which is worse than not answering.

``maximumVelocities`` is **specific activity** (``pmol/min/mg``, ``nmol/min/mg``,
``umol/min/mg``), not turnover. Converting to kcat needs the enzyme's molecular
weight *and* an assumption that the preparation was pure and fully active. Neither
is in the record, so that conversion is not done here.

## So this measures affinity, and says so

``g_enzyme`` in the schema means *is there a characterised, fast enough enzyme?* --
two questions. What is available answers the first well and the second not at all.
This module therefore computes a **substrate-affinity** score and names it that,
rather than quietly serving affinity under a label that promises turnover. That
substitution is exactly what `#208` fixed once already, in this package, by making
a mixed step distinguishable from a guessed one.

The transform is the Michaelis-Menten saturation fraction at a reference substrate
concentration:

.. math::

    g = \\frac{[S]}{K_M + [S]}

which is the **fraction of enzyme carrying substrate at** ``[S]`` -- bounded in
[0, 1] by construction rather than by clipping, monotone decreasing in K_M, and
exactly 0.5 when ``K_M == [S]``. Same shape of argument as
:mod:`engin_pathway.thermo`: a number whose meaning a reviewer can dispute, rather
than a rescaling over an arbitrary range.

``S_REFERENCE_UM`` is 1000 uM, the order of magnitude of a typical intracellular
metabolite pool. **It is a modelling choice, not a measurement**, and it is a
parameter precisely because a reviewer should be able to move it.

# implements D9
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

USER_AGENT = "engin-pathway (https://github.com/enginbio/engin-suite)"
"""Sent on every request. Naming the caller is the polite half of an anonymous API,
and `#214` learned the other half the hard way when Rhea 403'd ``Python-urllib``."""

UNIPROT_ENTRY = "https://rest.uniprot.org/uniprotkb/{accession}.json"

S_REFERENCE_UM = 1000.0
"""Reference substrate concentration, micromolar. A modelling choice -- see above."""


class EnzymeUnavailable(RuntimeError):
    """No usable kinetic record, and the reason.

    Raised rather than returning a default, for the reason `#206` established with
    the thermodynamic bridge: a confident wrong number with a narrow interval is
    worse than an error, because nothing downstream can tell it apart from a real
    one. Roughly 70% of enzymes land here, so callers must handle it.
    """


@dataclass(frozen=True)
class MichaelisRecord:
    """One K_M measurement, with the substrate it was measured against."""

    accession: str
    km_um: float
    substrate: str | None


def g_enzyme_affinity(km_um: float, s_reference_um: float = S_REFERENCE_UM) -> float:
    """Michaelis-Menten saturation fraction at ``s_reference_um``.

    ``km_um <= 0`` is rejected rather than clamped: a non-positive K_M is a parsing
    failure or a corrupt record, and silently mapping it to 1.0 would score the
    broken case as the best possible enzyme.
    """
    if km_um <= 0:
        raise ValueError(f"K_M must be positive, got {km_um}")
    if s_reference_um <= 0:
        raise ValueError(f"reference concentration must be positive, got {s_reference_um}")
    return float(s_reference_um / (km_um + s_reference_um))


def michaelis_constants(accession: str, timeout: float = 30.0) -> list[MichaelisRecord]:
    """Every K_M on a UniProt entry. Empty list if the entry has none."""
    request = urllib.request.Request(
        UNIPROT_ENTRY.format(accession=accession),
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            entry = json.load(response)
    except urllib.error.HTTPError as exc:  # pragma: no cover - network dependent
        raise EnzymeUnavailable(f"UniProt returned {exc.code} for {accession!r}") from exc
    out = []
    for comment in entry.get("comments", []):
        if comment.get("commentType") != "BIOPHYSICOCHEMICAL PROPERTIES":
            continue
        for m in comment.get("kineticParameters", {}).get("michaelisConstants", []):
            value, unit = m.get("constant"), m.get("unit")
            if value is None or unit != "uM":
                # Units vary (mM, nM). Not converted here: a silent unit conversion
                # is how an affinity score becomes wrong by three orders of
                # magnitude, and the caller should see what was skipped.
                continue
            out.append(MichaelisRecord(accession, float(value), m.get("substrate")))
    return out


def g_enzyme_for_uniprot(
    accession: str,
    substrate: str | None = None,
    s_reference_um: float = S_REFERENCE_UM,
    timeout: float = 30.0,
) -> tuple[float, MichaelisRecord]:
    """``(g_enzyme, the record it came from)`` for one UniProt accession.

    With several K_M values on an entry, the **largest** is used unless
    ``substrate`` selects one -- the weakest affinity is the binding step most
    likely to limit the reaction, and picking the best-looking number would make
    every multi-substrate enzyme score better than a single-substrate one for no
    reason. Passing ``substrate`` is the way to ask a question about a specific
    binding event instead.

    Raises :class:`EnzymeUnavailable` when the entry carries no usable K_M, which
    on a broad sample is roughly seven entries in ten.
    """
    records = michaelis_constants(accession, timeout=timeout)
    if substrate is not None:
        records = [r for r in records if r.substrate == substrate]
        if not records:
            raise EnzymeUnavailable(f"{accession!r} has no K_M in uM for substrate {substrate!r}")
    if not records:
        raise EnzymeUnavailable(
            f"{accession!r} carries no K_M in uM. UniProt has kinetic parameters for "
            f"roughly 30% of reviewed entries with an EC number, so this is the "
            f"common case rather than an error in the request."
        )
    worst = max(records, key=lambda r: r.km_um)
    return g_enzyme_affinity(worst.km_um, s_reference_um), worst
