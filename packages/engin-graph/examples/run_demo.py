"""engin-graph demo: rank graph-structured candidates against a count baseline.

Runs on a synthetic domain the package has never heard of — a chain of nodes whose
quality is dominated by its *worst* node. That's the shape `engin-graph` exists for,
and the reason the count-based baseline loses: it can't see which chain contains a
bad node, only how many nodes there are.

    python examples/run_demo.py
"""

from __future__ import annotations

import networkx as nx
import numpy as np

from engin_graph import GraphRanker, best_of_k_regret, spearman

D_IN = 4


class Chain:
    """A chain of nodes, each with D_IN goodness features in [0, 1]."""

    def __init__(self, feats: np.ndarray) -> None:
        self.feats = feats

    def node_features(self) -> np.ndarray:
        return self.feats

    def graph(self) -> nx.Graph:
        return nx.path_graph(len(self.feats))


def truth(feats: np.ndarray) -> float:
    """Worst-node-dominated quality, with a mild length penalty."""
    return float(0.8 * feats.min() + 0.2 * feats.mean() - 0.01 * len(feats))


def make_dataset(n: int, seed: int) -> tuple[list[Chain], np.ndarray]:
    rng = np.random.default_rng(seed)
    objs, ys = [], []
    for _ in range(n):
        feats = rng.uniform(0.2, 1.0, (int(rng.integers(3, 9)), D_IN))
        objs.append(Chain(feats))
        ys.append(truth(feats) + rng.normal(0, 0.01))
    return objs, np.array(ys)


def node_count_baseline(objs: list[Chain]) -> np.ndarray:
    """Fewer nodes assumed better — the heuristic the model must beat."""
    return -np.array([len(o.node_features()) for o in objs], float)


def main() -> None:
    objs, y = make_dataset(400, seed=1)
    train, cal, test = slice(0, 250), slice(250, 320), slice(320, None)

    ranker = GraphRanker(d_in=D_IN, lam=1.0, embed_seed=0)
    ranker.fit(objs[train], y[train])
    ranker.calibrate(objs[cal], y[cal], level=0.90)

    scores = ranker.predict(objs[test])
    lo, hi = ranker.predict_interval(objs[test])
    y_test = y[test]

    print("engin-graph demo — worst-node-dominated synthetic domain")
    print(f"  embedding dim        : {ranker.embedder.dim}")
    print(f"  train / cal / test   : {len(objs[train])} / {len(objs[cal])} / {len(objs[test])}")
    print()
    print("Ranking quality (Spearman rho vs truth)")
    print(f"  graph model          : {spearman(scores, y_test):+.3f}")
    print(f"  node-count baseline  : {spearman(node_count_baseline(objs[test]), y_test):+.3f}")
    print()
    print("Calibration (nominal 90%)")
    print(f"  empirical coverage   : {float(np.mean((y_test >= lo) & (y_test <= hi))):.3f}")
    print(f"  interval half-width  : {ranker.half_width():.4f}")
    print()

    rng = np.random.default_rng(7)
    model_reg, count_reg = [], []
    for _ in range(60):
        g_objs, g_y = make_dataset(6, seed=int(rng.integers(1_000, 100_000)))
        model_reg.append(best_of_k_regret(ranker.predict(g_objs), g_y, k=1))
        count_reg.append(best_of_k_regret(node_count_baseline(g_objs), g_y, k=1))
    print("Best-of-6 selection regret vs oracle (lower is better)")
    print(f"  graph model          : {np.mean(model_reg):.4f}")
    print(f"  node-count baseline  : {np.mean(count_reg):.4f}")
    print()
    print("M0: GCN weights are random and untrained. Not a claim about real-world accuracy.")


if __name__ == "__main__":
    main()
