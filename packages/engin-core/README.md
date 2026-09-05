# engin-core

Open toolkit for fermentation scale-up: a mechanistic fed-batch **simulator**, a
Gaussian-process **titer model** with **conformally calibrated** uncertainty, an
active-learning **next-batch recommender**, and reproducible **benchmarks**.
Built on mature libraries — scipy (integration), scikit-learn (GP), MAPIE
(conformal) — with only the domain models hand-written.

Part of the [engin-suite](../../README.md) strain-to-scale monorepo.

## Why

Most bioprocess optimizers give point predictions or intervals that quietly lie.
The trap is easy to fall into: form a 90% interval from the model's uncertainty
alone and assume normality, and it covers only ~55% of held-out runs — badly <!-- not-a-claim: measured on our own simulator; pinned in the calibration tests -->
overconfident. engin-core forecasts titer with **honest** coverage and recommends
the runs worth doing next.

Calibrated uncertainty is the whole point of the wedge: a scale-up decision needs
`P(hit $/kg target)`, not a number with no error bar.

## Install

```bash
pip install engin-core        # on PyPI as of 0.1.1; add the [cli] extra for the engin-process script
```

Pre-1.0 — pin an exact version. For development, install editable from a checkout
of the monorepo:

```bash
git clone https://github.com/enginbio/engin-suite
cd engin-suite
pip install -e "packages/engin-core[dev]"
```

## Quickstart

```python
import numpy as np
from engin_core import (
    simulate_unit, fit_gp, split_conformal_multiplier,
    cross_validated_r2,
    recommend_batch, ard_importance, unit_to_physical,
)

rng = np.random.default_rng(0)
U = rng.random((120, 5))                       # unit-cube DoE (5 design knobs)
y = simulate_unit(U)                            # titer (g/L) from the simulator

tr, ca, te = slice(0, 70), slice(70, 100), slice(100, 120)
gp = fit_gp(U[tr], y[tr])                        # fit the GP titer model

# Calibrate a 90% interval on a held-out set (split conformal):
mc, sdc = gp.predict(U[ca])
q90 = split_conformal_multiplier(y[ca], mc, sdc, level=0.90)

mean, sd = gp.predict(U[te])                     # forecast: mean ± q90*sd is a 90% PI
X_next, m_next, sd_next, ei = recommend_batch(gp, float(y[tr].max()), k=8)
print("recommended next runs (physical units):\n", unit_to_physical(X_next))
# Before quoting the ARD readout, ask whether the model learned anything at all:
# on a response unrelated to the design it still names a "top" knob (#309).
evidence = cross_validated_r2(U[tr], y[tr])
print(f"cross-validated R2: {evidence:+.2f}")
if evidence > 0:
    print("titer drivers (ARD):", np.round(ard_importance(gp), 2))
else:
    print("no usable signal — the ARD shares would describe noise")
```

**Running this in a loop?** `recommend_batch` draws a fresh candidate pool on each
call, because `seed` defaults to `None` (ADR 0011). Pass `seed=<int>` when you want
a bit-reproducible recommendation — but pass a *different* one each round, not a
fixed one, or every round searches the same fixed set of candidate points and the
campaign converges to the best point in that set rather than the best design.

Full end-to-end demo (writes plots, a DoE CSV, and a DoE round-reduction memo):

```bash
python examples/run_demo.py
```

## What's in the box

| Module | What it does |
|---|---|
| `engin_core.simulator` | Fed-batch Monod/Luedeking-Piret bioreactor with product inhibition — a non-monotonic titer landscape with a real interior optimum. Bespoke *equations*, integrated by scipy `solve_ivp` (piecewise across the feed/induction switches). 5 knobs: `feed_rate`, `feed_start`, `Sf`, `induction_time`, `S0`. |
| `engin_core.gp` | scikit-learn ARD-RBF Gaussian Process + **split-conformal** (heteroscedastic, sd-scaled) and **MAPIE**-backed interval calibration + `prob_at_least`. |
| `engin_core.recommend` | Expected-Improvement next-batch recommender with a diversity filter. |
| `engin_core.sensitivity` | ARD inverse-lengthscale sensitivity — which knobs actually move titer. |

## The calibration story (why conformal)

A raw GP interval is overconfident here because a space-filling DoE is "easier"
than the future query points the model is asked about (covariate shift), and the
epistemic sd ignores observation noise entirely. Split-conformal calibrates the
interval multiplier on a same-distribution held-out set using the finite-sample
conformal quantile — distribution-free, no normality assumption. The score is the classical
normalized nonconformity measure of Papadopoulos, Gammerman and Vovk —
`|y − ŷ| / σ`, with σ taken from the model's own predictive sd — and the
multiplier form keeps intervals riding the GP's per-point sd.

This is related to, but not the same as, MAPIE's `ResidualNormalisedScore`, which
estimates σ with a *separate learned model* fitted to log-residuals. Normalizing
by the GP's own sd needs no second model, which matters at the sample sizes this
targets.

Reproduce (`python benchmarks/benchmark.py`, mean over 20 seeds):

| 90% interval built from… | Coverage (target 0.90) |
|---|---|
| epistemic-only, Gaussian ×1.645 | **0.59** — naive, overconfident (seed-dependent; read as ~0.55–0.62) |
| total (model + noise), Gaussian ×1.645 | 0.86 — assumes normality, drifts per seed |
| total, split-conformal ×q90 | **0.96** — honest |

## Benchmarks

`python benchmarks/benchmark.py` (mean over 20 seeds, held-out):

- Forecast: **RMSE ≈ 3.8 g/L**, **R² ≈ 0.96**. <!-- not-a-claim: our own benchmark on our own simulator -->
- Calibration: see table above.
- Active-learning lift (best true titer of an 8-run batch vs the best true titer
  in the initial DoE): **EI ≈ +18%** vs **random ≈ −23%** — one recommended batch <!-- not-a-claim: our own benchmark on our own simulator -->
  moves the frontier; a random batch does not.

The single-seed `examples/run_demo.py` slice: R² 0.97, RMSE ~4 g/L, `feed_rate` <!-- not-a-claim: output of a script in this repository -->
the dominant driver, and one active-learning round lifting best titer +28% <!-- not-a-claim: output of a script in this repository -->
(86→110 g/L). <!-- not-a-claim: output of a script in this repository -->

## Development

```bash
pip install -e ".[dev]"
pytest            # tests
ruff check .      # lint
```

## License

Apache-2.0. Patent grant included, matching the BayBE/BioSTEAM ecosystem.
