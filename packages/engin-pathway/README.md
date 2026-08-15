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
  (step-count) — roughly **9× lower** regret. <!-- not-a-claim: measured against this package's own generator, so it is a fact about this repository -->

### How much of that is a finding, and how much is the generator

**Audited 2026-08-15 for issue #124, and the "beats step-count" line above says
less than it first appears.** Same shape as #88 in `engin-materials`, and the
numbers are kept with the caveat rather than deleted, for the same reason.

`make_dataset` produces both the routes and their labels, and `simulate.py:37`
builds the label as

```
manuf = (0.6 * worst_step + 0.4 * mean_step) * 0.96 ** (length - 2)
```

**Step-count sees only `length`.** So its score is not a result — it is a fixed
property of the generator, and no length-only heuristic can beat it. Over 2000
routes: the worst-step term carries r² 0.81 of the label, the length term 0.12,
and step-count's ceiling is ρ ≈ 0.41.

The decisive check is that the margin moves with the constants. Relabel the
**same routes** with the length base at 0.70 instead of 0.96 and **step-count
rises to ρ 0.95 while the worst-step signal falls to 0.31** — the ranking flips
with nothing about either method changed. Reproduce with
`python benchmarks/generator_audit.py`.

So the claim this package makes is the narrow one: **the graph model does recover
a worst-step signal that a length heuristic is blind to.** That is a correct check
that the implementation recovers a signal it ought to recover. **It is not a
discovery about metabolic routes.**

Whether real routes are worst-step dominated is an empirical question this package
has not touched. It is a design assumption of the generator — stated plainly in
its docstring, and defensible, since a toxic intermediate or a thermodynamic wall
does plausibly tank a route — but assumed, not measured. M1's real routes from
KEGG/MetaCyc/BiGG are what would test it.

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
