"""Put ``examples/`` on the import path.

``test_run_demo.py`` imports ``run_demo`` and calls its ``main()`` rather than
shelling out, so a failure surfaces as a traceback at the offending line instead of
a non-zero exit code. The examples directory is not a package and is not shipped in
the wheel (setuptools finds packages under ``src/`` only), so it needs adding here.

``__file__`` rather than a relative path keeps this correct under the CI job that
clears ``pythonpath`` and imports from site-packages. Same shape and same reason as
``packages/engin-protein/tests/conftest.py``, which does this for ``benchmarks/``.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
