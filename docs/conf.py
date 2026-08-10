"""
Sphinx configuration for the Engin documentation site.

Implements D15.

The load-bearing choice here is notebook execution. Every MyST document and
notebook is *executed* when the docs are built, so a broken example fails the
build. Documentation cannot silently rot, and no separate test harness for
examples is needed — building the docs is verifying them.

Execution happens in CI, not on Read the Docs. RTD's shared builders are
resource-limited and Engin's examples fit models; executing there risks slow
or flaky builds, which is exactly the pressure that eventually gets execution
switched off. So CI executes and commits the jupyter-cache, and RTD builds
from it.
"""

import os
from datetime import date

# -- Project ----------------------------------------------------------------

project = "Engin"
author = "EnginBio"
copyright = f"{date.today().year}, EnginBio — Apache-2.0"

# Single source of truth: read the installed package version rather than
# duplicating it here, so the docs cannot disagree with the code.
try:
    from importlib.metadata import version as _v

    release = _v("engin-core")
except Exception:  # not installed (e.g. a docs-only checkout)
    release = "0.0.0.dev0"

version = ".".join(release.split(".")[:2])

# -- Extensions -------------------------------------------------------------

extensions = [
    "myst_nb",                      # MyST markdown + executed notebooks
    "sphinx.ext.autodoc",           # API reference generated from docstrings
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",          # NumPy/Google docstring styles
    "sphinx.ext.intersphinx",       # cross-link to numpy, scipy, sklearn
    "sphinx.ext.viewcode",
    "sphinx_design",                # cards, tabs, grids
    "sphinx_copybutton",
]

# -- Executable documentation (the D15 commitment) --------------------------

ON_RTD = os.environ.get("READTHEDOCS") == "True"

# CI executes and commits the cache; RTD builds from it. Do not "fix" a slow
# RTD build by turning execution on there — fix it in CI, or the guarantee
# quietly stops being enforced anywhere.
nb_execution_mode = "off" if ON_RTD else "cache"
nb_execution_timeout = 300          # some examples fit models
nb_execution_raise_on_error = True  # a broken example FAILS THE BUILD
nb_execution_cache_path = ".jupyter_cache"  # committed, so RTD can read it

myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "dollarmath",
    "amsmath",
    "substitution",
]

# -- API reference ----------------------------------------------------------

autosummary_generate = True
autodoc_typehints = "description"
autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "undoc-members": False,         # undocumented members are a docs bug
    "show-inheritance": True,
}
napoleon_google_docstring = False
napoleon_numpy_docstring = True

# -- Cross-project links ----------------------------------------------------

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/", None),
    "sklearn": ("https://scikit-learn.org/stable/", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
}

# -- HTML -------------------------------------------------------------------

html_theme = "pydata_sphinx_theme"
html_title = "Engin"
html_baseurl = "https://engin.bio/"

html_theme_options = {
    "github_url": "https://github.com/enginbio/engin-suite",
    "show_prev_next": True,
    "navigation_with_keys": True,
    "use_edit_page_button": True,
    "footer_start": ["copyright"],
    "footer_end": ["theme-version"],
}

html_context = {
    "github_user": "enginbio",
    "github_repo": "engin-suite",
    "github_version": "main",
    "doc_path": "docs",
}

html_static_path = ["_static"]

# -- Build strictness -------------------------------------------------------

# Warnings are errors in CI. A dead cross-reference is a broken promise on a
# site whose whole argument is that the documentation is trustworthy.
nitpicky = True

exclude_patterns = ["_build", "**.ipynb_checkpoints", "Thumbs.db", ".DS_Store"]
