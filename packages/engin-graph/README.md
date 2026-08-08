# engin-graph

**Graph embedding + calibrated ranking over structured objects.** The shared graph engine of the
[engin suite](https://github.com/enginbio/engin-suite) — extracted from `engin-pathway` so that any
domain whose objects are graphs can rank candidates with an honest interval, not just metabolic
routes.

## The problem it solves

Several domains have the same shape: you have many candidate *structures*, you can only test a few,
and the thing that decides quality is often a **single bad part** rather than an average. Metabolic
routes are tanked by one thermodynamically-uphill step. Polymers are tanked by one weak bond. A
mean-pooled representation smooths exactly the signal that matters.

`engin-graph` gives you a message-passing embedding with **min/max pooling** (so the worst node
survives into the representation), a ridge head, and a **split-conformal interval** reusing
`engin_core` — so every domain in the suite speaks the same calibrated-uncertainty vocabulary.

## Use it

```python
from engin_graph import GraphRanker, best_of_k_regret, spearman

ranker = GraphRanker(d_in=5, lam=1.0, embed_seed=0)
ranker.fit(train_objects, train_labels)
ranker.calibrate(cal_objects, cal_labels, level=0.90)

scores = ranker.predict(test_objects)
lo, hi = ranker.predict_interval(test_objects)
```

Any object works as long as it exposes `node_features() -> (n_nodes, d_in)` and
`graph() -> nx.Graph`. That's the `GraphLike` protocol; pass a custom `GraphFeaturizer` if your
objects expose something else.

## What's in it

| Piece | What it does |
|---|---|
| `GraphFeaturizer` / `GraphLike` | The protocol: domain object → node features + graph |
| `GCNEmbedder` | 2-layer message-passing GCN, mean/max/**min** pooling |
| `ConformalRankingHead` | Ridge on the embedding + split-conformal interval |
| `GraphRanker` | The two composed — the usual entry point |
| `spearman`, `best_of_k_regret` | Ranking metrics, for reporting against a baseline |

## Milestone status

**M0.** The GCN weights are **random and untrained** — a random-weight GCN plus a ridge head
captures graph structure with zero backprop, which is enough to prove a ranking loop beats its
domain baseline. This is a deliberate stand-in, not an oversight: pulling PyTorch for an untrained
model would violate the suite's light-default-path rule (ADR 0002).

**M1** swaps in a trained GNN on PyTorch Geometric behind an optional extra. The
object-as-graph interface stays the same, so domain layers won't change.

Do not read M0 ranking numbers as a claim about real-world accuracy.

## Consumers

- `engin-pathway` — metabolic route manufacturability (stage [3])
- `engin-materials` — structure → property *(planned)*

## License

Apache-2.0.
