# 0011 — A fixed candidate-pool seed is reproducible for one call and a trap for a campaign

**Status:** Proposed (2026-08-19)

## Context

`recommend_batch` and `recommend_batch_by_cost` build their candidate pool from
`np.random.default_rng(seed)` with `seed: int = 1`. The pool is therefore **byte-identical on
every call**, and the reachable design space is a fixed lattice of 4,000 points rather than the
unit cube.

[#224](https://github.com/enginbio/engin-suite/issues/224) reports two independent defects in
these functions. Part 1 — the diversity filter never comparing candidates against `gp.X`, so a
multi-round loop re-recommends conditions already run — is claimed separately and is a
straightforward bug fix. This record is about part 2, which is not a bug: it is a decision about
what `seed` should *mean*, and it was deliberately left for a maintainer.

## What was measured

Reproduced independently on this checkout before writing anything, because two of the reported
numbers are load-bearing and counterintuitive. Bundled simulator, 5 knobs, 24 initial runs, 5
rounds of k=8, 4 initial-data seeds. *(The issue used 8 data seeds and a different per-round seed
schedule; figures below are mine.)*

| variant | campaign best | identical to an already-run design, by round (of 32) |
|---|---|---|
| default, fixed `seed=1` | **110.770** | 0, 13, 17, 12, 15 |
| add `gp.X` to the filter (part 1) | **110.770** | 0, 0, 0, 0, 0 |
| vary the pool seed per round (part 2) | **113.550** | 0, 0, 0, 0, 0 |

Three things follow, and all three reproduce.

**110.770 is the pool ceiling, exactly.** The best true titer among the 4,000 points of the
`seed=1` pool is 110.770 g/L. Every campaign converged to it and stopped, on every data seed, <!-- not-a-claim: measured on our own simulator, reproduced on this checkout -->
regardless of what it started from. This is not the optimizer plateauing — it is the optimizer
reaching the edge of the only design space it can see.

**The two defects are causally independent.** Adding `gp.X` to the diversity filter removed
100% of the repeats and recovered **0.000 g/L**. Repeats cost reactor runs, not titer. That is <!-- not-a-claim: measured on our own simulator, reproduced on this checkout -->
what makes part 1 and part 2 separable, and it is the claim most worth having from two
independent hands, because the obvious intuition is that fixing repeats must improve the
campaign. It does not.

**Part 2 is where the titer is.** Varying the pool seed per round recovered **+2.78 g/L** on <!-- not-a-claim: measured on our own simulator, reproduced on this checkout -->
these runs and also removed the repeats, because a fresh pool rarely re-proposes an existing
point.

## Decision

**Not taken here.** This record exists so the choice is made deliberately rather than inherited.

The options, with what each costs:

1. **Keep `seed: int = 1`.** One call is bit-reproducible with no ceremony. A campaign silently
   caps at the pool's best point, and `README.md:54` — `recommend_batch(gp, float(y[tr].max()), k=8)`
   — is the snippet a user copies into a loop, so the default teaches the trap.
2. **Default `seed: int | None = None`.** A fresh pool per call; reproducibility becomes opt-in by
   passing a seed. Removes the ceiling and most repeats. Costs bit-reproducibility for anyone who
   currently relies on the default, which is a real break even pre-1.0 — `cli.py` passes
   `seed=section.seed` from a committed `project.yaml`, so a project file that pins a seed keeps
   working, and one that does not changes behaviour.
3. **Keep the fixed default, document it at the call site and in the README.** Cheapest, changes no
   behaviour, and relies on users reading. The published multi-round benchmark already varies the
   seed per round (`benchmark.py:344`), so the project's own numbers are inoculated against a trap
   its users are not — which is the argument against relying on documentation here.

**Recommended: option 2.** A default that is correct for one call and wrong for the loop the
library is built around is the wrong default, and the reproducibility it buys is available by
typing a number. Option 3 leaves the project publishing benchmark numbers it obtained by avoiding
its own default.

## Consequences if option 2 is accepted

- `recommend_batch` and `recommend_batch_by_cost` change signature to `seed: int | None = None`.
  **Both are in files part 1 is currently editing**, so this lands after that PR.
- `README.md:54` and any example that loops need a line on when to pin a seed.
- The `api-stability` surface changes behaviour without changing names, which is exactly the
  case that page says gets a note.
- A test should assert that two calls with the default return different pools, and that passing
  an explicit seed still reproduces — the property, not the number.

## Not decided here

Whether the acquisition should be polished off the pool at all. #224 measures an L-BFGS-B polish
recovering considerably more titer than either fix, and notes it does *not* remove repeats. That
is a third change, larger than both, and it is not on the table in this record.
