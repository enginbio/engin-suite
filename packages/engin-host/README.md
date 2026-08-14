# engin-host

Host / chassis selection — **stage [4]** of the [engin-suite](../../README.md)
strain-to-scale funnel. Given a target molecule's capability profile, recommend
the microbial host with an explainable rationale, an honest confidence band, and
hard-constraint flags — so teams don't spend 18 months discovering E. coli was
the wrong chassis.

## Why

Host selection is a crucial design parameter still chosen empirically ("just use
E. coli" or tribal knowledge). **No published tool scores candidate chassis against
a production requirement with calibrated uncertainty** — searched 2026-08-13 and
written up, with the near-misses, in
[docs/design/host-selection.md](https://docs.engin.bio/en/latest/design/host-selection.html).
The honest competitor is not other software: it is building the constructs in six
hosts and measuring. Circuit failures are frequently host-interaction failures
rather than failures of the circuit itself — the contextual causes are catalogued
in [Cardinale & Arkin (2012)](https://doi.org/10.1002/biot.201200085).
<!-- ref: 2012-cardinale-context -->

*Corrected 2026-08-13 by the `D23` pass (#91), then searched under #107. This read
"with no standard commercial tool — genuine whitespace": an **absence claim about a
market, never searched**, on the day the equivalent claim about the data convention
proved flatly wrong. The search found no published tool, so the absence holds — but
"commercial" was dropped, because a literature and package search cannot settle what
sits inside a proprietary platform. It also read "**Most** circuit failures are
host-interaction failures"; the mechanism is well supported, the proportion is not.*

## What it does

A multi-criteria decision engine over a curated host-capability knowledge base:

- **scores** candidate hosts for a target profile (weighted suitability),
- shows **why** (per-capability contributions),
- flags **hard requirements** (glycosylation, secretion, GRAS, scale) and demotes
  infeasible hosts below every feasible one regardless of raw score,
- attaches a **confidence band** that widens honestly where the KB is thin.

Uncertainty is first-class and shared with the rest of the suite: `P(suitability ≥
threshold)` is computed with `engin_core`'s primitive.

## Quickstart

```python
from engin_host import default_kb, HostQuery, score, render_memo

kb = default_kb()
q = HostQuery(
    weights=dict(glyco=1.0, secretion=0.9, protein=1.0, titer=0.6, scaleup=0.7),
    hard=dict(glyco=0.6),          # a hard glycosylation requirement
)
ranked = score(kb, q)
print(ranked[0].host, ranked[0].score, "±", round(ranked[0].band90, 2))
print(render_memo("my target", ranked))
```

On two contrasting queries the engine picks the right hosts — CHO for a secreted
human glycoprotein, S. cerevisiae for a food-grade small molecule — correctly
demoting higher-scoring-but-infeasible chassis via hard constraints. Full demo:

```bash
python examples/run_demo.py     # writes memos + score charts to outputs/
```

## Status & roadmap

M0 (scoring + uncertainty + flags) works on an **illustrative** KB. Next: replace
the illustrative values with literature-grounded, cited capability data (M1);
calibrate the confidence band against retrospective host-choice cases, reusing
`engin_core`'s conformal machinery (M2); backtest and sign design partners (M3).

## Install

```bash
pip install -e "packages/engin-host[dev]"   # from an engin-suite checkout
```

Apache-2.0.
