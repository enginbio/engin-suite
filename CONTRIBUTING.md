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

### Adding a package

If the new package imports a sibling, list that sibling's source in its pytest configuration:

```toml
[tool.pytest.ini_options]
pythonpath = ["src", "../engin-core/src"]
```

Editable installs are not enough on their own: paths contributed by `.pth` files are absent from
`sys.path` during a pytest run, so `import engin_core` fails in tests even when `pip install -e`
succeeded. This is the one step that is easy to miss and produces a confusing `ModuleNotFoundError`
on a fresh clone. See [ADR 0004](https://docs.engin.bio/en/latest/adr/0004-hermetic-test-pythonpath.html).

Nothing else needs updating by hand — CI discovers packages from the filesystem, so a directory with
a `pyproject.toml` is tested, linted, built and audited automatically.

Before opening a pull request:

- `pytest` passes, including the calibration coverage tests
- `ruff check .` and `ruff format .` are clean — the whole tree, not the files you touched
- New behaviour has a test
- `ruff format --check .` is clean (READMEs are excluded; their examples are hand-aligned)

## Citing evidence

Every substantive claim in a public document resolves to a row in
[`sources.yaml`](https://github.com/enginbio/engin-suite/blob/main/sources.yaml). CI enforces this, so the convention is short.

**In prose**, footnote by source id:

```markdown
Yield directly defines the substrate cost.[^2024-konzock-try-costs]
```

**In code**, a `# ref:` comment at the implementing function, alongside the
existing decision reference:

```python
# implements D13; ref: 2024-konzock-try-costs
```

Those two are orthogonal and both are worth having. **`D<n>` says why we chose;
`ref:` says what evidence backed it.** A decision can be well-reasoned and
unevidenced, and the pair makes that visible instead of blurring it.

### Three rules

**1. A number in a public document has a citation or it doesn't ship.** The check
is `scripts/evidence/check_claims.py`, and it runs on every pull request. If the
number is a fact about *this repository* rather than about the world — a test
count, a nominal interval level, a figure from our own worked example — mark it:

```markdown
Raw material lands at roughly 2% of modelled cost. <!-- not-a-claim: measured on our simulator -->
```

Using that marker is deliberately visible in the diff. An unevidenced claim
should cost a sentence of justification, not be impossible.

**2. Claims from practitioner interviews are testimony, not evidence.** Twelve
founders saying feedstock is the blocker is a strong signal about *demand*. It is
not a measurement, and presenting it as one is the fastest available way to lose
the readers this project wants. Record interview sources with `type: interview`
and say "practitioners report" rather than "studies show".

**3. Editorial framing stays uncited and clearly marked.** Do not manufacture
citations for opinions. "We think titer is the wrong target" is a position, and
it is stronger stated as one than dressed as a finding.

### When the evidence disagrees with the document

Fix the document, and **keep the register row** with `strength: contradicts` or
`superseded`. The row is the record that the claim was corrected, which is worth
more than a clean-looking bibliography. This has already happened once, to `D13`
— see the `contested` row for the cost-share split.

### If you changed a documentation page that runs code

Rebuild the docs and **commit the refreshed `docs/.jupyter_cache`** along with your change:

```bash
sphinx-build -W --keep-going -b html docs docs/_build/html   # executes examples, refreshes cache
git add docs/.jupyter_cache
```

That cache is committed on purpose. Read the Docs renders example outputs *from* it rather than
executing them on shared builders (`D20`), so a stale cache means the published page either loses
its outputs or RTD starts executing — the thing that arrangement exists to prevent. CI fails with
an explicit message if you forget, so this is a reminder rather than a trap.

Worth knowing: the cache's SQLite index changes on every build even when nothing else does, so
expect it to show as modified. Commit it anyway.

## Things that will get a change rejected

Not to be discouraging — these are specific and rare:

- **Uncalibrated point estimates.** Calibrated uncertainty is the project's core commitment. A model that returns a number without an honest interval doesn't fit here.
- **Optimizing titer instead of net cost.** Titer is inflatable by running longer and says nothing about the substrate cost that yield governs, so it is the wrong objective (`D13`). Engin looks worse on the metric everyone reports as a result, and that is a considered trade. Both recommenders exist on purpose — `engin_core.tea.recommend_batch_by_cost` optimizes net $/kg and `engin_core.recommend_batch` optimizes titer as the comparison baseline. A change that deepens the dependence on titer is going the wrong way. *(Corrected 2026-08-11: this previously said the cost path "is not built". It shipped in PR #51.)*
- **Reimplementing what already exists.** `D9` names BayBE, BioSTEAM, COBRApy, MAPIE and eQuilibrator as the things not to rebuild. Two of those are wired in today — MAPIE as a dependency, BioSTEAM as an optional extra — and the rest are deferred-to rather than composed with, which is a rule about what not to build rather than a description of the dependency graph. *(Corrected 2026-08-13: this said "we compose with" all four.)*
- **Anything on the declined list in `BIOSECURITY.md`.**

## Reporting issues

For bugs, include what you ran, what you expected, what happened, and versions. For a modelling problem, the input data or a synthetic case that reproduces it is enormously more useful than a description.

Security vulnerabilities go through `SECURITY.md`, not the public tracker.

## Related

- `GOVERNANCE.md` · `CODE_OF_CONDUCT.md` · `SECURITY.md` · `BIOSECURITY.md`
