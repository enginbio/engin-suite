# engin-pathway

Metabolic route **manufacturability ranking** — **stage [3]** of the
[engin-suite](../../README.md) strain-to-scale funnel. Rank candidate routes to a
target by predicted manufacturability (not just feasibility), with a calibrated
interval, so a team spends its foundry cycles on the routes most likely to hit titer.

## Why

Route-finding tools exist (novoStoic, RetroBioCat, RetroPath) and FBA predicts
*feasibility* well — but it does **not** predict titer. The whitespace isn't
finding routes; it's **ranking** them by manufacturability. A single toxic or
thermodynamically-uphill step tanks a route, and step-count is blind to it.

## What it does

- represents each route as a **graph** (networkx) of enzymatic steps with goodness
  features (thermodynamics, enzyme availability, cofactor balance, toxicity, expression);
- embeds it with a **message-passing GCN** whose max/min-pooling captures the *worst
  step* — the structural signal step-count misses;
- predicts manufacturability with a ridge head and a **split-conformal** interval
  (reusing `engin_core`'s calibration), and **ranks** routes;
- is measured against the honest baseline it must beat: step-count.

## Results (synthetic routes, `python examples/run_demo.py`)

- Manufacturability forecast (held-out): **R² 0.73**, RMSE 0.05, **90% coverage 0.88**.
- Ranking: **Spearman ρ 0.85** (graph model) vs **0.51** (step-count).
- Best-of-6-route selection: regret-vs-oracle **0.008** (model) vs **0.074**
  (step-count) — roughly **9× lower** regret. <!-- not-a-claim: measured against this package's own synthetic generator, so it is a fact about this repository; whether it transfers to real routes is #124 -->


## Quickstart

```python
from engin_pathway import make_dataset, PathwayRanker, labels, spearman

data = make_dataset(500, seed=1)
ranker = PathwayRanker(lam=1.0).fit(data[:320])
ranker.calibrate(data[320:410], level=0.90)

test = data[410:]
pred = ranker.predict(test)                 # ranking scores
lo, hi = ranker.predict_interval(test)      # calibrated 90% interval
print("Spearman vs truth:", spearman(pred, labels(test)))
```

## Status & roadmap

M0 (this package): a **random-weight** GCN + ridge + conformal beats step-count on
**synthetic** routes. The weights are untrained — a deliberate stand-in.

**M1** swaps in a *trained* GNN on **PyTorch Geometric**, real routes from
KEGG/MetaCyc/BiGG via **COBRApy**/networkx, and ΔG node features from
**eQuilibrator**. The route-as-graph interface stays the same, so the upgrade is
local to `embed.py`. Titer-ranking validation needs wet outcomes (M3, via the
suite and partners).

## Install

```bash
pip install -e "packages/engin-pathway[dev]"   # from an engin-suite checkout
```

Apache-2.0.
