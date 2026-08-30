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

# Respect ``__all__``. Sphinx's default is to ignore it and document every public
# member it can reach, which would put names on the API pages that
# ``api-stability.md`` does not cover -- and that page counts anything documented
# here as public. So the default would quietly widen the guarantee. ``False``
# makes the generated pages track each package's ``__all__`` exactly, which is
# the first bullet of what the guarantee actually promises.
autosummary_ignore_module_all = False
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

# Presentation only. Every rule is theme-variable-based so light and dark both
# work, and the pages are fully functional with this file absent -- see the
# header comment in engin.css for why it stays that small.
html_css_files = ["engin.css"]

# -- Build strictness -------------------------------------------------------

# Warnings are errors in CI. A dead cross-reference is a broken promise on a
# site whose whole argument is that the documentation is trustworthy.
nitpicky = True

# Types that appear in signatures but have no resolvable target. `nitpicky` above
# is what makes these fail the build, and the API reference is what surfaces them
# -- none of this fires until autodoc actually renders a signature.
#
# Kept narrow on purpose. A blanket `.*` would switch nitpicky off in all but
# name, and the whole value of the setting is that a genuinely dead reference in
# prose still breaks the build.
nitpick_ignore_regex = [
    # -- Third-party, and not ours to fix. numpy's typing aliases resolve to
    # private paths (`numpy._typing._array_like.NDArray`) that its own published
    # inventory does not carry, and pydantic/annotated_types publish no inventory
    # we map. Adding intersphinx entries would not fix the numpy ones.
    ("py:class", r"(numpy|np)\..*"),
    ("py:class", r"(pydantic|annotated_types|networkx)\..*"),
    ("py:class", r"(pd|xr|xarray)\..*"),
    # Pydantic renders a field's constraints where a type belongs, so the
    # constraint repr itself arrives as a cross-reference.
    ("py:class", r"(gt|ge|lt|le|min_length|max_length|multiple_of)=.*"),
    # -- Ours, and a real trade rather than an oversight. Three-component paths
    # are submodule-qualified (`engin_core.simulator.ReactorConfig`), and
    # `api-stability.md` deliberately keeps submodules out of the public surface,
    # so there is no page for them to link to. The three public submodules are
    # excluded from the pattern, so a dead reference inside those still fails.
    #
    # What this hides is worth knowing: public functions take and return internal
    # types that a reader cannot look up. Widening `__all__` is the fix, and it is
    # a maintainer's call rather than a docs one -- see #322, which also records
    # that `stopping.py` carries a MyST fence that will fail this build the moment
    # any of its names is exported.
    ("py:class", r"engin_\w+\.(?!datasets\.|loaders\.|convention\.)\w+\.\w+.*"),
    # The same names again, unqualified, as autodoc writes them when the
    # annotation was already imported into the module being documented.
    (
        "py:class",
        r"(ArrayLike|NDArray|GaussianProcessRegressor"
        r"|ProductionScale|PurityGrade|Provenance|Tier|Orientation|Level"
        r"|QpsStatus|PathwayRanker\.half_width|purity_dsp_multiplier|q)$",
    ),
]

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
