---
file_format: mystnb
kernelspec:
  name: python3
  display_name: Python 3
  language: python
---

# Where the intervals stop holding

[Conformal calibration](conformal-calibration.md) shows the intervals covering at
roughly their nominal rate — and ends by saying that guarantee assumes
exchangeability, which covariate shift violates. This page is what happens when
you violate it on purpose.

Publishing a tool's own failure mode is the highest-trust move available to it,
and it is cheap for us and expensive for a vendor, which is most of why it is
worth doing. Every number below is computed when these docs are built.

```{code-cell} python
import numpy as np

from engin_core.gp import fit_gp, split_conformal_multiplier
from engin_core.simulator import Kinetics, simulate_unit

NOMINAL, D, TRAIN_HI = 0.90, 5, 0.6
SEEDS = range(5)

def observed(U, rng, kinetics=None):
    """Titer with heteroscedastic measurement noise."""
    y = simulate_unit(U, kinetics=kinetics)
    return np.maximum(y + rng.normal(0, 0.05 * y + 0.4), 0.0)

def calibrated_model(seed):
    """Fit and conformally calibrate on the lower 60% of every design axis."""
    rng = np.random.default_rng(seed)
    Utr = rng.uniform(0, TRAIN_HI, (70, D))
    Uca = rng.uniform(0, TRAIN_HI, (30, D))
    gp = fit_gp(Utr, observed(Utr, rng), seed=seed)
    mc, sdc = gp.predict(Uca, include_noise=True)
    q = split_conformal_multiplier(observed(Uca, rng), mc, sdc, level=NOMINAL)
    return gp, q, rng
```

Two things can shift, and they fail differently.

## Shift one: querying outside the design region

The model is trained on the lower 60% of every knob, then asked about designs <!-- not-a-claim: our own experimental design -->
progressively further outside it.

```{code-cell} python
REGIONS = [
    ("in-distribution", 0.0, 0.6),
    ("just outside",    0.6, 0.7),
    ("far outside",     0.9, 1.0),
]

results = {name: [] for name, _, _ in REGIONS}
for seed in SEEDS:
    gp, q, rng = calibrated_model(seed)
    for name, lo, hi in REGIONS:
        U = rng.uniform(lo, hi, (40, D))
        y = observed(U, rng)
        m, sd = gp.predict(U, include_noise=True)
        err = np.abs(m - y)
        results[name].append((np.mean(err <= q * sd), np.mean(2 * q * sd), np.mean(err)))

print(f"  {'region':<17}{'coverage':>9}{'width':>9}{'error':>9}")
for name, vals in results.items():
    cov, width, mae = np.array(vals).mean(axis=0)
    print(f"  {name:<17}{cov:>9.3f}{width:>9.1f}{mae:>9.1f}")
```

**Read the coverage column and you would reach the wrong conclusion.** It dips
where the model is asked just past its training region, then *recovers* far
outside it. Taken alone that says the far field is safe, which is exactly
backwards.

The width column is what makes it legible. Titers on this simulator run around
50 g/L, so an interval that has grown to comparable width or beyond is not a <!-- not-a-claim: this simulator's own titer scale -->
forecast — it is the model declining to answer. Coverage recovers far out
because the intervals become large enough to contain almost anything.

**So coverage alone is not a safety metric.** An interval that always covers is
trivially available: report ±∞. Any coverage number quoted without the width
beside it is close to meaningless, and this page is the reason the
[benchmarks](../benchmarks.md) report both.

The genuinely dangerous zone is the narrow band just past the training data,
where the model is still confident enough to give a usable-looking interval and
already wrong enough to miss.

```{warning}
The mechanism behind that dip is *not* settled here. The obvious story — error
grows faster than the interval near the boundary, then the interval catches up —
appears strongly in some sweeps and weakly in others, so it is reported as an
observation rather than an explanation. What is stable across every sweep run so
far is the shape: a dip just outside, recovery far out, and widths that grow
without bound.
```

## Shift two: a different process

The second axis is the one #12 asks for: train on one process, ask about
another. The design distribution is unchanged; only the underlying kinetics
differ, so the model is being asked about designs it has seen, on a process it
has not.

```{code-cell} python
VARIANTS = {
    "same process":                  Kinetics(),
    "stronger inhibition kp 18->6":  Kinetics(kp=6.0),
    "slower growth mu_max .35->.22": Kinetics(mu_max=0.22),
    "several at once":               Kinetics(kp=8.0, alpha=0.05, mu_max=0.26),
}

print(f"  {'test process':<32}{'coverage':>9}")
for label, kin in VARIANTS.items():
    covs = []
    for seed in SEEDS:
        gp, q, rng = calibrated_model(seed)
        U = rng.uniform(0, TRAIN_HI, (40, D))
        y = observed(U, rng, kinetics=kin)
        m, sd = gp.predict(U, include_noise=True)
        covs.append(np.mean(np.abs(m - y) <= q * sd))
    print(f"  {label:<32}{np.mean(covs):>9.3f}")
```

Here there is no recovery to hide behind. The designs are in-distribution, so
the intervals stay their usual width — and simply miss.

The asymmetry is the useful part: **a change in maximum growth rate costs far
more coverage than a change in product inhibition**, which barely registers.
That is not obvious in advance, and it is the kind of thing worth knowing before
deciding whether a model fit on one process can be pointed at a neighbouring
one. Growth rate rescales the whole trajectory, and with it the titer at every
design; inhibition mostly reshapes the optimum's *location*, which a model
queried across the same design region partly absorbs.

**These are different *processes*, not different organisms.** They are parameter
perturbations of a caricature model, and calling one "a different strain" would
be a claim about biology this simulator cannot support. The magnitude of the
coverage loss here should not be read as a prediction about what happens when a
model trained on *E. coli* meets *Pichia*.

## What to do with this

- **Ask for the width, not just the coverage.** On this evidence, a coverage
  number with no interval width beside it can be produced by a model that has
  stopped saying anything.
- **The edge of the training region is the risk, not the far field.** An
  optimizer proposing points just past the explored boundary — which is exactly
  what acquisition functions do — is operating in the band where these intervals
  are least trustworthy.
- **Refitting matters more than recalibrating when the process changes.**
  Conformal recalibration adjusts a multiplier; it cannot fix a mean function
  fit to different kinetics.

## What this does not establish

```{warning}
**All of this is measured on Engin's own simulator, including the "out of
distribution" part.** A shifted region of the same mechanistic model is a far
gentler shift than a different plant, a different assay, or a different year of
the same process. These numbers characterise a failure mode; they do not bound
how bad it gets on real data.

Doing this properly needs real fermentation data, which is tracked as
[issue #10](https://github.com/enginbio/engin-suite/issues/10) and is the
constraint on the whole validation programme (`D12`).
```

## Related

- [Conformal calibration](conformal-calibration.md) — the in-distribution behaviour this departs from
- [Limitations](../limitations.md) — validation status
- [Benchmarks](../benchmarks.md) — why results report width alongside coverage
