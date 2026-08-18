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
you also cannot tell. The interval keeps reporting 90% either way. <!-- not-a-claim: the nominal level we asked for -->

Split conformal replaces the assumption with a measurement. Hold out a calibration split the model
never trained on, measure how large its residuals *actually* are relative to the
sd it predicted, and take the empirical quantile:

$$q = \text{Quantile}_{1-\alpha}\left(\frac{|y_i - \hat{\mu}_i|}{\hat{\sigma}_i}\right)$$

Then the interval is $\hat{\mu} \pm q\hat{\sigma}$. This is the classical
**normalized** nonconformity measure of Papadopoulos, Proedrou, Vovk and
Gammerman (2002)[^2002-papadopoulos-inductive-confidence] — normalizing by the
model's own predictive sd so the interval stays heteroscedastic, wide where the
model is unsure and narrow where it is confident. The finite-sample guarantee for
the split (inductive) construction is Lei et al. (2018).[^2018-lei-distribution-free]
Engin keeps the thin multiplier form so an interval remains `mean ± q*sd` and can
be read without a library.

[^2002-papadopoulos-inductive-confidence]: Papadopoulos, Proedrou, Vovk & Gammerman, *Inductive Confidence Machines for Regression*, ECML 2002. [doi:10.1007/3-540-36755-1_29](https://doi.org/10.1007/3-540-36755-1_29)
[^2018-lei-distribution-free]: Lei, G'Sell, Rinaldo, Tibshirani & Wasserman, *Distribution-Free Predictive Inference for Regression*, JASA 2018. [doi:10.1080/01621459.2017.1307116](https://doi.org/10.1080/01621459.2017.1307116)

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

## The guarantee is marginal, and that word is doing a lot of work

Added 2026-08-13, during the literature pass for
[#86](https://github.com/enginbio/engin-suite/issues/86). **This page previously
never said it**, which was the most consequential omission in it.

Split conformal guarantees that coverage holds **on average over the joint
distribution of $(X, Y)$**. It does *not* guarantee coverage for any particular
$x$, or for any subgroup you name afterwards. That is the difference between
*marginal* and *conditional* coverage, and conditional coverage is provably
unattainable in a distribution-free setting without further
assumptions.[^2021-angelopoulos-gentle-intro]

Why it matters concretely here: the [out-of-distribution
page](out-of-distribution.md) reports coverage broken down by region — in
distribution, just outside, far outside. **Those are measurements, not the
theorem being honoured region by region.** A reader who takes "90% coverage,
distribution-free" to mean "90% wherever I ask" has been over-promised, and until <!-- not-a-claim: the nominal level we asked for, quoted -->
today this page did nothing to stop that reading.

The honest statement is narrower and still worth having: *averaged over the query
distribution the calibration set was drawn from*, the interval covers at its
nominal rate, without assuming normality.

[^2021-angelopoulos-gentle-intro]: Angelopoulos & Bates, *A Gentle Introduction to Conformal Prediction and Distribution-Free Uncertainty Quantification*, arXiv:2107.07511 (2021).

## How big does the calibration set have to be

Added 2026-08-17 for
[#144](https://github.com/enginbio/engin-suite/issues/144). The page above
measures coverage on a calibration set of 30 and reports it as working. That is
true on average and incomplete: **coverage is a random quantity**, and 30 points
buy a noisy draw from it.

Conditional on the calibration set, coverage is Beta
distributed,[^2012-vovk-conditional-validity]

$$P\big(Y_{\text{test}} \in C(X_{\text{test}}) \mid \{(X_i, Y_i)\}_{i=1}^{n}\big)
  \sim \mathrm{Beta}(n + 1 - l,\; l), \qquad l = \lfloor (n+1)\alpha \rfloor$$

The nominal level is that distribution's *mean*. Any particular calibration set
lands somewhere in its spread:

```{code-cell} python
from engin_core import conformal_coverage_interval, smallest_calibration_set

print(f"  floor for a {NOMINAL:.0%} interval: n = {smallest_calibration_set(NOMINAL)}\n")
for n in (9, 20, 30, 50, 100, 406, 1000):
    lo, mean, hi = conformal_coverage_interval(n, level=NOMINAL)
    print(f"  n = {n:>4}   coverage {lo:.3f} to {hi:.3f}   (mean {mean:.3f})")
```

Two things that table makes concrete.

**There is a floor, and below it the guarantee is not merely weak but absent.**
The method takes the $\lceil (n+1)(1-\alpha) \rceil$-th smallest calibration
score, so that index has to exist: $n \geq \text{level} / (1 - \text{level})$,
which is 9 at 90% and 99 at 99%.[^2018-lei-distribution-free] Below it
`split_conformal_multiplier` falls back to the largest observed score — the
widest interval those points justify, but not the requested level. **That
fallback used to be silent.** It now warns, which is the substance of #144.

**Even above the floor, small is expensive.** At the floor itself a "90%"
interval has a true coverage somewhere around 0.72 to
0.99,[^2012-vovk-conditional-validity] which is close to no statement at all.
The industrial set used in the
[quickstart](../quickstart.md) has 406 calibration points and earns a genuinely
tight band. A first fermentation campaign has neither, and that gap is the honest
reason this page's numbers should not be read as transferring to a new user's
first dozen runs.

Note the spread is quoted on **coverage**, not on the multiplier $q$ itself. The
result is about coverage; converting it into an interval on $q$ would need a
distributional assumption about the scores, which is the assumption split
conformal exists to avoid.

[^2012-vovk-conditional-validity]: Vovk, *Conditional validity of inductive conformal predictors*, PMLR 25:475–490 (2012). The same paper's Proposition 2a gives a PAC-type bound, $E \geq \epsilon + \sqrt{-\ln\delta / 2n}$; it is Hoeffding-based and markedly more conservative than the exact Beta result used here.

## What this does not establish

```{warning}
Split conformal's guarantee assumes **exchangeability** between the calibration
and test sets — and covariate shift is exactly a violation of that assumption. So
conformal is not a proof of correctness here; it is a substantially better
empirical estimate that happens to be conservative on this problem.

This is not a gap in the literature, only in what this page can claim: the
covariate-shift case has a weighted-conformal treatment,[^2019-tibshirani-covariate-shift]
and the general non-exchangeable case has bounds on the coverage
gap.[^2023-barber-beyond-exchangeability] **Engin implements neither.** It uses
unweighted split conformal and reports where that degrades, which is a weaker
position than the field's and is stated rather than obscured.
```

[^2019-tibshirani-covariate-shift]: Tibshirani, Foygel Barber, Candès & Ramdas, *Conformal Prediction Under Covariate Shift*, NeurIPS 32 (2019). [arXiv:1904.06019](https://arxiv.org/abs/1904.06019)
[^2023-barber-beyond-exchangeability]: Barber, Candès, Ramdas & Tibshirani, *Conformal prediction beyond exchangeability*, Annals of Statistics 51(2) (2023). [doi:10.1214/23-aos2276](https://doi.org/10.1214/23-aos2276)

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
