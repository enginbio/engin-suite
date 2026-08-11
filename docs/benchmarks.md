# Benchmarks

```{warning}
Results are not yet published. This page will carry the full table — including
cases where Engin loses — once real-data validation lands.
```

## What will be reported

Every claim is benchmarked against the simpler approach it says it beats:

| Engin component | Baseline |
|---|---|
| Process optimization | plain design-of-experiments / response surface methodology |
| Optimizer | an off-the-shelf Bayesian optimization library |
| Techno-economics | BioSTEAM |
| Pathway ranking | step-count heuristic |
| Host selection | "use *E. coli*" |

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
SHA-256 observed at download time, whether it matched what the registry expected,
the licence, the citation, and a UTC timestamp. A published number can then be
traced to a specific byte sequence obtained on a specific day — which is what
makes a benchmark checkable by someone who has no reason to trust you.

A checksum mismatch deletes the file rather than warning about it. Benchmarking
against a download that failed verification is worse than not benchmarking.

### The registry has one entry, on purpose

[IndPenSim](http://www.industrialpenicillinsimulation.com/) — and it is there as
the worked example of the licence problem rather than as a usable dataset. Adding
an entry means verifying its licence and a checksum yourself; an unverified entry
is worse than an absent one, because it looks authoritative.

Worth being precise about what IndPenSim is, since it is often described loosely:
a **simulation validated against industrial data**, not measurements from a real
plant. That places it at `D12` tier 2 — evidence a method is not overfitted to
our own model's quirks — rather than tier 3. It does not, by itself, close the
real-data gap.

See [Limitations](limitations.md) for current validation status.
