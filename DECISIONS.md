# Decisions

Substantive choices are recorded here with their reasoning, and cited by ID (`D13`, `D21`) in code, pull requests and issues. The point is that you can disagree with the reasoning rather than guess at it.

Several entries record changed minds. That's intentional. A project that revised a decision three times with stated reasons is easier to trust than one presenting a clean narrative, and `GOVERNANCE.md` promises reasoning is visible and contestable — which is only true if the revisions are visible too.

**Status vocabulary:** `standing` (in force) · `superseded` (replaced, pointer given) · `deliberately open` (a decision *not* to decide, with reasoning) · `deferred` (not scheduled, with a trigger).

---

## Licensing and openness

**D1 — Everything Engin builds is free.** `standing`
Not "free until we find the paid part." Free is the working assumption for every decision. Nobody has the knowledge to draw a commercial boundary before real users exist, and a guess encoded in architecture distorts what gets built.

**D2 — Never charge for what was previously given away.** `standing`
Anything paid must be net-new and additive. Preserved automatically by D1.

**D3 — Apache-2.0 on all public code.** `standing`
Three reasons, none of them goodwill. The **patent grant** is the substantive difference from MIT/BSD and matters disproportionately in a patent-dense field — an adopter gets assurance a contributor cannot later assert a patent over code they depend on. Corporate legal departments **pre-approve** it, removing a real barrier unrelated to the software. And it matches the surrounding ecosystem.

**D5 — Copyleft considered and rejected.** `standing`
AGPL would prevent service-hosting without contribution, but corporate legal routinely blocks AGPL outright, costing exactly the industry adoption the project exists to win.

**D4 — No contributor licence agreement.** `standing`
A CLA is what lets a project relicense or move open work behind a paid boundary later. Engin doesn't want that ability. Without one, copyright stays distributed across contributors, so **the project cannot relicense existing code even if a future version of it wanted to.** A structural commitment rather than a promise. DCO sign-off instead.

**D6 — The commercial boundary is deliberately undecided.** `deliberately open`
Paid opportunities may surface later from observed demand and would be evaluated then. Refusing to draw the line early is the load-bearing commitment, not indecision — a project with no declared moat, no CLA and no paid tier is far easier to standardize on, because there's nothing to be captured by.

**D7 — Revenue, if it comes, comes from services, not software.** `standing`
What people pay for here is labour, availability and liability — operating infrastructure, audit documentation, SLAs, integration work. None was ever in the repository, because none is a thing a repository can contain, so charging for them cannot violate D2. Software has near-zero marginal distribution cost; a person answering a ticket at 2am does not. That asymmetry is the revenue path and it survives any amount of open code.

**D8 — The TEA head and downstream-cost model are public.** `standing`
Earlier planning treated these as a private moat. They aren't. Superseded that framing entirely.

---

## Scope and technical direction

**D9 — Compose, don't reimplement.** `standing`
Build only what has no open equivalent, or where the equivalent has genuinely gone stale. Compose with BayBE, BioSTEAM, COBRApy, MAPIE, eQuilibrator.

**D10 — Don't fork the living.** `standing`
Forking a maintained-but-aging tool splits its community and burns the goodwill adoption depends on. Contribute upstream or wrap. Fork only where a project is genuinely abandoned and its maintainers say so.

**D11 — No bespoke data container. Use xarray and pandas; build the ingest layer.** `standing` — *revised twice*

This decision changed twice and the history is instructive.

*First version:* define a `BioprocessRun` interchange format, on the reasoning that standards win by owning the representation (scanpy via AnnData, COBRApy via the model object).

*Second version:* adopt MIFE/MIFD instead, since a fermentation metadata standard already existed. **That rested on a category error** — MIFE is a *minimum-information reporting checklist* (the MIAME lineage), not a data structure analysis code is written against. In genomics both exist doing different jobs: MIAME is the reporting requirement, AnnData is what people code against.

*Current version, after reading the specification:* build neither. Applying the test *"if an existing structure serves with little modification, don't build it"* — the endpoint-DoE case is a pandas DataFrame plus a column convention; the time-series case is an xarray Dataset natively, dims `(run, time)`, one data variable per channel, `attrs` for metadata. Bioprocess data isn't special enough to need its own container, and inventing one imposes an unfamiliar abstraction for no functional gain.

What genuinely isn't served turns out not to be data-structure shaped: calibration state and cost context are properties of *model outputs*, and getting from a messy vendor export to either structure is **loaders**.

**So: use xarray and pandas as-is, publish a thin versioned convention over them, and build the ingest layer.** That last is the real contribution — unglamorous, genuinely hard, and nobody has built it. Standard-hood, if it comes, comes from the convention and loaders being the obvious way to do this, not from owning a type. Precedent: climate science layered CF conventions onto netCDF rather than inventing an array format.

**D12 — Tiered validation, each tier's limitation published.** `standing`
Synthetic-only validation is disqualifying: R² 0.97 on your own simulator reads as "the code runs." But a binary synthetic-bad/real-good framing isn't achievable either — no public corpus of in-domain microbial DoE with absolute titers exists.

Five tiers, each published with what it does and does not prove: own simulator → an independent simulator → real but out-of-domain industrial data → in-domain literature DoE → partner data. More credible than a blanket "validated on real data," and a publishable methods contribution.

**Licence rule, binding: ship loaders that fetch, never data that ships.** Some upstream datasets are NonCommercial/NoDerivatives licensed, which conflicts with an Apache-2.0 project whose users are commercial.

**D13 — The recommender optimizes net $/kg, not titer.** `standing` — *justification replaced 2026-08-10*

Titer is the wrong optimization target, for four reasons:

- **Titer is an integrative metric.** It can be inflated by running the fermentation longer or at higher biomass — a better number without a better process.
- **TRY splits into three cost centres**: titer → downstream processing, rate → reactor size, yield → raw material.
- **Raw material cost is set by yield, and is a dominant term.** Konzock & Nielsen (2024) put it directly: yield "directly defines the substrate costs, which, for commodity products such as ethanol, can account for more than 50% of the total costs." That cost is governed by *yield*, which titer does not capture. <!-- ref: 2024-konzock-try-costs -->

  > **Corrected 2026-08-11 by the D23 evidence pass.** This bullet previously read "Media is roughly 35–50% of precision-fermentation cost of goods, ahead of facility depreciation (20–25%) and downstream processing (15–20%)." The direction survives and is now cited; the three-way percentage split does not. It traces to industry blog material rather than a peer-reviewed breakdown, and the nearest citable figure is for a *different product class* — commodity chemicals, not precision fermentation. The register keeps the row as `contested` rather than deleting it.
- **Which cost centre dominates tracks the product's value, not the process** — added 2026-08-13 by the `D23` pass for #87, and it is the bullet that carries the decision. Straathof (2011) assembles published process economics and finds downstream processing at **45–92%** of production cost for biopharmaceuticals against a typical **20–40%** for bulk fermentation products. <!-- ref: 2011-straathof-downstream-costs --> The organizing variable is *selling price*: "the relative DSP contribution tends to rise with the selling price", running from ~15% for ethanol at ~$0.5/kg to 60–70% for enzymes. So the weighting between titer's cost centre and yield's slides along a continuum. A single-metric objective cannot track a weighting that slides; net $/kg can.

  **Two conditions the same source attaches, both of which matter to this codebase.** First, **purity drives the DSP share**: crude penicillin G and crude lipase sit near 25%, and Straathof notes that purified and formulated versions of the same products would land nearer 50–55%. That is direct literature support for #17 (purity as a TEA input) — the same molecule at a different specification is a different economics problem. Second, the substrate-versus-DSP comparison is narrower than it first looks: carbohydrate feedstock is 15–60% of production cost and the largest *upstream* item, but **"only for the ethanol and penicillin processes analyzed, carbohydrate costs were larger than overall DSP costs."** <!-- ref: 2011-straathof-downstream-costs -->

  > **Corrected 2026-08-13, hours after being written.** The bullet first said that for bulk products "raw material takes the larger share instead" — i.e. larger than DSP. The primary source does not support that as a general statement about bulk products; it supports it for ethanol and penicillin specifically. The claim was written from the chapter's abstract while the chapter was paywalled, and the founder then bought it. **The correction arrived from reading the source, exactly as the first draft's own provenance note said it might.** The register row moves from `partially supports` to `supports` for the figures that verified, with a `contradicts` row kept for the part that did not.

  > **Worth recording for `D23` itself:** Straathof's motivating complaint is that the field's DSP percentages — 50–70%, 50–80%, 50–90%, 60–70%, 60–80%, 60–90% — are "generally not supported by proper data or references", published in "reputed scientific journals and books", and "often exaggerating". A paper whose contribution is going and checking the numbers everybody repeats is the closest thing this programme has to an external argument for its own existence. <!-- ref: 2011-straathof-downstream-costs -->
- **Cost is non-linear in TRY**, with thresholds and inflection points, so no single metric is a usable proxy for the objective.

**Accepted consequence: Engin looks worse on the metric everyone currently reports.** That trade is deliberate and is explained prominently rather than left to be discovered in a benchmark table.

> **Withdrawn justification, kept because the error is instructive.** This decision previously read: *"Recovery cost is determined upstream — by titer, strain and broth composition — but incurred downstream, so an optimizer maximizing titer can move the true objective backwards: a higher-titer strain with a messier broth can be economically worse."*
>
> **That mechanism is backwards.** Higher titer *reduces* downstream cost — less water to remove, smaller equipment, fewer unit operations — and purification is more expensive when broth concentration is low. Titer is the TRY metric that corresponds to downstream cost, and the two move together favourably.
>
> The decision survived; its reasoning did not. It was derived from mechanism and asserted confidently in three documents while the field had measurements saying the opposite. Recorded rather than quietly edited, because a project promising that its reasoning is contestable owes the reader its corrections too.
>
> **The retraction did not propagate, and that is the more useful lesson.** On 2026-08-13 the withdrawn sentence was still published in `README.md`, on the docs front page as one of three headline cards, and in `docs/guides/cost.md` — which cited `D13` as its authority for a claim `D13` had explicitly retracted three days earlier. Fixing the canonical document is not fixing the claim. **When a justification is withdrawn here, grep the tree for it**: the phrase, not the decision id, because the documents that repeat it rarely quote the id.

**D14 — Library, not framework.** `standing`
Stable public APIs, no hidden coupling, usable as a dependency. Required by the goal of being depended upon, independent of any commercial consideration. An earlier draft justified the same properties as preserving optionality for a future paid layer; that framing is withdrawn.

**D15 — Documentation is a product artifact.** `standing`
Dedicated site, executable documentation that runs in CI so it cannot silently rot, a worked case study per persona, a published API stability guarantee. scikit-learn's dominance is substantially a documentation achievement.

**D20 — Sphinx generates, Read the Docs Community hosts.** `standing`
MyST-NB executes documents at build time, so building the docs *is* verifying every example. RTD is chosen because the neighbours are there (COBRApy, BioSTEAM), and because versioned docs with a switcher come free — the API stability guarantee promises a reader pinned to an old release can read that release's docs, and on self-hosting that's DIY, doesn't get built, and the promise quietly becomes untrue.

Ads on the free tier are accepted: content-based rather than tracking-based, and the mechanism funding free hosting for projects like this.

**Execution runs in CI, not on RTD.** Shared builders plus examples that fit models produce slow, flaky builds — and that pressure is how someone eventually disables execution to ship a release, which is how the D15 guarantee dies quietly.

**D21 — One public monorepo. Repo boundaries follow maintainer boundaries.** `standing`
A single repository publishing separate PyPI packages, so users install only what they need with no multi-repo coordination cost.

The durable part is the heuristic: multi-repo buys independent release cadence and separate governance, which cost coordination overhead that only pays off when *different people* own different pieces. **The trigger for splitting is a package acquiring its own maintainer, not a line count.**

**D22 — Documentation lives in the repo, not in a private wiki.** `standing`
Architecture, decisions and contributor documentation are public and version-controlled beside the code. Private strategy and business material stays out of the repository entirely rather than in a private wiki that shadows it.

Reasoning: `GOVERNANCE.md` promises reasoning is visible and contestable, and issues cite decision IDs. Both are false if the record is private. D21's logic also applies to documentation — one maintainer shouldn't maintain four surfaces.

Three surfaces: this repository (why and how), the documentation site (users, built from the repository), the project board (state).

**D23 — Evidence lives in `sources.yaml` and is rendered, not hand-maintained. Claims cite by source id.** `standing`
Every factual claim in a public document traces to a source: a durable link, a DOI, or an archived copy. The register holding that mapping is machine-readable YAML at the repository root; the docs-site `references.md` is generated from it. Claims cite a short stable id — `2019-humbird-tea` — used identically in prose footnotes and in `# ref:` comments at the implementing function.

`D<n>` and `ref:` are orthogonal and both are wanted. A decision ID says *why we chose*; a source id says *what evidence backed it*. A decision can be well-reasoned and unevidenced, which is the state most of this record was in when D23 was written.

**Why YAML rather than a table in a markdown file:** the map is (document × source × claim) and runs to hundreds of rows. A table that size isn't reviewable in a diff, and — the decisive reason — **only a machine-readable register can be checked in CI.** Under a solo maintainer (D18) a review cadence decays; a check that fails when a public document gains an uncited number does not.

This also applies to dependency claims. `docs` asserts that particular libraries are the community standard, sometimes with performance numbers. Those are claims about the field, not about this project, and they carry citations or they come out.

**Where no community standard exists**, the absence is itself a claim requiring evidence: what was searched, when, and which near-misses were rejected and why, recorded in a public design note before the implementation is written. "Nobody has built this" is the most self-serving sentence available to a project like this one, and it should be the most heavily evidenced. Re-checked annually — if someone ships the standard, Engin adopts it and says so, per D9.

---

## Data, community and governance

**D16 — Self-funded for now; grants later, not donations.** `standing`
Individual donations fund creators with audiences, not infrastructure. Grants are the right instrument — but not yet. The capital need at this scale is small, federal grant overhead is disproportionate to it, and public funders fund *proposed future work*, which conflicts with building in public fast enough that work may be done before an application clears.

Revisit when the binding constraint shifts from *building* to *sustaining* — when documentation, triage and community work stop getting done because nobody wants to do them. That is what those programmes fund.

**D17 — Data is earned, not extracted; value strictly precedes any data ask.** `standing`
Contributed data would improve the models, but the incentive isn't symmetric: a contributor gives up competitive information for a marginal improvement in a shared tool, and process know-how is among the most guarded assets in this field. Acceptable mechanisms are federated contribution, benchmark contribution for citation, consortium arrangements, and contracted data-for-service. Asking before giving reads as extraction.

**D18 — Solo maintainer, with governance published up front, actively open to co-founders.** `standing` — *operational detail added 2026-08-10*
Publish the decision-making process, the maintainer-promotion path and a succession plan now, honestly describing a one-person project. Defer maintainer recruitment until there are contributors to promote — maintainers emerge from contributors, contributors from users, and inverting that means asking people to sign on to an idea.

Reviewers and adopters don't require a headcount; they require a credible answer to single-point-of-failure, and a written succession path is that answer. A **co-founder** is a separate route and the project is actively open to one — peer-level from the start, not earned by accumulating commits.

**What "actively open" means in practice**, since the posture without a method is just a sentence: *warm outreach to named individuals who already know the work* — not a public call. A public call advertises a seat before there is anything to sit on, and it sits close to the `D24` line. A co-founder comes from someone already familiar with the project, so this is the only route with a realistic yield, and it is also the longest-lead item on the board.

**The credible answer to single-point-of-failure is only half written.** The succession path is published (`GOVERNANCE.md` §5), but the infrastructure — PyPI, the `engin.bio` domain, Read the Docs, the GitHub organization — is held by one person, and §2 names that as a single point of failure. **A continuity runbook is therefore a standing commitment**, kept privately because it describes recovery paths: where each credential lives, how it is recovered, and who to contact. It contains no secrets and is not a substitute for a second holder — it converts an undocumented single point of failure into a documented one, which is what a bus-factor question is actually asking about. A second credential holder follows a co-founder rather than preceding one.

**D19 — Short public biosecurity statement with named boundaries.** `standing`
An honest assessment stated plainly rather than hedged: bioprocess optimization is not meaningfully uplift-relevant, because nobody attempting harm is constrained by cost of goods. Plus an explicit list of what the project declines to build.

Cultivation prediction for uncultured organisms is the one roadmap item where the question isn't theoretical, and it ships with hazardous-taxa screening as a required component or not at all. That screening is evadable and lists lag reality — stated openly, because overclaiming would be worse than the gap.

**D24 — Build and document first; no visibility push until the tools are validated on real data.** `standing`
Ordering, recorded as a constraint so it survives the temptation to reverse it. Coding and documentation now; then validation on real data; then deliberate outreach.

**Why a decision and not just a plan.** The pressure runs the other way. Visibility is the most legible form of progress, it's available at any moment, and a project with no users can always tell itself that talking to people *is* the validation. D12 says real data gates the claims; D24 says it also gates the audience.

**The asymmetry.** There is roughly one first introduction to any given community. Someone shown a tool calibrated only on synthetic data draws a conclusion about the project rather than about the demo, and doesn't revisit it. Early and quiet is recoverable; early and visibly thin is much less so. The cost of waiting is a few months of obscurity for a project nobody is currently waiting on.

**Gate, concretely — two conditions, not one.**

*Validation.* Real-data calibration coverage published, the out-of-distribution failure mode published, and one non-synthetic worked example a stranger can run. **All three are done** as of 2026-08-11.

*Evidence.* **Every main component backed by a curated literature review** covering its implementation, its motivation and its conclusions, **with citations** — and any defect that review surfaces actually fixed, not merely logged. This is `D23`'s programme. **Satisfied as of 2026-08-15** (see the status correction below).

**Status corrected 2026-08-19 (#242): the evidence condition above read "not started", and had been false for four days.** It also said "the packages currently carry zero citations between them", which was false by then too — the code carries eleven distinct `ref:` ids across `engin-core`, `engin-host` and `engin-protein`.

The condition was met on **2026-08-15**, not on the 13th as #242 proposed. Checked against the register's own history rather than taken on the issue's word, because a status line correcting a stale date should not introduce another one:

- 2026-08-13 — twelve component rows exist, **eight** carry evidence
- 2026-08-14 — **eleven** carry evidence; `D23`'s issue set (#79–#89) and the defects it spun out (#103, #107) are closed
- 2026-08-15 — the twelfth, engin-host's capability knowledge base and scoring, is evidenced. **The condition becomes true here.**

None of the twelve rows is `unaudited` or `bespoke-unjustified`; all six packages are covered; `references.md` is published and #80's uncited-claim check runs in CI.

**What this correction does not decide.** Both gate conditions are now satisfied as written, and what follows from that is the question #242 actually asks — whether the cost paragraph above is understated, what "visibility push" bundles, and what discharges the gate. **Those are open and are not settled by this edit.** Recording an accurate status is maintenance; deciding what the status licenses is not, and a correction that quietly opened a gate would be worse than the stale line it replaced.

**Amended 2026-08-11, because the first condition was read as the whole gate.** It was not, and the ordering matters: the validation items say the tool works; the evidence items say the project knows *why* it built what it built, and can show its reasoning to someone qualified to disagree. A tool that passes the first and fails the second is one whose author cannot answer "why this method rather than the obvious alternative" — which is the first question any serious reader asks, and the question this project's own audits keep answering badly.

The precedent is on the record: the Pass-1 component audit found **five of seven load-bearing claims wrong, overstated or narrower than stated**, and none of them was a coding error. Shipping to an audience before the remaining components get the same treatment would be shipping the same class of error, having already been shown it exists.

**What this does not license.** Deferring a visibility push is not deferring contact. Answering questions, publishing honestly, and talking to individual practitioners are unrestricted. A version of this decision that becomes a reason to talk to nobody has failed, and would contradict the reason this repository is public at all.

**D25 — No fiscal sponsor for now, with named triggers rather than a revisit date.** `standing` · 2026-08
Engin has no fiscal host and is not seeking one. Recording it as a decision rather than leaving it as an unexamined gap, because it had been carried in the planning notes as *blocked*, and that was wrong in two ways.

**It was blocked on the wrong thing.** The constraint was recorded as NumFOCUS's 3–5 signatories. The actual requirements are a leadership body of at least three people *not sharing a common affiliation*, an OSI licence, a Code of Conduct, and **an active community of reasonable size**. The licence and Code of Conduct are satisfied. The community is not, and no decision available today changes that — a project with no users cannot manufacture one by choosing a governance structure. Counting signatories mistook the symptom for the constraint.

**And it was on nobody's critical path.** Fiscal sponsorship matters for tax-deductible donations and for grant routes that require a non-profit host. `D16` rules out donations. The primary grant target, NSF PESOSE, accepts US for-profit organizations directly, so `EnginBio` needs no host to be *eligible*. Being "blocked" on something nothing depends on is a cost that only looks like diligence.

**Corrected 2026-08-16: this paragraph said `EnginBio` "can submit", and eligibility is not submittability.** Checked against the solicitation rather than recalled — the program is now [NSF 26-506](https://www.nsf.gov/funding/opportunities/pesose-pathways-enable-secure-open-source-ecosystems/nsf26-506/solicitation), *Pathways to Enable **Secure** Open-Source Ecosystems*, which replaces NSF 24-606. Every track, **Track 1 included**, requires as a mandatory supplementary document a minimum of three and up to five letters of collaboration from *"current users or contributors (who are not directly related to the proposing team)"*, at up to two pages each. Engin has no third-party users, so no compliant package can be assembled today regardless of eligibility.

**The two halves of this decision turn out to share one constraint.** The paragraph above concedes that the community requirement cannot be satisfied by choosing a governance structure, and the reasoning then treats PESOSE as unblocked *because* it needs no host. But what blocks PESOSE is the same missing thing that blocks sponsorship: outside users. The decision stands — no fiscal host, for the reasons given — but not because the grant route is open. It is gated on the same trigger, which is already listed below.

**Triggers to revisit** — any one of them, rather than a date:

- a first sustained outside contributor, which is also the `D18` trigger for maintainer promotion;
- a funding route the project actually wants that requires a non-profit host;
- users in sufficient number that the *community* requirement is plausibly met.

**NumFOCUS Affiliation is the lighter tier and is not ruled out.** Affiliated projects stay legally separate and receive no services, but gain community and funding-opportunity access. It is cheaper to qualify for than sponsorship and worth an enquiry when the first trigger fires — not before, since the answer today would be the same as the reason for this decision.

**D26 — The project is "Engin"; the packages are `engin-*`; nothing is ever named bare `engin`.** `standing` · 2026-08
The question that prompted this was whether to rebrand from `engin` to `enginbio`. The answer is no, and the reasoning inverts partway through, so it is recorded rather than left as a preference.

**Bare `engin` is unavailable, and that part is not a judgement call.** It belongs to an unrelated, actively maintained Python dependency-injection framework, which holds the PyPI distribution name, the top-level import module, the console script and the `engin.readthedocs.io` slug. Three of the four places this project already says `enginbio` — the GitHub organization, the Read the Docs slug, the entity — were forced by collisions of exactly this kind, not chosen. The rebrand had already half-happened by attrition.

**But `enginbio` is the *more* collided name, not the less.** It is one silent letter from Engine Biosciences (`enginebio.com`, ~$86M raised) and a homophone of EnGen Bio (`engenbio.com`), and it shares a prefix and an industry with EnginZyme (cell-free biomanufacturing). The fair objection is that those three coexist without trouble — true, but they are mutually distinguishable in speech, and `EnginBio` against `EngineBio` is not. So a rebrand would trade a cheap collision (a 21-star library, in software, routed around by namespacing) for an expensive one (funded companies, in our own field, resolved by lawyers).

**The resolution is the COBRApy pattern, which is the field norm rather than a workaround.** Brand and package name need not match: COBRApy ships as `cobra` against a 44k-star Go library of the same name and is unharmed, because "COBRApy" does all the public work and the generic word lives only at the import line. BioSTEAM, QSDsan, DNAChisel and eQuilibrator all carry a domain marker or are coined. Nobody in this space ships a bare common word as the brand.

So: the product is **Engin**, the entity stays **EnginBio**, the domain stays `engin.bio`, packages are always `engin-*`, and no distribution, module or console script is ever named bare `engin`. The private overlay was renamed to `engin-app` under this decision.

**What is *not* decided here.** No trademark clearance has been run — no register was queried and no live mark verified. A live `ENGIN` mark in class 9 or 42 would settle this outright and override this decision; that search is tracked privately and is the highest-information result available. Separately, PyPI has no prefix reservation (PEP 752 accepted, PEP 755 draft, Simple API still at 1.4), so `engin-*` cannot be reserved as a namespace — each name must be claimed by upload, which is why registering them is a live task rather than a formality.

**D27 — Stage [0] target screening is permitted in the industrial direction, and its biosecurity review is this record.** `standing` · 2026-08-18
Commitment #2 in `BIOSECURITY.md` requires that any capability bearing on §5 be assessed before it ships, with the assessment recorded here under a decision ID. This is that record for stage [0] (#176) — a screening layer that ranks candidate target molecules for a use type by cost and manufacturability interval.

**§7 trigger 2 has fired, and this is the ahead-of-schedule reassessment it calls for.** That trigger reads "a proposed capability would identify or rank routes to a target the user did not supply." Stage [0] is exactly that proposal, so the policy is reassessed now rather than at the scheduled 2027-02-07 review.

**Assessment: no meaningful uplift, and the reason is narrower than the sentence it replaces.** §3 previously rested part of its argument on "neither answers *what to make* — only *how this would be made at industrial scale*." Stage [0] makes the first clause false while leaving the conclusion intact, which is a sign the clause was never what carried it. What carries it is that the suite holds **no model of what a molecule does in an organism**. A ranking over manufacturing economics does not become uplift by having more than one candidate in it, and a cost-per-kilogram interval over a set of industrial molecules discloses nothing about physiological activity that was not already public.

**Conditions on release, binding rather than aspirational.** The function-category index is sourced from public-domain EPA CPDat only — no GPL dependency (`D3`), and no NonCommercial data (`D12`'s licence rule). The ranking emits intervals and an explicit indistinguishability verdict rather than a bare ordering, because a point-estimate ranker over inputs that disagree by an order of magnitude produces confident-looking noise at the most expensive decision point. The scope statement says plainly that it does not address formulation, qualification or go-to-market.

**What this decision does not touch.** Every item in `BIOSECURITY.md` §5 stands unchanged, including item 5 (predicted physiological activity, toxicity or pathogenicity). The medical / bioactivity direction is **#177**, it amends `D19` rather than this decision, and it is undecided. Nothing here authorises it, and stage [0] is scoped industrial-only precisely so the two can be decided separately.

**Status: not built.** Per the pattern `BIOSECURITY.md` §6 already uses for cultivation prediction, the conditions above are binding terms on shipping stage [0], not descriptions of code that exists. This record is what Commitment #2 requires to exist *before* that code does.

---

## Superseded

| Earlier position | Replaced by |
|---|---|
| TEA and cross-process priors are a private moat | **D8** |
| Preserve an architectural seam for a future paid layer | **D14** |
| Decide the paid layer now | **D6** |
| Donation-funded | **D16** |
| Define a `BioprocessRun` interchange format | **D11** |
| Adopt MIFE/MIFD as the data model | **D11** |
| Private wiki for architecture and ADRs | **D22** |

## Changing a decision

Open an issue arguing with the reasoning. Substantive changes are recorded here with their rationale, and the superseded version is kept rather than deleted — the history is part of what makes this record worth reading.
