"""Put ``benchmarks/`` on the import path.

``test_docstring_claims.py`` asserts the orderings produced by
``benchmarks/docstring_claims.py`` rather than restating its measurement code, so the
script a reader runs by hand and the one CI gates on cannot drift apart. The
benchmarks directory is not a package and is not shipped in the wheel (setuptools
finds packages under ``src/`` only), so it needs adding here; ``__file__`` keeps it
correct under the CI job that clears ``pythonpath`` and imports from site-packages.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "benchmarks"))
