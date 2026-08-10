# Install

```bash
pip install engin-core
```

Requires Python 3.11 or later.

## Optional extras

| Extra | Installs | For |
|---|---|---|
| `engin-core[dev]` | pytest, ruff | Development and testing |
| `engin-core[docs]` | Sphinx, MyST-NB, PyData theme | Building this documentation |

## From source

```bash
git clone https://github.com/enginbio/engin-suite
cd engin-suite
pip install -e ".[dev]"
pytest
```

## Versioning

Pre-1.0: pin an exact version. See [API stability](api-stability.md).
