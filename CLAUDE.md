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
Six distributions. Two are shared engines, two are funnel stages, two point the
same machinery at adjacent domains.
- **engin-core** — shared engine: scipy fed-batch simulator, scikit-learn GP with
  conformal calibration (split-conformal + MAPIE), EI recommender, ARD sensitivity.
- **engin-graph** — shared graph engine: embedder + calibrated ranking head over
  structured objects, extracted from engin-pathway. Depends on engin-core.
- **engin-host** — stage [4] chassis selection: pydantic-typed capability KB,
  multi-criteria scoring with uncertainty + hard-constraint flags. Depends on engin-core.
- **engin-pathway** — stage [3] graph-ML manufacturability ranking (networkx GCN +
  ridge + conformal). M0 (random-weight GCN); M1 = trained PyG GNN +
  COBRApy/eQuilibrator. Depends on engin-core, engin-graph.
  **Do not describe this as "beats step-count" without the caveat.** The margin is
  a property of the synthetic generator — relabel with a different length constant
  and step-count wins instead. Audited in #124 / PR #137; the package README carries
  the numbers and what survives.
- **engin-protein** — protein design cycle over the same GP + EI + conformal loop:
  evaluation, low-N campaigns, batch planning. Depends on engin-core.
- **engin-materials** — structure-property ranking for biomaterial formulations,
  with calibrated intervals. Depends on engin-graph.

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
pip install -r requirements-dev.txt    # all six, editable, with dev extras

# Per package, the way CI runs it. `pytest packages/` fails at collection: six
# test basenames repeat across packages, no tests/ has an __init__.py, and each
# package sets its own pytest pythonpath against its own rootdir (ADR 0004).
for p in packages/*/; do
  [ -f "$p/pyproject.toml" ] || continue     # skip stray dirs, as CI does
  ( cd "$p" && python -m pytest -q ) || exit 1
done

ruff check .                           # from the repo root
```

## Adding a package
New stages (e.g. engin-pathway) go under `packages/<name>/` with the same shape
(`src/`, `tests/`, `pyproject.toml`, README, CLAUDE.md) and depend on engin-core —
plus engin-graph if its objects are graphs.

Update the root README table and add the package to `requirements-dev.txt`. You do
**not** update a CI matrix: `.github/workflows/ci.yml` discovers packages with
`for pkg in packages/*/`, deliberately, so a new package cannot be silently
untested. A `lint` step fails the build if `requirements-dev.txt` misses one.
