# Install

```{note}
**Engin is on PyPI as of 0.1.1.** Each stage ships a console script, and
installing any one pulls its siblings, so a single line gives you all three:

    pip install "engin-host[cli]" "engin-pathway[cli]"

Pre-1.0, so pin an exact version (see [Versioning](#versioning)). Prefer a source
checkout for development, or to build against unreleased changes — below.
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
`packages/`, and it installs them editable from there, so a checkout exercises
local changes rather than the released wheels.

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

(versioning)=
## Versioning

Pre-1.0: pin an exact version, or a commit. See
[API stability](api-stability.md).
