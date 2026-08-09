# engin-protein — build log

## [2026-08-07] Session 1 — M0, three faces on a synthetic landscape

Phase 1a of the synergy plan: Plans 2, 5, and 9 built as one package with three faces
(`DesignEvaluator`, `LowNCopilot`, `CampaignPlanner`) rather than three products. Followed
`routines/add-a-new-package.md` from the wiki step by step; 58 tests, ruff clean, CI wired.

### Three things the plan got wrong, found by measuring

**1. The GP head doesn't work here.** The plan specified "`engin_core` GP head + EI acquisition +
`split_conformal_multiplier`." `fit_gp` builds an ARD-RBF kernel initialized at `length_scale=0.3`
over a unit cube — right for six continuous fermentation knobs, wrong for a few hundred sparse
binary sequence features, where typical pairwise distances are ~10× the length scale so every point
looks infinitely far from every other and predictions collapse to the mean. Measured (Spearman ρ,
60-variant campaign):

| epistasis | additive ridge | GP, best config |
|---|---|---|
| 0.0 | 0.942 | 0.423 |
| 0.5 | 0.508 | 0.100 |
| 0.8 | 0.292 | 0.104 |

Switched to ridge with a bootstrap ensemble for spread. **The engine is still reused where it
matters** — `split_conformal_multiplier`, `prob_at_least`, and `expected_improvement` are all
estimator-agnostic and all used unchanged. The shared asset is the uncertainty vocabulary, not the
regressor. Worth an ADR; `fit_gp`'s docstring does say "unit-cube design points," so the contract
was documented and I violated it.

**2. The first synthetic landscape was unlearnable.** Initially generated free 20-mers over all 20
residues — a space of 20²⁰, where 42 training points teach nothing, and the model scored at chance
while looking broken. Real campaigns explore a *combinatorial library*: site-saturation at a handful
of designable positions over a reduced alphabet. Rebuilt on that basis (8 sites × 8 residues ≈ 16.7M
variants) and the loop works. A model can look broken when the benchmark is impossible.

**3. Bagging the mean was pure loss.** Taking the prediction from the bootstrap ensemble cost
ranking accuracy (ρ 0.806 vs 0.873 at e=0) for no benefit — the ensemble is only needed for the
spread, and a full-data fit is available for the mean.

### Honest results (M0, synthetic)

`evaluate` vs the confidence proxy, 80-variant campaign, 300-design library:

| epistasis | model ρ | proxy ρ | model hit@10 | proxy hit@10 | coverage |
|---|---|---|---|---|---|
| 0.0 | +0.806 | +0.586 | 0.60 | 0.30 | 0.997 |
| 0.3 | +0.587 | +0.485 | 0.40 | 0.20 | 1.000 |
| 0.5 | +0.321 | +0.292 | 0.30 | 0.10 | 0.993 |
| 0.8 | +0.208 | +0.036 | 0.20 | 0.00 | 0.987 |

`lown`: EI batch mean 0.631 vs random 0.528 at a 48-variant campaign (+0.103, 6 seeds).
`planner`: best-found 0.858 vs random 0.819 over 3×6 assays (5 seeds).

### What these numbers do not show

- **Nothing about real pLDDT/ipTM.** The proxy is a constructed stand-in built to overlap with
  function without being a transform of it. Beating it shows the loop is wired, not that the wedge
  holds. The kill criterion needs held-out wet data (M1).
- **Rank correlation and hit@10 disagree.** At moderate epistasis the proxy often lands *more* of
  the top-10 (0.50 vs 0.20 on some seeds) while the model ranks the full library better. Both are
  reported because only one is what a buyer experiences. There's a test pinning this.
- **Transfer is not validated.** Mean lift with a similarity-0.9 prior is +0.098, but an
  *unrelated* prior (similarity 0.0) still gives +0.023 — so most of the effect is "more training
  data," not transfer. Cross-project priors are the claimed moat, so this needs a real experiment,
  not a hopeful reading. `transfer_benefit` tests assert structure only, never lift.
- **The additive baseline is strong.** Plain additive ridge beats the calibrated model on ranking
  (0.975 vs 0.873 at e=0) because the faces hold out a calibration split and train on ~70% of the
  campaign. That's the price of an honest interval, and it should be quoted, not tuned away.
- Coverage runs conservative (0.99 vs nominal 0.90): with a small calibration split, split-conformal
  approaches the max residual ratio. Too-wide is the safe direction.

### Design notes

- **Light path held.** Default featurizer is one-hot + physicochemical descriptors — no downloads,
  no PyTorch (ADR 0002). `PrecomputedFeaturizer` covers the PLM case by accepting embeddings
  computed elsewhere, so the heavy dependency never enters this package.
- **Pairwise interaction features are off by default.** They win only at high epistasis (0.313 vs
  0.292 at e=0.8) and lose meaningfully at low (0.816 vs 0.942 at e=0).
- The schema caught a real bug during the build: the planner pooled a seed campaign and a design
  library that both numbered variants from zero, and the uniqueness validator refused it.

**Next:** M1 — ProteinGym / public DMS sets, PINDER, Adaptyv open results. That is where the kill
criteria actually get tested; everything above is plumbing validation.
