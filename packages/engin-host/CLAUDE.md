# engin-host — chassis selection (stage [4])

Multi-criteria host-selection engine over a curated capability KB. Light path:
**pydantic** schemas + **numpy** for the (small) MCDA math + **engin-core** for
the shared uncertainty vocabulary. Part of the engin-suite monorepo.

## Layout
- `src/engin_host/schema.py` — pydantic models: `Host`, `KnowledgeBase`, `HostQuery`, `HostScore`.
- `src/engin_host/kb.py` — the illustrative KB (6 hosts × 9 capabilities = 54 cells; `gras` was a tenth until ADR 0010 retired it). **Illustrative, not sourced yet** (M1 replaces it with cited data).
- `src/engin_host/scoring.py` — weighted MCDA + linear uncertainty propagation + hard-constraint flags + attribution; `prob_meets` via `engin_core.prob_at_least`.
- `src/engin_host/memo.py` — recommendation memo.
- `examples/run_demo.py`, `tests/`.

## Principles
- **Calibrated uncertainty is first-class** — every recommendation carries a band;
  it must widen where the KB confidence is low. (M2 turns this heuristic band into
  a conformal one, reusing engin-core.)
- **Hard constraints demote, never just penalize** — a glyco-incapable prokaryote
  must rank below every feasible host for a glycoprotein target, regardless of score.
- **KB honesty** — values are illustrative until M1; keep confidences truthful so
  the bands don't lie. Don't dress up illustrative numbers as sourced.
- **Light deps** — don't pull a heavy MCDA framework; the weighted sum is trivial.
  pydantic earns its place by validating the KB loudly.

## Dev
```bash
pip install -e "packages/engin-core[dev]" -e "packages/engin-host[dev]"
pytest -q
ruff check .
python examples/run_demo.py
```
