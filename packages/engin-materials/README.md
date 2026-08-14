# engin-materials

**Rank biomaterial formulations by predicted property, with a calibrated interval.**
Plan 15 — the materials cousin of metabolic route ranking, built on the same
[`engin-graph`](../engin-graph) engine with a different featurization.

## Why it's the same problem

The formulator's default tool is a **composition average**: take the weighted mean of
your monomer descriptors and rank by that. It's blind to two things that matter —
*where* the weak unit sits, and the **topology** (crosslinking), which isn't
composition at all. A graph model sees both.

### Which of those two actually earns the win

The extraction was motivated by the first one: a chain fails where it's weakest, just
as a metabolic route is tanked by one uphill step, and min-pooling preserves exactly
that. **Measured on the synthetic model, that isn't what's doing the work here**
(Spearman ρ, 500 formulations):

| weakest_link | topology | graph | composition | isolates |
|---|---|---|---|---|
| 0.0 | 0.0 | 0.969 | **1.000** | neither — baseline is correct, and wins |
| 0.9 | 0.0 | 0.505 | 0.502 | **weakest-link only — a tie** |
| 0.0 | 0.25 | **0.678** | 0.590 | topology only |
| 0.9 | 0.25 | **0.512** | 0.436 | both |

With topology switched off, the graph model ties the heuristic even when the property
is almost entirely weakest-link driven. The whole edge comes from **topology**.

The likely reason: a composition average over a variable-length chain already
correlates strongly with that chain's minimum, so min-pooling adds little the mean
hadn't already implied. Metabolic routes may differ — there the worst step is a sharp
thermodynamic cliff rather than a draw from the same distribution as its neighbours.

### How much of that is a finding, and how much is the generator

**Checked 2026-08-13 for issue #88, and the table above says less than it first
appears.** The ground truth in `PropertyModel.raw` is

```
value = (1 - topology_weight) * structural + topology_weight * topo
```

where `topo` depends on crosslink density alone, and a composition average is blind to
it *by construction* — the source comment there says as much. So the only part of the
target where a graph model **can** beat the baseline is the topology term, and turning
`topology_weight` up makes it win exactly there. That is a correct check that the
implementation recovers a signal it ought to recover. **It is not a discovery about
materials.** The weakest-link rows read the same way: both models see the same
per-unit features, which is a simpler explanation than min-pooling being redundant.

**The field's evidence also points the other way on the general claim.** Comparing
descriptor-based and graph-based models across 11 public datasets and 8 algorithms,
[Jiang et al. (2021)](https://doi.org/10.1186/s13321-020-00479-8) conclude that
"descriptor-based models outperform the graph-based models in terms of prediction
accuracy and computational efficiency". A graph model earning its keep is the
exception in that literature, not the default.

So the claim this package makes is now the narrow one: **the engine recovers
connectivity signal that a composition average cannot see, in a domain that has such
signal.** Whether real biomaterial properties have it in the amount this simulator
assumes is untested here — and on the balance of published evidence, a descriptor
baseline deserves to be beaten before a graph model is preferred.

*This section previously read: "it says the graph engine transfers to domains where
topology carries signal, which is a narrower and more useful claim than 'domains with
a worst part.'" The narrowing was real. It was not narrow enough.*

## Use it

```python
from engin_materials import PolymerRanker, composition_scores, make_dataset, true_property

data = make_dataset(400, seed=1)
ranker = PolymerRanker().fit(data[:250]).calibrate(data[250:320])

scores = ranker.predict(data[320:])
lo, hi = ranker.predict_interval(data[320:])
```

## How thin it is

This package is a schema, a synthetic generator, and ~70 lines of ranking glue.
Everything that does the modelling — message-passing embedder, min/max pooling,
conformal ranking head, ranking metrics — comes from `engin-graph` unchanged, the same
code `engin-pathway` runs on. `Polymer` satisfies `engin_graph.GraphLike` structurally
via `node_features()` and `graph()`, so no adapter was needed.

If this file list ever grows thick, the shared-engine thesis is failing.

## Honest status: M0, and a probe

Everything here runs on a **synthetic** structure→property model: weakest-link
dominated, with a non-monotone crosslink-density term (crosslinking helps, then
embrittles). It is a mechanistic caricature — no real chemistry, no processing
history, no assay-specific saturation.

The shortlist is blunt about the commercial read, and it hasn't changed: **niche
buyers, slow and wet validation.** This package exists to prove the graph edge
*transfers* cheaply, not because materials is a lead bet. Treat a good number here as
evidence about the engine, not about the market.

**M1** would be real public bio-polymer datasets. Note that validation in this domain
is genuinely slow — the Plan 4 vitamin-vs-painkiller risk applies with force.

## Kill criteria (from the shortlist)

Niche buyers plus slow wet validation → keep exploratory. Do not over-invest ahead of
a demand signal.

## License

Apache-2.0.
