# Contributing

Thanks for considering it. This is an early project with one maintainer, so contributions land quickly and shape direction more than they would in a mature codebase.

Read `GOVERNANCE.md` for how decisions get made and how to join. This file covers mechanics.

## What's most wanted

Listed in order of how much it would help.

**Real fermentation data**, or pointers to public datasets we've missed. This is the project's hardest problem and the field's too: process knowledge is trade secret, so there is no public corpus to learn from. A dataset with documented provenance is worth more than a feature. See `BIOSECURITY.md` for how contributed data is handled.

**Benchmarks where Engin loses.** A benchmark suite that always favours its author is worthless. If a simpler baseline — plain DoE, a step-count heuristic, an off-the-shelf optimizer — beats Engin on a case, that belongs in the published results table alongside the wins. We will not quietly drop it.

**Domain corrections.** If a modelling assumption is wrong in a way that would be obvious to someone who has actually run a campaign, say so. Bluntly is fine.

**The unglamorous layer.** Data loaders for bioreactor export formats, documentation, tests, provenance manifests.

## Before you start

For anything beyond a small fix, **open an issue first.** It keeps design discussion public and searchable, and it avoids you building something that conflicts with a decision you had no way of knowing about.

Decisions are recorded and numbered. If a change touches one, cite it (`implements D13`, `revisits D11`). If you think a decision is wrong, argue with the reasoning rather than routing around it — that's a legitimate contribution and sometimes the most valuable kind.

## Sign your commits (DCO)

We use [Developer Certificate of Origin](https://developercertificate.org/) sign-off rather than a contributor licence agreement:

```bash
git commit -s -m "your message"
```

This adds a `Signed-off-by` line attesting you have the right to contribute what you're contributing. It transfers nothing.

**There is deliberately no CLA.** A CLA is what lets a project relicense or move previously-open work behind a paid boundary later. Engin doesn't want that ability — without one, copyright stays distributed across contributors, so the project *cannot* relicense the existing code even if a future version of it wanted to. The commitment is structural rather than a promise. See `GOVERNANCE.md`.

## Development

```bash
git clone https://github.com/enginbio/engin-suite
cd engin-suite
pip install -r requirements-dev.txt   # whole monorepo, editable
cd packages/engin-core && pytest      # tests run per package
```

The suites don't actually need the install — each package's pytest configuration
points at the sibling sources it imports, so a bare checkout runs green.

Before opening a pull request:

- `pytest` passes, including the calibration coverage tests
- `ruff check .` and `ruff format .` are clean
- New behaviour has a test
- `ruff format --check .` is clean (READMEs are excluded; their examples are hand-aligned)

## Things that will get a change rejected

Not to be discouraging — these are specific and rare:

- **Uncalibrated point estimates.** Calibrated uncertainty is the project's core commitment. A model that returns a number without an honest interval doesn't fit here.
- **Optimizing titer instead of net cost.** The recommender optimizes net $/kg deliberately, because recovery cost is determined upstream but incurred downstream. This makes Engin look worse on the metric everyone reports, and that is a considered trade (`D13`).
- **Reimplementing what already exists.** We compose with BayBE, BioSTEAM, COBRApy and MAPIE rather than rebuilding them (`D9`).
- **Anything on the declined list in `BIOSECURITY.md`.**

## Reporting issues

For bugs, include what you ran, what you expected, what happened, and versions. For a modelling problem, the input data or a synthetic case that reproduces it is enormously more useful than a description.

Security vulnerabilities go through `SECURITY.md`, not the public tracker.

## Related

- `GOVERNANCE.md` · `CODE_OF_CONDUCT.md` · `SECURITY.md` · `BIOSECURITY.md`
