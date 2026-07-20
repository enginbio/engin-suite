"""Host recommendation memo generation."""
from __future__ import annotations

from .schema import HostScore


def render_memo(title: str, ranked: list[HostScore]) -> str:
    """Render a ranked host list as a markdown recommendation memo."""
    L = [
        f"# Host recommendation — {title}\n",
        "_engin-host first-slice; illustrative KB. Score in [0,1]; "
        "± is a 90% band from KB confidence._\n\n",
        "| rank | host | score (90% band) | top drivers | flags |\n",
        "|---|---|---|---|---|\n",
    ]
    for r, d in enumerate(ranked, 1):
        drivers = ", ".join(f"{c} {v:.2f}" for c, v in d.contributions)
        flags = "; ".join(d.flags) if d.flags else "—"
        L.append(f"| {r} | {d.host} | {d.score:.2f} ± {d.band90:.2f} | {drivers} | {flags} |\n")
    best = ranked[0]
    L.append(
        f"\n**Recommendation:** {best.host} (score {best.score:.2f} ± {best.band90:.2f}). "
        f"Driven by {', '.join(c for c, _ in best.contributions)}. "
        f"{'No hard-constraint conflicts.' if best.feasible else 'Caveats above.'}\n"
    )
    return "".join(L)
