# 0004 — Hermetic test `pythonpath`, not editable installs

**Status:** Accepted (2026-08-07)

## Context

`engin-host` and `engin-pathway` both import `engin_core`, but each package's pytest config listed
only its own source:

```toml
pythonpath = ["src"]
```

Cross-package imports were therefore satisfied — when they were satisfied at all — by the editable
install of `engin-core` in the active virtualenv.

That turns out not to work: **paths contributed by `.pth` files are absent from `sys.path` during a
pytest run.** So `pip install -e` alone does not satisfy `import engin_core` in a test, and both
suites failed to collect with `ModuleNotFoundError`. `engin-core`'s own suite passed throughout,
because `pythonpath = ["src"]` is self-sufficient for a package with no siblings to import — which
masked the problem.

The failure surfaced during a virtualenv that had gone subtly corrupt, but the fragility is
independent of that: any suite that depends on an editable finder resolving correctly will break on
a fresh clone, a rebuilt environment, or a slightly different install mode.

## Decision

Each package's pytest config lists **every sibling source it imports**:

```toml
[tool.pytest.ini_options]
pythonpath = ["src", "../engin-core/src"]
```

pytest resolves these relative to rootdir, so they work from the package directory and in CI, which
sets `working-directory` per package.

This makes explicit what `engin-core`'s config comment already claimed as intent: *run from a bare
checkout without relying on an editable install.*

## Consequences

- Every suite passes with **no editable install and no `PYTHONPATH`** — a fresh clone can run tests
  immediately. Verified by deleting the editable installs entirely.
- CI becomes more robust: test collection no longer depends on the install step having produced a
  working finder.
- Cost: a new package that imports a sibling must remember to add it.
- Relative paths assume the monorepo layout. A package extracted to its own repo needs this
  revisited.

## Since this was written

- The suite has grown from four packages to six, and the test counts quoted in the original record
  (`engin-core` 14, `engin-host` 12, `engin-pathway` 9) are long superseded — `engin-core` alone is
  well past that. The decision itself has held unchanged.
- CI verifies the property rather than trusting it. The `build` job installs the built wheels and
  runs each suite with `pytest -o pythonpath=`, which blanks this setting — so a package that has
  come to depend on the source layout fails there rather than silently.
- The checklist item for adding a new package lived in the private wiki retired under `D22`. It is
  now in [Contributing](../contributing.md).

## Related

- [ADR 0002](0002-light-default-dependency-path.md) — the packaging this topology serves
- [Contributing](../contributing.md) — running the suites
