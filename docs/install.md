# Install

```{warning}
**Engin has not been released to PyPI, and `pip install engin-core` is worse than
a clean failure.** Four names — `engin-core`, `engin-graph`, `engin-host` and
`engin-materials` — are registered as **placeholder reservations**, so that
command *succeeds* and installs a `0.0.1.dev0` stub containing nothing.
`engin-pathway` and `engin-protein` are not registered at all and will fail
outright.

Install from source until this page says otherwise.
```

## From source

```bash
git clone https://github.com/enginbio/engin-suite
cd engin-suite
pip install -r requirements-dev.txt   # whole monorepo, editable
cd packages/engin-core && pytest
```

`requirements-dev.txt` is a requirements file rather than a root package because
there is no root package to install — the six distributions live under
`packages/`, and a root `pyproject.toml` would have to declare them as
dependencies pip would then look for on PyPI, where they are not published.

Requires **Python 3.10 or later**. Continuous integration runs the suites on
3.10, 3.11, 3.12 and 3.13, and separately against the oldest dependency versions
each package declares.

## Optional extras

Each package's extras are declared in its own `pyproject.toml` and install with
the package:

| Extra | Installs | For |
|---|---|---|
| `[cli]` | PyYAML | The command line and the project file |
| `[io]` | xarray, pandas, pint | The data convention and ingest layer |
| `[tea]` | BioSTEAM (Python ≥ 3.12) | Flowsheet-backed techno-economics |
| `[examples]` | matplotlib | Running the bundled examples |
| `[dev]` | pytest, ruff, and the above | Development and testing |

The default install stays deliberately light — scikit-learn, scipy, MAPIE and
pydantic, with no PyTorch — so that trying Engin is cheap. See
[ADR 0002](adr/0002-light-default-dependency-path.md).

## Command line

Each stage ships its own console script, so a decision can be made without writing
Python. They all read the same project file:

```bash
engin-host --init project.yaml   # writes a commented starter file to edit
engin-host     --config project.yaml   # [4] which chassis?
engin-pathway  --config project.yaml   # [3] which route?
engin-process  --config project.yaml   # [1] what to run next?
```

Add `--json` to any of them for machine-readable output.

```{note}
**Three scripts rather than one `engin` with subcommands**, which is the shape you
might expect. Two reasons, both recorded in
[#141](https://github.com/enginbio/engin-suite/issues/141): no package depends on both
`engin-host` and `engin-pathway`, so none could host a unified entry point; and the
`engin` script name belongs to an unrelated, maintained package on PyPI, so shipping
it would silently overwrite theirs for anyone who had both.
```

The starter file is commented throughout, and those comments are where the field names
are explained. Read them before trusting any number that comes back — in particular the
pathway step features are your own judgement entered by hand, not computed from
structure ([#140](https://github.com/enginbio/engin-suite/issues/140)).

## Versioning

Pre-1.0: pin an exact version, or a commit. See
[API stability](api-stability.md).
