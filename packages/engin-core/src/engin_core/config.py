"""The project file: one YAML a non-programmer edits, read by every stage's CLI.

Lives in ``engin_core`` for the same reason :mod:`engin_core.handoff` does — both
stage packages depend on core and neither depends on the other, so this is the only
place all of them can read the same file.

**Why YAML and not JSON.** Comments. This file is where someone who does not write
Python finds out what ``g_thermo`` means, and a format that cannot carry an
explanation next to the number it explains would defeat the point. The cost is a
dependency, so PyYAML is an extra (``pip install "engin-core[cli]"``) rather than a
default — ADR 0002 keeps the modelling path light.

Every section is optional. A file with only a ``host:`` block is a valid project;
``engin-host`` will read it and ``engin-pathway`` will say plainly that it has nothing
to do rather than inventing a default.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .simulator import ReactorConfig
from .tea import CostParameters

__all__ = [
    "HostSection",
    "RouteSpec",
    "PathwaySection",
    "ProcessSection",
    "ProjectConfig",
    "load_project",
    "starter_yaml",
]


class HostSection(BaseModel):
    """Stage [4] inputs: what the target needs from a chassis."""

    weights: dict[str, float] = Field(
        ..., description="capability -> importance; any positive scale, renormalised"
    )
    hard: dict[str, float] = Field(
        default_factory=dict,
        description="capability -> minimum; a host below it is demoted, not penalised",
    )

    @model_validator(mode="after")
    def _check(self) -> HostSection:
        if not self.weights:
            raise ValueError("host.weights must name at least one capability")
        if any(w < 0 for w in self.weights.values()):
            raise ValueError("host.weights must all be >= 0")
        if sum(self.weights.values()) <= 0:
            raise ValueError("host.weights must not be all zero")
        return self


class RouteSpec(BaseModel):
    """One candidate route, as it appears in the project file.

    Deliberately structural rather than typed against ``engin_pathway.Step``: core
    cannot import a package that depends on it, and the feature names are that
    package's business. ``engin-pathway`` validates them when it builds real steps,
    so a typo surfaces there with the right vocabulary in the message.
    """

    id: str
    steps: list[dict[str, float]] = Field(..., min_length=1)
    manufacturability: float | None = Field(
        None, description="known label in [0,1], if this route has been measured"
    )


class PathwaySection(BaseModel):
    """Stage [3] inputs: the candidate routes to rank."""

    routes: list[RouteSpec] = Field(..., min_length=1)


class ProcessSection(BaseModel):
    """Stage [1] inputs: the vessel, the economics, and how much to plan.

    ``reactor`` and ``cost`` default to the bundled caricature, which is the honest
    behaviour: a user who states neither gets our process, and the report says so.
    """

    reactor: ReactorConfig = Field(default_factory=ReactorConfig)
    cost: CostParameters = Field(default_factory=CostParameters)
    n_runs: int = Field(40, gt=0, description="how many runs to simulate when none are given")
    batch_size: int = Field(4, gt=0, description="how many designs to recommend")
    seed: int = Field(0, description="makes a run reproducible")


class ProjectConfig(BaseModel):
    """A whole project. Every stage section is optional and independent."""

    target: str = Field("", description="what you are making; labels the output only")
    notes: str = ""
    host: HostSection | None = None
    pathway: PathwaySection | None = None
    process: ProcessSection | None = None

    model_config = {"extra": "forbid"}


def _require_yaml() -> Any:
    try:
        import yaml
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised by the message itself
        raise ModuleNotFoundError(
            "Reading a project file needs PyYAML, which the default install deliberately "
            "omits to keep the modelling path light (ADR 0002).\n\n"
            '    pip install "engin-core[cli]"'
        ) from exc
    return yaml


def load_project(path: str | Path) -> ProjectConfig:
    """Read and validate a project file.

    Uses ``yaml.safe_load``: a project file is data, and a format that can construct
    arbitrary Python objects is not something to point at a file a user was handed.
    """
    yaml = _require_yaml()
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"no project file at {p}")

    raw = yaml.safe_load(p.read_text()) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"{p}: expected a mapping at the top level, got {type(raw).__name__}")
    return ProjectConfig.model_validate(raw)


STARTER = """\
# ---------------------------------------------------------------------------
#  Engin project file
#
#  Every section is optional. Run whichever stage you have filled in:
#
#      engin-host     --config project.yaml     # which chassis?
#      engin-pathway  --config project.yaml     # which route?
#      engin-process  --config project.yaml     # what to run next?
#
#  Numbers here are illustrative. Nothing in this file has been validated
#  against your molecule -- see docs.engin.bio/en/latest/limitations.html
# ---------------------------------------------------------------------------

target: "my molecule"          # labels the output; nothing computes from it


# --------------------------------------------------------------- stage [4]
# Which host organism to build in.
host:
  # How much each capability matters. Any positive numbers -- they are
  # renormalised, so 2/1 and 20/10 mean the same thing.
  #
  #   secretion  exports product rather than holding it inside the cell
  #   glyco      attaches sugar groups (needed for most therapeutic proteins)
  #   titer      how much product per litre it tends to reach
  #   speed      how fast it grows, and how fast you can iterate
  #   tools      how mature the genetic toolkit is
  #   scaleup    how well it behaves in a large vessel
  #   cost       how cheap it is to feed and run
  #   gras       generally-recognised-as-safe status (food//cosmetic routes)
  #   smallmol   suited to small-molecule products
  #   protein    suited to protein products
  weights:
    secretion: 1.0
    titer: 1.0
    scaleup: 0.7
    cost: 0.7

  # Minimums. A host scoring below one of these is ranked below every host
  # that clears them, however good its overall score -- use this for things
  # that are not tradeable, like glycosylation for a therapeutic protein.
  hard:
    secretion: 0.40


# --------------------------------------------------------------- stage [3]
# Which biosynthetic route to build. Each step is scored 0-1, higher = better.
#
#   g_thermo    is the reaction thermodynamically downhill?
#   g_enzyme    is there a characterised, fast enough enzyme?
#   g_cofactor  does it balance with what the cell can supply?
#   g_tox       is the intermediate non-toxic to the host?
#   g_expr      does the enzyme express and fold in this host?
#
# NOTE: today these are your judgement, entered by hand -- nothing computes
# them from structure yet. See github.com/enginbio/engin-suite/issues/140.
pathway:
  routes:
    - id: "route-A"
      steps:
        - {g_thermo: 0.80, g_enzyme: 0.70, g_cofactor: 0.90, g_tox: 0.95, g_expr: 0.60}
        - {g_thermo: 0.60, g_enzyme: 0.85, g_cofactor: 0.75, g_tox: 0.90, g_expr: 0.70}
    - id: "route-B"
      steps:
        - {g_thermo: 0.95, g_enzyme: 0.60, g_cofactor: 0.80, g_tox: 0.40, g_expr: 0.65}
        - {g_thermo: 0.70, g_enzyme: 0.75, g_cofactor: 0.85, g_tox: 0.90, g_expr: 0.80}
        - {g_thermo: 0.85, g_enzyme: 0.80, g_cofactor: 0.70, g_tox: 0.95, g_expr: 0.75}


# --------------------------------------------------------------- stage [1]
# Your vessel and your economics. Both default to a 1 L -> 2.5 L, 48 h
# bench fed-batch, which is almost certainly not yours -- change them.
process:
  reactor:
    v0: 1.0          # starting volume, litres
    vmax: 2.5        # full working volume; feeding stops here. v0 == vmax is a
                     # plain batch (no feed) reactor, which is allowed.
    t_end: 48.0      # run length, hours
    x0: 0.2          # inoculum biomass, g/L

  cost:
    substrate_usd_per_kg: 0.55        # what you pay for feedstock
    reactor_usd_per_L_h: 0.045        # vessel occupancy: capital, utilities, labour
    downstream_base_usd_per_kg: 46.0  # recovery cost at the reference titer below
    downstream_reference_titer_g_L: 40.0
    target_usd_per_kg: 200.0          # the price you need to beat

  batch_size: 4      # how many designs to recommend
  seed: 0            # same seed, same answer
"""


def starter_yaml() -> str:
    """A commented project file to edit.

    The comments are the deliverable, not decoration: this is where a reader who does
    not write Python learns what the fields mean, so keep them explanatory and keep
    the honest caveats (hand-entered pathway features, a vessel that is not theirs)
    where they cannot be missed.
    """
    return STARTER
