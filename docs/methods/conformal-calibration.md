---
file_format: mystnb
kernelspec:
  name: python3
  display_name: Python 3
  language: python
---

# Conformal calibration, and the covariate shift underneath it

Engin's central claim is a titer forecast with an **honest** interval on it. This
page shows what "honest" costs, because the obvious way to build that interval is
wrong by a wide margin, and the way it is wrong is a trap most people meet
eventually rather than a quirk of this codebase.

Every number below is computed when these docs are built. Nothing here is quoted
from a previous run.

```{code-cell} python
import numpy as np
from scipy.stats import norm

from engin_core.gp import fit_gp, split_conformal_multiplier
from engin_core.simulator import simulate_unit

GAUSS_90 = norm.ppf(0.95)   # ±1.645 sd, the textbook 90% Gaussian interval
NOMINAL = 0.90

def campaign(seed, n=120, d=5):
    """A space-filling DoE with heteroscedastic observation noise."""
    rng = np.random.default_rng(seed)
    U = rng.random((n, d))
    y_true = simulate_unit(U)
    y_obs = np.maximum(y_true + rng.normal(0, 0.05 * y_true + 0.4), 0.0)
    return U, y_obs
```

## Three intervals, one of which works

Split into train / calibrate / test, fit the GP on train, and compare three ways
of turning its posterior into a 90% interval.

```{code-cell} python
def coverages(seeds):
    epistemic, gaussian, conformal = [], [], []
    for seed in seeds:
        U, y = campaign(seed)
        tr, ca, te = slice(0, 70), slice(70, 100), slice(100, 120)
        gp = fit_gp(U[tr], y[tr], seed=seed)

        # calibration split -> one multiplier, from residuals the model never saw
        mc, sdc = gp.predict(U[ca], include_noise=True)
        q = split_conformal_multiplier(y[ca], mc, sdc, level=NOMINAL)

        m_noise, sd_noise = gp.predict(U[te], include_noise=True)
        m_epi,   sd_epi   = gp.predict(U[te], include_noise=False)
        err_noise = np.abs(m_noise - y[te])
        err_epi   = np.abs(m_epi - y[te])

        epistemic.append(np.mean(err_epi   <= GAUSS_90 * sd_epi))
        gaussian.append( np.mean(err_noise <= GAUSS_90 * sd_noise))
        conformal.append(np.mean(err_noise <= q * sd_noise))
    return epistemic, gaussian, conformal

seeds = range(6)
epistemic, gaussian, conformal = coverages(seeds)

for name, cov in (
    ("epistemic-only Gaussian", epistemic),
    ("Gaussian, noise included", gaussian),
    ("split conformal", conformal),
):
    print(f"  {name:26s} {np.mean(cov):.3f}   (nominal {NOMINAL})")
```

**The first row is the trap.** A GP's `predict` returns the uncertainty *about
the mean function* — epistemic uncertainty. Reach for it, multiply by 1.645, call
it a 90% interval, and it covers barely more than half the time. It is not
slightly optimistic; it is wrong by roughly a third of the probability mass, and
it looks completely reasonable while being so.

The reason is that it answers a different question. Epistemic sd asks *where is
the true mean?* A forecast interval has to answer *where will the next
measurement land?*, which also has to carry observation noise. Including the
noise term (row two) fixes most of it.

## Why conformal, when row two already looks fine

Read the second row honestly: on this simulator, adding the noise term gets
coverage to nominal. It would be overclaiming to say the Gaussian interval is
broken once the noise is included — on this problem it is not.

The argument for conformal is not that row two fails here. It is that row two
*happens* to work here for reasons it cannot check. It assumes residuals are
Gaussian with exactly the sd the model claims — and that sd comes from
hyperparameters fitted on a small design, so it is an estimate standing in for a
guarantee. When the assumption holds you cannot tell, and when it stops holding
you also cannot tell. The interval keeps reporting 90% either way.

Split conformal replaces the assumption with a measurement. Hold out a calibration split the model
never trained on, measure how large its residuals *actually* are relative to the
sd it predicted, and take the empirical quantile:

$$q = \text{Quantile}_{1-\alpha}\left(\frac{|y_i - \hat{\mu}_i|}{\hat{\sigma}_i}\right)$$

Then the interval is $\hat{\mu} \pm q\hat{\sigma}$. This is the classical
**normalized** nonconformity measure (Papadopoulos, Gammerman and Vovk),
normalizing by the model's own predictive sd so the interval stays
heteroscedastic — wide where the model is unsure, narrow where it is confident.
Engin keeps the thin multiplier form so an interval remains `mean ± q*sd` and can
be read without a library.

```{code-cell} python
U, y = campaign(0)
tr, ca = slice(0, 70), slice(70, 100)
gp = fit_gp(U[tr], y[tr], seed=0)
mc, sdc = gp.predict(U[ca], include_noise=True)
q = split_conformal_multiplier(y[ca], mc, sdc, level=NOMINAL)

print(f"  Gaussian multiplier : {GAUSS_90:.3f}")
print(f"  conformal multiplier: {q:.3f}")
print(f"  intervals are {q / GAUSS_90:.2f}x wider than the Gaussian interval")
```

That ratio is the price of honesty on this problem, and it is worth stating in
those terms: the calibrated interval is *worse-looking* than the naive one, and
that is the point.

## The covariate shift, which is the part that generalizes

Why should a fitted model's own sd be too small at all?

A design of experiments is deliberately space-filling — spread out, balanced,
chosen to be informative. The points a model is asked about afterwards are not
drawn that way. They cluster where the optimizer is hunting, near the edge of the
region the campaign explored. **The training distribution and the query
distribution differ**, which is covariate shift, and a model evaluated under it is
being asked something harder than it was calibrated on.

This is not specific to bioprocess data or to this GP. Any active-learning or
Bayesian-optimization loop generates its own covariate shift by construction: the
acquisition function's whole job is to propose points unlike the ones already
collected.

## What this does not establish

```{warning}
Split conformal's guarantee assumes **exchangeability** between the calibration
and test sets — and covariate shift is exactly a violation of that assumption. So
conformal is not a proof of correctness here; it is a substantially better
empirical estimate that happens to be conservative on this problem.
```

Two honest caveats, both visible in the numbers above:

**The measured coverage sits above nominal, not on it.** Over-coverage means the
intervals are wider than strictly required — safe, but not free, and not evidence
that the theory's conditions hold.

**The exact figure is seed-dependent, so do not quote one.** Widening the sweep
moves it around:

```{code-cell} python
for label, s in (("6 seeds", range(6)), ("12 seeds", range(12))):
    epi, _, conf = coverages(s)
    print(f"  {label:9s} epistemic-only {np.mean(epi):.3f}   split conformal {np.mean(conf):.3f}")
```

The epistemic-only figure lands somewhere around 0.55–0.62 depending on how many
seeds you average, and a wider sweep of 30 seeds sits in the same band. What is
robust is the **ordering and the magnitude of the failure**, not the third
decimal. Any single number quoted for it — including in this project's own source
comments — should be read as "roughly this", and this page recomputes rather than
repeats.

Above all: **all of this is measured on Engin's own simulator.** Coverage against
the process that generated the data demonstrates that the machinery works. It is
not evidence about real fermentation data, where the shift is larger and less
well behaved. See [Limitations](../limitations.md).

## A cross-check that is not ours

`mapie_split_interval` exposes a [MAPIE](https://mapie.readthedocs.io/)-backed
constant-width split conformal. It is deliberately a *different* method — not
sd-normalized — kept as an independent implementation to check against rather
than a second copy of the same idea.

```{code-cell} python
from engin_core.gp import mapie_split_interval

te = slice(100, 120)
lo, hi = mapie_split_interval(gp, U[ca], y[ca], U[te], level=NOMINAL)
covered = np.mean((y[te] >= lo) & (y[te] <= hi))
_, sd_te = gp.predict(U[te], include_noise=True)
widths = hi - lo
print(f"  MAPIE constant-width coverage: {covered:.3f}")
print(f"  width, narrowest to widest:    {widths.min():.3f} to {widths.max():.3f} g/L")
print(f"  sd-normalized, for comparison: {(2 * q * sd_te).min():.3f} to {(2 * q * sd_te).max():.3f} g/L")
```

Constant width is the giveaway: it cannot be narrow where the model is confident
and wide where it is not. That is why the sd-normalized form is the default here,
with this one kept as the honest baseline.

## Related

- [Limitations](../limitations.md) — what has and has not been validated
- [Benchmarks](../benchmarks.md) — current validation tier
- [Decisions](../decisions.md) — `D15` (executable documentation), `D12` (validation tiers)
