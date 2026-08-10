# API Stability and Versioning

Nobody builds on a foundation that breaks them. This page is the promise that makes depending on Engin reasonable, and it is deliberately specific — a stability guarantee without a written policy behind it is decoration.

## Current status: pre-1.0

**Engin is below 1.0, and the public API is not yet stable.** Breaking changes can land in any minor release. If you are depending on Engin today, pin an exact version.

Being early is not a reason to be vague about it. What follows is what the guarantee will be at 1.0, published now so you can judge whether it is one you would rely on.

## What counts as public

Only these are covered by the guarantee:

- Names exported from a package's top-level `__init__`
- Anything documented in the API reference on this site
- The command-line interface — subcommands, flags, exit codes
- On-disk formats we read and write, and the documented convention over xarray/pandas (dimension and coordinate names, units attributes)

Everything else is internal and may change without notice, including:

- Any name beginning with an underscore
- Submodule paths not re-exported at the top level
- The contents of `_build`, cache directories and intermediate artifacts
- Exact numerical output. See the separate section below — this one is subtle

## Versioning

[Semantic versioning](https://semver.org/), from 1.0 onward:

| Change | Version bump |
|---|---|
| Breaking change to anything public above | **major** |
| New functionality, backwards compatible | **minor** |
| Bug fix, no interface change | **patch** |

Pre-1.0, the minor version acts as the major: `0.4.x` → `0.5.0` may break you.

## Deprecation policy

From 1.0, nothing in the public API is removed without warning first.

1. **Announce.** The release notes name the deprecation, the replacement, and the removal version.
2. **Warn in code.** A `DeprecationWarning` fires on use, naming the replacement.
3. **Wait.** At minimum two minor releases *and* six months, whichever is longer.
4. **Remove**, only in a major release.

If a replacement exists, the deprecation message says what it is. A warning that tells you something is going away without telling you what to use instead is an unfinished job.

**One exception, stated plainly:** a bug producing incorrect scientific results may be fixed immediately, in a patch release, without a deprecation cycle. Correctness outranks stability. Such fixes are called out prominently in release notes, because a silently changed number is worse than a loud breaking change.

## Numerical output is not an API guarantee

This matters more here than in most libraries and is easy to get wrong.

Model improvements change predictions. A better calibration method, a bug fix in the conformal quantile, or an upgraded dependency will move numbers — and none of that is a breaking API change under this policy. The *interface* is stable; the *values* are subject to improvement.

What we guarantee instead:

- **Coverage stays honest.** Conformal interval coverage is tested in CI. If a change would push empirical coverage outside tolerance, it fails the build.
- **Changes that move results are documented.** Any release that materially shifts predictions says so in the release notes, with the reason.
- **Reproducibility is available on request.** Seeds are settable, and benchmark results are published with the dataset versions and seeds that produced them.

If you need bit-identical results across time — for a regulatory submission, say — pin the exact version and record it. That is the correct approach with any modelling library, and we would rather say so than imply a stability we cannot deliver.

## Python and dependency support

- **Python**: the three most recent stable releases. Dropping one is a minor bump pre-1.0 and a major bump after.
- **Dependencies**: minimum supported versions are declared in `pyproject.toml`. Raising a minimum is a minor bump.
- Upper bounds are avoided unless a known incompatibility exists — over-constrained dependencies are a tax on every downstream user.

## Experimental features

Anything genuinely unsettled is marked `@experimental` in code and flagged in its documentation. Experimental features are exempt from the deprecation policy and can change or disappear in any release.

This exists so that shipping something early does not require either pretending it is stable or hiding it. If a feature is unmarked, the guarantee applies.

## Release notes

Every release has notes. Breaking changes and result-affecting changes go at the top, not buried under new features.

## Changing this policy

Via pull request, with the reasoning recorded in the decisions record. Loosening the guarantee would be a significant change and would be argued in public before it happened.
