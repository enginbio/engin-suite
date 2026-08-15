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
| Multi-round optimization campaign | sequential RSM (Box–Wilson: steepest ascent, central composite, re-centre) | **implemented** — synthetic only |
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

### Two things that cut against reading this as decisive — and neither rescues it

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
ascent, refit, re-centre) versus multi-round EI is the fair fight. **It has since
been built, and it did not rescue us either** — see the next section.

Neither caveat changes what is published today. The claim on the front page is
**fewer DoE rounds**; measured over one round against the method practitioners
actually use, Engin is behind. Anyone evaluating this project should know that
before they read the calibration results, which is why it is here and not in a
footnote.

## The fair fight: several rounds, one budget — and RSM still wins

The second caveat is a real objection, and the comparison that answers it is the
one [PR #113](https://github.com/enginbio/engin-suite/pull/113) deliberately did
not build. It is built now, and it does not go our way either.

Every method starts from the **same 40-run initial DoE** — identical designs,
identical noisy observations — and then gets **10 rounds of 8 runs**: 120 runs
each. Equal budget is the entire point of the exercise. Eight bioreactors a
round, ten rounds, for everybody.

```bash
cd packages/engin-core
python benchmarks/benchmark.py --multi-round
```

Three arms, two of them the baseline:

- **Engin.** Fit the GP on everything observed so far, take eight designs by
  expected improvement, observe, refit, repeat.
- **Sequential RSM.** Box–Wilson as it is actually practised: a two-level
  fractional factorial in a region of interest around the current operating
  point, a first-order fit for the gradient, runs along the path of steepest
  ascent, re-centre on the best of them, and — when the ascent stops improving —
  augment to a central composite design, fit the full second-order model over the
  region and go to its stationary point. The designs come from the NIST/SEMATECH
  handbook's catalogue rather than being improvised: for five knobs in eight runs
  that is the $2^{5-2}_{III}$ fraction, generators $D = AB$ and $E = AC$, and the
  star points are face-centred because the knobs have hard operating limits.
- **Single-shot RSM, iterated.** The one-round baseline from the section above,
  refit on everything and re-run each round. Not Box–Wilson, but it is the
  obvious way to make the published baseline multi-round, and reporting it
  removes the objection that the sequential implementation was a weak version of
  RSM.

The sequential arm is reported at the region half-width that does best, swept
across the full admissible range and printed in full by the script — tuning the
baseline upward is the only direction it is safe to tune in.

### The result

| round | runs each | Engin (GP+EI) | sequential RSM | single-shot RSM | best RSM − EI | RSM wins |
|---|---|---|---|---|---|---|
| 1 | 48 | +26.6 ± 3.2 | +34.2 ± 3.5 | +33.3 ± 3.5 | +7.7 ± 0.9 | 20/20 |
| 2 | 56 | +29.7 ± 3.4 | +34.2 ± 3.5 | +33.9 ± 3.5 | +4.8 ± 0.5 | 20/20 |
| 3 | 64 | +30.4 ± 3.3 | +34.2 ± 3.5 | +33.9 ± 3.5 | +4.0 ± 0.4 | 20/20 |
| 4 | 72 | +30.9 ± 3.4 | +34.3 ± 3.5 | +34.0 ± 3.5 | +3.6 ± 0.2 | 20/20 |
| 5 | 80 | +31.1 ± 3.4 | +34.3 ± 3.5 | +34.0 ± 3.5 | +3.4 ± 0.1 | 20/20 |
| 6 | 88 | +31.1 ± 3.4 | +34.3 ± 3.5 | +34.0 ± 3.5 | +3.4 ± 0.1 | 20/20 |
| 7 | 96 | +31.2 ± 3.4 | +34.3 ± 3.5 | +34.0 ± 3.5 | +3.3 ± 0.1 | 20/20 |
| 8 | 104 | +31.2 ± 3.4 | +34.4 ± 3.5 | +34.1 ± 3.5 | +3.4 ± 0.2 | 20/20 |
| 9 | 112 | +31.2 ± 3.4 | +34.5 ± 3.5 | +34.1 ± 3.5 | +3.4 ± 0.2 | 20/20 |
| 10 | 120 | +31.2 ± 3.4 | +34.5 ± 3.5 | +34.1 ± 3.5 | +3.5 ± 0.1 | 20/20 |

Best-true-titer lift over the best run of the shared initial DoE, mean ± standard
error over 20 seeds. Round 0 is the shared initial DoE and is identical for all
three by construction. The gap and the win count are against whichever RSM arm is
ahead **on that seed and that round**, which is an oracle over the two baselines
and generous to them on purpose.

**There is no crossover, on either reading of the word.** RSM leads the mean at
every one of the ten rounds, and it wins on **20 of 20 seeds at every round** —
not 18 of 20 as in the single-round comparison, but 20 of 20, ten times over. A
mean that crossed while a third of the seeds still disagreed would not be a
crossover, so the benchmark reports both readings separately. Neither crosses.

**EI's exploration does pay back — partially, and not nearly enough.** The gap
narrows from 7.7 percentage points after one round to 3.5 after ten. That is the
shape the caveat predicted, and it is the part of the defence that survives. It
simply never reaches zero: the narrowing stops after round five, and the gap
settles between 3.3 and 3.5 points for the rest of the campaign, against a
standard error of 0.1. That is not seed noise.

The tightness of the gap is itself worth reading. The lift varies a great deal
from seed to seed — the ±3.4 and ±3.5 on the three lift columns — while the
*paired* gap between the methods on the same seed barely varies at all. Which
seeds are easy is a property of the draw; who wins is a property of the method.

**The round-1 gap here is not comparable to the 5.4 points in the single-round
table.** Different experiment: a 40-run initial design rather than a 70-run
training split, and lift measured against the best of 40 runs rather than 120.
The two numbers are not two measurements of one quantity, and reading them as a
trend would be wrong.

### What multi-round evidence settles, and what it does not

**Settled.** The exploration-repayment defence of the single-round result is
tested and does not hold on this simulator. It was the better of the two caveats
— it named a specific mechanism and predicted a specific shape — and the
mechanism is visibly there in the narrowing gap while the conclusion it was
offered to support is not. That defence should not be made again without new
evidence.

**Not settled: the other caveat, which is now doing all the work.** This is still
Engin's own simulator — `D12` **tier 1**, five continuous knobs and a smooth
mechanistic surface, which is the condition a quadratic is built for. Every
number on this page above the real-data table is a statement about our own model,
not about a fermenter. The multi-round comparison cannot be run on the 406
industrial batches at all: an adaptive campaign has to be able to query a design
point nobody ran, and a fixed dataset cannot answer. That is a property of the
comparison, not a gap in the dataset registry, and no dataset available today
would close it.

**Not settled: whether a local method needed more rounds.** The sequential RSM is
reported at the region half-width that performs best, swept across the full
admissible range and printed in full by the script. That best setting turns out
to be the widest one — a region covering the whole design space, which makes
Box–Wilson behave much like the global fit. The genuinely *local* settings are
slower and had not converged when the budget ran out: at half-width 0.10 the
campaign is still climbing at round ten, having reached +29.1 from +14.0. On a
longer horizon the local variant might overtake the global one. It would still be
RSM overtaking RSM.

**Not settled: anything about the tool's own settings.** The sweep tunes the
baseline. There is no corresponding sweep over EI's exploration parameter, the
GP's kernel or the batch diversity radius, and there should not be one — tuning
the opponent upward is the only direction that is safe to tune in.

The single-round numbers above stay exactly as they were. They were not wrong,
and a result that later gets more context is not a result that gets edited.

Nothing here has been compared to BayBE or to BioSTEAM on any data, and none of
these comparisons has been run on real data.

**Correcting this cost the page its best-sounding paragraph, which is the right
trade.** A benchmarks page that overstates its own coverage is worse than one
with gaps, because the gaps are recoverable and the credibility is not. Building
the first of those baselines then cost the page a win, which is the same trade a
second time. Building the follow-up that was supposed to explain the loss away
confirmed the loss instead — the same trade a third time, and the cheapest of the
three, because the alternative was leaving a defence standing that we had reason
to doubt and had not tested.

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
