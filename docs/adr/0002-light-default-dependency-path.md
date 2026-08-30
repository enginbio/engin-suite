# 0002 — Light default dependency path

**Status:** Accepted (2026-07-20)

## Context

The prototypes this project grew out of were pure-numpy by necessity — the sandbox they were written
in had no scipy or scikit-learn and no package index, so the GP, conformal calibration, EI
recommender, ODE integrator, ridge head, and GCN were all hand-written.

That was fine for proving loops and bad as a production stance. The port surfaced exactly the class
of bug that libraries exist to prevent: an **EI unit bug** (incumbent passed in standardized units,
EI computed against a physical-unit mean, collapsing the acquisition into pure exploitation) and a
**calibration overstatement** (an epistemic-only interval reported as if it were calibrated, at 0.55
actual coverage against a 0.90 target).

But the obvious correction — adopt GPyTorch/BoTorch/PyG for everything — drags PyTorch into the
default install of a package whose main selling point is that it is easy to try.

## Decision

Stand on mature libraries for solved wheels, but **keep the default install light**: scikit-learn
`GaussianProcessRegressor` + MAPIE + scipy + pydantic. No mandatory PyTorch. Heavy dependencies go
behind optional extras.

Hand-write only what is genuinely domain-specific: the mechanistic bioreactor equations (integrated
with `scipy.solve_ivp`, not a hand-rolled RK4), the host-capability knowledge base and its scoring
semantics, and the synthetic data generators.

## Consequences

- `engin-core` installs in seconds and runs anywhere. That is the adoption path.
- `engin-pathway` ships a **random-weight** GCN rather than pulling torch/PyG for an untrained
  model. A trained PyG GNN is the later upgrade, kept local to `embed.py` behind the
  route-as-graph interface so the swap does not touch the domain layer.
- `recommend.py` keeps hand-written EI — cheap, and correct after the unit fix — rather than moving
  to Ax/BoTorch/BayBE. Revisit if the campaign framing needs transfer learning.
- `engin-host` needed no MCDA library: linear uncertainty propagation is exact for a weighted sum, so
  `scikit-criteria` and `uncertainties` proved unnecessary.
- Cost accepted: some duplication of what a heavier framework would give for free, and a future
  migration if the light path stops scaling.

## Since this was written

- **The original text said heavy heads would be kept behind a private boundary.** That is no longer
  the case and the phrasing has been dropped rather than preserved, because it would contradict
  `D8` — the techno-economic head and downstream-cost model are public — and `D1`. Nothing
  methodological in this project sits behind a boundary.
- The rule has held and has since been applied by the same reasoning to new work: `BioSteamCostModel`
  sits behind a `[tea]` extra, and xarray/pandas/pint behind an `[io]` extra, so neither the
  techno-economics nor the data convention weighs down the default install.
- The related reading named in the original — a dependency survey and a package map — lived in the
  private wiki retired under `D22`. The parts that outlived it are in `DECISIONS.md` (`D9`, compose
  rather than reimplement) and each package's `pyproject.toml`, where the extras are declared with
  comments explaining what is deliberately kept out.
- **2026-08-30 — `pooch` declined for `engin_core.datasets`, on a measurement (#296).** The proposal
  was to hand the download layer to `pooch` rather than maintain retry, caching and checksum logic
  here. Measured with `pip install --dry-run --ignore-installed`, `pooch` pulls **8** packages into
  a bare environment — `requests`, `urllib3`, `certifi`, `charset-normalizer`, `idna`,
  `platformdirs`, `packaging` and itself — and **none** is already provided: `engin-core` resolves
  to 12 packages, and `datasets.py` runs on stdlib `urllib.request`. A 67% increase in install <!-- not-a-claim: our own install, resolved locally; method below -->
  footprint, for the module whose whole job is getting a new user to real data, is the trade this
  ADR exists to refuse. It would not have closed `Range` resume either, which `pooch` does not do.
  Retry with backoff was written here instead, in about fifteen lines.

  **The measurement method is part of the record**, because the obvious version of it is wrong: a
  plain `pip install --dry-run pooch` reports *one* package on a typical developer machine, which
  already has `requests` from something else. `--ignore-installed` is what shows the cost to
  somebody running `pip install engin-core`. Any future dependency argued on install weight should
  be measured that way.

## Related

- [Decisions](../decisions.md) — `D9` (compose, don't reimplement), `D8`, `D1`
- [ADR 0004](0004-hermetic-test-pythonpath.md) — the test topology this packaging implies
