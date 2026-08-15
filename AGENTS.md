# AGENTS.md

Context for AI coding agents. Deliberately short — the 2026 research on repository guidance found that minimal, precise, human-written files help while comprehensive generated ones **reduce** task success rates and raise inference cost. If you're tempted to expand this file, don't.

## What this is

Engin turns a handful of fermentation runs into a calibrated titer forecast, a recommendation for what to run next, and a probabilistic cost-per-kilogram read that accounts for downstream recovery. Open source, Apache-2.0, monorepo publishing separate PyPI packages.

## Setup

```bash
pip install -r requirements-dev.txt          # whole monorepo, editable
cd packages/engin-core && pytest             # tests run per package
ruff check . && ruff format --check .        # from the repo root
```

There is no root *package* — `pip install -e ".[dev]"` will not work, because a root
package would declare the sub-packages as dependencies and pip would look for them on
PyPI, where they are not published yet.

Test suites do **not** require the install: each package's pytest `pythonpath` lists
the sibling sources it imports, so a bare checkout works. CI additionally builds
wheels and re-runs every suite against the installed distribution.

## Layout

```
packages/engin-core/      engine: GP + conformal calibration, EI recommender,
                          fed-batch simulator, inter-stage handoff contracts
packages/engin-graph/     shared graph engine: embedder + conformal ranking head
packages/engin-host/      chassis selection
packages/engin-pathway/   metabolic route ranking (thin layer over engin-graph)
packages/engin-protein/   protein design cycle: eval / low-N / planner
packages/engin-materials/ structure-property ranking (thin layer over engin-graph)
packages/engin-core/benchmarks/   reproducible, includes losses
docs/                     currently a minimal Pages site
```

**Not yet built**, though documents here describe them as goals: the TEA head and
ingest layer (`D8`, `D11`), and the Sphinx documentation site with executed
examples (`D15`, `D20`). Don't assume they exist.

## Before working an issue: claim it

Several agents work this repository concurrently. **Read an issue's comments before starting.** A comment saying someone is on it means it's taken — pick another. No such comment means it's free, but leave one saying you're starting *before* you begin, so the next agent sees the claim instead of racing you. If you stop without finishing, say so in a follow-up.

## Before changing anything: read DECISIONS.md

Several choices in this codebase look like bugs and are not. They're recorded with reasoning in `DECISIONS.md` and cited by ID in code and issues. **If a change would contradict a decision, raise it in an issue rather than "fixing" it.**

The ones most likely to be mistaken for defects:

- **`D13` — the recommender will optimize net $/kg, not titer.** Titer is inflatable by running longer, and omits raw material cost, which dominates COGS and is governed by yield. Engin will look *worse* on the metric everyone reports; that is deliberate. **Not yet implemented** — `engin_core.recommend` maximizes titer, because the techno-economic head it needs (`D8`) does not exist. Don't mistake the current behaviour for the intended design, and don't entrench it. Note the justification changed on 2026-08-10: the earlier "recovery cost rises with titer" mechanism was backwards and is withdrawn.
- **`D12` — benchmarks report real-data results including where coverage degrades**, and publish out-of-distribution failures. Do not substitute synthetic-data numbers because they look better.
- **`D14` — library, not framework.** Stable public API, no hidden coupling, usable as a dependency. Don't add framework-shaped machinery.
- **`D4` — there is no CLA, on purpose.** Don't add one as standard hygiene. DCO sign-off (`git commit -s`) only.
- **`D11` — no bespoke data container.** Use xarray and pandas with the documented convention. Don't introduce a custom type for run data.
- **`D9` — compose, don't reimplement.** BayBE, BioSTEAM, COBRApy, MAPIE. Don't rebuild what they do.

## Conventions

- Calibrated uncertainty is a first-class deliverable. No point estimate ships without an honest interval, and coverage tests must stay green.
- Every model is reported against the simpler baseline it claims to beat. Cases where a baseline wins get published in the same table.
- Documentation examples are *intended* to run in CI (`D15`); the Sphinx site that would do that is not built yet. When it lands, a broken example must fail the build — don't disable execution to get a build through.
- Warnings are errors once the docs build exists (`-W`, `nitpicky`). Fix the cause, don't relax the setting.

## Boundaries

- Don't add anything on the declined list in `BIOSECURITY.md`.
- Don't commit data files. Benchmarks fetch; they don't vendor. Some upstream datasets are NC/ND licensed and cannot ship here.
- **`engin_core.fit_gp` is for low-dimensional continuous design spaces.** Its ARD kernel is
  initialised for unit-cube inputs and collapses to the prior mean on high-dimensional sparse
  features such as one-hot sequences. Bring a different estimator and feed its `(mean, sd)` to the
  shared conformal and acquisition primitives, which are estimator-agnostic.

  This is a fact about *that kernel*, not about Gaussian processes. Purpose-built GP approaches for
  protein fitness exist — a zero-shot predictor as the prior mean with a dedicated substitution
  kernel — and have not been evaluated here. Ridge on one-hot features is a well-established strong
  few-shot baseline, so `engin-protein` using it is defensible; treating it as the ceiling is not.

## Where things are written down

| | |
|---|---|
| Why a choice was made | `DECISIONS.md` |
| How to contribute | `CONTRIBUTING.md` |
| Governance, maintainership | `GOVERNANCE.md` |
| Dual-use position and declined scope | `BIOSECURITY.md` |
| API stability and deprecation | planned — `docs/api-stability.md` |
| What's planned | the public project board |
