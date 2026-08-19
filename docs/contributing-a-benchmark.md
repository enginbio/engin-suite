# Contributing a benchmark where Engin loses

`CONTRIBUTING.md` names two things that help this project most. One of them —
real fermentation data — is the field's hardest problem and most people cannot
supply it. The other needs a laptop and an afternoon:

> **Benchmarks where Engin loses.** A benchmark suite that always favours its
> author is worthless.

This page is how to actually do that one. It exists because the ask was stated in
prose with no path from the sentence to the machinery
([#241](https://github.com/enginbio/engin-suite/issues/241)).

**The promise first, because it is the reason to bother.** A case where a simpler
method beats Engin gets published in [Benchmarks](benchmarks.md) alongside the
wins. That is not an aspiration — it is what the page already does. Sequential
RSM currently leads Engin at every one of ten rounds and wins on 20 of 20 seeds,
and an off-the-shelf Bayesian-optimization library beats us too. Both are on the
results page, in the same table, above the fold.

## You will need a clone

`benchmarks/` is **not** part of the installed package — setuptools ships only
what is under `src/`, so `pip install` does not give you these scripts. This is
deliberate and worth stating once rather than leaving implicit: they are a
development surface, not an API, and packaging them would freeze their shape.

```bash
git clone https://github.com/enginbio/engin-suite
cd engin-suite
pip install -r requirements-dev.txt
```

## Reproduce a published result first

Start by reproducing something, so you know your environment matches before you
try to beat anything.

```bash
cd packages/engin-core
python benchmarks/benchmark.py               # coverage, RMSE, AL lift
python benchmarks/benchmark.py --multi-round # the RSM comparison
```

The first takes about two minutes, the second about ten.
<!-- not-a-claim: measured on our own machine; yours will differ -->
Every run prints a provenance line — package version, commit, seed range, numpy
version, date — and that line is what makes a number checkable. Quote it when you
report anything.

If your numbers differ from [Benchmarks](benchmarks.md), that is itself worth an
issue. A result that does not reproduce is a defect regardless of which direction
it moves.

## What a baseline actually is

One function. The multi-round comparison drives every arm through the same
signature, in `packages/engin-core/benchmarks/benchmark.py`:

```python
def your_campaign(U0, y0_obs, y0_true, seed, rounds, k) -> list[float]:
    """Best *true* titer after each round, starting from the shared initial DoE."""
```

- `U0` — the shared initial design, in the unit cube. Every arm gets the same one.
- `y0_obs` — its noisy observations. Also shared.
- `y0_true` — the noiseless truth, for scoring only. **Do not let your method see
  this**; it is what makes the comparison meaningful.
- returns `rounds + 1` numbers, index 0 being the shared starting point.

Read `single_shot_rsm_campaign` for the shortest self-contained example — ten
lines of code under its docstring. `rsm_campaign` shows the other shape, where the
baseline is a stateful `ask(k)` / `tell(X, y)` object; `SequentialRSM` in
`sequential_rsm.py` is that object, and it is worth copying if your method is a
real sequential design.

**You do not have to wire it into the comparison table.** Adding an arm to
`multi_round` is genuinely fiddly — the existing single-shot arm's name appears
fifteen times in that one function, across accumulation, averaging and six lines
of print formatting. That is our plumbing, not your contribution. **A campaign
function plus the numbers it produces is a complete submission**, and if the
result holds up, wiring it in is our job.

## What makes the comparison informative

The bar is not a checklist to get past. It is the small number of things that
decide whether a result means anything:

- **Same budget.** Same initial DoE, same rounds, same batch size. The existing
  comparison gives every arm 120 runs because equal budget is the whole exercise;
  a method that wins on more runs has not won.
- **Same data.** Every arm starts from one shared `U0` / `y0_obs`. Re-drawing the
  initial design per arm makes the comparison about luck.
- **State your seeds, and use more than a few.** The published runs use 20. A
  single seed cannot distinguish a result from noise, and paired per-seed
  comparison is what turns "ours is higher" into "ours wins on 18 of 20".
- **Tune the baseline, not us.** The RSM arm sweeps its region half-width and the
  sweep is printed in full. If tuning your method is what produces the win, say
  so and show the sweep — a headline picked from a hidden sweep is a result
  nobody can check.

**And the one that is easiest to miss.** Ask what your result is a property *of*.
[#124](https://github.com/enginbio/engin-suite/issues/124) audited engin-pathway's
advantage over a step-count heuristic and found it was partly a property of the
synthetic generator: relabel with a different length constant and step-count wins
instead. Nothing in the code was wrong. A comparison on a simulator measures the
method **on that simulator**, and the strongest submissions say which part of
their result would survive a different one.

## What to open

**An issue, not a pull request**, at least to start —
[open one here](https://github.com/enginbio/engin-suite/issues/new). Include the
provenance line, your campaign function, and your seeds. A PR is welcome once
there is agreement on what the result shows, but a result that turns out to be a
misconfiguration is much cheaper to sort out in an issue than in review.

**What happens next**, stated because `CONTRIBUTING.md` does the same for gap
reports and this path deserves it too:

- It is read by one person (`D18`), so silence is a queue rather than a verdict.
- If it holds up, it goes in the results table with attribution.
- If it turns out to be a configuration difference, that gets written down too —
  "your baseline was misconfigured" is a finding about our documentation as often
  as about your run.
- **A loss is not quietly dropped.** That is the commitment in `CONTRIBUTING.md`
  and this page exists to make it actionable.

## Related

- [Benchmarks](benchmarks.md) — the published results, and the provenance lines
- [Limitations](limitations.md) — what has and has not been shown
- [Contributing](contributing.md) — the general guide
