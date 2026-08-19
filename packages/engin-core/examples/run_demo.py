"""End-to-end demo of engin-core's core loop:

    simulate a small DoE  ->  fit an uncertainty-aware titer model
    ->  calibrate the intervals (split conformal)  ->  check they are honest
    ->  recommend the next DoE batch  ->  cost it  ->  write the memo.

Everything runs on synthetic mechanistic data (``engin_core.simulator``), so no
partner data is required to demonstrate the value proposition. The active-
learning step is *self-validating*: we simulate the "true" titer of the runs
the model recommends, so we can see whether it actually found higher-titer
conditions than the initial DoE explored.

Run:  python examples/run_demo.py    (needs numpy + matplotlib)
"""

from __future__ import annotations

import csv
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from engin_core import (
    ard_importance,
    fit_gp,
    prob_at_least,
    recommend_batch,
    simulate_unit,
    split_conformal_multiplier,
    unit_to_physical,
)
from engin_core import simulator as sim
from engin_core.tea import CostParameters, cost_summary

OUT = os.path.join(os.path.dirname(__file__), "outputs")
RNG = np.random.default_rng(7)


def add_noise(y, rng, rel=0.05, abs_=0.4):
    return np.maximum(y + rng.normal(0, rel * y + abs_), 0.0)


def main():
    # Created here rather than at import. Importing a module should not touch the
    # filesystem, and the smoke test in tests/test_run_demo.py points OUT at a tmp
    # directory before calling main() -- which only works if the directory is made
    # when the demo runs rather than when it is imported.
    os.makedirs(OUT, exist_ok=True)
    d = len(sim.KNOB_NAMES)

    # ---- 1. Synthetic runs, split train / calibration / test (all same dist) ----
    N = 120
    U = RNG.random((N, d))
    y_true = simulate_unit(U)
    y_obs = add_noise(y_true, RNG)  # full set of known runs
    tr, ca, te = slice(0, 70), slice(70, 100), slice(100, 120)
    n_tr, n_ca, n_te = 70, 30, 20
    gp = fit_gp(U[tr], y_obs[tr])  # fit on 70 training runs

    # ---- 2. Split-conformal interval calibration on the 30 calibration runs ----
    mc, sdc = gp.predict(U[ca], include_noise=True)
    z90 = split_conformal_multiplier(y_obs[ca], mc, sdc, level=0.90)
    gp.q90 = z90

    # ---- 3. Forecast quality on the untouched 20 test runs ----
    m_te, sd_te = gp.predict(U[te], include_noise=True)
    y_obs_te = y_obs[te]
    resid = m_te - y_obs_te
    rmse = float(np.sqrt(np.mean(resid**2)))
    ss = 1 - np.sum(resid**2) / np.sum((y_obs_te - y_obs_te.mean()) ** 2)
    cover = float(np.mean(np.abs(resid) <= z90 * sd_te))  # target ~0.90

    # ---- 4. Sensitivity: which knobs move titer ----
    imp = ard_importance(gp)
    order = np.argsort(-imp)

    # ---- 5. Recommend the next DoE batch (active learning) ----
    best_prior = float(y_obs.max())
    Xnext, m_next, sd_next, ei = recommend_batch(gp, best_prior, k=8, seed=3)
    phys_next = unit_to_physical(Xnext)
    y_next_true = simulate_unit(Xnext)  # self-validation
    best_new = float(y_next_true.max())
    lift = 100.0 * (best_new - best_prior) / best_prior

    # ---- 6. P(hit target) for a stretch target ----
    # Cost the two designs the bottom line compares (#231). The memo's headline used
    # to be titer lift, which is the metric D13 exists to argue against -- the one
    # artifact a human reads should not close on it.
    i_best_known = int(np.argmax(y_obs))
    costs = cost_summary(gp, np.vstack([U[i_best_known], Xnext[int(np.argmax(y_next_true))]]))
    cost_params = CostParameters()

    target = float(np.percentile(y_obs, 95))
    p_best_known = float(prob_at_least(*gp.predict(U[[np.argmax(y_obs)]]), target)[0])
    p_reco = float(prob_at_least(m_next[[0]], sd_next[[0]], target)[0])

    # ---------- console report ----------
    print("=== engin-core demo — session-1 slice ===")
    print(f"Runs: {N}  (train {n_tr} / calibration {n_ca} / test {n_te})")
    print(
        f"Forecast on held-out runs:  RMSE={rmse:.2f} g/L   R^2={ss:.2f}   "
        f"90%-interval coverage={cover:.2f}"
    )
    print("Titer drivers (ARD sensitivity, desc):")
    for j in order:
        print(f"   {sim.KNOB_NAMES[j]:14s} {imp[j] * 100:5.1f}%")
    print(f"Best titer in initial DoE:      {best_prior:.2f} g/L")
    print(f"Best titer among 8 recommended: {best_new:.2f} g/L   ({lift:+.1f}% vs best prior)")
    print(f"Stretch target (95th pct):      {target:.2f} g/L")
    print(f"P(hit target) best-known cond:  {p_best_known:.2f}")
    print(f"P(hit target) top recommendation:{p_reco:.2f}")

    # ---------- plots ----------
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.errorbar(
        y_obs_te,
        m_te,
        yerr=z90 * sd_te,
        fmt="o",
        capsize=3,
        color="#2b6cb0",
        ecolor="#90cdf4",
        label="held-out runs (90% PI)",
    )
    lim = [0, max(y_obs_te.max(), m_te.max()) * 1.1]
    ax.plot(lim, lim, "k--", lw=1, label="perfect")
    ax.set_xlabel("actual titer (g/L)")
    ax.set_ylabel("predicted titer (g/L)")
    ax.set_title(f"Forecast calibration\nRMSE={rmse:.1f}  R²={ss:.2f}  cov={cover:.0%}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(f"{OUT}/calibration.png", dpi=130)

    fig, ax = plt.subplots(figsize=(6, 3.4))
    ax.barh(
        [sim.KNOB_NAMES[j] for j in order[::-1]],
        [imp[j] * 100 for j in order[::-1]],
        color="#38a169",
    )
    ax.set_xlabel("relative sensitivity (%)")
    ax.set_title("Which knobs move titer (ARD)")
    fig.tight_layout()
    fig.savefig(f"{OUT}/sensitivity.png", dpi=130)

    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.hist(y_obs, bins=12, color="#cbd5e0", label="initial DoE titers")
    ax.axvline(best_prior, color="#718096", ls="--", label=f"best prior {best_prior:.0f}")
    ax.scatter(
        y_next_true,
        np.full_like(y_next_true, 1.0),
        color="#dd6b20",
        zorder=5,
        label="recommended (realized)",
    )
    ax.axvline(best_new, color="#dd6b20", ls="--", label=f"best new {best_new:.0f}")
    ax.set_xlabel("titer (g/L)")
    ax.set_ylabel("count")
    ax.set_title("Active-learning batch beats the initial DoE")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(f"{OUT}/active_learning.png", dpi=130)

    # ---------- artifacts: dataset + memo ----------
    phys = unit_to_physical(U)
    with open(f"{OUT}/doe_dataset.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(sim.KNOB_NAMES + ["titer_obs_gL", "titer_true_gL"])
        for i in range(N):
            w.writerow([f"{v:.3f}" for v in phys[i]] + [f"{y_obs[i]:.2f}", f"{y_true[i]:.2f}"])

    write_memo(
        f"{OUT}/doe-round-reduction-memo.md",
        N,
        n_tr,
        n_te,
        rmse,
        ss,
        cover,
        order,
        imp,
        best_prior,
        best_new,
        lift,
        target,
        p_best_known,
        p_reco,
        phys_next,
        m_next,
        sd_next,
        costs,
        cost_params,
    )
    print(
        "\nWrote outputs/ -> calibration.png, sensitivity.png, active_learning.png, "
        "doe_dataset.csv, doe-round-reduction-memo.md"
    )


def write_memo(
    path,
    n,
    ntr,
    nte,
    rmse,
    ss,
    cover,
    order,
    imp,
    best_prior,
    best_new,
    lift,
    target,
    p_best,
    p_reco,
    phys_next,
    m_next,
    sd_next,
    costs,
    cost_params,
):
    L = []
    L.append("# DoE round-reduction memo (auto-generated)\n")
    L.append(
        f"_engin-core demo — trained on {ntr} DoE runs, "
        f"validated on {nte} independent held-out runs._\n"
    )
    # The tier caveat travels with the artifact (#231). This is the surface most
    # likely to leave the repo as a screenshot, and it was the only public one
    # that did not say its numbers came from a simulator.
    L.append(
        "\n> **Tier 1 — simulator output, not laboratory data.** Every run below is "
        "`engin_core.simulator`, so this memo shows that the loop is wired and "
        "calibrated end to end. It is not evidence about any real strain or plant. "
        "See `docs/limitations.md` for what each validation tier does and does not "
        "establish.\n\n"
    )
    L.append("## Forecast quality (held-out)\n")
    L.append(f"- RMSE **{rmse:.1f} g/L**, R² **{ss:.2f}**\n")
    L.append(f"- 90% predictive-interval coverage **{cover:.0%}** (target ~90%)\n")
    L.append("\n## What actually drives titer\n")
    for j in order:
        L.append(f"- **{sim.KNOB_NAMES[j]}** — {imp[j] * 100:.0f}% relative sensitivity\n")
    L.append("\n## Recommended next DoE batch (highest expected improvement)\n")
    L.append("| # | " + " | ".join(sim.KNOB_NAMES) + " | pred titer (g/L) |\n")
    L.append("|---|" + "|".join(["---"] * (len(sim.KNOB_NAMES) + 1)) + "|\n")
    for i in range(len(m_next)):
        row = " | ".join(f"{v:.2f}" for v in phys_next[i])
        L.append(f"| {i + 1} | {row} | {m_next[i]:.1f} ± {1.645 * sd_next[i]:.1f} |\n")
    L.append("\n## Bottom line\n")
    L.append(f"- Best titer in the existing {n}-run DoE: **{best_prior:.1f} g/L**.\n")
    L.append(
        f"- Best titer among the 8 model-recommended runs (simulated): "
        f"**{best_new:.1f} g/L** (**{lift:+.0f}%**).\n"
    )
    L.append(
        f"- Stretch target (95th pct of current data): **{target:.1f} g/L**. "
        f"P(hit) rises from **{p_best:.0%}** at the best known condition to "
        f"**{p_reco:.0%}** at the top recommendation.\n"
    )
    L.append(
        "- Interpretation: one active-learning round moved the frontier without "
        "any new wet runs beyond the recommended batch — the DoE-round-reduction "
        "claim, demonstrated on mechanistic data.\n"
    )

    known, reco = costs
    d_cost = 100.0 * (reco.expected_usd_per_kg - known.expected_usd_per_kg)
    d_cost /= known.expected_usd_per_kg
    disjoint = (
        reco.upper_usd_per_kg < known.lower_usd_per_kg
        or known.upper_usd_per_kg < reco.lower_usd_per_kg
    )
    L.append("\n## What it costs\n")
    L.append(
        f"- Best known condition: **${known.expected_usd_per_kg:.2f}/kg** "
        f"(90% {known.lower_usd_per_kg:.2f}–{known.upper_usd_per_kg:.2f}).\n"
    )
    L.append(
        f"- Top recommendation: **${reco.expected_usd_per_kg:.2f}/kg** "
        f"(90% {reco.lower_usd_per_kg:.2f}–{reco.upper_usd_per_kg:.2f}) — "
        f"**{d_cost:+.1f}%**.\n"
    )
    L.append(
        f"- Against a **${cost_params.target_usd_per_kg:.0f}/kg** target, P(clears) is "
        f"**{known.prob_meets_target:.0%}** and **{reco.prob_meets_target:.0%}**.\n"
    )
    L.append(
        f"- The two cost intervals {'do not overlap' if disjoint else 'overlap'}, so "
        f"the cost ranking {'is' if disjoint else 'is not'} decisive at this sample "
        f"size.\n"
    )
    L.append(
        f"- **Read the two deltas together.** Titer moved **{lift:+.0f}%** and cost "
        f"**{d_cost:+.1f}%** — cost improves, but not in lockstep, because this "
        "process is facility- and downstream-dominated and the yield lever is "
        "correspondingly muted. `D13` is the decision to optimize net $/kg rather "
        "than titer; this section is what that decision looks like when it is "
        "measured instead of asserted.\n"
    )
    L.append(
        "- **This is not a demonstration that cost optimization picks a different "
        "design.** Here the cheaper design is also the higher-titer one, so titer "
        "would have chosen the same batch. `docs/limitations.md` records why they "
        "coincide on this simulator, and showing them disagree needs a process "
        "where pushing titer costs yield or rate.\n"
    )
    L.append(
        "- The cost interval is a **propagated credible interval, not a conformal "
        "one** — it carries the GP's titer uncertainty through the cost model. "
        "Calibrating it would need held-out *cost* observations, which require a "
        "costed campaign nobody has run. The titer intervals above are conformal; "
        "these are not, and the words are not interchangeable.\n"
    )
    with open(path, "w") as f:
        f.write("".join(L))


if __name__ == "__main__":
    main()
