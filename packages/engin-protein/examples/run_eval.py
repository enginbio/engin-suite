"""The ``evaluate`` face [Plan 2]: rank designs, against a structure-confidence proxy.

    python examples/run_eval.py

Sweeps epistasis, because that is where the story lives: a confidence proxy tracks
the additive part of fitness and is blind to interactions, so the learned ranker's
advantage should widen as epistasis rises.
"""
from __future__ import annotations

import numpy as np

from engin_protein import DesignEvaluator, make_landscape

CAMPAIGN_N = 80
LIBRARY_N = 300


def main() -> None:
    print("engin-protein — evaluate face [Plan 2]")
    print(f"  campaign {CAMPAIGN_N} measured variants -> rank a {LIBRARY_N}-design library\n")
    print(f"  {'epistasis':>10}  {'model rho':>10}  {'proxy rho':>10}  "
          f"{'model hit@10':>13}  {'proxy hit@10':>13}  {'coverage':>9}")
    print("  " + "-" * 74)

    for eps in (0.0, 0.3, 0.5, 0.8):
        ls = make_landscape(epistasis=eps, seed=0)
        ev = DesignEvaluator().fit(ls.sample_campaign(CAMPAIGN_N, seed=1))
        lib = ls.library(LIBRARY_N, seed=2)
        truth = ls.true_fitness(lib)
        res = ev.compare_to_baseline(lib, truth, ls.confidence_scores(lib), k=10)

        scored = ev.model.score(lib)
        lo = np.array([s.lower for s in scored])
        hi = np.array([s.upper for s in scored])
        cov = float(np.mean((truth >= lo) & (truth <= hi)))

        print(f"  {eps:>10.1f}  {res['model_spearman']:>+10.3f}  {res['baseline_spearman']:>+10.3f}"
              f"  {res['model_hit_rate']:>13.2f}  {res['baseline_hit_rate']:>13.2f}  {cov:>9.3f}")

    print("\n  hit@10 = fraction of the top-10 picks that are truly top-decile.")
    print("  Random selection scores 0.10 by construction.")
    print("  Coverage is nominal 90%; it runs conservative because the calibration")
    print("  split is small, which is the safe direction.")
    print("\n  M0: synthetic landscape, and the proxy is a constructed stand-in for")
    print("  pLDDT/ipTM. This shows the loop is wired and calibrated — it is NOT")
    print("  evidence about real structure-confidence metrics. That needs wet data (M1).")


if __name__ == "__main__":
    main()
