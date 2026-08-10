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
- **Raw material dominates COGS.** Media is roughly 35–50% of precision-fermentation cost of goods, ahead of facility depreciation (20–25%) and downstream processing (15–20%). That cost is governed by *yield*, which titer does not capture.
- **Cost is non-linear in TRY**, with thresholds and inflection points, so no single metric is a usable proxy for the objective.

**Accepted consequence: Engin looks worse on the metric everyone currently reports.** That trade is deliberate and is explained prominently rather than left to be discovered in a benchmark table.

> **Withdrawn justification, kept because the error is instructive.** This decision previously read: *"Recovery cost is determined upstream — by titer, strain and broth composition — but incurred downstream, so an optimizer maximizing titer can move the true objective backwards: a higher-titer strain with a messier broth can be economically worse."*
>
> **That mechanism is backwards.** Higher titer *reduces* downstream cost — less water to remove, smaller equipment, fewer unit operations — and purification is more expensive when broth concentration is low. Titer is the TRY metric that corresponds to downstream cost, and the two move together favourably.
>
> The decision survived; its reasoning did not. It was derived from mechanism and asserted confidently in three documents while the field had measurements saying the opposite. Recorded rather than quietly edited, because a project promising that its reasoning is contestable owes the reader its corrections too.

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

**D18 — Solo maintainer, with governance published up front, actively open to co-founders.** `standing`
Publish the decision-making process, the maintainer-promotion path and a succession plan now, honestly describing a one-person project. Defer maintainer recruitment until there are contributors to promote — maintainers emerge from contributors, contributors from users, and inverting that means asking people to sign on to an idea.

Reviewers and adopters don't require a headcount; they require a credible answer to single-point-of-failure, and a written succession path is that answer. A **co-founder** is a separate route and the project is actively open to one — peer-level from the start, not earned by accumulating commits.

**D19 — Short public biosecurity statement with named boundaries.** `standing`
An honest assessment stated plainly rather than hedged: bioprocess optimization is not meaningfully uplift-relevant, because nobody attempting harm is constrained by cost of goods. Plus an explicit list of what the project declines to build.

Cultivation prediction for uncultured organisms is the one roadmap item where the question isn't theoretical, and it ships with hazardous-taxa screening as a required component or not at all. That screening is evadable and lists lag reality — stated openly, because overclaiming would be worse than the gap.

**D24 — Build and document first; no visibility push until the tools are validated on real data.** `standing`
Ordering, recorded as a constraint so it survives the temptation to reverse it. Coding and documentation now; then validation on real data; then deliberate outreach.

**Why a decision and not just a plan.** The pressure runs the other way. Visibility is the most legible form of progress, it's available at any moment, and a project with no users can always tell itself that talking to people *is* the validation. D12 says real data gates the claims; D24 says it also gates the audience.

**The asymmetry.** There is roughly one first introduction to any given community. Someone shown a tool calibrated only on synthetic data draws a conclusion about the project rather than about the demo, and doesn't revisit it. Early and quiet is recoverable; early and visibly thin is much less so. The cost of waiting is a few months of obscurity for a project nobody is currently waiting on.

**Gate, concretely:** real-data calibration coverage published, the out-of-distribution failure mode published, and one non-synthetic worked example a stranger can run.

**What this does not license.** Deferring a visibility push is not deferring contact. Answering questions, publishing honestly, and talking to individual practitioners are unrestricted. A version of this decision that becomes a reason to talk to nobody has failed, and would contradict the reason this repository is public at all.

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
