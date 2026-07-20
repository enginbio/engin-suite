# engin-suite

The open **strain-to-scale** engine for fermentation biomanufacturing. De-risk
each decision in the funnel — **pick the host → rank the pathway → optimize the
process** — with *calibrated uncertainty* rather than point guesses.

> The closed differentiators (probabilistic techno-economics, cross-process
> priors, partner data) live in a private overlay that depends on this suite.

## The funnel

```
  target molecule + constraints
            │
   [4] host-selection   ──►  chosen chassis (+ why, + confidence)      engin-host
            │
   [3] pathway-ranking  ──►  routes ranked by manufacturability ± CI   engin-pathway
            │
   [1] fermentation     ──►  titer forecast ± CI + next-batch + TEA    engin (+ engin-core)
            │
        scale-up decision
```

Each stage hands its decision **and its uncertainty** to the next; all are thin
domain layers over one shared engine, `engin-core`.

## Packages

- **engin-core** — fed-batch simulator (scipy), scikit-learn GP with conformal
  calibration (split-conformal + MAPIE), Expected-Improvement recommender, ARD
  sensitivity. The honest-uncertainty engine.
- **engin-host** — chassis selection: multi-criteria scoring over a capability KB
  with uncertainty and hard-constraint flags.
- **engin-pathway** — graph-ML manufacturability ranking of metabolic routes *(planned)*.

## Why calibrated uncertainty

Form a 90% interval from model uncertainty alone and assume normality: it covers
~55% of held-out runs. Split-conformal restores ~96% honest coverage,
distribution-free. Every scale-up decision needs `P(hit target)`, which is only
meaningful if the intervals are calibrated.

## Links

- [Source & README](https://github.com/enginbio/engin-suite)
- Package quickstarts and benchmarks are in each `packages/*/README.md`.
