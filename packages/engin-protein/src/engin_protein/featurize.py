"""Sequence → feature matrix. The one place the heavy-model question lives.

The default is **one-hot plus physicochemical descriptors**: no downloads, no
PyTorch, runs on a laptop. That is a deliberate choice, not a limitation of ambition
— the suite's rule is that the default install stays light (ADR 0002), because a
package nobody can try is a package nobody adopts.

For real work you want a protein language model (ESM-class) or structure-derived
features. Rather than take that dependency, :class:`PrecomputedFeaturizer` accepts an
embedding matrix you produced however you like. The engine downstream cannot tell
which featurizer produced its inputs, which is what makes the swap safe.
"""

from __future__ import annotations

from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from .schema import AA_INDEX, AMINO_ACIDS

# Coarse physicochemical descriptors per residue: hydropathy, volume, charge,
# polarity, aromaticity. Values are normalized to roughly [0,1]; the point is to give
# the kernel a smooth notion of "similar residue", not to be biochemically exact.
_HYDROPATHY = {
    "A": 1.8,
    "C": 2.5,
    "D": -3.5,
    "E": -3.5,
    "F": 2.8,
    "G": -0.4,
    "H": -3.2,
    "I": 4.5,
    "K": -3.9,
    "L": 3.8,
    "M": 1.9,
    "N": -3.5,
    "P": -1.6,
    "Q": -3.5,
    "R": -4.5,
    "S": -0.8,
    "T": -0.7,
    "V": 4.2,
    "W": -0.9,
    "Y": -1.3,
}
_VOLUME = {
    "A": 88.6,
    "C": 108.5,
    "D": 111.1,
    "E": 138.4,
    "F": 189.9,
    "G": 60.1,
    "H": 153.2,
    "I": 166.7,
    "K": 168.6,
    "L": 166.7,
    "M": 162.9,
    "N": 114.1,
    "P": 112.7,
    "Q": 143.8,
    "R": 173.4,
    "S": 89.0,
    "T": 116.1,
    "V": 140.0,
    "W": 227.8,
    "Y": 193.6,
}
_CHARGE = {**dict.fromkeys(AMINO_ACIDS, 0.0), "D": -1.0, "E": -1.0, "K": 1.0, "R": 1.0, "H": 0.5}
_POLAR = set("STNQCYDEKRH")
_AROMATIC = set("FWY")

_N_DESCRIPTORS = 5


def _descriptors(aa: str) -> list[float]:
    return [
        (_HYDROPATHY[aa] + 4.5) / 9.0,
        (_VOLUME[aa] - 60.1) / 167.7,
        (_CHARGE[aa] + 1.0) / 2.0,
        1.0 if aa in _POLAR else 0.0,
        1.0 if aa in _AROMATIC else 0.0,
    ]


_DESCRIPTOR_TABLE = np.array([_descriptors(a) for a in AMINO_ACIDS], dtype=float)


class Featurizer(Protocol):
    """Maps sequences to a ``(n_sequences, d)`` feature matrix."""

    def __call__(self, sequences: list[str]) -> NDArray[np.float64]: ...


class OneHotPhysicochemical:
    """One-hot identity plus physicochemical descriptors, per position.

    Feature width is ``length * (20 + 5)``. That grows quickly, which is fine in the
    low-N regime this serves — with 40 training points the model is
    variance-limited, not width-limited, and the GP's ARD length scales handle the
    irrelevant columns.
    """

    def __init__(self, use_descriptors: bool = True) -> None:
        self.use_descriptors = use_descriptors

    def __call__(self, sequences: list[str]) -> NDArray[np.float64]:
        if not sequences:
            raise ValueError("cannot featurize an empty sequence list")
        L = len(sequences[0])
        if any(len(s) != L for s in sequences):
            raise ValueError("all sequences must share a length to featurize positionally")

        n_aa = len(AMINO_ACIDS)
        width = n_aa + (_N_DESCRIPTORS if self.use_descriptors else 0)
        X = np.zeros((len(sequences), L * width), dtype=float)
        for r, seq in enumerate(sequences):
            for pos, aa in enumerate(seq):
                a = AA_INDEX[aa]
                base = pos * width
                X[r, base + a] = 1.0
                if self.use_descriptors:
                    X[r, base + n_aa : base + width] = _DESCRIPTOR_TABLE[a]
        return X


class PrecomputedFeaturizer:
    """Serves embeddings you computed elsewhere — the PLM path without the dependency.

    Build it with a ``{sequence: vector}`` mapping. Raises on an unseen sequence
    rather than silently substituting a zero vector, because a zero vector is a
    perfectly plausible-looking input that quietly poisons a low-N fit.
    """

    def __init__(self, embeddings: dict[str, NDArray[np.float64]]) -> None:
        if not embeddings:
            raise ValueError("embeddings mapping is empty")
        widths = {len(np.asarray(v).ravel()) for v in embeddings.values()}
        if len(widths) > 1:
            raise ValueError(f"embeddings must share a width; got {sorted(widths)}")
        self._emb = {k: np.asarray(v, float).ravel() for k, v in embeddings.items()}
        self.width = widths.pop()

    def __call__(self, sequences: list[str]) -> NDArray[np.float64]:
        missing = [s for s in sequences if s not in self._emb]
        if missing:
            raise KeyError(
                f"{len(missing)} sequence(s) have no precomputed embedding "
                f"(first: {missing[0][:20]}...). Compute embeddings for the full library."
            )
        return np.vstack([self._emb[s] for s in sequences])
