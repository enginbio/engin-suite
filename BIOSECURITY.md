# Biosecurity Policy

**Version 1.1 · Effective 2026-08-13 · Next scheduled review 2027-02-07**

*1.1 is a correction, not a scheduled review: §3 overstated who endorses the community statement it cites, and §6 stated a contested empirical claim as settled. Both are marked in place. The §3 risk assessment and the §5 declined scope are unchanged.*

Maintainer contact: **biosecurity@engin.bio**

This policy states Engin's assessment of the dual-use risk presented by its software, the commitments the project makes as a result, and the capabilities it declines to build. It covers biological misuse risk only. Software vulnerabilities are handled under [SECURITY.md](https://github.com/enginbio/engin-suite/blob/main/SECURITY.md).

---

## 1. Scope

This policy applies to all code, models, documentation and datasets published under the `enginbio` organization, and to contributions proposed to those repositories.

**Definitions used in this document:**

| Term | Meaning here |
|---|---|
| **Select agent** | A biological agent or toxin listed under the US Federal Select Agent Program (7 CFR 331, 9 CFR 121, 42 CFR 73) |
| **Controlled precursor** | A chemical or biological item on the Australia Group common control lists |
| **Screened provider** | A DNA synthesis provider adhering to the IGSC Harmonized Screening Protocol, the US Framework for Nucleic Acid Synthesis Screening, or an equivalent standard such as ISO 20688-2:2024 |
| **Uplift** | A meaningful reduction in the difficulty, cost, time or expertise required to cause biological harm |

---

## 2. What Engin does

Engin helps a team decide how to manufacture a molecule they have **already selected**, and what that will cost at industrial scale.

| Component | Function |
|---|---|
| `engin-host` | Scores candidate microbial chassis against a production requirement, with a confidence band and hard-constraint flags |
| `engin-pathway` | Ranks candidate metabolic routes by predicted *manufacturability* — metabolic burden, toxic-intermediate risk, thermodynamic feasibility, host fit |
| `engin-core` | Forecasts titer with calibrated uncertainty from a small number of runs, recommends the next experiment, and produces a probabilistic cost-per-kilogram estimate including downstream recovery |

Engin does not propose targets, predict biological activity, model toxicity or pathogenicity, or design sequences.

---

## 3. Risk assessment

**Assessment: Engin does not provide meaningful uplift toward biological harm.**

This is stated plainly rather than hedged, because vague reassurance is less useful to a reader than a falsifiable claim.

**Reasoning.** Engin addresses industrial viability — whether a route reaches an economical titer at tonne scale, and whether recovery costs consume the gain. These are questions about manufacturing economics over months of process development. Misuse is not constrained by cost of goods, unit economics, or whether a process survives transfer to a 100,000-litre reactor.

The components are individually oriented the same way. Pathway ranking scores manufacturability and holds no model of physiological activity; it cannot distinguish a pharmaceutical intermediate from a solvent. Host selection matches a chassis to a production requirement. Neither answers *what to make* — only *how this would be made at industrial scale*.

**Where the field locates the real chokepoint.** The community statement *Community Values, Guiding Principles, and Commitments for the Responsible Development of AI for Protein Design* (released 2024-03-08; 189 signatories as of 2026-02-06, a list that is still open) identifies nucleic acid synthesis as the key biosecurity checkpoint for computational biodesign, on the reasoning that no computationally designed construct causes physical harm until it is manufactured. Engin sits downstream of design and upstream of nothing that bypasses that checkpoint.

*Corrected 2026-08-13:* this paragraph previously described the statement as "supported by IBBIS, NTI | bio, the International Gene Synthesis Consortium and others." **That was wrong, and wrong in the direction that flattered this document.** Signatories sign as individuals, and the statement says twice that affiliations "are for identification only and do not imply any institutional endorsement." People from those organizations signed; the organizations did not endorse. Claiming named biosecurity institutions stand behind a document they have not endorsed is precisely the kind of borrowed authority a biosecurity policy has no business trading on, so it is corrected here rather than quietly dropped.

**This assessment is not permanent.** It is reviewed on the cadence in §8 and reassessed whenever §7's triggers fire.

---

## 4. Commitments

1. **Screened providers only.** Any DNA ordered by the project, for benchmarking or development, is obtained from a screened provider as defined in §1. The project supports the extension and improvement of synthesis screening and will not develop capabilities that erode it.

2. **Capability review before release.** Any new capability that could plausibly bear on §5 is assessed before it ships, and the assessment is recorded in `DECISIONS.md` with a decision ID. Where a risk is identified and unresolved, the capability is not released.

3. **Screening safeguards ship with the capability they guard**, not as an optional layer or a later addition. See §6.

4. **No red-team roadmaps.** Where evaluation of misuse potential is warranted, findings are reported at the level of capability and mitigation. The project does not publish material that would function as instructions for the misuse it describes.

5. **Openness is not overridden without cause.** Consistent with the community statement referenced in §3, security concerns are not used as an unexamined justification for closing research. Restriction requires an identified, articulated and unresolved risk — recorded in `DECISIONS.md`, not asserted informally.

6. **Concerns are answered.** Reports under §9 receive an acknowledgement within 5 working days and a substantive response within 20.

---

## 5. Declined scope

The project will not build, and will decline contributions implementing:

1. **Route identification toward a specified hazardous product.** Engin ranks routes for manufacturability against a target supplied by the user. It will not gain a capability whose purpose is determining how to synthesize a toxin, select agent, or controlled precursor.

2. **Production optimization targeting select agents or controlled precursors**, including datasets curated to that end.

3. **Anything bearing on synthesis screening evasion** — sequence obfuscation, screening-detection probing, or tooling that routes around provider controls.

4. **Wet-lab protocol detail for regulated organisms.** Engin operates at the level of design and economics. Handling, propagation and containment procedures for controlled agents are out of scope.

5. **Predicted physiological activity, toxicity or pathogenicity.** These are outside the project's purpose and would change its risk profile materially.

A contribution touching any of the above will be closed with reference to this section. Maintainers are not required to explain further, and the closure is not a judgement about the contributor.

---

## 6. Cultivation prediction — specific safeguard

The roadmap includes predicting cultivation conditions (media, temperature, pH, oxygen tolerance) for non-model and uncultured organisms from genome sequence.

**This is the one component where the dual-use question is not theoretical.** "How do I grow this organism" is a genuine barrier — for legitimate work, and equally for illegitimate work involving an organism the actor could not otherwise propagate. Unlike the rest of the suite, this addresses a bottleneck that is not purely economic.

**How large that barrier is, is contested in the primary literature, and this policy should say so.** The majority position is that most bacterial and archaeal taxa remain uncultured (Steen et al. 2019, *ISME J* 13:3126, [doi:10.1038/s41396-019-0484-y](https://doi.org/10.1038/s41396-019-0484-y)). It is a direct rebuttal to Martiny 2019, *ISME J* 13:2125, [doi:10.1038/s41396-019-0410-3](https://doi.org/10.1038/s41396-019-0410-3), which reports that roughly half of sequences and a third of taxa across major biomes have a closely related cultured relative. Note which way that cuts: if Martiny is nearer right, the cultivation barrier is *lower* than this section assumes, and the uplift argument for building the safeguard is correspondingly weaker. The safeguard is kept anyway — a contested barrier is not an absent one, and §6's constraint costs little if the pessimistic reading is wrong.

The capability is judged worth building: non-model organism onboarding currently costs research groups years, and the benefit is broad and concrete. It ships with the following constraint, or it does not ship.

**Safeguard — mandatory taxonomic exclusion.**

- Organisms on the US Select Agent and Toxin lists, and their close relatives as resolved through NCBI Taxonomy, are excluded from training data.
- Predictions are refused for excluded taxa at inference, with the refusal logged.
- The exclusion list is maintained in-repository, versioned, and reviewed on the §8 cadence.
- Tests asserting that exclusion is enforced run in CI, and a change disabling them fails the build.

**Status: the cultivation capability is not built.** The safeguards above are binding conditions on shipping it, not descriptions of code that exists today. This section will read in the present tense when there is something for it to describe.

**Stated limitations.** Taxonomic screening is evadable by a determined and adequately resourced actor. Lists lag emerging agents. A genome can be submitted without accurate taxonomic labelling. **This safeguard is not a solution to misuse and the project does not claim it is.** It raises the floor, makes the tool not casually useful for the purpose we do not want it serving, and constitutes a constraint the project accepts a real cost to maintain.

---

## 7. Triggers for reassessment

This policy is reassessed ahead of schedule if any of the following occurs:

- A proposed capability would predict biological activity, toxicity or host range.
- A proposed capability would identify or rank routes to a target the user did not supply.
- Published work demonstrates uplift from a bioprocess-optimization capability comparable to Engin's.
- A change in the US Federal Select Agent Program, Australia Group control lists, or applicable national synthesis-screening frameworks materially alters §1 definitions.
- A concern reported under §9 is assessed as credible and not addressed by existing commitments.

---

## 8. Review

Reviewed every six months by the maintainers, and on any §7 trigger. Each review records: whether the §3 assessment still holds, whether §5 requires additions, and whether the §6 exclusion list is current.

Review outcomes are recorded in `DECISIONS.md` and the version and date at the head of this document are updated. Superseded versions remain available in the repository history.

---

## 9. Reporting a concern

**Publicly**, where the concern can be discussed openly: <https://github.com/enginbio/engin-suite/issues/new?labels=biosecurity>

**Privately**, where it cannot: **biosecurity@engin.bio**

Please include what capability concerns you, the mechanism by which you believe harm could occur, and any conditions you place on onward disclosure. Do not include operational detail describing how to cause harm — a description of the capability gap is sufficient and preferred.

Acknowledgement within 5 working days, substantive response within 20. Reports are handled confidentially where requested. The project would rather receive a concern that proves unfounded than miss one that does not.

---

## 10. Openness

Engin is open source, which raises a reasonable objection: access cannot be restricted after publication.

The project's position is that openness remains correct here, for three reasons.

**The capability is not uplift-relevant**, per §3. Restricting non-uplift-relevant software imposes a real cost on legitimate users while removing no meaningful capability from an adversary.

**Closed tooling is the condition this project exists to correct.** Large organizations hold internal bioprocess software that smaller teams must rebuild from nothing. That asymmetry is the problem Engin addresses, and reproducing it would defeat the purpose.

**Openness makes these claims checkable.** The §6 exclusion list, its enforcement tests, and every commitment above are in a public repository. A reader does not have to take this document's word for any of it.

---

## Related documents

| Document | Covers |
|---|---|
| [SECURITY.md](https://github.com/enginbio/engin-suite/blob/main/SECURITY.md) | Software vulnerability disclosure |
| [GOVERNANCE.md](https://github.com/enginbio/engin-suite/blob/main/GOVERNANCE.md) | Decision-making, maintainership, succession |
| [DECISIONS.md](https://github.com/enginbio/engin-suite/blob/main/DECISIONS.md) | Decision record, including biosecurity assessments |
| [CONTRIBUTING.md](https://github.com/enginbio/engin-suite/blob/main/CONTRIBUTING.md) | Contribution process |

## References

- [Community Values, Guiding Principles, and Commitments for the Responsible Development of AI for Protein Design](https://responsiblebiodesign.ai/) (2024)
- [IBBIS Common Mechanism for DNA Synthesis Screening](https://ibbis.bio/our-work/common-mechanism/)
- [International Gene Synthesis Consortium Harmonized Screening Protocol](https://genesynthesisconsortium.org/)
- [US Federal Select Agent Program](https://www.selectagents.gov/)
- [Australia Group common control lists](https://www.dfat.gov.au/publications/minisite/theaustraliagroupnet/site/en/controllists.html)
