# engin-suite

The open **strain-to-scale** engine for fermentation-based biomanufacturing:
de-risk each decision in the funnel — **pick the host → rank the pathway →
optimize the process** — with *calibrated uncertainty* rather than point guesses.

This is a monorepo of the open (Apache-2.0) suite. The closed differentiators
(probabilistic techno-economics, cross-process priors, partner data) live in a
separate private overlay that depends on these packages.

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
- **Open-core discipline** — the engine, simulators, and calibration are public
  here; cross-process priors, partner data, and the economics coupling stay
  private.
- **Stand on mature libraries** — scipy (integration), scikit-learn/GPyTorch (GP),
  MAPIE (conformal), pydantic (schemas). Hand-write only the domain models.

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
