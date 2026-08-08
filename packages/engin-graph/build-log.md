# engin-graph — build log

## [2026-08-07] Session 1 — extracted from engin-pathway

The refactor prerequisite for the materials cluster: the graph machinery was living inside
`engin-pathway`, and Plan 15 needs the same machinery over a different graph. Extracted rather than
copy-pasted, so the "one engine, many domains" thesis stays literal in the import graph.

**What moved out of `engin-pathway`:**

- `_normalized_adjacency` → `engin_graph.normalized_adjacency`
- `GraphEmbedder` (2-layer message-passing GCN, mean/max/min pooling) → `engin_graph.GCNEmbedder`,
  generalized from a hardcoded `len(FEATURES)` to any `d_in`
- the ridge + split-conformal head out of `PathwayRanker` → `engin_graph.ConformalRankingHead` and
  `GraphRanker`
- `spearman` → `engin_graph.metrics`, joined by `best_of_k_regret` and `mean_regret`

**What was added, not just moved:**

- **`GraphFeaturizer` / `GraphLike` protocols.** The domain boundary is now explicit and is the only
  place a new domain plugs in. `Route` satisfies `GraphLike` structurally via its existing
  `node_features()` / `graph()`, so no adapter was needed — but a domain whose objects look different
  (an RDKit mol, a raw dict) passes a featurizer instead of subclassing anything.
- **`best_of_k_regret`.** Was previously inline in a pathway test. It's the metric that matches how
  the tool is actually used — you get K foundry slots, and what matters is whether the best candidate
  was among them, not the RMSE of the scores.
- **`GCNEmbedder.dim` and `raw_min_block()`.** The pooling order is a public contract that consumers
  index into; the old pathway test hardcoded `[10:15]` to reach the raw-feature min-pool. Those
  offsets shift with `d_in`, so the accessor exists to stop the next domain from hardcoding them.
- Pointed errors on the featurizer path. A bare `AttributeError` sends the reader hunting; the fix is
  "pass a featurizer," so the message says so.

**Verification.** The acceptance bar was `engin-pathway`'s 9 existing tests staying green **without
being modified** — confirmed, `git diff` on its `tests/` is empty. 27 new tests for `engin-graph`.
All suites green with no editable install and no `PYTHONPATH`: engin-core 14, engin-graph 27,
engin-host 12, engin-pathway 9, overlay 4.

**Honest note on the demo numbers.** On the synthetic worst-node domain: Spearman 0.715 for the graph
model vs **0.614** for the node-count baseline; best-of-6 regret 0.0124 vs 0.0360; coverage 0.925
against a nominal 0.90. The baseline is stronger here than in the metabolic case because longer
chains have lower minima, so node count is a real proxy for the worst node rather than a strawman.
The model's edge is genuine but modest, and the test thresholds are set where they won't flake rather
than where they'd look impressive.

**M0 status unchanged.** The GCN weights are still random and untrained — a deliberate stand-in that
keeps PyTorch out of the default install (ADR 0002), not an oversight. M1 swaps in a trained GNN on
PyTorch Geometric behind an optional extra; the object-as-graph interface stays put so domain layers
won't change.

**Next:** `engin-materials` (Plan 15) is now unblocked — it needs a monomer/polymer featurizer and a
property head, and reuses every line of this package.
