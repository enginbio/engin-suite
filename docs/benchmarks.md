# Benchmarks

## Real data first

Real-data validation has landed, so the numbers that matter lead:

| | synthetic (tier 1) | **real, 406 industrial batches (tier 3)** |
|---|---|---|
| R² | 0.96 | **0.12** |
| split-conformal coverage | 0.96 | **0.886** |
| what it establishes | the loop runs | the calibration transfers |

```bash
cd packages/engin-core
python benchmarks/benchmark.py               # synthetic
python benchmarks/benchmark.py --data real   # 406 industrial batches
```

The `cd` is load-bearing and was missing here until 2026-08-13: the script lives
in the package, not at the repository root, so the command as previously printed
failed with `No such file or directory` for anyone who copied it.

**Every run states which data it used in its first line of output.** That is the
point of the flag. The gap between those two columns is the honest summary of
this project: an R² of 0.96 against our own simulator says the code runs; an R²
of 0.12 against a working plant says the modelling does not yet transfer, while
the coverage says the *calibration* does.

A number quoted without saying which column it came from is close to meaningless,
and it is the easiest number in this project to quote carelessly.

Full real-data results: [Calibration on real production
data](methods/real-data-calibration.md).

## Baselines: what runs, and what is still a plan

The commitment is that every claim is benchmarked against the simpler approach it
says it beats. **This table used to be written as though that had been done.** It
had not, and the distinction is now in the table itself:

| Engin component | Baseline | Status |
|---|---|---|
| Next-experiment recommendation | random batch of the same size | **implemented** — synthetic only |
| Process optimization | response surface methodology (fitted quadratic) | **implemented** — synthetic only |
| Optimizer | an off-the-shelf Bayesian optimization library (BayBE, Ax) | not built |
| Techno-economics | BioSTEAM | not built |
| Pathway ranking | step-count heuristic | not built |
| Host selection | "use *E. coli*" | not built |

## Engin loses to response surface methodology

This is the result the page exists to be able to report, so it goes above the
wins rather than below them.

Given the same 70-run training split and the same noisy observations, a textbook
second-order response surface — intercept, linear, quadratic and two-factor
interaction terms, fitted by ordinary least squares — proposes **better designs**
than Engin's GP with expected improvement.

| over 20 seeds | best-true-titer lift | forecast R² |
|---|---|---|
| RSM optima | **+21.3%** | 0.955 |
| Engin (GP + EI) | +15.9% | 0.962 |
| random batch | −24.5% | — |

**RSM wins on 18 of 20 seeds**, mean gap +5.4 percentage points with a standard
error of 0.75 — about seven standard errors, so this is not seed noise. The two
tie on forecast accuracy. Both beat random on 20 of 20.

### Its intervals are also better than ours here

The obvious defence would be that Engin trades optimization for *honest
uncertainty*. Measured, that defence does not hold on this problem either.

| over 20 seeds, nominal 0.90 | coverage | mean interval width |
|---|---|---|
| Engin, split-conformal | 0.960 | 16.2 g/L |
| **RSM, OLS prediction interval** | **0.887** | **13.8 g/L** |

RSM's textbook interval — `ŷ ± t·s·√(1 + leverage)`, carrying observation noise
so the comparison is like for like — lands closer to nominal than ours and is
**17% narrower**. Engin over-covers by six points and charges width for it. <!-- not-a-claim: both measured on our own simulator, same 20 seeds -->

**This was predicted to go the other way, and it is recorded because it didn't.**
The expectation was that an OLS interval, assuming its model class is correct,
would under-cover. On a smooth five-dimensional mechanistic surface the quadratic
*is* close to the right model class, so the assumption holds and the model-based
interval is efficient precisely when it should be.

Which is the same thing [the conformal page](methods/conformal-calibration.md)
already says about the Gaussian interval: it *happens* to work here, for reasons
it cannot check. The argument for conformal was never that the alternative fails
always — it is that the alternative fails **without warning** when its assumption
breaks, and reports the same nominal level either way.

**So the test that would actually settle this has not been run.** Fit both inside
the training region, then query outside it, and see which interval notices. The
[out-of-distribution page](methods/out-of-distribution.md) does exactly that for
the GP alone; extending it to RSM is the missing measurement, and until it exists
this project cannot claim its calibration is better than a response surface's —
only that it is differently derived.

### Two things that cut against reading the optimization result as decisive — and neither rescues it

**This simulator is RSM's home ground.** Five continuous knobs, a smooth
mechanistic surface, no discrete choices and no plateaus. A quadratic is close to
the right model class here, which is exactly the condition under which decades of
practice say to use one. The comparison would look different on a rugged or
higher-dimensional surface, and that is a claim this project cannot currently
test.

**One round favours pure exploitation.** RSM goes straight to its predicted
optimum. Expected improvement deliberately spends part of its batch on
uncertainty it expects to pay back *in later rounds* — and this benchmark scores
one round, so EI pays the cost and never collects. Sequential RSM (steepest
ascent, refit, re-centre) versus multi-round EI is the fair fight, and it is
[not built](https://github.com/enginbio/engin-suite/issues/20).

Neither caveat changes what is published today. The claim on the front page is
**fewer DoE rounds**; measured over one round against the method practitioners
actually use, Engin is behind. Anyone evaluating this project should know that
before they read the calibration results, which is why it is here and not in a
footnote.

Nothing here has been compared to BayBE or to BioSTEAM on any data, and none of
these comparisons has been run on real data.

**Correcting this cost the page its best-sounding paragraph, which is the right
trade.** A benchmarks page that overstates its own coverage is worse than one
with gaps, because the gaps are recoverable and the credibility is not. Building
the first of those baselines then cost the page a win, which is the same trade a
second time.

The work has been tracked the whole time, as
[#20](https://github.com/enginbio/engin-suite/issues/20), which names these same
five baselines. The roadmap knew; this page did not say so.

**Cases where a baseline wins are published in the same table as the wins.** A
benchmark suite that always favours its author is not evidence.

Each result records the dataset version and random seed that produced it, so a
third party can reproduce it exactly. Coverage of calibrated intervals is tested
in continuous integration; a change pushing empirical coverage outside tolerance
fails the build.

## Datasets: fetched, never shipped

`engin_core.datasets` obtains real data. **Engin ships no datasets and will not**,
and the reason is licensing rather than repository size: several of the most
useful public fermentation datasets are NonCommercial or NoDerivatives, while
Engin is Apache-2.0 and its users are commercial by assumption. Vendoring one, or
deriving a shipped default from it, would hand every downstream user a licence
restriction they never agreed to.

That is easy to state and easy to forget under deadline, so it is enforced in
code rather than left as a convention — `fetch("indpensim")` raises:

```text
PermissionError: 'indpensim' is licensed CC-BY-NC-ND-4.0, which does not permit
commercial use and/or derivatives. Engin is Apache-2.0, so its users are
commercial by assumption, and a default path built on this data would hand them
a licence restriction they never accepted (D12).
  You may still fetch it for your own evaluation by passing
  accept_noncommercial=True, which records that the decision was yours.
```

The refusal is not paternalism about your own research — one argument overrides
it. It is that nothing *inside* Engin may quietly build on such data, and a test
asserts that no module in the package ever passes that flag.

### The provenance manifest

Every fetched file gets a JSON manifest beside it recording the source URL, the
digests observed at download time, whether they matched what the registry expected,
the licence, the citation, and a UTC timestamp. A published number can then be
traced to a specific byte sequence obtained on a specific day — which is what
makes a benchmark checkable by someone who has no reason to trust you.

A checksum mismatch deletes the file rather than warning about it. Benchmarking
against a download that failed verification is worse than not benchmarking.

### What is registered

| Dataset | Licence | Tier | What it is |
|---|---|---|---|
| `erythromycin-efp` | CC-BY-4.0 | 3 | 406 industrial fed-batch production batches, hourly, with a product-potency target |
| `cho-k1-cultivations` | CC-BY-4.0 | 3 | 24 CHO-K1 cultivations, batch and fed-batch, 38 inline + 10 offline variables |
| `indpensim` | CC-BY-NC-ND-4.0 | 2 | the worked example of the licence problem — **fetch refuses it** |

Adding an entry means checking the licence against the publisher and recording a
checksum that is either the publisher's own or verified against it. An unverified
entry is worse than an absent one, because it looks authoritative.

**On checksums, against the usual advice: md5 is often the right one to record.**
What provenance needs is a match against the value *the publisher published* —
that is what detects a file being swapped, truncated or quietly revised. A sha256
computed by whoever added the entry proves only that the bytes have not changed
since *they* downloaded it: a weaker claim wearing a stronger algorithm. Zenodo
publishes md5, so md5 is usually the checkable value, and insisting on sha256
would mean downloading 227 MB — or IndPenSim's 2.5 GB — to produce a digest
nobody can check you against.

Worth being precise about IndPenSim, since it is often described loosely: a
**simulation validated against industrial data**, not measurements from a real
plant. That places it at `D12` tier 2 — evidence a method is not overfitted to
our own model's quirks — rather than tier 3.

See [Limitations](limitations.md) for current validation status.
