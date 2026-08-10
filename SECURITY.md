# Security

## Reporting a vulnerability

Report privately to **security@engin.bio**, or via GitHub's [private vulnerability reporting](https://github.com/enginbio/engin-suite/security/advisories/new) on this repository.

Please don't open a public issue for a security problem.

Include what you can: affected version, what an attacker could do, and steps to reproduce. A proof of concept helps but isn't required — a clear description of the weakness is enough to start.

## What to expect

- **Acknowledgement within 3 working days.** If you don't hear back, the mail may have gone astray — follow up by opening a public issue saying only that you're waiting on a security response, with no details.
- **An assessment within 10 working days**, including whether we consider it a vulnerability and a rough timeline.
- **Credit**, unless you'd rather not be named.

This is a one-maintainer project, so response is best-effort rather than contractual. Being honest about that is better than publishing a service level nobody is on call to meet.

## Scope

Engin is a library and CLI for bioprocess modelling. It has no hosted service, no authentication, and stores no user data. The realistic surface is therefore:

- Code execution through crafted input files — malformed bioreactor exports, spreadsheets, or manifests fed to the ingest layer
- Deserialization issues in model or checkpoint loading
- Dependency vulnerabilities reachable through our code paths
- Anything that could cause a benchmark or calibration result to be silently falsified

That last one matters more here than in most libraries. The project's central claim is calibrated uncertainty, so a bug that makes coverage look better than it is undermines the whole thing. **We treat silent correctness failures in calibration or benchmarking as security-class**, even though nobody would normally call them vulnerabilities. Report them the same way.

## Out of scope

- Vulnerabilities in dependencies not reachable through our code — report upstream
- Attacks requiring an already-compromised machine
- Results being wrong because the model is wrong; that's a bug or a modelling disagreement, and belongs in the public tracker

## Supported versions

Pre-1.0. Only the latest release gets fixes. This changes at 1.0, alongside the API stability guarantee.

## Supply chain

Stated as it currently stands rather than as intended, because a security document that overstates its own posture is worse than one that admits a gap:

- Dependencies declare **minimum versions, not pins**, and there is no lockfile. CI resolves the latest compatible set, so the declared floors are untested.
- **Dependabot covers GitHub Actions only**, not Python dependencies.
- **Nothing is released yet**, so nothing is signed. Signing is intended from the first release.

Gaps here are in scope and a report that closes one is welcome.

## Related

- `BIOSECURITY.md` — dual-use assessment and declined scope
- `CONTRIBUTING.md` · `GOVERNANCE.md`
