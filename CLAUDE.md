# engin-suite — monorepo

The open (Apache-2.0) **strain-to-scale** suite: de-risk each decision in the
biomanufacturing funnel (host → pathway → process) with calibrated uncertainty.
Public monorepo, and nothing methodological is held back: probabilistic TEA ships
here in `engin_core.tea` (`D8`). A private overlay exists for hosted-service
plumbing and any future partner data under NDA, and holds no methods.

## Before you start work on a GitHub issue: claim it

Several agents work this repository concurrently, so issues are claimed by comment.

1. **Read the issue's comments first.** If one says the issue is being worked on,
   treat it as taken and pick a different one — don't duplicate the work.
2. **No such comment means it's free.** Leave one saying you're starting *before*
   you begin, so the next agent to look sees the claim rather than racing you.

If you stop or hand off without finishing, say so in a follow-up comment. A stale
claim that blocks everyone else is worse than never having claimed it.

### Claiming the issue is necessary and not sufficient — check the PR list too

A claim stops two agents *starting* the same issue. It does not stop one of them
landing overlapping work while you are still building, and `main` on this
repository moves in hours, not days.

- **Run `gh pr list` immediately before you open a PR**, not only before you start.
  A branch cut an hour ago may already be redundant.
- **Rebase, then re-verify.** Passing tests on a stale base say nothing. Re-run the
  package suite after the rebase, not before.
- **Scope your claim narrowly and say what you are leaving.** A comment reading
  "taking part 1, not part 2, because part 2 is a decision" lets someone else take
  part 2 in parallel instead of waiting for you. That is the mechanism working.

**When someone lands overlapping work first, rebuild the surviving part on current
`main` rather than rebasing a branch that is now mostly redundant** — a clean PR of
what is still needed reviews far better than a large one with the collisions merged
out of it. Close the superseded PR with a note saying which parts went where.

**Do not revert a merged decision because you reached a different one.** If your
work argued the opposite call and you have evidence for it, the evidence belongs in
a comment on the issue, where it survives for whoever revisits the question. The
merged decision stands until the maintainer changes it.

## Packages (`packages/`)
Six distributions. Two are shared engines, two are funnel stages, two point the
same machinery at adjacent domains.
- **engin-core** — shared engine: scipy fed-batch simulator, scikit-learn GP with
  conformal calibration (split-conformal + MAPIE), EI recommender, ARD sensitivity.
- **engin-graph** — shared graph engine: embedder + calibrated ranking head over
  structured objects, extracted from engin-pathway. Depends on engin-core.
- **engin-host** — stage [4] chassis selection: pydantic-typed capability KB,
  multi-criteria scoring with uncertainty + hard-constraint flags. Depends on engin-core.
- **engin-pathway** — stage [3] graph-ML manufacturability ranking (networkx GCN +
  ridge + conformal). M0 (random-weight GCN); M1 = trained PyG GNN +
  COBRApy/eQuilibrator. Depends on engin-core, engin-graph.
  **Do not describe this as "beats step-count" without the caveat.** The margin is
  a property of the synthetic generator — relabel with a different length constant
  and step-count wins instead. Audited in #124 / PR #137; the package README carries
  the numbers and what survives.
- **engin-protein** — protein design cycle over the same GP + EI + conformal loop:
  evaluation, low-N campaigns, batch planning. Depends on engin-core.
- **engin-materials** — structure-property ranking for biomaterial formulations,
  with calibrated intervals. Depends on engin-graph.

## Principles (enforced across packages)
- **Calibrated uncertainty is first-class** — no naked point estimates; conformal
  coverage tests stay green.
- **Honest baselines** — every model reported against the dumb heuristic it beats
  (naive-Gaussian intervals, random batches, step-count, "just use E. coli").
- **Everything methodological is public** — engine, simulators, calibration and
  the economics coupling alike (`D1`, `D8`). There is no held-back core, and the
  techno-economic head lives here in `engin_core.tea`. Only partner data under
  NDA could ever sit outside this repository, and none exists. **If a document
  tells you to keep the TEA coupling or priors private, that document is stale.**
- **Stand on mature libraries** — scipy / scikit-learn / MAPIE / pydantic for the
  solved wheels; hand-write only the domain models. Keep a light path (no torch
  required for the default install).

## Dev
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt    # all six, editable, with dev extras

# Per package, the way CI runs it. `pytest packages/` fails at collection: six
# test basenames repeat across packages, no tests/ has an __init__.py, and each
# package sets its own pytest pythonpath against its own rootdir (ADR 0004).
for p in packages/*/; do
  [ -f "$p/pyproject.toml" ] || continue     # skip stray dirs, as CI does
  ( cd "$p" && python -m pytest -q ) || exit 1
done

# The lint job is two gates, and running only the first is how a green local
# checkout still fails CI. Both from the repo root.
ruff check .
ruff format --check .
```

If a documentation page or `sources.yaml` changed, run the evidence pass too. CI
runs three checks in `docs.yml` and none of them are in the package test loop
above:

```bash
python scripts/evidence/render.py --check    # docs/references.md is generated
python scripts/evidence/check_claims.py      # every public number resolves
python scripts/evidence/check_corrections.py
```

Editing `sources.yaml` means re-running `render.py` **without** `--check` to
regenerate `docs/references.md` and committing both — `test_committed_view_matches_the_register`
fails on a stale view, and it runs in the engin-core suite rather than in `docs.yml`,
so a docs-only mental model misses it.

### When a source is paywalled: say so, and say what it is worth

**The maintainer will buy access to a source that has real leverage.** Cost is not
the constraint people assume it is, and a claim quietly weakened because a PDF was
gated is a worse outcome than an email asking for twenty dollars.

So when a source cannot be reached:

1. **Do not silently downgrade the claim.** Record what was verified, from where,
   and what could not be — in the `sources.yaml` note, not only in a PR comment.
   The register is where the next person looks.
2. **Say what the missing piece would change.** "Behind a paywall" is not a
   decision; "this would tell us whether the adverse result runs on our own
   conformal library, which is the difference between adjacent work and a direct
   comparison" is. Name the price if it is visible.
3. **Ask rather than assume.** Flag it and let the maintainer decide.

Two things this does *not* license. **Open access is not always reachable, and
that is worth checking before asking** — Crossref, PubMed Central, arXiv, an
author's institutional copy, and the publisher's own landing page often carry what
a bot-blocked PDF endpoint will not; `2025-pham-cqr-bioprocess-robust-optimisation`
is CC BY 4.0 and still gated at the PDF, and its bibliographic record came from
Crossref instead. And **paying for a source does not change `D3` or `D12`**: a
licence that forbids redistribution or derivatives still forbids them after
purchase, which is exactly the trap the EFSA CC BY-ND row exists to flag.

## Adding a package
New stages (e.g. engin-pathway) go under `packages/<name>/` with the same shape
(`src/`, `tests/`, `pyproject.toml`, README, CLAUDE.md) and depend on engin-core —
plus engin-graph if its objects are graphs.

Update the root README table and add the package to `requirements-dev.txt`. You do
**not** update a CI matrix: `.github/workflows/ci.yml` discovers packages with
`for pkg in packages/*/`, deliberately, so a new package cannot be silently
untested. A `lint` step fails the build if `requirements-dev.txt` misses one.
