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

See [Limitations](limitations.md) for current validation status.
