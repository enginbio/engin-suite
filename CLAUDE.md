# engin-suite — monorepo

The open (Apache-2.0) **strain-to-scale** suite: de-risk each decision in the
biomanufacturing funnel (host → pathway → process) with calibrated uncertainty.
Public monorepo; the closed moat (probabilistic TEA, cross-process priors,
partner data) lives in a separate private overlay that depends on these packages.

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
- **Open-core discipline** — engine + simulators + calibration are public here;
  priors, partner data, and the economics coupling stay in the private overlay.
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
