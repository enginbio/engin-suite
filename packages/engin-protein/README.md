# engin-protein

**One calibrated engine, three faces of the protein design cycle.** Plans 2, 5, and 9 from the
venture shortlist are not three companies — they are the same GP + Expected-Improvement +
conformal-interval loop pointed at a fitness landscape instead of fermentation knobs.

## The wedge

Protein campaigns share the shape the rest of the [engin suite](https://github.com/enginbio/engin-suite)
serves: **few measurements, expensive assays, irreversible commitments.** A model that is 5% more
accurate doesn't change what you order next. A model that says *"82% chance this variant clears your
threshold, here's the batch that most reduces your uncertainty, and here's what's driving it"* does.

| Face | Plan | Question it answers |
|---|---|---|
| `evaluate` | 2 | Which of these designs are actually worth ordering? |
| `lown` | 5 | I have 40 assay points. What do I test next? |
| `planner` | 9 | Run my whole campaign — batches, transfer across projects |

Built as one package because they share a featurizer, an engine, and an uncertainty vocabulary.
Splitting them would mean maintaining three copies of the same calibration story.

## Use it

```python
from engin_protein import Campaign, LowNCopilot, make_landscape

landscape = make_landscape(length=20, epistasis=0.5, seed=0)
campaign  = landscape.sample_campaign(n=40, seed=1)

copilot = LowNCopilot().fit(campaign)
batch   = copilot.recommend(landscape.library(200, seed=2), k=8)   # what to order next
```

Every prediction carries an interval or a probability. There are no naked point estimates in the
public API — that's a suite-wide rule, not a stylistic preference.

## Honest status: M0

**This package is at M0: everything runs on a synthetic fitness landscape, not real assay data.**
The landscape is an additive + pairwise-epistatic model with a tunable `epistasis` knob, which is
enough to prove the loops work and to show each face beating its baseline. It is *not* evidence
about real proteins.

Two claims specifically that M0 **cannot** support, and which the plan's kill criteria turn on:

- **`evaluate` beating pLDDT/ipTM.** The baseline here is a *simulated* confidence signal, built to
  correlate with foldability but only weakly with function — which is what the literature reports
  about the real thing. Beating it on a landscape constructed that way tests the plumbing, not the
  hypothesis. The real test needs held-out wet data (M1).
- **`lown` beating single-round design.** M0 shows it on a landscape whose epistasis we chose. Real
  campaigns get to pick their own.

Read the numbers as "the loop is wired correctly and calibrated," nothing more.

## Kill criteria (from the shortlist, verbatim in spirit)

- If function-aware ranking can't beat pLDDT/ipTM on held-out wet data, the `evaluate` value prop
  fails.
- If low-N can't beat single-round on <100 points, reposition.
- Cradle owns the funded low-N lane. `lown` wins only on the genuinely-low-N regime plus price.
- BayBE owns generic Bayesian optimization, open source. `planner` differentiates on
  biology-specific priors or it doesn't differentiate.

## Featurization and the light path

Default is **one-hot + physicochemical descriptors** — no downloads, no PyTorch, runs anywhere. That
keeps the suite's light-default-path rule (ADR 0002) intact.

For real work you want PLM embeddings (ESM-class) or structure-derived features. Rather than pulling
that dependency in, `PrecomputedFeaturizer` accepts an embedding matrix you computed however you
like. The engine never learns which featurizer produced its inputs.

## Milestones

- **M0** *(here)* — synthetic landscape with tunable epistasis; all three faces beat their baselines,
  calibrated coverage asserted in tests.
- **M1** — real ProteinGym / public DMS sets, PINDER, Adaptyv open competition results. Report
  wet-correlation where public wet data exists. This is where the kill criteria actually get tested.

## License

Apache-2.0.
