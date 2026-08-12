# Install

```{warning}
**Engin is not on PyPI yet.** No distribution name is registered to this project,
so `pip install engin-core` does not work today and will fetch nothing. Install
from source until this page says otherwise.
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
| `[io]` | xarray, pandas, pint | The data convention and ingest layer |
| `[tea]` | BioSTEAM (Python ≥ 3.12) | Flowsheet-backed techno-economics |
| `[examples]` | matplotlib | Running the bundled examples |
| `[dev]` | pytest, ruff, and the above | Development and testing |

The default install stays deliberately light — scikit-learn, scipy, MAPIE and
pydantic, with no PyTorch — so that trying Engin is cheap. See
[ADR 0002](adr/0002-light-default-dependency-path.md).

## Versioning

Pre-1.0: pin an exact version, or a commit. See
[API stability](api-stability.md).
