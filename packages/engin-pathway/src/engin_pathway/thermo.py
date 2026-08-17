"""Turn a reaction Gibbs energy into ``g_thermo``, carrying its uncertainty.

`#140` item 1: ``g_thermo`` is currently a number the user types. This is the
transform that lets it come from a measurement instead, and the transform is a
**modelling choice** rather than a lookup -- so it is written down here with what
it assumes.

## The transform, and why this one

``g_thermo`` must be in [0, 1] with higher meaning better. The obvious move is to
rescale ΔG'° linearly over some plausible range, and the range would be arbitrary
-- a knob nobody could argue with because it means nothing.

Instead:

.. math::

    g = \\frac{1}{1 + e^{\\Delta_r G'^\\circ / RT}}

which is **the equilibrium mole fraction of product** for a one-to-one reaction at
unit activities, since :math:`K_{eq} = e^{-\\Delta_r G'^\\circ / RT}` and the product
fraction is :math:`K/(1+K)`. It is bounded in [0, 1] by construction rather than by
clipping, monotone decreasing in ΔG, and it lands at exactly 0.5 when ΔG'° = 0 --
a reaction with no thermodynamic preference scores neutral, which is the behaviour
you would want a "goodness" score to have and not a coincidence of tuning.

So the number has a meaning a reviewer can argue with: *the fraction of this step
that sits on the product side at equilibrium under standard conditions*.

## What it assumes, stated because the assumptions bite

**One-to-one stoichiometry at unit activities.** For :math:`A \\rightleftharpoons B`
the expression is exact. For :math:`A \\rightleftharpoons 2B`, or any reaction whose
mole counts differ across the arrow, the equilibrium fraction is a different
function of :math:`K` and this one is an approximation. It stays monotone and stays
in [0, 1], so the *ranking* it produces is defensible where the absolute value is
not.

**Standard state, not physiological.** ΔG'° assumes 1 M reactants. Real cellular
concentrations move it, sometimes across zero -- which is the difference between
"thermodynamically unfavourable" and "unfavourable at the concentrations this cell
actually runs". eQuilibrator can compute the physiological value given
concentrations, and that would be the better input; it needs concentration data
this package does not have.

**RT is fixed at 298.15 K.** Fermentations run warmer. The sensitivity is mild
over the range that matters -- RT moves about 4% between 25 °C and 37 °C -- but it
is a fixed constant here rather than a modelled one.

**It saturates, and the threshold is further out than it looks.** Below about
**-91 kJ/mol the score is exactly 1.0** in double precision, so steps at -95 and
-200 are indistinguishable. That is physically right -- both go to completion, and
nothing is more complete than complete -- but it bounds what this feature can
separate.

The practical range matters more than the hard limit: by -30 kJ/mol the score is
already 0.99999, so *discrimination among favourable steps is effectively gone
long before the float does*. Anything below roughly -30 is "goes to completion" as
far as a ranking is concerned. If a route's ordering turns on distinguishing -40
from -80, this feature is not the one carrying that information.

The unfavourable tail behaves differently and does not saturate: +200 kJ/mol still
evaluates to about 9e-36 rather than to zero, so strongly unfavourable steps stay
ordered.

## Where the number comes from

``equilibrator-api`` returns ΔG'° as a ``Measurement`` carrying a standard
deviation -- ``-44.8 ± 0.6 kJ/mol`` in its own tutorial's example -- so this
feature can be an interval rather than a point value, which is what the rest of
this project would expect of it. :func:`g_thermo_interval` maps that through.

It is an **optional extra** (``pip install engin-pathway[thermo]``) and not a
default dependency, for two measured reasons rather than taste: it requires
Python >= 3.11 where this package supports >= 3.10, and its first call downloads
a compound database from Zenodo that its own documentation puts at about ten
minutes. The same shape as engin-core's ``[tea]`` extra for BioSTEAM.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.special import expit

__all__ = ["RT_KJ_PER_MOL", "g_thermo", "g_thermo_interval"]

RT_KJ_PER_MOL = 8.314462618e-3 * 298.15
"""Gas constant times 298.15 K, in kJ/mol -- about 2.479.

kJ/mol because that is what eQuilibrator returns.
"""


def g_thermo(dg_prime_standard: ArrayLike) -> NDArray[np.float64]:
    """Map ΔG'° in kJ/mol to a goodness score in [0, 1], higher = more favourable.

    Uses :func:`scipy.special.expit` rather than writing the logistic out, because
    the naive form overflows for strongly unfavourable reactions: ``exp(200/2.479)``
    is about 1e35 and the ratio that follows loses precision long before it raises.
    """
    dg = np.asarray(dg_prime_standard, float)
    return np.asarray(expit(-dg / RT_KJ_PER_MOL), float)


def g_thermo_interval(
    dg_prime_standard: ArrayLike, sd: ArrayLike
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """One-sigma bounds on :func:`g_thermo`, as ``(low, high)``.

    **The bounds swap on the way through**, which is the whole reason this is a
    function rather than a comment. ``g_thermo`` is *decreasing* in ΔG, so the
    upper bound on the score comes from the *lower* bound on the energy. Mapping
    ``(dg - sd, dg + sd)`` in order would return an inverted interval that still
    looks plausible.

    Exact rather than propagated: the transform is monotone, so mapping the
    endpoints gives the true image of the input interval. No delta-method
    approximation is involved and none is needed.
    """
    dg = np.asarray(dg_prime_standard, float)
    s = np.abs(np.asarray(sd, float))
    return g_thermo(dg + s), g_thermo(dg - s)
