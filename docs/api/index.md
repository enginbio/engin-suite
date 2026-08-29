# API reference

Generated from docstrings at build time. **This page is scoped deliberately, and
the scope is the same one [API stability](../api-stability.md) promises** — not a
sweep of everything importable.

That page says the guarantee covers "anything documented in the API reference on
this site". So generating a page per submodule would not merely be untidy: it
would silently promote every internal module to public, contradicting the same
page's exclusion of "submodule paths not re-exported at the top level". The
listing below is therefore the guaranteed surface and nothing else.

What that leaves out is real. `engin_core.gp`, `engin_core.tea`,
`engin_core.simulator` and their siblings carry the machinery this project is
mostly *about*, and they are absent here on purpose — reach them through the
top-level exports, or read the source. The methods pages
([conformal calibration](../methods/conformal-calibration.md),
[out-of-distribution](../methods/out-of-distribution.md)) explain them properly,
which generated signatures would not.

## Packages

Each page lists what its package's `__init__` exports — the first bullet of the
guarantee — and nothing beyond it.

Fourteen exported names do not appear, and the omission is deliberate rather than
a wiring gap. Six are `__version__`; the rest are module-level constants and type
aliases carrying no docstring (`KNOBS`, `KNOB_NAMES`, `N_POOLINGS`,
`CAPABILITIES`, `QpsStatus`, `MONOMER_FEATURES`, `FEATURES`, `AMINO_ACIDS`).
`conf.py` sets `undoc-members: False` on the principle that an undocumented member
is a docs bug, so they are left out rather than rendered blank. Giving one a
docstring is what puts it on the page.

```{eval-rst}
.. autosummary::
   :toctree: generated

   engin_core
   engin_graph
   engin_host
   engin_pathway
   engin_protein
   engin_materials
```

## Public submodules

Three modules are public without being re-exported, because the
[Quickstart](../quickstart.md) and the [data formats
guide](../guides/data-formats.md) teach them as the documented route for getting
real data in. The guarantee names them individually for that reason.

```{eval-rst}
.. autosummary::
   :toctree: generated

   engin_core.datasets
   engin_core.loaders
   engin_core.convention
```

```{note}
Pre-1.0, the public API is unstable — breaking changes can land in any minor
release. Pin an exact version. See [API stability](../api-stability.md) for what
is covered, the deprecation policy, and why numerical output is deliberately
*not* part of the guarantee.
```
