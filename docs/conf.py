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
switched off. So the examples are executed in CI, and Read the Docs renders them
from a committed jupyter-cache without executing anything.

Two details of that are easy to get wrong, and both were wrong here until
2026-08-10. It needs ``nb_execution_mode = "cache"`` rather than ``"off"``,
because ``"off"`` ignores the cache and renders code without its outputs. And
the cache is kept current by contributors plus a CI *check*, not by CI pushing
to ``main`` --- a bot cannot push to a protected branch. See the comment on
``nb_execution_mode`` below.
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
    "myst_nb",  # MyST markdown + executed notebooks
    "sphinx.ext.autodoc",  # API reference generated from docstrings
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",  # NumPy/Google docstring styles
    "sphinx.ext.intersphinx",  # cross-link to numpy, scipy, sklearn
    "sphinx.ext.viewcode",
    "sphinx_design",  # cards, tabs, grids
    "sphinx_copybutton",
]

# -- Executable documentation (the D15 commitment) --------------------------

ON_RTD = os.environ.get("READTHEDOCS") == "True"

# Do not "fix" a slow RTD build by turning execution on there — fix it in CI, or
# the guarantee quietly stops being enforced anywhere.
#
# `cache` everywhere, including on Read the Docs, and the reason is load-bearing.
#
# This used to be `"off" if ON_RTD else "cache"`, on the belief that "off" would
# render the committed cache without executing. It does not: "off" ignores the
# cache entirely and renders every code cell *without its outputs*, so the
# published site showed bare code while CI showed results. Measured, not assumed.
#
# `cache` gets what D20 actually wants -- RTD does not execute -- by a different
# route: a cache hit renders stored outputs and runs nothing. The cache is
# committed, and content-hash keyed rather than path keyed, so it is portable
# across machines. Contributors refresh it with any change to an executed page
# (CONTRIBUTING.md); .github/workflows/docs.yml *verifies* it is current rather
# than maintaining it, because a bot cannot push to a protected branch.
#
# The residual risk is honest: on a cache *miss* RTD would execute. That is why
# CI refreshes the committed cache rather than leaving it to drift.
nb_execution_mode = "cache"
nb_execution_timeout = 300  # some examples fit models
nb_execution_raise_on_error = True  # a broken example FAILS THE BUILD
# Anchored to this file rather than left relative: the path is resolved against
# sphinx-build's working directory, so a bare ".jupyter_cache" landed at whatever
# directory the build was invoked from -- the repository root in practice, where
# .gitignore's `docs/.jupyter_cache/` entry never matched it.
nb_execution_cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".jupyter_cache")

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
    "undoc-members": False,  # undocumented members are a docs bug
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

# Canonical URL. Read the Docs sets READTHEDOCS_CANONICAL_URL to the fully
# versioned URL of the version being built, so the canonical tag stays correct
# as versions are added rather than needing an edit each time.
#
# Deliberately not hardcoded to https://engin.bio/: that host 302-redirects to
# docs.engin.bio, and a canonical pointing at a redirect is a conflicting
# signal to search engines. The fallback below is for local builds only.
html_baseurl = os.environ.get("READTHEDOCS_CANONICAL_URL", "https://docs.engin.bio/en/latest/")

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

# .jupyter_cache lives under docs/ (see nb_execution_cache_path) and contains an
# executed .ipynb per cached document. Sphinx globs those as source files and then
# reports each as absent from any toctree, which -W turns into a failed build. CI
# cannot catch this: it builds from a fresh checkout, where the cache does not yet
# exist when the glob runs. Only a rebuild -- anyone's second local build -- hits it.
exclude_patterns = [
    "_build",
    ".jupyter_cache",
    "**.ipynb_checkpoints",
    "Thumbs.db",
    ".DS_Store",
]
