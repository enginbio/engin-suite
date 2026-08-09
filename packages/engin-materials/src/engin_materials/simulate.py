"""Synthetic structure→property generator, deliberately weakest-link dominated.

The mechanistic caricature: a polymer chain fails where it is weakest. One labile
linkage sets the hydrolytic lifetime of the whole chain regardless of how good the
other ninety-nine units are, and one floppy unit sets the effective stiffness. So the
property is dominated by a **minimum** over units, with a smaller contribution from
the composition average and a real contribution from **topology** (crosslink density).

That shape is why this domain was framed as the materials cousin of metabolic route
ranking: both are "a candidate is killed by its worst part," which is what min-pooling
in ``engin_graph`` exists to preserve and what an averaging heuristic destroys.

**Measured, that framing turns out to be wrong for this domain.** Isolating the two
effects (Spearman ρ, 500 formulations):

    weakest_link  topology_weight   graph   composition
    0.0           0.0               0.969   1.000        baseline is correct, and wins
    0.9           0.0               0.505   0.502        weakest-link only -> a tie
    0.0           0.25              0.678   0.590        topology only -> graph wins
    0.9           0.25              0.512   0.436        both

With topology removed, the graph model **ties** the composition average even at
``weakest_link=0.9``. The whole advantage comes from **topology** — crosslinks, which
are not composition at all — not from seeing which unit is weakest. The likely reason
is that a composition average over a variable-length chain already correlates strongly
with its minimum, so the min-pool adds little that the mean hadn't already implied.

Keep the two knobs separable so this stays checkable rather than becoming folklore.
``weakest_link=0`` and ``topology_weight=0`` together make the heuristic exactly
correct — the negative control the graph model should *not* win.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from .schema import MONOMER_FEATURES, Monomer, Polymer

# Which unit features drive the modelled property, and how strongly.
_PROPERTY_WEIGHTS = np.array([0.30, 0.20, 0.15, 0.25, 0.10])


class PropertyModel:
    """Maps a polymer's structure to a property value in [0, 1]."""

    def __init__(
        self,
        weakest_link: float = 0.6,
        topology_weight: float = 0.25,
    ) -> None:
        if not 0.0 <= weakest_link <= 1.0:
            raise ValueError(f"weakest_link must be in [0,1]; got {weakest_link}")
        if not 0.0 <= topology_weight <= 1.0:
            raise ValueError(f"topology_weight must be in [0,1]; got {topology_weight}")
        self.weakest_link = weakest_link
        self.topology_weight = topology_weight

    def raw(self, polymer: Polymer) -> float:
        X = polymer.node_features()
        per_unit = X @ _PROPERTY_WEIGHTS / _PROPERTY_WEIGHTS.sum()
        structural = (
            self.weakest_link * per_unit.min() + (1.0 - self.weakest_link) * per_unit.mean()
        )
        # Crosslinking helps, with diminishing returns — and over-crosslinking
        # embrittles, so the response is non-monotone. An averaging heuristic sees
        # none of this, because crosslinks aren't composition.
        d = polymer.crosslink_density
        topo = np.clip(1.6 * d - 1.4 * d**2, 0.0, 1.0)
        return float((1.0 - self.topology_weight) * structural + self.topology_weight * topo)

    def value(self, polymer: Polymer) -> float:
        """Property in [0, 1]."""
        return float(np.clip(self.raw(polymer), 0.0, 1.0))


def sample_polymer(
    rng: np.random.Generator,
    polymer_id: str,
    n_units: tuple[int, int] = (8, 20),
    max_crosslink_density: float = 0.5,
) -> Polymer:
    """One unlabeled candidate formulation with random composition and topology."""
    n = int(rng.integers(*n_units))
    units = [
        Monomer(features=dict(zip(MONOMER_FEATURES, rng.uniform(0.15, 1.0, 5), strict=True)))
        for _ in range(n)
    ]
    n_links = int(rng.integers(0, max(1, int(max_crosslink_density * n)) + 1))
    links: set[tuple[int, int]] = set()
    attempts = 0
    while len(links) < n_links and attempts < 50 * max(n_links, 1):
        attempts += 1
        i, j = sorted(rng.choice(n, size=2, replace=False))
        if j - i > 1:
            links.add((int(i), int(j)))
    return Polymer(polymer_id=polymer_id, units=units, crosslinks=sorted(links))


def make_dataset(
    n: int,
    seed: int = 0,
    weakest_link: float = 0.6,
    noise: float = 0.02,
    prefix: str = "p",
    topology_weight: float = 0.25,
) -> list[Polymer]:
    """``n`` labeled formulations — the mechanistic bootstrap, zero partner data.

    ``weakest_link`` and ``topology_weight`` are separable on purpose: the graph
    model has two distinct advantages over a composition average (it sees *which*
    unit is weakest, and it sees topology), and a claim that doesn't say which one is
    doing the work isn't worth much. Set either to zero to isolate the other.
    """
    rng = np.random.default_rng(seed)
    model = PropertyModel(weakest_link=weakest_link, topology_weight=topology_weight)
    out = []
    for i in range(n):
        p = sample_polymer(rng, f"{prefix}{i}")
        y = model.value(p) + rng.normal(0, noise)
        out.append(
            Polymer(
                polymer_id=p.polymer_id,
                units=p.units,
                crosslinks=p.crosslinks,
                property_value=float(np.clip(y, 0.0, 1.0)),
            )
        )
    return out


def true_property(
    polymers: list[Polymer], weakest_link: float = 0.6, topology_weight: float = 0.25
) -> NDArray[np.float64]:
    """Noiseless property values — for scoring, never for training."""
    model = PropertyModel(weakest_link=weakest_link, topology_weight=topology_weight)
    return np.array([model.value(p) for p in polymers], float)
