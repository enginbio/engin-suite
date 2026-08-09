"""Synthetic fitness landscape with a tunable epistasis knob.

The mechanistic-first bootstrap: prove every loop here, with zero partner data and
no downloads, before touching real assay data (M1).

**The model.** Fitness is a mixture of an additive term and a pairwise-epistatic one::

    f(x) = (1 - e) * sum_i  a[i, x_i]
         +      e  * sum_(i,j) b[i, j, x_i, x_j]

with ``e = epistasis`` in [0, 1]. At ``e = 0`` a linear model on one-hot features is
*exactly* correct, so any advantage a GP shows there is noise or overfitting — which
makes ``e = 0`` a useful negative control, not just a boring case. As ``e`` rises the
additive model becomes progressively mis-specified, and the gap between an additive
baseline and an interaction-capturing model is the thing the low-N face sells.

**Why this shape.** Real epistasis is sparse and mostly pairwise-dominated at the
scales these campaigns explore, so a sparse random interaction graph is a defensible
caricature. It is still a caricature: no structural constraints, no fold stability
cliff, no assay-specific saturation.

**The design space is a combinatorial library, not free sequence space.** Variants
range over a handful of *designable sites* with a restricted alphabet — site-saturation
at 8 positions with 6 options each, say. That is what these campaigns actually explore,
and it matters for more than realism: a landscape over free 20-mers spans 20^20
sequences, and no model learns anything useful about it from 40 measurements. Getting
this wrong makes a working model look broken. The full-length protein is assumed fixed
outside the designable region, so a ``sequence`` here is the variable region.

**A deliberately weak "confidence" signal.** :meth:`FitnessLandscape.confidence`
returns a foldability-like score correlated with the additive component but only
weakly with total fitness. That mirrors what the literature reports about pLDDT/ipTM
— they capture whether a structure is *plausible*, not whether it *works* — and it
is what the ``evaluate`` face is benchmarked against at M0. Because we constructed
that weakness, beating it here tests plumbing, not the hypothesis. See the README.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from .schema import AMINO_ACIDS, Campaign, Variant


class FitnessLandscape:
    """A synthetic sequence→fitness map with controllable epistasis."""

    def __init__(
        self,
        length: int,
        epistasis: float,
        n_interactions: int,
        rng: np.random.Generator,
        alphabet: str = AMINO_ACIDS,
    ) -> None:
        if not 0.0 <= epistasis <= 1.0:
            raise ValueError(f"epistasis must be in [0,1]; got {epistasis}")
        if length < 2:
            raise ValueError("length must be at least 2 for pairwise epistasis")
        self.length = length
        self.epistasis = epistasis
        self.alphabet = alphabet
        A = len(alphabet)
        self._aa_index = {a: i for i, a in enumerate(alphabet)}

        # Additive site effects, and a sparse pairwise interaction graph.
        self._add = rng.normal(0, 1, (length, A))
        # A separate "structural" field driving the confidence proxy. Confidence is a
        # blend of this and the additive term, so it *overlaps* with function without
        # being a transform of it — which is the actual relationship pLDDT has to
        # activity. Without this the proxy would be a noiseless oracle of the additive
        # component and any comparison against it would be rigged in the model's favour
        # at low epistasis (and against it at high).
        self._conf_field = rng.normal(0, 1, (length, A))
        self._conf_divergence = 0.5
        max_pairs = length * (length - 1) // 2
        n_interactions = min(n_interactions, max_pairs)
        pairs = rng.choice(max_pairs, size=n_interactions, replace=False)
        triu = [(i, j) for i in range(length) for j in range(i + 1, length)]
        self._pairs = [triu[p] for p in pairs]
        self._epi = rng.normal(0, 1, (n_interactions, A, A))

        # Calibrate the [0,1] normalization on a random sample, so fitness values are
        # comparable across landscapes with different epistasis settings.
        probe = np.array([self._raw(self._random_seq(rng)) for _ in range(512)])
        self._lo, self._hi = float(probe.min()), float(probe.max())
        if self._hi - self._lo < 1e-9:  # degenerate landscape
            self._hi = self._lo + 1.0

    # ---------------------------------------------------------------- internals

    def _random_seq(self, rng: np.random.Generator) -> str:
        return "".join(rng.choice(list(self.alphabet), size=self.length))

    def _raw(self, sequence: str) -> float:
        idx = [self._aa_index[c] for c in sequence]
        additive = sum(self._add[i, a] for i, a in enumerate(idx))
        epi = 0.0
        for k, (i, j) in enumerate(self._pairs):
            epi += self._epi[k, idx[i], idx[j]]
        return (1.0 - self.epistasis) * additive + self.epistasis * epi

    def _additive_only(self, sequence: str) -> float:
        idx = [self._aa_index[c] for c in sequence]
        return float(sum(self._add[i, a] for i, a in enumerate(idx)))

    # ------------------------------------------------------------------- public

    def fitness(self, sequence: str) -> float:
        """True fitness in [0, 1]."""
        if len(sequence) != self.length:
            raise ValueError(f"sequence length {len(sequence)} != landscape length {self.length}")
        return float(np.clip((self._raw(sequence) - self._lo) / (self._hi - self._lo), 0.0, 1.0))

    def confidence(self, sequence: str) -> float:
        """A foldability-like score: overlaps with function, blind to epistasis.

        The pLDDT/ipTM stand-in — a deterministic function of sequence, blending the
        additive fitness term with a separate structural field. It is *constructed* to
        be partially informative, so see the module docstring before reading anything
        into a comparison against it.
        """
        idx = [self._aa_index[c] for c in sequence]
        struct = float(sum(self._conf_field[i, a] for i, a in enumerate(idx)))
        w = self._conf_divergence
        blended = (1.0 - w) * self._additive_only(sequence) + w * struct
        # Squash to [0,1] with a logistic; scale chosen so the spread is realistic.
        return float(1.0 / (1.0 + np.exp(-blended / max(1.0, np.sqrt(self.length)))))

    def library(self, n: int, seed: int = 0, prefix: str = "lib") -> list[Variant]:
        """``n`` unmeasured candidate variants — the design library to rank.

        ``prefix`` namespaces the ids. A seed campaign and a design library get
        different prefixes so that pooling them (as the planner does) doesn't trip
        the uniqueness check with two unrelated variants sharing ``lib0``.
        """
        rng = np.random.default_rng(seed)
        return [
            Variant(variant_id=f"{prefix}{i}", sequence=self._random_seq(rng)) for i in range(n)
        ]

    def measure(self, variants: list[Variant], noise: float = 0.02, seed: int = 0) -> list[Variant]:
        """Assay the variants: true fitness plus Gaussian readout noise, clipped to [0,1]."""
        rng = np.random.default_rng(seed)
        out = []
        for v in variants:
            y = self.fitness(v.sequence) + rng.normal(0, noise)
            out.append(
                Variant(
                    variant_id=v.variant_id,
                    sequence=v.sequence,
                    fitness=float(np.clip(y, 0.0, 1.0)),
                )
            )
        return out

    def sample_campaign(
        self,
        n: int,
        seed: int = 0,
        noise: float = 0.02,
        campaign_id: str = "synthetic",
        prefix: str | None = None,
    ) -> Campaign:
        """A measured campaign of ``n`` variants — the low-N training substrate.

        Ids are namespaced by ``campaign_id`` unless ``prefix`` overrides it, so two
        campaigns can be pooled for transfer without id collisions.
        """
        lib = self.library(n, seed=seed, prefix=prefix or f"{campaign_id}_")
        return Campaign(campaign_id=campaign_id, variants=self.measure(lib, noise=noise, seed=seed))

    def related(self, similarity: float = 0.8, seed: int = 0) -> FitnessLandscape:
        """A *related* landscape — the realistic transfer setting.

        Blends this landscape's fields with fresh random ones at weight
        ``similarity``. ``1.0`` reproduces this landscape exactly; ``0.0`` is an
        unrelated protein.

        This exists because pooling a prior campaign drawn from the *same* landscape
        measures "more data," not transfer, and would overstate the case for
        cross-project priors — which are supposed to be the moat, so the test has to
        be the honest one.
        """
        if not 0.0 <= similarity <= 1.0:
            raise ValueError(f"similarity must be in [0,1]; got {similarity}")
        rng = np.random.default_rng(seed)
        other = FitnessLandscape(
            length=self.length,
            epistasis=self.epistasis,
            n_interactions=len(self._pairs),
            rng=rng,
            alphabet=self.alphabet,
        )
        w = similarity
        other._add = w * self._add + (1 - w) * other._add
        other._conf_field = w * self._conf_field + (1 - w) * other._conf_field
        other._pairs = list(self._pairs)  # share the interaction topology
        other._epi = w * self._epi + (1 - w) * other._epi
        probe = np.array([other._raw(other._random_seq(rng)) for _ in range(512)])
        other._lo, other._hi = float(probe.min()), float(probe.max())
        if other._hi - other._lo < 1e-9:
            other._hi = other._lo + 1.0
        return other

    def true_fitness(self, variants: list[Variant]) -> NDArray[np.float64]:
        """Noiseless true fitness for a list of variants — for scoring, never for training.

        Evaluations score true-vs-true. The best *observed* variant can be a
        noise-inflated outlier above what the landscape can actually produce, and
        scoring against it is an unfair bar.
        """
        return np.array([self.fitness(v.sequence) for v in variants], float)

    def confidence_scores(self, variants: list[Variant]) -> NDArray[np.float64]:
        """The pLDDT/ipTM-style baseline signal for a list of variants."""
        return np.array([self.confidence(v.sequence) for v in variants], float)


# A chemically spread-out default alphabet: small/polar/charged/hydrophobic/aromatic.
# Site-saturation libraries are usually built from a reduced set like this rather than
# all 20 residues, and the reduced space is what makes low-N learning tractable.
DEFAULT_ALPHABET = "AGSDKLVW"


def make_landscape(
    length: int = 8,
    epistasis: float = 0.5,
    n_interactions: int = 12,
    seed: int = 0,
    alphabet: str = DEFAULT_ALPHABET,
) -> FitnessLandscape:
    """Build a landscape over a combinatorial library of designable sites.

    Defaults describe site-saturation at 8 positions over an 8-residue alphabet —
    about 16.7M variants, explorable from tens of measurements. ``epistasis=0`` makes
    an additive model exactly correct, which is the useful negative control.
    """
    return FitnessLandscape(
        length=length,
        epistasis=epistasis,
        n_interactions=n_interactions,
        rng=np.random.default_rng(seed),
        alphabet=alphabet,
    )
