"""Demo: two very different target profiles should pick very different hosts,
with explainable drivers, honest confidence bands, and hard-constraint flags.

Run:  python examples/run_demo.py    (needs matplotlib)
"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from engin_host import HostQuery, default_kb, render_memo, score

OUT = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(OUT, exist_ok=True)

QUERIES = {
    "Secreted human glycoprotein, industrial scale (therapeutic)": HostQuery(
        weights=dict(
            glyco=1.0,
            secretion=0.9,
            protein=1.0,
            titer=0.6,
            scaleup=0.7,
            speed=0.3,
            cost=0.4,
            tools=0.4,
        ),
        hard=dict(glyco=0.6),
    ),
    # Named for the *use case*, not for a regulatory score. QPS status is printed
    # in the memo and does not enter this query -- ADR 0010, and #22 for ranking.
    "Food-grade small molecule via fermentation, cost-sensitive & fast": HostQuery(
        weights=dict(
            smallmol=1.0,
            cost=0.9,
            titer=0.7,
            speed=0.7,
            scaleup=0.6,
            tools=0.5,
            secretion=0.1,
            protein=0.2,
        ),
    ),
}


def main():
    kb = default_kb()
    for i, (title, q) in enumerate(QUERIES.items()):
        ranked = score(kb, q)
        print(f"\n=== {title} ===")
        for r, d in enumerate(ranked, 1):
            flag = "  [FLAG] " + "; ".join(d.flags) if d.flags else ""
            drivers = ", ".join(c for c, _ in d.contributions)
            print(f"  {r}. {d.host:18s} {d.score:.2f} ± {d.band90:.2f}   drivers: {drivers}{flag}")
        with open(f"{OUT}/host-memo-{i + 1}.md", "w") as f:
            f.write(render_memo(title, ranked))

        names = [d.host for d in ranked]
        sc = [d.score for d in ranked]
        er = [d.band90 for d in ranked]
        col = ["#dd6b20" if d.flags else "#2b6cb0" for d in ranked]
        fig, ax = plt.subplots(figsize=(6, 3.4))
        ax.barh(range(len(names))[::-1], sc, xerr=er, color=col, capsize=3)
        ax.set_yticks(range(len(names))[::-1])
        ax.set_yticklabels(names)
        ax.set_xlabel("suitability score (90% band)")
        ax.set_title(title, fontsize=9)
        ax.text(
            0.98,
            0.02,
            "orange = hard-constraint flag",
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=7,
            color="#dd6b20",
        )
        fig.tight_layout()
        fig.savefig(f"{OUT}/host-scores-{i + 1}.png", dpi=130)
    print("\nWrote outputs/ -> host-memo-*.md, host-scores-*.png")


if __name__ == "__main__":
    main()
