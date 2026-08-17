# 0010 — Regulatory status is two facts in two jurisdictions, not a scalar

**Status:** Proposed (2026-08-17)

## Context

`engin-host`'s knowledge base carries a `gras` capability scored in [0,1] for each of six hosts,
alongside a confidence value. [#22](https://github.com/enginbio/engin-suite/issues/22) proposes
promoting it to a scored regulatory-pathway input, and [#146](https://github.com/enginbio/engin-suite/issues/146)
item 3 names `gras` as the obvious first cell to source, on the grounds that regulatory status is a
question with a citable answer.

[#188](https://github.com/enginbio/engin-suite/issues/188) established that the premise does not
hold as stated. A GRAS conclusion attaches to a substance under specific conditions of use, is
strain-specific, and FDA issues a "no questions" letter rather than an approval. A scalar per
organism therefore cannot be given a `sources.yaml` id without laundering an editorial judgement
into a citation — the failure `D23` exists to prevent. #188 left open whether *any* sourceable
per-organism encoding exists, and blocked #22 on the answer, because scoring a number that
corresponds to no regulatory fact only makes the problem heavier.

This record answers that question. It is a schema decision, so it sits here rather than in
`DECISIONS.md`.

## What the sources actually support

**EFSA's Qualified Presumption of Safety list is organism-level by construction.** The lowest
taxonomic unit for which QPS status is granted is the species, for bacteria, yeasts and
protists/algae.[^2026-efsa-qps-update-23] That is precisely the shape of fact a per-host cell can
carry, and it is a different fact from GRAS rather than a European translation of it. Where a hazard
can be tested at strain or product level, a *qualification* is attached to the taxonomic unit — for
example, that strains carry no acquired resistance genes to clinically relevant antimicrobials, or
that QPS applies for production purposes only, meaning viable cells are absent from the final
product.[^2026-efsa-qps-update-23]

The list is published as a spreadsheet on EFSA's Knowledge Junction with columns for group,
subgroup, family, genus, species, synonyms and up to three qualifications, and a companion sheet
recording taxonomic units *excluded* from QPS with the reason and the opinion that excluded
them.[^2026-efsa-qps-list]

Checked against the six hosts in `kb.py`, the result is not a rescaling of the existing column:

| KB host | QPS position |
|---|---|
| *E. coli* | **Excluded by name**, because many strains are pathogens for humans and animals |
| *S. cerevisiae* | Listed, with distinct qualifications for viable-cell use and for production-strain use |
| *P. pastoris* | Listed as *Komagataella phaffii* and *Komagataella pastoris*; *Pichia pastoris* is an obligate synonym of the latter. Production purposes only |
| *B. subtilis* | Listed, qualified on acquired antimicrobial resistance and on absence of toxigenic activity |
| CHO (mammalian) | Out of scope — QPS covers bacteria, yeasts, protists/algae and viruses |
| Cell-free (TXTL) | Out of scope — not an organism |

**The US side has no organism-level field to read.** The GRAS Notice Inventory records the substance
name, the notice number, the notifier, the intended conditions of use, the statutory basis, and a
link to FDA's response letter.[^2026-fda-gras-inventory] The production organism is not a field; it
appears inside free-text substance names such as *pepsin A from Komagataella phaffii DFB-002*, or
only inside the notice itself. A per-organism count is therefore an extraction with judgement in it,
not a lookup.

## Decision

**1. The `gras` scalar is retired rather than sourced.** It conflates three states that are not
points on one axis: *listed with qualifications*, *excluded by name*, and *outside the scheme's
scope*. The conflation is not cosmetic — the shipped KB gives *E. coli* 0.50 and CHO 0.30, ordering
an organism that was assessed and refused above one that was never in scope. No amount of
re-estimating the number fixes an axis that does not exist.

**2. Encode EFSA QPS, at species level, with its qualifications.** A host carries a status of
`listed`, `excluded` or `out_of_scope`, the taxonomic unit the status attaches to, the verbatim
qualifications where present, and a `sources.yaml` id. This is the first cell in the KB that can
honestly claim `sourced` under the mechanism #187 added.

**3. Do not encode a US GRAS scalar or a derived notice count.** Not as a smaller number, not as a
count. Deriving "how many notices name this organism" requires parsing free-text substance names, and
the resulting figure would carry a citation while resting on our own extraction — the exact laundering
#188 identified, in a form harder to spot because it would look like a count of records. If the US
side is wanted later it should be a per-substance lookup surfaced next to a specific product, which
is a different feature.

**4. Do not average the two jurisdictions into one score.** They answer different questions, and a
host can be QPS-listed in the EU while its relevance to a US filing depends entirely on the substance
being made.

**5. #22 is unblocked but narrowed.** A regulatory-pathway input can be scored over the QPS encoding
plus the user's target market. It cannot be scored over a single number meaning "how GRAS is this
organism", because no such quantity exists.

## Consequences

- **`gras` disappears from `CAPABILITIES` and the weighted score.** Regulatory status stops being one
  of ten interchangeable capabilities blended into a weighted sum. It becomes a flag with its own
  semantics, which is closer to how `engin-host` already treats hard constraints.
- **One host's headline changes direction.** *E. coli* currently scores mid-range on `gras`. Under
  the QPS encoding it is explicitly excluded, which is a stronger negative signal than 0.50 conveys —
  and *E. coli* is the default chassis this project's own "just use E. coli" baseline is named after.
  That is a real change to an output, not a relabelling.
- **A licence trap is avoided by using the data rather than the paper.** The QPS list on the Knowledge
  Junction is CC BY 4.0.[^2026-efsa-qps-list] The EFSA Journal article restating it is CC
  BY-**ND**,[^2026-efsa-qps-update-23] and a derived machine-readable table extracted from the article
  would be a derivative work under a no-derivatives licence. Cite the article for definitions; take
  values from the Zenodo record.
- **The encoding has a refresh cadence.** QPS is revised on a published schedule, so a vendored
  snapshot goes stale on a known clock rather than silently. The concept DOI resolves to the current
  version, which is what the register row points at.
- **Fifty-nine cells are untouched.** This settles the one capability #146 item 3 named as citable and
  says nothing about the rest. If anything it strengthens that issue's suspicion that some cells are
  permanently editorial: `gras` looked like the easy one and turned out to need a schema change.

## Not decided here

Whether the QPS status should influence ranking at all, or only appear in the memo as a flag, is
`#22`'s remaining question and depends on the target-market input this record does not design.

[^2026-efsa-qps-update-23]: EFSA BIOHAZ Panel, *Update of the list of qualified presumption of safety (QPS) recommended microbiological agents … 23*, EFSA Journal 2026. [doi:10.2903/j.efsa.2026.9824](https://doi.org/10.2903/j.efsa.2026.9824). Open access under CC BY-ND 4.0.
[^2026-efsa-qps-list]: EFSA, *Updated list of QPS-recommended microorganisms for safety risk assessments carried out by EFSA*, EFSA Knowledge Junction on Zenodo, CC BY 4.0. Concept DOI [10.5281/zenodo.1146566](https://doi.org/10.5281/zenodo.1146566), resolving at the time of writing to the version published 2026-07-06.
[^2026-fda-gras-inventory]: FDA, *GRAS Notice Inventory*. <https://www.fda.gov/food/generally-recognized-safe-gras/gras-notice-inventory>
