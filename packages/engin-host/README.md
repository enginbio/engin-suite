# engin-host

Host / chassis selection — **stage [4]** of the [engin-suite](../../README.md)
strain-to-scale funnel. Given a target molecule's capability profile, recommend
the microbial host with an explainable rationale, an honest confidence band, and
hard-constraint flags — so teams don't spend 18 months discovering E. coli was
the wrong chassis.

## Why

Host selection is a crucial design parameter still chosen empirically ("just use
E. coli" or tribal knowledge), with no standard commercial tool — genuine
whitespace. Most circuit failures are really host-interaction failures.

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
