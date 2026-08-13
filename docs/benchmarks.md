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
| Process optimization | plain design-of-experiments / response surface methodology | not built |
| Optimizer | an off-the-shelf Bayesian optimization library (BayBE, Ax) | not built |
| Techno-economics | BioSTEAM | not built |
| Pathway ranking | step-count heuristic | not built |
| Host selection | "use *E. coli*" | not built |

So the one head-to-head that exists is expected-improvement against random, on
the simulator, and it is reported in the run above. Nothing here has been
compared to DoE/RSM, to BayBE, or to BioSTEAM on any data — synthetic or real.

**Correcting this cost the page its best-sounding paragraph, which is the right
trade.** A benchmarks page that overstates its own coverage is worse than one
with gaps, because the gaps are recoverable and the credibility is not.

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
