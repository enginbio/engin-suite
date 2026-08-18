# Architecture decision records

Two numbered series run in this project, and they answer different questions.

| Series | Question | Where |
|---|---|---|
| **`D` decisions** | Why does the project exist in this shape — licensing, scope, governance, what gets built | [Decisions](../decisions.md), canonical |
| **ADRs** | Why is the *code* arranged this way — dependencies, test topology, packaging | here |

An ADR is a record of a decision at the moment it was made. They are not edited when the world
moves; a *Since this was written* note is appended instead, so the reasoning and its shelf life stay
legible together.

## Why the numbering has gaps

These originated in a private wiki that was retired under `D22`, which moved documentation into this
repository. Only the ADRs that **shipped source code cites** were ported, because a citation an
outside reader cannot resolve is worse than no citation:

```{toctree}
:maxdepth: 1

0002-light-default-dependency-path
0004-hermetic-test-pythonpath
0009-vendor-profiles-are-a-convention-gap
0010-regulatory-status-is-two-facts-not-a-scalar
```

The unported numbers — 0001, 0003, 0005 through 0008 — covered repository layout and process
decisions that either no longer apply or are now stated directly in `DECISIONS.md`, `CONTRIBUTING.md`
and `GOVERNANCE.md`. They are not cited from code. If one turns out to be load-bearing later, port it
then and keep its original number.

New records start at **0009**, leaving that range free so a ported record can keep the number it was
written under.
