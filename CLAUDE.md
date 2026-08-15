# engin-suite — monorepo

The open (Apache-2.0) **strain-to-scale** suite: de-risk each decision in the
biomanufacturing funnel (host → pathway → process) with calibrated uncertainty.
Public monorepo, and nothing methodological is held back: probabilistic TEA ships
here in `engin_core.tea` (`D8`). A private overlay exists for hosted-service
plumbing and any future partner data under NDA, and holds no methods.

## Before you start work on a GitHub issue: claim it

Several agents work this repository concurrently, so issues are claimed by comment.

1. **Read the issue's comments first.** If one says the issue is being worked on,
   treat it as taken and pick a different one — don't duplicate the work.
2. **No such comment means it's free.** Leave one saying you're starting *before*
   you begin, so the next agent to look sees the claim rather than racing you.

If you stop or hand off without finishing, say so in a follow-up comment. A stale
claim that blocks everyone else is worse than never having claimed it.

## Packages (`packages/`)
- **engin-core** — shared engine: scipy fed-batch simulator, scikit-learn GP with
  conformal calibration (split-conformal + MAPIE), EI recommender, ARD sensitivity.
- **engin-host** — stage [4] chassis selection: pydantic-typed capability KB,
  multi-criteria scoring with uncertainty + hard-constraint flags. Depends on engin-core.
- **engin-pathway** — stage [3] graph-ML manufacturability ranking (networkx GCN +
  ridge + conformal; beats step-count). M0 (random-weight GCN); M1 = trained PyG GNN
  + COBRApy/eQuilibrator. Depends on engin-core.

## Principles (enforced across packages)
- **Calibrated uncertainty is first-class** — no naked point estimates; conformal
  coverage tests stay green.
- **Honest baselines** — every model reported against the dumb heuristic it beats
  (naive-Gaussian intervals, random batches, step-count, "just use E. coli").
- **Everything methodological is public** — engine, simulators, calibration and
  the economics coupling alike (`D1`, `D8`). There is no held-back core, and the
  techno-economic head lives here in `engin_core.tea`. Only partner data under
  NDA could ever sit outside this repository, and none exists. **If a document
  tells you to keep the TEA coupling or priors private, that document is stale.**
- **Stand on mature libraries** — scipy / scikit-learn / MAPIE / pydantic for the
  solved wheels; hand-write only the domain models. Keep a light path (no torch
  required for the default install).

## Dev
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e "packages/engin-core[dev]" -e "packages/engin-host[dev]"
pytest packages/          # all packages
ruff check .
```

## Adding a package
New stages (e.g. engin-pathway) go under `packages/<name>/` with the same shape
(`src/`, `tests/`, `pyproject.toml`, README, CLAUDE.md) and depend on engin-core.
Update the root README table and the CI matrix.
