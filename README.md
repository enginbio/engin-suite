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
| [`engin-graph`](packages/engin-graph) | — | Shared graph engine: embedding + calibrated ranking over structured objects. Extracted from `engin-pathway` so any graph-shaped domain can rank candidates with an honest interval. Depends on `engin-core`. | ✅ working |
| [`engin-host`](packages/engin-host) | [4] | Host/chassis selection: multi-criteria scoring over a capability KB, with uncertainty and hard-constraint flags. Depends on `engin-core`. | ✅ working |
| [`engin-pathway`](packages/engin-pathway) | [3] | Graph-ML manufacturability ranking of metabolic routes, with a calibrated interval. M0 ships a random-weight stand-in, scored against its own synthetic generator. Depends on `engin-core`, `engin-graph`. | ✅ working (M0) |
| [`engin-protein`](packages/engin-protein) | — | Protein design cycle over the same GP + Expected-Improvement + conformal loop: evaluation, low-N campaigns, batch planning. Depends on `engin-core`. | ✅ working |
| [`engin-materials`](packages/engin-materials) | — | Structure-property ranking for biomaterial formulations, with calibrated intervals. Depends on `engin-graph`. | ✅ working |

Not every package is a funnel stage: `engin-core` and `engin-graph` are the shared
engines, and `engin-protein` and `engin-materials` point the same machinery at
adjacent domains.

## Design principles (suite-wide)

- **Calibrated uncertainty is first-class** everywhere — no naked point estimates;
  conformal coverage stays honest.
- **Honest baselines** — every model should be reported against the dumb heuristic
  it claims to beat. **Four of the seven committed baselines are implemented**
  (random batches, response-surface methodology, sequential RSM, step-count
  ranking); BayBE/Ax, BioSTEAM and "just use *E. coli*" are not built yet.
  [Benchmarks](https://docs.engin.bio/en/latest/benchmarks.html) has the table,
  including **the two baselines that beat us** and the one whose margin turned out
  to be a property of its own generator. This bullet was written in the present
  tense as though all of them were done; `docs/benchmarks.md` and `docs/index.md`
  were corrected on that in August 2026 and this one was missed.
- **Everything methodological is public** — engine, simulators, calibration and
  the economics coupling alike (`D1`, `D8`). There is no held-back core. The only
  thing that could sit outside this repository is partner data under NDA, which
  does not exist yet.
- **The objective is net $/kg, not titer** (`D13`) — titer captures one of three
  cost centres, and which one dominates tracks the product's value: downstream
  processing runs 45–92% of production cost for biopharmaceuticals against a
  typical 20–40% for bulk fermentation products, rising with selling price
  (Straathof 2011). <!-- ref: 2011-straathof-downstream-costs -->
  Purity moves it too — crude penicillin G sits near 25%, purified and formulated
  nearer 50–55%. Titer is also inflatable by running
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
pip install -r requirements-dev.txt              # all six, editable, with dev extras

# Tests run per package, the way CI runs them -- not `pytest packages/`, which
# fails at collection: six test basenames repeat across packages and no tests/
# has an __init__.py, so pytest cannot tell them apart. Each package also sets
# its own pytest `pythonpath` (ADR 0004), resolved against its own rootdir.
for p in packages/*/; do
  [ -f "$p/pyproject.toml" ] || continue
  ( cd "$p" && python -m pytest -q ) || exit 1
done

ruff check .                                     # from the repo root
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
