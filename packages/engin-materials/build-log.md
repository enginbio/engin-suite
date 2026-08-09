# engin-materials — build log

## [2026-08-07] Session 1 — M0, and the extraction's first real test

Phase 1b: structure→property ranking for biomaterial formulations (Plan 15), built on `engin-graph`.
29 tests, ruff clean, CI wired.

### The extraction paid off

The package is a schema, a synthetic generator, and ~70 lines of ranking glue. Every modelling
component — message-passing embedder, min/max pooling, conformal ranking head, ranking metrics —
comes from `engin-graph` unchanged, the same code `engin-pathway` runs on. `Polymer` satisfies
`engin_graph.GraphLike` structurally through `node_features()` and `graph()`, so **no adapter and no
featurizer subclass were needed**. That was the whole bet of the extraction and it held.

### The finding that corrects this package's own motivation

`engin-graph` was extracted on the argument that these domains are "killed by their worst part," so
min-pooling preserves the signal an averaging heuristic destroys. Materials was supposed to be the
second instance of that pattern.

**Measured, min-pooling is not where the advantage comes from.** Isolating the generator's two
knobs (Spearman ρ, 500 formulations):

| weakest_link | topology_weight | graph | composition | isolates |
|---|---|---|---|---|
| 0.0 | 0.0 | 0.969 | **1.000** | neither — heuristic is correct, and wins |
| 0.9 | 0.0 | 0.505 | 0.502 | **weakest-link only — a tie** |
| 0.0 | 0.25 | **0.678** | 0.590 | topology only |
| 0.9 | 0.25 | **0.512** | 0.436 | both |

With topology switched off, the graph model only *ties* the composition average, even where the
property is almost entirely weakest-link driven. The entire edge comes from **topology** —
crosslinks, which aren't composition at all.

Likely reason: a composition average over a variable-length chain already correlates strongly with
that chain's minimum, so the min-pool adds little the mean hadn't already implied. Metabolic routes
may genuinely differ, since there the worst step is a sharp thermodynamic cliff rather than another
draw from the same distribution as its neighbours — but that is now a hypothesis to check in
`engin-pathway`, not something to assert.

**Why this matters beyond this package:** the graph engine transfers to domains where **topology
carries signal**. That is narrower than "domains with a worst part," and more useful, because it
actually predicts where to point the engine next. Pinned with a test
(`test_the_advantage_comes_from_topology_not_min_pooling`) so it can't drift back into folklore.

### Results (M0, synthetic)

Default setting (weakest_link 0.6, topology 0.25): graph ρ **+0.573** vs composition **+0.505**;
coverage **0.942** against nominal 0.90; lower best-of-1 regret across 8-candidate groups. The
topology signal itself is strong (ρ 0.774 between crosslink density and property) and completely
invisible to the baseline — two formulations with identical composition and different crosslinking
score identically under the heuristic, which is asserted in a test.

### Honest limits

- **Synthetic throughout.** A mechanistic caricature: no real chemistry, no processing history, no
  assay saturation. The crosslink response is non-monotone (helps, then embrittles) because a purely
  monotone one would make a "more crosslinks is better" heuristic sufficient.
- **Still a probe, not a lead bet.** The shortlist's read hasn't changed — niche buyers, slow wet
  validation. A good number here is evidence about the *engine*, not about the market.
- The GCN weights remain random and untrained (M0, ADR 0002).

### Notes

- Negative control included: with both knobs at zero the property *is* the composition average, the
  heuristic scores 1.000, and the graph model correctly does not beat it. A model that won there
  would indicate a leak, not skill.
- The regret test averages over small candidate groups. Top-5-of-120 is trivially solved by both
  rankers (regret 0.0 each), so a single large pool would have let the test pass while measuring
  nothing.

**Next:** M1 would be real public bio-polymer datasets — but per the kill criteria, only if a demand
signal appears first.
