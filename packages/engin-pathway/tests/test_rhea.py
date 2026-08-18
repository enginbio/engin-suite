"""Rhea reaction lookup (#140 item 3, the reachable half).

Network tests are marked and skipped by default: CI must not depend on
rhea-db.org being up, and a suite that fails because someone else's server is
down teaches people to ignore red. Run them with `-m network`.
"""

from __future__ import annotations

import pytest

from engin_pathway.rhea import RHEA_TSV_ENDPOINT, RheaLookupError, reaction_equation


def test_lookup_error_is_catchable_as_lookup_error():
    """Subclasses LookupError so ordinary handling works, but is its own type."""
    assert issubclass(RheaLookupError, LookupError)


def test_the_endpoint_is_the_licence_clean_one():
    """Rhea rather than KEGG or MetaCyc, per #209. Pinned so a well-meaning
    change to a 'richer' source has to argue with a test."""
    assert "rhea-db.org" in RHEA_TSV_ENDPOINT


def test_the_module_imports_without_the_thermo_extra():
    """engin-pathway must stay importable on a default install: the eQuilibrator
    import is deferred into the function that needs it."""
    from engin_pathway import rhea

    assert rhea.reaction_equation is reaction_equation


@pytest.mark.network
def test_a_real_identifier_returns_a_parsable_equation():
    eq = reaction_equation("RHEA:10000")
    assert "=" in eq
    assert "pentanamide" in eq


@pytest.mark.network
def test_the_bare_number_is_accepted_too():
    assert reaction_equation("10000") == reaction_equation("RHEA:10000")


@pytest.mark.network
def test_an_unknown_identifier_raises_rather_than_returning_nothing():
    with pytest.raises(RheaLookupError):
        reaction_equation("RHEA:99999999")
