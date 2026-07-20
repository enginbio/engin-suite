"""Demo: learn to rank candidate metabolic routes by manufacturability from graph
structure, with calibrated intervals — and beat the step-count heuristic at
picking the best route among alternatives.

Run:  python examples/run_demo.py    (needs matplotlib)
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from engin_pathway import (
    PathwayRanker,
    labels,
    make_dataset,
    sample_route,
    spearman,
    step_counts,
)

OUT = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUT, exist_ok=True)


def main():
    data = make_dataset(500, seed=1)
    y = labels(data)
    tr, ca, te = slice(0, 320), slice(320, 410), slice(410, 500)

    ranker = PathwayRanker(lam=1.0, embed_seed=0).fit(data[tr])
    ranker.calibrate(data[ca], level=0.90)

    # ---- test-set forecast quality + calibration ----
    pred_te = ranker.predict(data[te])
    yte = y[te]
    rmse = float(np.sqrt(np.mean((pred_te - yte) ** 2)))
    ss = 1 - np.sum((pred_te - yte) ** 2) / np.sum((yte - yte.mean()) ** 2)
    hw = ranker.half_width()
    cover = float(np.mean(np.abs(pred_te - yte) <= hw))
    rho = spearman(pred_te, yte)
    rho_base = spearman(-step_counts(data[te]), yte)         # step-count as a ranker

    # ---- the real task: pick the best route among alternatives ----
    rng = np.random.default_rng(7)
    G, K = 80, 6
    oracle, modelp, basep, randp = [], [], [], []
    for gi in range(G):
        grp = [sample_route(rng, f"g{gi}_{k}") for k in range(K)]
        yt = labels(grp)
        pr = ranker.predict(grp)
        L = step_counts(grp)
        oracle.append(yt.max())
        modelp.append(yt[int(np.argmax(pr))])
        basep.append(yt[int(np.argmin(L))])                 # fewest steps
        randp.append(yt[int(rng.integers(K))])
    oracle, modelp, basep, randp = map(np.array, (oracle, modelp, basep, randp))
    win = float(np.mean(modelp > basep))
    def reg(a):
        return float(np.mean(oracle - a))

    print("=== engin-pathway — session-1 slice ===")
    print(f"Manufacturability forecast (test): R²={ss:.2f}  RMSE={rmse:.3f}  "
          f"90% coverage={cover:.2f}")
    print(f"Ranking (Spearman ρ):  graph model {rho:.2f}   vs   step-count {rho_base:.2f}")
    print(f"Best-route pick among {K} alternatives ({G} groups):")
    print(f"   mean true manufacturability of pick — "
          f"oracle {oracle.mean():.3f} | model {modelp.mean():.3f} | "
          f"step-count {basep.mean():.3f} | random {randp.mean():.3f}")
    print(f"   model beats step-count in {win:.0%} of groups")
    print(f"   regret vs oracle — model {reg(modelp):.3f} | "
          f"step-count {reg(basep):.3f} | random {reg(randp):.3f}")

    # ---- plots ----
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.errorbar(yte, pred_te, yerr=hw, fmt="o", ms=4, capsize=2,
                color="#6b46c1", ecolor="#d6bcfa", alpha=0.8, label="test routes (90% PI)")
    lim = [0, max(yte.max(), pred_te.max()) * 1.1]
    ax.plot(lim, lim, "k--", lw=1)
    ax.set_xlabel("true manufacturability")
    ax.set_ylabel("predicted")
    ax.set_title(f"Pathway forecast  R²={ss:.2f}  ρ={rho:.2f}  cov={cover:.0%}")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{OUT}/pathway_forecast.png", dpi=130)

    fig, ax = plt.subplots(figsize=(5.2, 3.4))
    ax.bar(["oracle", "graph model", "step-count", "random"],
           [oracle.mean(), modelp.mean(), basep.mean(), randp.mean()],
           color=["#2f855a", "#6b46c1", "#a0aec0", "#e2e8f0"])
    ax.set_ylabel("mean true manufacturability of pick")
    ax.set_title(f"Best-route selection ({K} alternatives) — model beats step-count {win:.0%}")
    fig.tight_layout()
    fig.savefig(f"{OUT}/pathway_selection.png", dpi=130)

    with open(f"{OUT}/pathway-ranking-memo.md", "w") as f:
        f.write(
            f"# Pathway ranking memo (auto-generated)\n"
            f"_engin-pathway first slice — random-weight GCN + ridge + split conformal, "
            f"on {len(data)} synthetic routes._\n\n"
            f"- Manufacturability forecast (held-out): **R² {ss:.2f}**, RMSE {rmse:.3f}, "
            f"**90% coverage {cover:.0%}**.\n"
            f"- Ranking quality (Spearman ρ): **graph model {rho:.2f}** "
            f"vs step-count {rho_base:.2f}.\n"
            f"- Picking the best of {K} candidate routes: model lands at "
            f"**{modelp.mean():.3f}** mean true manufacturability vs step-count "
            f"{basep.mean():.3f} (oracle {oracle.mean():.3f}); **beats step-count in "
            f"{win:.0%} of cases**, cutting regret-vs-oracle from {reg(basep):.3f} to "
            f"{reg(modelp):.3f}.\n\n"
            f"Reading: step-count is a real but blunt heuristic; reading graph structure "
            f"(esp. the worst step via max/min-pooling) recovers the manufacturability "
            f"signal it misses. Next: a trained GNN (PyG) + real KEGG/MetaCyc routes.\n"
        )
    print("\nWrote outputs/ -> pathway_forecast.png, pathway_selection.png, "
          "pathway-ranking-memo.md")


if __name__ == "__main__":
    main()
