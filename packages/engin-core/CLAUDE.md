# engin-core — OSS engine

Open toolkit for fermentation scale-up: a mechanistic fed-batch simulator, a
Gaussian-process titer model with **conformally calibrated** uncertainty, an
active-learning next-batch recommender, and an ARD sensitivity readout. Built on
mature libraries — **scipy** (`solve_ivp`), **scikit-learn** (`GaussianProcessRegressor`),
**MAPIE** (conformal) — with only the domain models (bioreactor equations,
recommender) hand-written. This is the public core; the closed product overlay
(`engin`) layers the TEA head, cross-process priors, ingest, and API on top.

## Layout
- `src/engin_core/simulator.py` — Monod/Luedeking-Piret fed-batch model; scipy
  `solve_ivp`, integrated piecewise across the feed/induction switches.
- `src/engin_core/gp.py` — sklearn GP + split-conformal (sd-scaled) + MAPIE interval
  + OOF calibration + `prob_at_least`. Normal CDF/PDF via `scipy.stats`.
- `src/engin_core/recommend.py` — Expected-Improvement batch recommender.
- `src/engin_core/sensitivity.py` — ARD sensitivity (GP lengthscales).
- `examples/run_demo.py` — end-to-end demo (needs matplotlib).
- `benchmarks/benchmark.py` — reproducible coverage / RMSE / AL-lift, with baselines.
- `tests/` — pytest.

## Principles
- **Calibrated uncertainty is a first-class deliverable.** Never ship point
  estimates without intervals; keep the conformal coverage test green. The
  lesson is settled — the naive *epistemic-only* Gaussian interval is
  overconfident (~0.55 at nominal 0.90) because it ignores observation noise and
  a space-filling DoE is "easier" than future query points (covariate shift);
  split-conformal on a same-distribution calibration set restores honest coverage
  (~0.96). Do not relitigate this.
- **Honest baselines.** Report against the naive-Gaussian multiplier (for
  calibration) and a random batch (for active-learning lift). Never quote a
  headline number without the baseline next to it.
- **Open-core discipline.** Simulator + calibration + BO layer are public here.
  Partner data, the TEA coupling, and cross-process priors stay in the private
  `engin` overlay — do not port them into this package.
- **Stand on mature libraries.** scipy/scikit-learn/MAPIE for the solved wheels;
  hand-write only the domain models. matplotlib is an `examples` extra only.

## Dev
```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q                       # tests
python benchmarks/benchmark.py  # reproducible numbers
python examples/run_demo.py     # end-to-end + plots (needs matplotlib)
ruff check .
```
