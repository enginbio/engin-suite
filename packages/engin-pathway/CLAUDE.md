# engin-pathway — manufacturability ranking (stage [3])

Graph-ML ranking of metabolic routes by predicted manufacturability, with
calibrated intervals. M0 light path: **networkx** (route graphs), **numpy**
(random-weight message passing — the M0 stand-in), **scikit-learn** (ridge head),
**scipy.stats** (Spearman), **pydantic** (schemas), **engin-core** (shared
conformal). Part of the engin-suite monorepo.

## Layout
- `src/engin_pathway/schema.py` — pydantic `Step`, `Route` (+ networkx graph builder).
- `src/engin_pathway/simulate.py` — synthetic route generator; **worst-step-dominated**
  ground-truth manufacturability. Bespoke by design; M1 replaces it with real routes.
- `src/engin_pathway/embed.py` — message-passing GCN embedder (mean/max/min pooling).
  **Random-weight (untrained) — the M0 stand-in for a trained PyG GNN.**
- `src/engin_pathway/rank.py` — ridge head + split-conformal (via `engin_core`) +
  Spearman eval + step-count baseline + best-route regret.
- `examples/run_demo.py`, `tests/`.

## Principles
- **Rank, don't just find.** The wedge is manufacturability ranking above FBA
  feasibility / step-count. Always report against the **step-count** baseline.
- **Structure over length.** The signal step-count misses is the worst step;
  max/min-pooling must stay in the embedding.
- **Calibrated intervals** via the suite's shared conformal (engin-core), so the
  vocabulary matches host and process.
- **M0 is honest about being untrained.** The GCN weights are random; don't dress
  the stand-in up as a trained model. M1 = trained **PyG** GNN + **COBRApy**/
  **eQuilibrator** real routes; keep the route-as-graph interface stable so the
  swap is local to `embed.py`.

## Dev
```bash
pip install -e "packages/engin-core[dev]" -e "packages/engin-pathway[dev]"
pytest -q
ruff check .
python examples/run_demo.py
```
