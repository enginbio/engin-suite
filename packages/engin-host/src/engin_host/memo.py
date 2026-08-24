"""Host recommendation memo generation."""

from __future__ import annotations

from .schema import HostScore


def render_memo(title: str, ranked: list[HostScore]) -> str:
    """Render a ranked host list as a markdown recommendation memo.

    The provenance line is **derived from the scores**, not written here. It used
    to be the fixed string "illustrative KB", which is true today and would have
    quietly become false the moment any cell was sourced -- the same
    prose-goes-stale failure this field exists to fix (#146).
    """
    any_illustrative = any(d.provenance != "sourced" for d in ranked)
    basis = (
        "Some capability values are **illustrative** -- hand-assigned, not sourced"
        if any_illustrative
        else "All capability values behind these scores are sourced"
    )
    L = [
        f"# Host recommendation — {title}\n",
        f"_engin-host first-slice. {basis}. Score in [0,1]; "
        "± is a 90% band from KB confidence, which is a separate question from "
        "whether the value was sourced._\n\n",
        "| rank | host | score (90% band) | top drivers | flags | basis |\n",
        "|---|---|---|---|---|---|\n",
    ]
    for r, d in enumerate(ranked, 1):
        drivers = ", ".join(f"{c} {v:.2f}" for c, v in d.contributions)
        flags = "; ".join(d.flags) if d.flags else "—"
        L.append(
            f"| {r} | {d.host} | {d.score:.2f} ± {d.band90:.2f} | {drivers} | {flags} "
            f"| {d.provenance} |\n"
        )
    # Regulatory status: printed, never scored (ADR 0010). It is a separate block
    # rather than a table column because the three states are not comparable and a
    # column invites reading them as one.
    if any(d.qps for d in ranked):
        L.append("\n## EFSA QPS status (displayed, not scored)\n\n")
        L.append(
            "_QPS covers microorganisms **intentionally added to food or feed**. It does "
            "not speak to an enzyme, a pharmaceutical intermediate or a material, which "
            "is what most of these hosts are used for. `excluded` means assessed and "
            "refused; `out_of_scope` means the scheme never reached it. The two are not "
            "points on one scale, and neither affects the ranking above._\n\n"
        )
        for d in ranked:
            q = d.qps
            if q is None:
                continue
            unit = f" ({q.taxonomic_unit})" if q.taxonomic_unit else ""
            L.append(f"- **{d.host}**{unit} — `{q.status}`\n")
            for qual in q.qualifications:
                L.append(f"  - qualification: {qual}\n")

    best = ranked[0]
    L.append(
        f"\n**Recommendation:** {best.host} (score {best.score:.2f} ± {best.band90:.2f}). "
        f"Driven by {', '.join(c for c, _ in best.contributions)}. "
        f"{'No hard-constraint conflicts.' if best.feasible else 'Caveats above.'}\n"
    )
    if best.unsourced:
        L.append(
            f"\n**This recommendation rests on unsourced values.** "
            f"{len(best.unsourced)} of the capabilities it weighs are illustrative: "
            f"{', '.join(best.unsourced)}. Treat the ranking as a demonstration of the "
            f"scoring machinery rather than as evidence about these organisms.\n"
        )
    return "".join(L)
