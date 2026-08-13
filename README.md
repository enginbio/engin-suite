# engin-suite

The open **strain-to-scale** engine for fermentation-based biomanufacturing:
de-risk each decision in the funnel — **pick the host → rank the pathway →
optimize the process** — with *calibrated uncertainty* rather than point guesses.

This is a monorepo of the open (Apache-2.0) suite, and there is no closed
counterpart holding the interesting parts back. Probabilistic techno-economics
ships here in `engin_core.tea` (`D8`); everything methodological is public
(`D1`). A private overlay exists for hosted-service plumbing and any future
partner data under NDA — nothing methodological, and no partner data yet.

```
  target molecule + constraints
            │
   [4] host-selection   ──►  chosen chassis (+ why, + confidence)      engin-host
            │
   [3] pathway-ranking  ──►  routes ranked by manufacturability ± CI   engin-pathway
            │
   [1] fermentation     ──►  titer forecast ± CI + next-batch + TEA    engin (+ engin-core)
            │
        scale-up decision
```

Each stage hands its decision **and its uncertainty** to the next. All stages are
thin domain layers over one shared engine, `engin-core`.

## Packages

| Package | Stage | What it is | Status |
|---|---|---|---|
| [`engin-core`](packages/engin-core) | — | Shared engine: fed-batch simulator (scipy), scikit-learn GP with conformal calibration (split-conformal + MAPIE), Expected-Improvement recommender, ARD sensitivity. | ✅ working |
| [`engin-host`](packages/engin-host) | [4] | Host/chassis selection: multi-criteria scoring over a capability KB, with uncertainty and hard-constraint flags. Depends on `engin-core`. | ✅ working |
| [`engin-pathway`](packages/engin-pathway) | [3] | Graph-ML manufacturability ranking of metabolic routes (beats step-count; calibrated). Depends on `engin-core`. | ✅ working (M0) |

## Design principles (suite-wide)

- **Calibrated uncertainty is first-class** everywhere — no naked point estimates;
  conformal coverage stays honest.
- **Honest baselines** — every model is reported against the dumb heuristic it
  claims to beat (naive Gaussian intervals, random batches, step-count ranking,
  "just use E. coli").
- **Everything methodological is public** — engine, simulators, calibration and
  the economics coupling alike (`D1`, `D8`). There is no held-back core. The only
  thing that could sit outside this repository is partner data under NDA, which
  does not exist yet.
- **The objective is net $/kg, not titer** (`D13`) — titer captures one of three
  cost centres, and which one dominates is a property of the product: downstream
  processing is reported at 45–92% of production cost for biopharmaceuticals
  against 20–40% for bulk fermentation products, where raw material takes the
  larger share instead (Straathof 2011). <!-- ref: 2011-straathof-downstream-costs -->
  Titer is also inflatable by running
  longer, and says nothing about the raw-material cost that *yield* governs.
  *(Corrected 2026-08-13: this read "recovery cost is determined upstream but
  incurred downstream, so an optimizer maximizing titer can move the true
  objective backwards" — a mechanism `D13` withdrew as backwards on 2026-08-10.)*
  **The accepted
  consequence is that Engin will look worse on the metric everyone reports**, and
  it is better to say so here than to let it be discovered in a benchmark table.
  `engin_core.tea.recommend_batch_by_cost` optimizes cost;
  `engin_core.recommend_batch` optimizes titer and is kept for comparison.
- **Stand on mature libraries** — scipy (integration), scikit-learn (GP),
  MAPIE (conformal), pydantic (schemas), BioSTEAM (techno-economics, optional
  extra). Hand-write only the domain models. *(Corrected 2026-08-13: this listed
  GPyTorch, which is not a dependency and is imported nowhere — the same
  overclaim fixed on the docs front page in #95.)*

## Develop

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e "packages/engin-core[dev]" -e "packages/engin-host[dev]" -e "packages/engin-pathway[dev]"
pytest packages/                 # all packages
ruff check .
```

## License

Apache-2.0 (see [LICENSE](LICENSE)). The private product overlay is proprietary.

## Project documents

| | |
|---|---|
| [DECISIONS.md](DECISIONS.md) | Why choices were made. **Canonical** — cited by ID (`D13`) in code and issues |
| [GOVERNANCE.md](GOVERNANCE.md) | How decisions get made, maintainership, succession |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute, and what gets rejected |
| [BIOSECURITY.md](BIOSECURITY.md) | Dual-use assessment and declined scope |
| [SECURITY.md](SECURITY.md) | Software vulnerability disclosure |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Conduct expectations and reporting |
| [AGENTS.md](AGENTS.md) | Context for AI coding agents |
