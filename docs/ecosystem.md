# Ecosystem

**What Engin deliberately does not build, and where to go instead.**

`D9` says compose, don't reimplement: build only what has no open equivalent, or
where the equivalent has genuinely gone stale. `D10` says don't fork the living.
Both decisions are load-bearing, and both are invisible from the outside — a
reader arriving at this repository sees the code that exists, not the much larger
set of capabilities that were considered and left to someone else.

This page is that missing half. For each capability adjacent to the strain-to-scale
funnel, it records whether Engin implements it, and if not, the two or three open
implementations a practitioner should actually reach for.

```{note}
**How to read an entry.** Every implementation links to its own repository, which
is the reference for what it does and the place to check whether the description
below has gone stale. Version and maintenance observations are dated snapshots,
not commitments — a project healthy on the date shown can be abandoned by the time
you read this.

Pros and cons are editorial judgements about fit for bioprocess work, offered as
such rather than dressed as findings (`CONTRIBUTING.md`, rule 3). Where a claim is
about the world rather than about a package's own documented behaviour, it cites a
source (`D23`).
```

```{warning}
**Licences are stated because they bite.** Engin is Apache-2.0 and its users are
commercial. Several tools in this space are GPL, non-commercial, or no-derivatives,
and at least one has *become* more restrictive over time. Nothing here is legal
advice; check the LICENSE file yourself before you depend on anything.
```

Entries marked **dead end** are recorded on purpose. Half the cost of surveying a
field is rediscovering that the obvious-looking package stopped being maintained
in 2021, and that finding is worth as much as the recommendation.

---

## Bayesian optimization and design of experiments

*Funnel stage: process optimization (`engin-core`), campaign planning (`engin-protein`).*

**Engin's position: composes, and benchmarks against.** `engin-core` ships a
Gaussian-process recommender with expected improvement because the recommender's
objective is net $/kg rather than titer (`D13`), which is a different question from
"optimize this response". The optimization machinery itself is not Engin's
contribution, and a textbook response-surface baseline currently beats it on our
own simulator — see [Benchmarks](benchmarks).

### BayBE — [emdgroup/baybe](https://github.com/emdgroup/baybe)

Apache-2.0. A BoTorch-backed Bayesian DoE engine built for wet-lab campaigns.

- **Pro** — models the constraints that actually break generic BO on media work:
  mixed discrete/continuous/categorical parameters, linear and cardinality
  constraints ("at most four of these nine components"), batch recommendation, and
  asynchronous partial measurements.
- **Pro** — transfer learning is first-class, which is the shape of the
  shake-flask-to-bioreactor problem, and it ships a backtesting harness so you can
  run the honest BO-versus-RSM comparison on your own history.
- **Con** — pulls the full torch/botorch/gpytorch stack for a package whose job is
  "suggest eight flask conditions", and the release cadence is aggressively
  breaking. Pin the exact version.

Reference: Fitzner et al., *Digital Discovery* (2025),
[10.1039/D5DD00050E](https://doi.org/10.1039/D5DD00050E).

### Ax + BoTorch — [facebook/Ax](https://github.com/facebook/Ax), [meta-pytorch/botorch](https://github.com/meta-pytorch/botorch)

MIT. The reference implementation of modern acquisition functions, plus a campaign
layer over it.

- **Pro** — everything downstream in this slot is built on BoTorch, so the learning
  transfers; qNEHVI gives real multi-objective support (titer versus cost versus
  impurity) that nothing else here matches.
- **Pro** — Ax persists trial state between weeks-long experiment rounds and can
  mark a trial abandoned, which is what a contaminated run actually needs.
- **Con** — no domain affordances whatsoever, and Ax pins an exact BoTorch version,
  so a bump breaks you until Meta cuts a matching release. Most tutorials online
  target the retired Service API.

Reference: Balandat et al., NeurIPS 2020, [arXiv:1910.06403](https://arxiv.org/abs/1910.06403).

### BoFire — [experimental-design/bofire](https://github.com/experimental-design/bofire)

BSD-3-Clause. A BoTorch-backed framework that treats constrained DoE and Bayesian
optimization as one problem, written by industrial chemical and pharmaceutical
practitioners.

- **Pro** — the only entry in this slot with first-class *constrained* experimental
  design: it generates designs that satisfy linear, non-linear and black-box output
  constraints, and it ships sampling for constrained mixed continuous/discrete/
  categorical spaces. That is the mixture-constraint gap this section flags below,
  addressed directly rather than worked around.
- **Pro** — objectives are separated from the outputs they operate on, including
  close-to-target objectives, so "hit this impurity spec while maximizing titer" is
  expressible without encoding it into a scalarization by hand. Single and
  multi-objective are both supported.
- **Pro** — every domain object is JSON-serializable, which is what makes a campaign
  definition storable and replayable across weeks-long rounds rather than living in a
  notebook.
- **Con** — torch and BoTorch, same as BayBE, so it does not relieve the dependency
  objection that sends readers to ProcessOptimizer.
- **Con** — the maintainer base is concentrated in a small number of industrial
  sponsors, and the feature surface is wide enough that parts of it are thinly
  exercised outside the authors' own use cases.

Reference: Dürholt et al., *Journal of Machine Learning Research* 26(204) (2025),
[jmlr.org/papers/v26/24-1540.html](https://jmlr.org/papers/v26/24-1540.html).

### ProcessOptimizer — [novonordisk-research/ProcessOptimizer](https://github.com/novonordisk-research/ProcessOptimizer)

BSD-3-Clause. `LICENSE.md` opens with the words "New BSD License" and carries the
standard three-clause text; GitHub's classifier reports `NOASSERTION`, which is a
detection artefact of the `.md` extension and the `a./b./c.` enumeration rather than
a licensing question. A scikit-optimize fork retuned for noisy physical processes.

- **Pro** — no torch. scipy and numpy only, installs in seconds, plausible inside a
  regulated or air-gapped environment where the alternatives are not.
- **Pro** — ships D-optimal classical designs alongside the optimizer, so screening
  design and sequential optimization live in one dependency.
- **Con** — inherits scikit-optimize's ageing internals and its scikit-learn version
  fragility, and there is still no fully-Bayesian option.
- **Con** — the GitHub releases tab lags PyPI, so judge this one from PyPI and from
  commits rather than from the releases page.

Reference: Bertelsen et al., *Journal of Chemical Information and Modeling* 65(4)
(2025), [10.1021/acs.jcim.4c02240](https://doi.org/10.1021/acs.jcim.4c02240).

**Classical DoE.** [pydoe](https://github.com/pydoe/pydoe) (BSD-3) is the maintained
home of the classical designs — factorial, Plackett-Burman, Box-Behnken, central
composite, mixture designs, definitive screening. Mixture designs matter more here
than anything else, because media components are a constrained mixture and most BO
libraries have no first-class notion of that — BoFire above is the exception, and is
the reason that sentence now says *most* rather than *all*. pydoe generates designs
and does not fit them; the response-surface fit is statsmodels. **There is no
maintained dedicated Python RSM package, and Engin should stop implying otherwise.**
That remains true: BoFire builds designs under constraints, it does not give you the
fitted quadratic and its prediction interval.

**Dead ends.** `pyDOE3` was archived in May 2026 and points back at `pydoe`.
[scikit-optimize](https://github.com/holgern/scikit-optimize) has been dormant since
mid-2024. [dexpy](https://github.com/statease/dexpy) last moved in 2018.
[Summit](https://github.com/sustainable-processes/summit) is useful now only as a
source of benchmark problems. [Atlas](https://github.com/aspuru-guzik-group/atlas)
has a good paper and a Python ceiling below 3.11.
[EDBO+](https://github.com/doyle-lab-ucla/edboplus) is research code — cite the
method, don't depend on the package.

**If you pick one:** BayBE, unless the torch dependency is disqualifying, in which
case ProcessOptimizer. Pick BoFire instead of BayBE when the binding difficulty is
*constraints on the design itself* — a media mixture that must sum, a component that
can only appear with another — because that is the case it is built for and the one
where BayBE's constraint support runs out first.

---

## Distribution-free uncertainty quantification

*Funnel stage: every calibrated interval Engin publishes.*

**Engin's position: wraps.** Split-conformal calibration with an sd-normalized
multiplier is implemented in `engin-core`; MAPIE is kept as an independent
cross-check precisely because it is a *different* method, which is the point of a
cross-check. See [Conformal calibration](methods/conformal-calibration).

### MAPIE — [scikit-learn-contrib/MAPIE](https://github.com/scikit-learn-contrib/MAPIE)

BSD-3. The scikit-learn-contrib conformal library.

- **Pro** — breadth nothing else matches: split, CV+, jackknife+, CQR,
  classification sets, EnbPI for time series, and conformal risk control, all behind
  an sklearn-compatible API.
- **Pro** — `StdConformityScore` conformalizes an estimator that already reports a
  predictive standard deviation, so a GP forecast can be conformalized without
  discarding the model's own variance.
- **Con** — the v1 API is a rewrite; most tutorials on the internet target the dead
  v0 classes. The newer conditional-conformal features require torch, so
  "lightweight" holds only on the classical path.
- **Con** — the guarantee it implements is the marginal one, and the library will not
  stop you reading a per-stratum number off it. That is a property of split conformal
  rather than of MAPIE, but it is where users of it go wrong.

Reference: Cordier et al., *Proceedings of COPA* (PMLR 204:549-581, 2023).

```{note}
**Corrected 2026-08-16.** This entry previously said MAPIE "has a preprint and no
peer-reviewed software publication", and congratulated this register for recording
the absence rather than papering over it. The absence was not real. MAPIE's own
`CITATION.cff` sets its preferred citation to the COPA 2023 conference paper above
and demotes the arXiv item this page used to print to a field named `old-citation`.
So the entry cited the superseded reference *and* drew a conclusion from an absence
that the project had itself already filled — the failure mode `D23` exists to catch,
committed by the page that implements `D23` from the reader's side.
```

### crepes — [henrikbostrom/crepes](https://github.com/henrikbostrom/crepes)

BSD-3. Conformal predictive *systems* — a calibrated predictive distribution per
test object, not an interval at one confidence level.

- **Pro** — this is the right primitive for Engin's actual use case. Propagating
  titer uncertainty into a cost-per-kilogram model wants a distribution to integrate
  over, and MAPIE does not give you one.
- **Pro** — Mondrian and difficulty-normalized variants give conditional coverage
  per stratum, which is what you need when a calibration set mixes shake-flask and
  bioreactor runs; and conformal test martingales give an actual alarm for
  exchangeability drift.
- **Con** — single-maintainer, pre-1.0, and willing to change default behaviour
  between point releases. Narrower than MAPIE: no time series, no risk control.

Reference: Boström, *Proceedings of COPA* (PMLR 230:236-249, 2024).

### TorchCP — [ml-stat-Sustech/TorchCP](https://github.com/ml-stat-Sustech/TorchCP)

**LGPL-3.0 / GPL-3.0 — copyleft, and categorically different from everything else in
this slot.** For an Apache-2.0 project with commercial users this needs legal review,
not a shrug.

- **Pro** — a peer-reviewed JMLR software paper, and by far the widest catalogue of
  published classification score functions.
- **Con** — torch is a hard requirement. If your forecaster is a GP, a
  gradient-boosted tree, or a mechanistic ODE — the common case in this field — you
  are installing a deep-learning stack to compute quantiles.
- **Con** — the project has **never cut a GitHub release**, and PyPI has not been
  refreshed in roughly ten months while commits continue to land. There is no tagged
  point you can pin to and reason about; you are pinning to a PyPI upload or to a
  commit hash.

**Also worth knowing.** [puncc](https://github.com/deel-ai/puncc) is MIT with a
genuinely optional torch dependency and a certification-oriented framing. This page
called its feature velocity low; after a long quiet stretch it has shipped several
releases through 2026, so treat that as withdrawn rather than merely softened. One
thing to know before depending on it: the MIT licence is declared in packaging
metadata and per-file headers, and there is no top-level LICENSE file — which this
page treats as disqualifying elsewhere, so it is named here too.
[venn-abers](https://github.com/ip200/venn-abers) solves a
different problem — validity of predicted *probabilities* for go/no-go decisions —
and is a complement, not a substitute.

**Dead ends.** [nonconformist](https://github.com/donlnz/nonconformist), the historical
reference implementation, has been dormant since 2021; crepes is the natural migration
target. [Amazon Fortuna](https://github.com/awslabs/fortuna) was archived by AWS in
April 2025 — anyone arriving from an old AWS blog post should be redirected.

**If you pick one:** MAPIE, and add crepes the moment you need a predictive
distribution rather than an interval.

---

## Techno-economic analysis

*Funnel stage: cost-per-kilogram (`engin-core`, the `[tea]` extra).*

**Engin's position: composes.** BioSTEAM backs techno-economics as an optional extra.
Engin's contribution is the coupling — propagating a calibrated titer forecast through
recovery into a probabilistic $/kg — not the flowsheet simulation. See
[Cost](guides/cost).

### BioSTEAM — [BioSTEAMDevelopmentGroup/biosteam](https://github.com/BioSTEAMDevelopmentGroup/biosteam)

NCSA (permissive). Flowsheet design, simulation, TEA and LCA of biorefineries.

- **Pro** — uncertainty is a first-class construct rather than a bolt-on, which is
  the whole differentiator against the commercial tools.
- **Pro** — ships a library of published, peer-reviewed biorefinery models
  (Bioindustrial-Park) you can diff against, so "compose" actually means something
  other than an empty flowsheet.
- **Con** — fermentation is modelled at the stoichiometric-conversion and
  reactor-sizing level. No structured kinetics, no scale-up correlation layer.
  BioSTEAM sits *downstream* of a titer forecast; it does not produce one.
- **Con** — effectively a single dominant committer, and the GitHub Releases tab is
  years stale because the project ships via PyPI only. Judge maintenance from
  commits, not from releases.

Reference: Cortés-Peña et al., *ACS Sustainable Chem. Eng.* (2020),
[10.1021/acssuschemeng.9b07040](https://doi.org/10.1021/acssuschemeng.9b07040).

### IDAES-PSE — [IDAES/idaes-pse](https://github.com/IDAES/idaes-pse)

BSD. A Pyomo-based, equation-oriented framework for simultaneous simulation and
design optimization.

- **Pro** — fully differentiable through Pyomo, so "minimize cost subject to the
  flowsheet" is one optimization problem rather than an outer loop around a
  sequential-modular simulator. Nothing else free in this slot does that.
- **Pro** — DOE national-lab backing and multiple active committers. The lowest
  abandonment risk in this category by a distance.
- **Con** — no biorefinery or fermentation model library at all; the model library
  targets energy systems. Everything bioprocess-specific you write yourself.
- **Con** — requires a post-install binary fetch for solvers, which breaks
  air-gapped and locked-down CI, and convergence debugging demands real PSE fluency.

### QSDsan — [QSD-Group/QSDsan](https://github.com/QSD-Group/QSDsan)

NCSA. A BioSTEAM-derived platform coupling simulation, TEA and life-cycle assessment
in one system object.

- **Pro** — integrated LCA reading the same streams as the TEA, with BioSTEAM's
  Monte Carlo machinery inherited, so impact results carry uncertainty. Most LCA
  tooling does not do that.
- **Con** — the unit library, cost correlations and defaults are sanitation and
  resource-recovery shaped, not industrial aerobic fermentation shaped.
- **Con** — inherits BioSTEAM's pins and bus-factor risk, and adds a second layer of
  the same.

**Not open, but name them honestly.** SuperPro Designer remains the industry default
for batch bioprocess TEA and scheduling, and has no open-source equal on
equipment-occupancy or campaign scheduling. Aspen Plus is the continuous-process
default. Both are closed and per-seat licensed, which is the gap BioSTEAM occupies.
[DWSIM](https://github.com/DanWBR/dwsim) is the credible free Aspen-alike but is a
GPL-3.0 .NET desktop application reached from Python over a bridge — hostile to
scriptable, CI-testable pipelines.

**If you pick one:** BioSTEAM, because it is the only permissively licensed,
pip-installable option that treats TEA uncertainty as a first-class construct and
ships fermentation models to start from.

---

## Genome-scale metabolic modelling and strain design

*Funnel stage: upstream of route ranking (`engin-pathway`) and host selection (`engin-host`).*

**Engin's position: does not build, and is downstream of.** FBA predicts feasibility
well and does not predict titer. That gap is the whole reason `engin-pathway` exists —
it ranks routes by manufacturability, and route feasibility is somebody else's
correctly-solved problem.

### COBRApy — [opencobra/cobrapy](https://github.com/opencobra/cobrapy)

**Dual GPLv2+ / LGPLv2+.** For a permissively licensed project this needs a deliberate
decision — shelling out is not the same as importing.

- **Pro** — it is the interoperability layer, not merely an option. StrainDesign,
  CarveMe, ModelSEEDpy and Escher all read or write `cobra.Model`; choosing anything
  else in Python means writing adapters.
- **Pro** — solver-agnostic via optlang, works on free GLPK by default and scales to
  CPLEX/Gurobi without code changes; full SBML Level 3 FBC round-tripping.
- **Con** — pure stoichiometry. No kinetics, no enzyme cost, no thermodynamic
  feasibility, and it will return thermodynamically impossible loops unless you add
  loopless constraints.
- **Con** — the packaging metadata's Python classifiers are stale, so test against
  your interpreter rather than trusting `requires_python`.

Reference: Ebrahim et al., *BMC Syst. Biol.* (2013),
[10.1186/1752-0509-7-74](https://doi.org/10.1186/1752-0509-7-74).

### StrainDesign — [klamt-lab/straindesign](https://github.com/klamt-lab/straindesign)

Apache-2.0 — the cleanest licence in this slot. Minimal cut sets, OptKnock,
RobustKnock, OptCouple over a COBRApy model.

- **Pro** — currently the only maintained Python package implementing this breadth of
  design algorithms. Its predecessors are dormant, so this is a category of one.
- **Pro** — supports SCIP as well as the commercial solvers, and SCIP handles
  indicator constraints where GLPK does not, so genome-scale minimal cut sets are
  reachable without a licence.
- **Con** — practical performance on real genome-scale models still leans on CPLEX or
  Gurobi; budget for an academic licence if you are serious.
- **Con** — self-classified as alpha on PyPI. Pin the version.

Reference: Schneider et al., *Bioinformatics* (2022), 38(21):4981.

### Model reconstruction: CarveMe and gapseq

[CarveMe](https://github.com/cdanielmachado/carveme) (Apache-2.0) carves an
organism-specific model out of a curated universal model from a genome annotation, in
minutes. Fast, BiGG-namespaced, community-model capable — but it needs Diamond and an
MILP solver installed out of band, the free-solver path is slow, and it is
prokaryote-oriented, so *S. cerevisiae* and *P. pastoris* hosts are out of scope.

[gapseq](https://github.com/jotech/gapseq) (GPL-3.0) infers pathways from sequence
homology and gap-fills, producing per-reaction evidence a reviewer can interrogate —
which carved output does not give you. It is the more actively curated of the two, with
dated reference-database provenance. But it is R plus shell, so it is a subprocess
dependency in a Python stack, and it is bacteria and archaea only.

**Reaction thermodynamics.** [eQuilibrator](https://gitlab.com/equilibrator/equilibrator-api)
(MIT, on GitLab) is the right answer for ΔG′° estimation and is actively developed. The
real cost is setup: the initial data download is large and slow, which is hostile to CI
and containers. [pyTFA](https://github.com/EPFL-LCSB/pytfa) is a trap — the repository
sees occasional commits but the published package is four years old and will not install
cleanly on a modern interpreter. Install from git or not at all.

**Model quality.** [memote](https://github.com/opencobra/memote) is still the only
standardized GEM test suite and the community scoring convention, and it has seen no
commits since January 2024. Run it, pin the whole dependency tree, and do not build a
CI gate on it.

**Dead ends.** [cameo](https://github.com/biosustain/cameo) has been dormant since 2022
and is superseded by StrainDesign. [MEWpy](https://github.com/BioSystemsUM/mewpy) had the
most interesting evolutionary strain-design layer and has been dormant since 2024. The
MATLAB COBRA Toolbox requires a commercial MATLAB seat, which makes it non-reproducible
for anyone without an institutional licence regardless of its own terms.

**If you pick one:** COBRApy — it is not really a choice, it is the data model. Decide
the GPL question deliberately before importing it.

---

## Biosynthetic route enumeration

*Funnel stage: immediately upstream of `engin-pathway`.*

**Engin's position: explicitly does not build.** Route-finding tools exist and work.
The whitespace is *ranking* the routes they produce by manufacturability, not finding
them. `engin-pathway` consumes routes; it does not enumerate them.

### DORAnet — [wsprague-nu/doranet](https://github.com/wsprague-nu/doranet)

Apache-2.0 — the only licence in this slot that is a drop-in match for Engin's.
Forward, retro and hybrid chemo-enzymatic reaction network enumeration; the explicit
successor to Pickaxe and NetGen.

- **Pro** — plain `pip install` on modern Python with no KNIME, Java, CPLEX or ChemAxon
  tail. It behaves like modern software: typed, linted, CI'd.
- **Pro** — genuinely hybrid. It enumerates routes mixing enzymatic and chemocatalytic
  steps, which the pure-bio tools structurally cannot.
- **Con** — self-classified pre-alpha and currently published as an alpha pre-release.
  The API is not stable; pin the exact version.
- **Con** — small maintainer surface (one lab), no tagged releases and no changelog, so
  you cannot diff behaviour between versions from the repository alone.

Reference: Zhang et al., *Digital Discovery* (2025),
[10.1039/d5dd00229j](https://doi.org/10.1039/d5dd00229j).

### RetroPath2.0 — [brsynth/retropath2-wrapper](https://github.com/brsynth/retropath2-wrapper)

MIT code over the [RetroRules](https://retrorules.org/) rule set, with
[rp2paths](https://github.com/brsynth/rp2paths) extracting pathways from the network.

- **Pro** — the de facto standard in metabolic-engineering retrosynthesis and the one
  a reviewer will recognize; the rules are reusable independently of the workflow, and
  diameter-parameterised rules let you dial promiscuity explicitly.
- **Con** — **requires a KNIME installation.** The Python package wraps a Java GUI
  workflow; it is heavy, brittle in containers, and awkward in CI.
- **Con** — **`pip install retropath2-wrapper` gets you a package from 2020.** PyPI
  is not empty, which is what makes this a trap rather than an inconvenience: it is
  frozen many minor versions behind a repository that is still moving. Install from
  conda or from source, and check what you actually got.
- **Con** — the code is MIT but the RetroRules *dataset* states no licence anywhere we
  could find. Ask before redistributing rules.

Reference: Delépine et al., *Metabolic Engineering* (2018),
[10.1016/j.ymben.2017.12.002](https://doi.org/10.1016/j.ymben.2017.12.002).

### RetroBioCat 2 — [willfinnigan/RetroBioCat-2](https://github.com/willfinnigan/RetroBioCat-2)

**CC BY-NC 4.0 — non-commercial, not an OSI licence.** Note the regression: version 1
was MIT. Listed because it is the most actively developed biocatalysis-specific route
finder, shipping template-based and template-free expanders plus MCTS search with
expert-curated enzyme rules. **Engin's commercial users cannot use it.** List it, don't
depend on it.

**Also.** [BioNavi](https://github.com/zengtsysu/BioNavi) (MIT) is a transformer-ensemble
search that is strongest exactly where rule-based enumeration is weakest — complex
natural-product scaffolds — but it needs a GPU, installs from a shell script, and has
been quiet for over a year. Use `zengtsysu/BioNavi`, not the unlicensed original
`prokia/BioNavi-NP`.

**Dead ends and traps.** [Pickaxe / MINE-Database](https://github.com/tyo-nu/MINE-Database)
is abandoned and supports only Python 3.7-3.9; DORAnet is its successor.
[novoStoic2.0](https://github.com/maranasgroup/novoStoic2.0) **has no LICENSE file at
all** — default copyright, no grant of rights — and additionally requires proprietary
CPLEX and ChemAxon. [ATLASx](https://lcsb-databases.epfl.ch/Atlas2) is scientifically
excellent and is a login-gated web service with no stated terms of use; treat it as a
manual lookup, not a dependency. The Selenzyme enzyme-selection ecosystem is fragmented,
with the maintained forks archived.

**If you pick one:** DORAnet, with the pre-alpha caveat stated loudly. RetroPath2.0 if
you need the publication-defensible answer and can eat KNIME.

---

## Protein fitness prediction and representation

*Funnel stage: `engin-protein` featurization and the low-N loop.*

**Engin's position: composes.** `engin-protein` is a GP plus expected improvement plus
conformal intervals pointed at a fitness landscape. The representation feeding it is
somebody else's model, and the benchmark judging it should be somebody else's benchmark.

```{warning}
Licences in this slot are unusually treacherous and have changed recently in both
directions. Check the LICENSE file *and* the specific model checkpoint's card before
committing to anything.
```

### ESM-2 and the ESM family — [Biohub/esm](https://github.com/Biohub/esm)

MIT, with a caveat. ESM-2 weights on HuggingFace are MIT; the newer ESM C / ESM3 /
ESMFold2 code and weights are now MIT under Chan Zuckerberg Biohub, a genuine
improvement on the previous non-commercial terms. **But** the repository points at a
separate Acceptable Use Policy, and at least one checkpoint card carries an unexplained
`other` licence tag alongside `mit`. Do not tell your legal team "it's just MIT".

- **Pro** — frozen ESM-2 embeddings plus a simple supervised head on tens-to-hundreds of
  measured variants remains the best-understood, lowest-risk low-N baseline available,
  and it needs no MSA — critical for engineered or chimeric sequences.
- **Con** — zero-shot likelihood is a mediocre predictor of engineering-relevant
  properties. It scores evolutionary plausibility, not activity at 55 °C or expression
  titre. Treat it as a prior.
- **Con** — weak on indels; the masked-marginal convention is defined for substitutions
  and indel scoring needs poorly calibrated workarounds. The original ESM-2 repository is
  archived, so you depend on the HuggingFace reimplementation.

Reference: Lin et al., *Science* (2023),
[10.1126/science.ade2574](https://doi.org/10.1126/science.ade2574).

### EVcouplings — [debbiemarkslab/EVcouplings](https://github.com/debbiemarkslab/EVcouplings)

MIT, with a stated carve-out for included CNS scripts. Fits a Potts model to an MSA and
scores variant effects.

- **Pro** — on families with deep alignments this remains competitive with large language
  models at a fraction of the compute, CPU-only, and it models epistasis explicitly —
  which matters for the combinatorial variants a real campaign proposes.
- **Con** — requires an MSA, and the alignment's depth is the whole ballgame. Shallow
  families give confidently wrong scores; check effective sequence depth before trusting
  output.
- **Con** — needs external HMMER and PLMC binaries on PATH, cannot score indels, and
  cannot score outside the aligned region.

### ProteinGym — [OATML-Markslab/ProteinGym](https://github.com/OATML-Markslab/ProteinGym)

MIT. The standard benchmark suite of deep mutational scanning assays, shipping splits
plus reference implementations of the baselines — including an indel benchmark, which
very few resources offer.

- **Pro** — it is how Engin avoids shipping an unbenchmarked ranking claim. Dozens of
  zero-shot and supervised baselines are implemented, so you compare without
  reimplementing competitors.
- **Con** — a benchmark, not a predictor. Heavyweight data, not CI-friendly.
- **Con** — DMS assays are a biased proxy for engineering campaigns: mostly single
  substitutions on well-studied natural proteins, mostly saturating rather than low-N.
  Good ProteinGym numbers do not guarantee good performance on a 96-variant plate.

**Also.** [SaProt](https://github.com/westlake-repl/SaProt) (MIT) fuses sequence with
Foldseek structural tokens and has a companion aimed explicitly at wet-lab scientists
fine-tuning on small in-house data — the right persona — at the cost of a fold-then-tokenize
pipeline stage. [ProteinNPT](https://github.com/OATML-Markslab/ProteinNPT) (MIT) is one of
very few architectures built *for* the low-N regime rather than adapted to it, but it is
GPU-hungry, research-packaged, and slowing.
[FLIP](https://github.com/J-SNACKKB/FLIP) tests distribution shift on enzyme-engineering
datasets, which complements ProteinGym's sample-scarcity splits.
[ProteinMPNN](https://github.com/dauparas/ProteinMPNN) and
[LigandMPNN](https://github.com/dauparas/LigandMPNN) are MIT for code *and* weights but are
inverse-folding models — a decent zero-shot stability proxy and a poor activity predictor.

**Licensed out of reach.** [VenusFSFP / Pro-FSFP](https://github.com/ai4protein/VenusFSFP)
is arguably the most on-topic low-N method published, and it is **CC BY-NC-ND** —
non-commercial *and* no-derivatives, so you may not even distribute a modified version.
Reimplement from the paper under your own licence; do not fork the repository.

**If you pick one:** ESM-2 at the 650M checkpoint via HuggingFace, benchmarked with
ProteinGym, with EVcouplings as the CPU-only epistasis-aware second opinion where the
family has a deep alignment.

---

## Mechanistic simulation and digital twins

*Funnel stage: `engin-core`'s fed-batch simulator.*

**Engin's position: builds a deliberately small one, and would rather not.** The
simulator exists to generate benchmark data with known ground truth, not to be a
credible process model — see [Limitations](limitations).

```{note}
**There is no dominant, actively maintained, open-source fermentation digital twin.**
The purpose-built candidates are dead; the live candidates are generic ODE engines or
flowsheet simulators that happen to contain bioreactor units. Recent digital-twin work
in this field publishes papers, not maintained packages. That absence is a real finding
and is stated here rather than papered over (`D15`).
```

### BASICO / COPASI — [copasi/basico](https://github.com/copasi/basico)

Artistic-2.0. A Pythonic wrapper over the COPASI biochemical network engine.

- **Pro** — parameter estimation and sensitivity analysis are first-class and
  battle-tested, which is precisely the part a hand-written ODE simulator gets wrong.
- **Pro** — discrete events handle feed starts, bolus additions and induction switches
  natively, and SBML round-trips so users are not locked into anyone's object model.
- **Con** — the data model is species-and-reaction centric. Volume change from feeding,
  gas transfer and off-gas balances become awkward pseudo-reactions; there is no
  bioreactor abstraction.
- **Con** — effectively one maintainer, and a SWIG-wrapped C++ engine means integration
  failures drop you out of Python fast.

Reference: Bergmann, *JOSS* (2023), [10.21105/joss.05553](https://doi.org/10.21105/joss.05553).

### Tellurium / libRoadRunner — [sys-bio/tellurium](https://github.com/sys-bio/tellurium)

Apache-2.0. Antimony's readable model language over a JIT-compiled SBML simulator.

- **Pro** — JIT compilation makes parameter sweeps and Monte Carlo over a fed-batch model
  dramatically cheaper than a `scipy.integrate` loop, and SED-ML makes the *experiment*
  reproducible, not just the model.
- **Con** — same structural mismatch as COPASI: no reactor, no feed or gas-transfer
  abstraction. Parameter estimation is weaker, so you bolt on your own optimizer — the
  exact reimplementation trap.
- **Con** — LLVM-backed binary wheels are a recurring install problem on new interpreters
  and on ARM. The GitHub releases tab also lags PyPI here, so judge it the way this page
  judges BioSTEAM: from commits and PyPI, not from the releases page.

**Downstream.** [CADET-Core](https://github.com/cadet/CADET-Core) and
[CADET-Process](https://github.com/fau-advanced-separations/CADET-Process) are
best-in-class for chromatography and downstream unit operations, actively developed, and
GPL-family. They do not simulate fermentation, but recovery is where a large share of
cost-of-goods lives for high-value products — so for the downstream half of a $/kg model
this is the right thing to point at.

**Dead ends, and this one hurts.** [pyFOOMB](https://github.com/MicroPhen/pyFOOMB) is the
closest thing to a purpose-built bioprocess ODE plus parameter estimation plus uncertainty
framework that has ever existed, and it has not moved since February 2021. Cite the paper
for design ideas; do not send users to install it.
[PenSimPy](https://github.com/smpl-env/PenSimPy) has been dormant since 2021 and needs a
C++ extension built from source; the valuable artifact there is the IndPenSim dataset and
benchmark, not the Python port. [dfba](https://gitlab.com/davidtourigny/dynamic-fba)
remains the reference dynamic-FBA implementation and has not released since 2020.

**If you pick one:** BASICO, for the parameter estimation Engin's own simulator does not
attempt — and BioSTEAM alongside it for the economics half, because they solve different
problems.

---

## Bioprocess data standards

*Funnel stage: the ingest layer (`engin-core.loaders`, `engin-core.convention`).*

**Engin's position: builds the loaders, adopts the vocabulary.** `D11` resolved to use
xarray and pandas as-is with a thin published convention over them, because bioprocess
data is not special enough to need its own container. The ingest layer — messy vendor
export to usable structure — is the actual contribution. See
[Data convention](design/data-convention).

```{note}
**These get conflated constantly, so the taxonomy comes first.** A reporting *checklist*
(MIFE, MIFD) says which fields must exist. A data *structure* (xarray, Frictionless,
AnnData) says how bytes are laid out. A *model* exchange format (SBML) carries a model,
not a run. A *device protocol* (SiLA 2, OPC UA) is a wire format at runtime. You need one
from each of the first two rows. Choosing OPC UA does not give you a file format, and
SBML has nowhere to put your dissolved-oxygen trace.
```

### MIFE / MIFD — [bioindustry-4.0/mim_ontology](https://gitlab.com/bioindustry-4.0/mim_ontology)

GPL-3.0-or-later. The first fermentation-specific minimum-information standard, as paired
metadata schemas for the experiment and the device.

- **Pro** — the only standard here actually designed for fermentation runs. Everything
  else is borrowed from genomics, geoscience, or lab automation.
- **Pro** — LinkML source means a machine-readable JSON Schema for free, so it is a
  checklist you can enforce in CI rather than a table in a PDF.
- **Con** — new, with no tagged release and no adoption track record. Building on it is a
  bet and should be labelled one.
- **Con** — metadata only. It does not tell you how to serialize a high-frequency sensor
  trace; you still need a structure underneath.

Reference: Georgakilas et al., *GigaScience* (2026),
[10.1093/gigascience/giag038](https://doi.org/10.1093/gigascience/giag038).
*(Corrected 2026-08-16: this read "Koehorst et al." Koehorst is the paper's last
author, not its first.)*

### xarray and CF conventions — [pydata/xarray](https://github.com/pydata/xarray)

Apache-2.0. Labeled N-dimensional arrays serializing to netCDF or Zarr.

- **Pro** — the data model is already the right shape: run × time × channel with per-run
  attributes and irregular time coordinates. Zarr gives chunked, appendable,
  object-store-friendly storage you can stream a running batch into.
- **Pro** — the best maintenance profile of anything on this page, by a wide margin.
- **Con** — CF's controlled vocabulary is geoscience. There is no CF standard name for
  dissolved oxygen in a bioreactor, OUR, or specific growth rate, so you borrow the
  *mechanism* (units, `cell_methods`) and invent the names. Claiming "CF compliant" would
  be misleading, and Engin's convention says so.
- **Con** — rectangular arrays. Channels sampled at different rates force NaN-padding or
  DataTree, neither ergonomic.

### Frictionless Data — [frictionlessdata/frictionless-py](https://github.com/frictionlessdata/frictionless-py)

MIT. A JSON descriptor that types columns and travels next to plain CSVs.

- **Pro** — radically lower adoption cost than anything else here. Runs stay as CSVs
  anyone can open, and validation is scriptable, so "pH is missing on three of forty runs"
  fails CI instead of failing silently in a model fit.
- **Con** — tabular only. Long-format CSV for high-frequency multichannel data is wasteful
  and does not scale.
- **Con** — types columns, carries no domain semantics. Two labs can produce valid and
  mutually incompatible packages, so it does not solve interchange without MIFE on top.

**Device protocols, clearly labelled as such.** [asyncua](https://github.com/FreeOpcUa/opcua-asyncio)
(LGPL-3.0) is the pure-Python OPC UA client you will actually meet on a plant-floor skid;
it gives a live tag stream, not a stored dataset. The reference
[sila2 Python implementation](https://gitlab.com/sila2/sila_python) declares itself
maintenance-only and redirects to a fork — SiLA 2 remains the better-designed lab-device
standard, and its reference implementation is not being developed.

**Evaluated and rejected.** The Allotrope Data Format is **not open** — the ontologies are
CC-BY but the format and APIs are gated behind consortium membership, so it fails the test
regardless of technical merit. SBML is excellent and is a *model* format with nowhere to
put measured data. [AnnData](https://github.com/scverse/anndata) is well-engineered and
shaped by single-cell genomics; forcing run × time × channel into observations × variables
is a mis-modelling that will hurt later. Rejected on fit, not quality.

**If you pick one:** MIFE/MIFD as the metadata contract, with xarray/Zarr underneath for
high-frequency data or a Frictionless package for hand-off — and be explicit that MIFE is
a young standard.

---

## Molecular and graph featurization

*Funnel stage: `engin-graph`, and through it `engin-pathway` and `engin-materials`.*

**Engin's position: composes, and insists on the boring baseline.** `engin-graph` embeds
structured candidates and ranks them with a calibrated interval. The featurization and the
message passing are not Engin's contribution.

### RDKit — [rdkit/rdkit](https://github.com/rdkit/rdkit)

BSD-3. The standard cheminformatics toolkit.

- **Pro** — it is the substrate. PyTorch Geometric's molecular featurizers, DeepChem and
  the descriptor packages all call it; depending on it directly is honest rather than new.
- **Pro** — sanitization and valence handling is the part everyone underestimates, and
  structures pulled from public databases are dirty.
- **Con** — polymers are a genuine weak spot for `engin-materials`: repeat-unit and
  molecular-weight-distribution semantics are not first-class.
- **Con** — C++ behind Python bindings, so stack traces stop being informative at the
  boundary. It gives you graphs and descriptors, never a model.

### PyTorch Geometric — [pyg-team/pytorch_geometric](https://github.com/pyg-team/pytorch_geometric)

MIT. The dominant GNN library.

- **Pro** — heterogeneous graph support maps directly onto metabolic routes, where
  reaction nodes and metabolite nodes are genuinely different types. This is the right
  primitive, not a workaround.
- **Pro** — correct batching of variable-sized graphs is subtle, easy to get wrong, and
  exactly the don't-reimplement case.
- **Con** — the optional compiled accelerator packages remain the most common install
  failure in this ecosystem, and the quality gradient across contributed layers is steep.
  Commits continue to land but no release has been cut since late 2025.
- **Con, and Engin should say it out loud** — for ranking a few thousand candidates, a
  gradient-boosted model over descriptors is frequently the stronger baseline. Reach for a
  GNN after the simpler thing has been shown to lose, not before.

Reference: Fey & Lenssen, [arXiv:1903.02428](https://arxiv.org/abs/1903.02428).

### mordredcommunity — [JacksonBurns/mordred-community](https://github.com/JacksonBurns/mordred-community)

BSD-3. A maintained fork of Mordred computing a wide 2D and 3D descriptor block.

- **Pro** — the cheap, strong baseline any GNN claim should be measured against, which a
  self-critical project needs to have on hand.
- **Con** — a very wide descriptor block on a modest dataset is a p ≫ n overfitting trap,
  with many near-duplicate or NaN descriptors, and the library does not filter for you.
- **Con** — effectively one maintainer doing compatibility triage. Treat it as frozen
  functionality on life support. The original `mordred` has been dead since 2019.

**Dead end, and this one surprises people.** [DGL](https://github.com/dmlc/dgl) is
effectively abandoned upstream: no release since September 2024, a single outside-contributor
commit in the last year, and a direct "is this still supported?" issue that received no
maintainer response and was auto-labelled stale. NVIDIA still publishes DGL containers, which
is why it looks alive from a distance — that is vendor packaging of a frozen codebase.
DGL-LifeSci, which much older molecular-GNN tutorial content depends on, inherits this.

**Split verdict.** [DeepChem](https://github.com/deepchem/deepchem) has a very active
source tree and a stable PyPI release over two years old, so the practical install is a
pre-release or a git checkout. Its featurizer collection is the best-curated anywhere and
worth reading even if you don't depend on it.

**If you pick one:** RDKit — it is the only genuinely load-bearing dependency, and the
capability it provides is the one Engin would most certainly get wrong by hand.

---

## What this page is not

It is not a claim that Engin has surveyed the field exhaustively. `D15` holds: where this
page asserts that no maintained option exists — mechanistic bioprocess simulation, dedicated
Python RSM, semantic mapping of vendor exports — that absence is a claim about the world and
carries the same evidential burden as any other. Where the survey behind an entry is thin,
the honest response to a correction is to update the entry, not to defend it.

Corrections are among the most useful contributions this project can receive. If a tool
listed here is better or worse than described, if a licence has changed, or if something
maintained is missing entirely, open an issue — see [Contributing](contributing).
