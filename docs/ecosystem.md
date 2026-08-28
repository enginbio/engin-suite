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

## What is in here

Eleven capability areas. Each card names what Engin does about that capability and the
one implementation to reach for if you only take one — the detail sits under the link.

::::{grid} 1 1 2 3
:gutter: 3

:::{grid-item-card} Bayesian optimization & DoE
:link: eco-bo
:link-type: ref

**Engin:** composes, and benchmarks against

**Reach for:** BayBE
:::

:::{grid-item-card} Distribution-free UQ
:link: eco-uq
:link-type: ref

**Engin:** wraps

**Reach for:** MAPIE
:::

:::{grid-item-card} Techno-economic analysis
:link: eco-tea
:link-type: ref

**Engin:** composes

**Reach for:** BioSTEAM
:::

:::{grid-item-card} Metabolic modelling & strain design
:link: eco-gsmm
:link-type: ref

**Engin:** does not build

**Reach for:** COBRApy
:::

:::{grid-item-card} ML recommendation across DBTL
:link: eco-dbtl
:link-type: ref

**Engin:** does not build

**Reach for:** none, for a commercial user
:::

:::{grid-item-card} Biosynthetic route enumeration
:link: eco-routes
:link-type: ref

**Engin:** explicitly does not build

**Reach for:** DORAnet
:::

:::{grid-item-card} Protein fitness prediction
:link: eco-protein
:link-type: ref

**Engin:** composes

**Reach for:** ESM-2 (650M)
:::

:::{grid-item-card} Mechanistic simulation & twins
:link: eco-sim
:link-type: ref

**Engin:** builds a small one, reluctantly

**Reach for:** BASICO
:::

:::{grid-item-card} Downstream processing & recovery
:link: eco-dsp
:link-type: ref

**Engin:** does not build

**Reach for:** CADET, with a licence warning
:::

:::{grid-item-card} Bioprocess data standards
:link: eco-standards
:link-type: ref

**Engin:** builds loaders, adopts vocabulary

**Reach for:** MIFE/MIFD + xarray
:::

:::{grid-item-card} Molecular & graph featurization
:link: eco-featurization
:link-type: ref

**Engin:** composes

**Reach for:** RDKit
:::

::::

---

(eco-bo)=

## Bayesian optimization and design of experiments

*Funnel stage: process optimization (`engin-core`), campaign planning (`engin-protein`).*

**Engin's position: composes, and benchmarks against.** `engin-core` ships a
Gaussian-process recommender with expected improvement because the recommender's
objective is net $/kg rather than titer (`D13`), which is a different question from
"optimize this response". The optimization machinery itself is not Engin's
contribution, and a textbook response-surface baseline currently beats it on our
own simulator — see [Benchmarks](benchmarks).

:::{dropdown} BayBE — Apache-2.0
:animate: fade-in-slide-down

[emdgroup/baybe](https://github.com/emdgroup/baybe)

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
:::

:::{dropdown} Ax + BoTorch — MIT
:animate: fade-in-slide-down

[facebook/Ax](https://github.com/facebook/Ax), [meta-pytorch/botorch](https://github.com/meta-pytorch/botorch)

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
:::

:::{dropdown} BoFire — BSD-3-Clause
:animate: fade-in-slide-down

[experimental-design/bofire](https://github.com/experimental-design/bofire)

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
- **Con** — torch and BoTorch, but *undeclared* rather than unconditional, which is
  worse for an auditor than BayBE's honest pin. Core dependencies are numpy, pandas,
  pydantic, scipy, typing-extensions and formulaic; torch comes through the
  `optimization` extra. Yet `bofire/strategies/doe/objective.py` does a bare
  `import torch` and `doe/design.py` imports it unconditionally, so the D-optimal
  designer raises `ImportError` on a core install rather than degrading. This con used
  to read "same as BayBE" and end "so it does not relieve the dependency objection that
  sends readers to ProcessOptimizer", which implied there was somewhere to send them.
  There is not: ProcessOptimizer pulls torch too, see below. *(Read from PyPI metadata
  for 0.5.0 and from `main` on 2026-08-25.)*
- **Con** — the maintainer base is concentrated in a small number of industrial
  sponsors, and the feature surface is wide enough that parts of it are thinly
  exercised outside the authors' own use cases.

Reference: Dürholt et al., *Journal of Machine Learning Research* 26(204) (2025),
[jmlr.org/papers/v26/24-1540.html](https://jmlr.org/papers/v26/24-1540.html).
:::

:::{dropdown} ProcessOptimizer — BSD-3-Clause
:animate: fade-in-slide-down

[novonordisk-research/ProcessOptimizer](https://github.com/novonordisk-research/ProcessOptimizer)

BSD-3-Clause. `LICENSE.md` opens with the words "New BSD License" and carries the
standard three-clause text; GitHub's classifier reports `NOASSERTION`, which is a
detection artefact of the `.md` extension and the `a./b./c.` enumeration rather than
a licensing question. A scikit-optimize fork retuned for noisy physical processes.

- **Pro** — ships D-optimal classical designs alongside the optimizer, so screening
  design and sequential optimization live in one dependency.
- **Con, and it is the one this page had backwards** — **torch is a hard runtime
  dependency.** `pyproject.toml` lists it unconditionally in `[project] dependencies`,
  alongside numpy, matplotlib, scipy, bokeh, `scikit-learn>=0.24.2`, six, deap, pyYAML
  and patsy. It is not an extra and there is no torch-free install path. It was added
  on 2025-06-27 in a commit whose message reads "fix: Added dependency of pytorch, used
  in model system"
  ([51b2c7f](https://github.com/novonordisk-research/ProcessOptimizer/commit/51b2c7fa4f68600f01cac96f1959da35bc6babda)),
  which is after the `1.1.1` release and before every release since, and it is still
  there on `develop` today. *(Checked 2026-08-25.)*
- **Con** — inherits scikit-optimize's ageing internals and its scikit-learn version
  fragility, and there is still no fully-Bayesian option.
- **Con** — **none of the repository's version signals agrees with the others**,
  so you cannot tell from it what a `pip install` gets you, and the releases tab is
  the least reliable of them. The latest git tag is
  `v1.1.0`. The latest PyPI release is `1.1.2`, published 2026-02-13. The repository's
  own `CHANGELOG.md` heads that same `1.1.2` section "[unpublished]", and heads a
  further `1.1.3` section the same way. Meanwhile `develop` has not moved since
  2026-02-10. The DRSC constraint-handling algorithm merged in
  [#367](https://github.com/novonordisk-research/ProcessOptimizer/pull/367) — the
  constraint capability this page otherwise sends readers to BoFire for — sits under
  the `1.1.3` heading. Whether its code nevertheless shipped inside `1.1.2`, cut three
  days after the merge and plausibly from the same tree, **could not be verified from
  the repository**, which is the con: judge this one from PyPI, and expect the
  changelog to disagree with what you installed. *(Checked 2026-08-25.)*

Reference: Bertelsen et al., *Journal of Chemical Information and Modeling* 65(4)
(2025), [10.1021/acs.jcim.4c02240](https://doi.org/10.1021/acs.jcim.4c02240).

```{note}
**Corrected 2026-08-25, and the delay is the part worth recording.** This entry led
with "**Pro** — no torch. scipy and numpy only, installs in seconds, plausible inside
a regulated or air-gapped environment where the alternatives are not." Every clause of
that was false, and the whole slot was routed on it.

The finding is not new to this repository. It was reported on
[#191](https://github.com/enginbio/engin-suite/pull/191#issuecomment-5324018365) on
2026-08-18, from PyPI metadata for `1.1.2`, and deliberately left for whoever edited
this file next because another pull request had it open. It then reached
`packages/engin-core/pyproject.toml` and `packages/engin-core/benchmarks/baybe_baseline.py`,
both of which have said since that ProcessOptimizer "pulls torch too — see #191". This
page, which is the only one of the three a reader sees, kept the opposite claim through
eight subsequent edits to it.

`D13` states the rule this broke: fixing the canonical document is not fixing the
claim, so grep the tree for the phrase. `scripts/evidence/check_corrections.py` runs
that rule in CI — but it extracts retracted spans from `DECISIONS.md` only, and this
retraction lived in a pull-request comment. Nothing was watching the difference.
```
:::

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

**Licensed out of reach, and easy to mistake for BayBE.**
[obsidian](https://github.com/MSDLLCpapers/obsidian) is a BoTorch-backed process
optimizer and experiment designer aimed squarely at pharmaceutical process development
— the closest thing in this slot to Engin's own use case. It is **GPL-3.0**, copyright
Merck & Co., Inc. (Rahway), which is a *different company* from the Merck KGaA that
publishes BayBE; readers conflate the two and the licences could not be further apart.
Two things to know before reading it for ideas: the published PyPI package
(`obsidian-apo`) and the latest GitHub release are both `0.8.6` from 2025-03-20, while
`main` carries a squashed "Release 1.0.0" commit from 2026-07-29 that among other things
deletes the Dash web app — so the installable package trails the repository by a major
version with no tag to pin. And the repository was silent between those two commits.
Cite the method; do not take the dependency. *(Checked 2026-08-18.)*

**Dead ends.** `pyDOE3` was archived in May 2026 and points back at `pydoe`.
[scikit-optimize](https://github.com/holgern/scikit-optimize) has been dormant since
mid-2024. [dexpy](https://github.com/statease/dexpy) last moved in 2018.
[Summit](https://github.com/sustainable-processes/summit) is useful now only as a
source of benchmark problems. [Atlas](https://github.com/aspuru-guzik-group/atlas)
has a good paper and a Python ceiling below 3.11.
[EDBO+](https://github.com/doyle-lab-ucla/edboplus) is research code — cite the
method, don't depend on the package.

:::{dropdown} Benchmark harnesses: there is not one to run inside — dead end
:animate: fade-in-slide-down

**Dead end, recorded here because the finding was living in a pull-request
comment.** [#201](https://github.com/enginbio/engin-suite/pull/201) settled this
for [#20](https://github.com/enginbio/engin-suite/issues/20) — `D9` says compose,
so the prior question was whether an existing harness should own the
benchmark comparison rather than this repository hand-rolling one. The answer was
no, on two independent grounds: **both neutral harnesses are dormant**, and they
**benchmark optimization planners against chemistry response surfaces**, which is
one of the five comparisons #20 names and not the other four.

This page is where a reader looks before re-surveying, so the snapshot lives here
too. Checked 2026-08-17:

| | licence | last pushed | last release |
|---|---|---|---|
| [Summit](https://github.com/sustainable-processes/summit) | MIT | Sep 2024 | 0.8.8, Dec 2022 |
| [Olympus](https://github.com/the-matter-lab/olympus) | MIT | Nov 2024 | none, ever |

Two details worth carrying, both of which cost time to find:

**Olympus moved.** The widely-linked `aspuru-guzik-group/olympus` path is a
**301 redirect** to `the-matter-lab/olympus`, not a dead link — so the GitHub API
follows it silently and reports the new name, while a reader clicking an old
citation lands somewhere they did not expect. Link the current path.

**BayBE is not the third option here, despite shipping a `benchmarks/` module.**
That module's own README describes it as testing "the performance of BayBE", with
settings that parameterise BayBE scenario executions over `baybe.simulation`.
Engin cannot run inside it without first becoming a BayBE campaign, which is a far
larger commitment than a baseline comparison. BayBE stays what #20 already calls
it — a *baseline to beat*, not a frame to sit in — and it is Apache-2.0, so that
comparison carries no licence question when someone builds it.
:::

**If you pick one:** BayBE. **If torch is disqualifying, this slot has no answer** —
but not for the same reason in every case, and the difference matters if you are
auditing an install. BayBE, Ax and ProcessOptimizer declare torch or BoTorch
unconditionally in `[project] dependencies`. **BoFire does not**: `pip install bofire`
pulls only numpy, pandas, pydantic, scipy, typing-extensions and formulaic, and torch
arrives through the `optimization` extra. That install is torch-free and it is also
unusable for this slot's purpose — `bofire/strategies/doe/objective.py` does a bare
`import torch` and takes `hessian` and `jacobian` from `torch.autograd.functional`, and
`doe/design.py` imports that module unconditionally, so the D-optimal designer raises
`ImportError` on a core install. The dependency is real and undeclared rather than
absent. Either way there is no escape hatch to route you to, and saying so is more use
than a redirect that does not help. Pick BoFire instead of BayBE when the binding difficulty is
*constraints on the design itself* — a media mixture that must sum, a component that
can only appear with another — because that is the case it is built for and the one
where BayBE's constraint support runs out first.

---

(eco-uq)=

## Distribution-free uncertainty quantification

*Funnel stage: every calibrated interval Engin publishes.*

**Engin's position: wraps.** Split-conformal calibration with an sd-normalized
multiplier is implemented in `engin-core`; MAPIE is kept as an independent
cross-check precisely because it is a *different* method, which is the point of a
cross-check. See [Conformal calibration](methods/conformal-calibration).

:::{dropdown} MAPIE — BSD-3
:animate: fade-in-slide-down

[scikit-learn-contrib/MAPIE](https://github.com/scikit-learn-contrib/MAPIE)

BSD-3. The scikit-learn-contrib conformal library.

- **Pro** — breadth nothing else matches: split, CV+, jackknife+, CQR,
  classification sets, EnbPI for time series, and conformal risk control, all behind
  an sklearn-compatible API.
- **Pro** — `StdConformityScore` conformalizes an estimator that already reports a
  predictive standard deviation, so a GP forecast can be conformalized without
  discarding the model's own variance. **Pin `mapie>=1.5.0` if you want it.** It
  shipped in 1.5.0 (2026-08-05) and does not exist at 1.4.1 or below — verified by
  reading `mapie/conformity_scores/bounds/__init__.py` at both tags, where the export
  list gains `StdConformityScore` only at 1.5.0. Paired with
  `CrossConformalRegressor(method="plus")` it is the construction MAPIE's own
  docstring calls J+GP, citing Jaber et al.; the preprint is
  [arXiv:2401.07733](https://arxiv.org/abs/2401.07733), whose abstract describes
  weighting non-conformity scores by the GP posterior standard deviation. The
  published version named in that docstring is behind a paywall this page could not
  read, so it is reported as MAPIE's citation rather than as one checked here.
- **Pro** — `mapie.exchangeability_testing` tests the assumption the rest of the
  library rests on, instead of assuming it. It arrived in **1.4.0 (2026-04-30)** and
  exports `FixedDatasetExchangeabilityTest`, `PValuePermutationTest`, `PermutationTest`,
  `SequentialMonteCarloTest`, `OnlineExchangeabilityTest`, `OnlineMartingaleTest` and
  `RiskMonitoring`. The fixed-dataset default statistic is
  `MaxSplitMeanDifferenceTestStatistic` — a CUSUM on the conformity scores maximized
  over every split point, against a permutation null — so it needs no guess about when
  a shift began, and it reads the data in the order you hand it: `_prepare_estimator`
  refuses the cross-conformal estimators outright, "because they mix the data".
  This is the slot's most useful recent addition for anyone holding time-ordered
  process history, which is most people in this field.
  *(Read from `mapie/exchangeability_testing/` and `HISTORY.md` on `master`, and from
  the PyPI release dates, on 2026-08-28.)*
- **Con** — it tests exchangeability without offering the repair. MAPIE ships **no**
  non-exchangeable weighted conformal — NexCP, Barber et al. 2023 — so a test that
  fires leaves you shopping. Searched 2026-08-28: grepping the 1.5.0 source tree for
  `nexcp`, `non_exchangeable`, `nonexchangeable`, `recency` and `weighted_quantile`
  returns nothing outside prose in `doc/`, and a GitHub code search for `NexCP` inside
  the repository returns no hits. `TimeSeriesRegressor` covers ACI and EnbPI, which
  adapt online and are a different family from reweighting a fixed calibration set.
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
:::

:::{dropdown} crepes — BSD-3
:animate: fade-in-slide-down

[henrikbostrom/crepes](https://github.com/henrikbostrom/crepes)

BSD-3. Conformal predictive *systems* — a calibrated predictive distribution per
test object, not an interval at one confidence level.

- **Pro** — this is the right primitive for Engin's actual use case. Propagating
  titer uncertainty into a cost-per-kilogram model wants a distribution to integrate
  over, and MAPIE does not give you one.
- **Pro** — Mondrian and difficulty-normalized variants give conditional coverage
  per stratum, which is what you need when a calibration set mixes shake-flask and
  bioreactor runs; and conformal test martingales give an actual alarm for
  exchangeability drift. **Pin `crepes>=0.9.0` for that second one** — the
  `crepes.martingales` module (`SimpleJumper`, `SleeperStayer`, `SleeperDrifter`,
  `CompositeMartingale`, over `semi_online_p_values`) arrived in 0.9.0 on 2025-10-08,
  and this entry claimed the capability with no version attached before that was
  checked. Latest is 0.9.1, 2026-06-12.
- **Con** — single-maintainer, pre-1.0, and willing to change default behaviour
  between point releases. Narrower than MAPIE: no time series, no risk control.

Reference: Boström, *Proceedings of COPA* (PMLR 230:236-249, 2024).

*(Licence, versions and module contents read from the repository and PyPI on
2026-08-28.)*
:::

:::{dropdown} TorchCP — LGPL-3.0 / GPL-3.0 — copyleft
:animate: fade-in-slide-down

[ml-stat-Sustech/TorchCP](https://github.com/ml-stat-Sustech/TorchCP)

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
:::

**Conformal when the calibration set is time-ordered.** Split conformal's guarantee is
marginal *and* exchangeable, and a production record is neither shuffled nor stationary.
Two families answer that: adapt online as errors arrive (ACI, AgACI, EnbPI), which MAPIE
ships; or reweight the calibration quantile toward recent residuals (NexCP), which it
does not. Only one maintained, permissively licensed, published package was found with
the second.

:::{dropdown} tsbootstrap — MIT
:animate: fade-in-slide-down

[astrogilda/tsbootstrap](https://github.com/astrogilda/tsbootstrap)

MIT (root `LICENSE`, "Copyright (c) 2023 Sankalp Gilda"). A time-series bootstrap
library that carries a small conformal layer under `src/tsbootstrap/uq/`.

- **Pro** — `nexcp_quantile` in `uq/adaptive.py` is the only NexCP implementation this
  search found in a maintained, permissively licensed package on PyPI. Alongside it
  `uq/adaptive.py` has `aci_halfwidths` and `agaci_bounds`, `uq/conformal.py` has
  `EnbPIEnsemble` and `enbpi_intervals`, and `uq/calibrators.py` exposes them as `NexCP`,
  `ACI`, `AgACI`, `SlidingWindow` and `Static`. Verified by importing 0.7.1, not by
  reading the README.
- **Pro** — released and moving: PyPI 0.7.1 on 2026-07-15, last commit on the default
  branch 2026-08-27.
- **Con, and it is the one to read before adopting** — `nexcp_quantile` is the
  fixed-weight estimator, not the paper's method. It weights score `i` by
  `decay ** (n - 1 - i)` and returns the smallest score whose weighted CDF reaches
  `1 - alpha`. Its own docstring states that at `decay = 1` this is "the ordinary
  empirical quantile" — so it is the *empirical* quantile it degenerates to, not the
  finite-sample conformal one at the `ceil((n + 1) * (1 - alpha))`-th order statistic,
  and there is no point mass at infinity. At a calibration set the size of Engin's it
  is the anti-conservative side of the difference. Barber et al.'s coverage-gap bound,
  which is the reason to want NexCP at all, is not implemented.
- **Con** — conformal is a side room here, not the product. The main surface is block
  bootstraps, and the conformal layer has no publication or benchmark of its own to
  point at.

*(Licence, version, commit date and module contents read from the repository, from
PyPI, and by importing the installed package, on 2026-08-28.)*
:::

**Also worth knowing.** [puncc](https://github.com/deel-ai/puncc) is MIT with a
genuinely optional torch dependency and a certification-oriented framing. This page
called its feature velocity low; after a long quiet stretch it has shipped several
releases through 2026, so treat that as withdrawn rather than merely softened. One
thing to know before depending on it: the MIT licence is declared in packaging
metadata and per-file headers, and there is no top-level LICENSE file — which this
page treats as disqualifying elsewhere, so it is named here too.
[venn-abers](https://github.com/ip200/venn-abers) (MIT) solves a
different problem — validity of predicted *probabilities* for go/no-go decisions —
and is a complement, not a substitute. **If you depend on it, pin `>=1.5.4`.** That
release (2026-08-12) is a correctness fix, not a feature drop: its notes state that
`VennAbersCV.fit` had been reusing one mutated estimator across folds, leaving
`self.estimators_` holding "K+1 references to a single mutated object", that
`predict_interval` scored the test set with the final fold's model and applied other
folds' calibrators to it, that `epsilon` was ignored entirely on the
cross-validation path, and that the regression upper bound returned a slope instead
of the extreme calibration label when a test prediction exceeded all calibration
predictions. A pin below 1.5.4 is silently miscalibrated in the cross path — the
failure mode this page exists to warn about, and one no version-range check catches.
Reference: [release v1_5_4](https://github.com/ip200/venn-abers/releases/tag/v1_5_4).
*(Checked 2026-08-19.)*

**Dead ends.** [nonconformist](https://github.com/donlnz/nonconformist), the historical
reference implementation, has been dormant since 2021; crepes is the natural migration
target. [Amazon Fortuna](https://github.com/awslabs/fortuna) was archived by AWS in
April 2025 — anyone arriving from an old AWS blog post should be redirected.

**The time-ordered corner is mostly dead ends**, and each one looks like the answer from
a search result. [salesforce/online_conformal](https://github.com/salesforce/online_conformal)
is Apache-2.0 and **archived**, frozen at a last push of 2025-05-01 with no PyPI upload
since March 2023. [aangelopoulos/conformal-time-series](https://github.com/aangelopoulos/conformal-time-series),
the reference code for conformal PID control, is MIT and has not been touched since
2023-11-30. And three of the implementations the literature sends you to —
[DtACI](https://github.com/isgibbs/DtACI), [SPCI-code](https://github.com/hamrel-cxu/SPCI-code)
and [AdaptiveConformal](https://github.com/isgibbs/AdaptiveConformal) — carry **no LICENSE
file of any kind** at their repository root. This page treats a missing licence as
disqualifying when it finds one in a package it would otherwise recommend, so it treats
these the same way: read them, don't depend on them. *(Root listings and archive status
checked 2026-08-28.)*

**Bayesian is the other answer, and it is not on this page's shelf.** A reader asking
*"why distribution-free rather than Bayesian?"* should know that the maintained
bioprocess-specific Bayesian stack is `calibr8` / `murefi` / `estim8`, under
[mechanistic simulation](eco-sim). It is AGPL-3.0, which is why it is filed there as a
thing to read rather than a thing to depend on.

**If you pick one:** MAPIE, and add crepes the moment you need a predictive
distribution rather than an interval. Reach for anything in the time-ordered paragraph
only *after* an exchangeability test has actually fired — the adaptive and reweighted
methods buy robustness by giving up the clean finite-sample statement, and paying that
on a suspicion rather than a measurement is a bad trade.

---

(eco-tea)=

## Techno-economic analysis

*Funnel stage: cost-per-kilogram (`engin-core`, the `[tea]` extra).*

**Engin's position: composes.** BioSTEAM backs techno-economics as an optional extra.
Engin's contribution is the coupling — propagating a calibrated titer forecast through
recovery into a probabilistic $/kg — not the flowsheet simulation. See
[Cost](guides/cost).

:::{dropdown} BioSTEAM — NCSA
:animate: fade-in-slide-down

[BioSTEAMDevelopmentGroup/biosteam](https://github.com/BioSTEAMDevelopmentGroup/biosteam)

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
:::

:::{dropdown} IDAES-PSE — BSD
:animate: fade-in-slide-down

[IDAES/idaes-pse](https://github.com/IDAES/idaes-pse)

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
:::

:::{dropdown} QSDsan — NCSA
:animate: fade-in-slide-down

[QSD-Group/QSDsan](https://github.com/QSD-Group/QSDsan)

NCSA. A BioSTEAM-derived platform coupling simulation, TEA and life-cycle assessment
in one system object.

- **Pro** — integrated LCA reading the same streams as the TEA, with BioSTEAM's
  Monte Carlo machinery inherited, so impact results carry uncertainty. Most LCA
  tooling does not do that.
- **Con** — the unit library, cost correlations and defaults are sanitation and
  resource-recovery shaped, not industrial aerobic fermentation shaped.
- **Con** — inherits BioSTEAM's pins and bus-factor risk, and adds a second layer of
  the same.
:::

:::{dropdown} OpenPyTEA — MIT
:animate: fade-in-slide-down

[pbtamarona/OpenPyTEA](https://github.com/pbtamarona/OpenPyTEA)

MIT. Equipment cost correlations, plant CAPEX/OPEX, cash flow and Monte Carlo
uncertainty — the *costing* half of a TEA, with no process simulation underneath it.

- **Pro** — the closest open analogue to what `engin_core.tea` hand-rolls: a
  correlation database with CEPCI inflation adjustment, a capital and operating
  build-up, levelized cost of production, and Monte Carlo propagation over the lot.
  Under `D9` it is the entry in this slot that most deserves reading before Engin's
  own cost model is extended again.
- **Pro** — the lightest install in this section by a distance: matplotlib, numpy,
  pandas, scienceplots, scipy, seaborn, tqdm, jinja2. No solver fetch, no torch, no
  .NET bridge. *(Read from `pyproject.toml` on `main`, 2026-08-26.)*
- **Pro** — peer-reviewed, and the paper is about the software rather than an
  application of it, so the assumptions are the thing being reviewed.
- **Con** — **it is not a simulator and does not claim to be.** Its own README places
  it downstream of one: the user supplies equipment sizing and simulation results.
  No unit-operation models, no mass or energy balances, no thermodynamics. It cannot
  produce a titer, a stream, or a recovery yield, so it does not touch the coupling
  that is Engin's actual contribution.
- **Con** — the cost database is general chemical and energy plant, not bioprocess.
  Of 417 correlations across 34 categories, exactly two are fermentation-specific — a
  fermenter and an inoculum tank, both Turton Table A.1 carbon-steel *purchased*-cost
  curves, and the fermenter curve is stated only over a small vessel range.
  Centrifuges are covered; chromatography and homogenization are not, so a
  bioseparation train has nowhere to live. *(Counted from
  `src/openpytea/data/cost_correlations.csv` at `main`, 2026-08-26.)*
- **Con** — one dominant author with two minor contributors, first commit May 2025,
  and a FastAPI + React GUI already in the tree — surface growing faster than the
  maintainer count. Judge it as a young single-author project, because it is one.

Reference: Tamarona, Vlugt & Ramdin, *SoftwareX* 35:102816 (2026),
[10.1016/j.softx.2026.102816](https://doi.org/10.1016/j.softx.2026.102816).
:::

**Not open, but name them honestly.** SuperPro Designer remains the industry default
for batch bioprocess TEA and scheduling, and has no open-source equal on
equipment-occupancy or campaign scheduling. Aspen Plus is the continuous-process
default. Both are closed and per-seat licensed, which is the gap BioSTEAM occupies.
[DWSIM](https://github.com/DanWBR/dwsim) was the credible free Aspen-alike but is a
GPL-3.0 .NET desktop application reached from Python over a bridge — hostile to
scriptable, CI-testable pipelines — and **its repository is now archived and
read-only**, with the last commit on the `windows` branch dated 2026-07-17. Do not
start anything new on it. *(`archived: true` read from the repository API on
2026-08-20; the API exposes no archive date, and the repository's `updated_at` of
2026-08-15 is the tightest upper bound available.)*

**If you pick one:** BioSTEAM, because it is the only permissively licensed,
pip-installable option that treats TEA uncertainty as a first-class construct and
ships fermentation models to start from. OpenPyTEA now satisfies the first three of
those and not the fourth, which is the distinction to hold on to: it is the better
read if what you want is a transparent costing layer, and it is not a substitute if
you need the flowsheet.

---

(eco-gsmm)=

## Genome-scale metabolic modelling and strain design

*Funnel stage: upstream of route ranking (`engin-pathway`) and host selection (`engin-host`).*

**Engin's position: does not build, and is downstream of.** FBA predicts feasibility
well and does not predict titer. That gap is the whole reason `engin-pathway` exists —
it ranks routes by manufacturability, and route feasibility is somebody else's
correctly-solved problem.

**"Strain design" here means the mechanistic sense only** — compute a set of knockouts
or interventions from a genome-scale model. Every entry below is stoichiometric and
none of them reads a previous cycle's measurements. The data-driven sense of the same
phrase — learn from the titers you measured last round, recommend what to build next —
is a different capability with a different and much worse-supplied tool list, and it
has its own slot, *Machine-learning recommendation across DBTL cycles*, below. A reader
who takes this slot as covering both would conclude the problem is solved. It is not.

:::{dropdown} COBRApy — GPLv2+ / LGPLv2+
:animate: fade-in-slide-down

[opencobra/cobrapy](https://github.com/opencobra/cobrapy)

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
:::

:::{dropdown} StrainDesign — Apache-2.0
:animate: fade-in-slide-down

[klamt-lab/straindesign](https://github.com/klamt-lab/straindesign)

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
:::

:::{dropdown} Model reconstruction: CarveMe and gapseq — Apache-2.0 / GPL-3.0
:animate: fade-in-slide-down

[CarveMe](https://github.com/cdanielmachado/carveme) (Apache-2.0) carves an
organism-specific model out of a curated universal model from a genome annotation, in
minutes. Fast, BiGG-namespaced, community-model capable — but it needs Diamond and an
MILP solver installed out of band, the free-solver path is slow, and it is
prokaryote-oriented, so *S. cerevisiae* and *P. pastoris* hosts are out of scope.
**Its last commit and its last release are the same day, 2025-09-12** — not archived,
no deprecation notice, no successor named, but nothing has moved in close to a year.
Not yet a dead end; treat it as one to re-check rather than one to build a pipeline
on. *(Checked 2026-08-17.)*

[gapseq](https://github.com/jotech/gapseq) (GPL-3.0) infers pathways from sequence
homology and gap-fills, producing per-reaction evidence a reviewer can interrogate —
which carved output does not give you. It is the more actively curated of the two, with
dated reference-database provenance — and that gap has widened: gapseq moved to a `2.x`
line during 2026 (`v2.1.0`, 2026-05-30) with commits through August while CarveMe stood
still. *(Checked 2026-08-17.)* But it is R plus shell, so it is a subprocess
dependency in a Python stack, and it is bacteria and archaea only.
:::

**Reaction thermodynamics.** [eQuilibrator](https://gitlab.com/equilibrator/equilibrator-api)
(MIT, on GitLab) is the right answer for ΔG′° estimation, and it is alive but slow:
`0.7.0` (2026-04-16) is the first release since `0.6.0` (2024-01-28). This page called
it "actively developed" until 2026-08-25, which is a fair description of a project that
still ships and a misleading one for one release in the last two years — the distinction
this page exists to draw. `engin-pathway`'s `[thermo]` extra depends on it, so that
cadence is Engin's problem too. *(Checked 2026-08-25.)* The
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

(eco-dbtl)=

## Machine-learning recommendation across DBTL cycles

*Funnel stage: between route ranking (`engin-pathway`) and process optimization
(`engin-core`) — the Design step that picks which strains to build next.*

**Engin's position: does not build, and the reason is not that someone else has
this covered.** The slot above ranks *interventions computed from a model*; this one
is *learning from the last cycle's measurements* — given titers from the strains you
built, which combination of gene targets, promoters or knockdowns should the next
cycle build? `engin-core`'s recommender does exactly this shape of job over
continuous process conditions, and nothing in the suite does it over genetic
designs. Recorded here because a reader who assumes `D9` applies — that Engin skips
this because a good open implementation exists — would be assuming something false.
Whether Engin should serve it is [#211](https://github.com/enginbio/engin-suite/issues/211);
`BIOSECURITY.md` §2 currently says it does not.

:::{dropdown} ART — not open source
:animate: fade-in-slide-down

[JBEI/ART](https://github.com/JBEI/ART)

**Not open source, and this is the entry the page's licence warning was written for.**
Non-commercial academic use only, *Patent Pending*, and access is by emailing Berkeley
Lab for admission to a private repository.

- **Pro** — the only tool in this slot with a published multi-cycle wet-lab record:
  six consecutive DBTL cycles raising isoprenol titer in *P. putida* over an sgRNA
  combination space. Engin already registers that campaign's final cycle as a dataset.
- **Pro** — it recommends a *set* of strains with probabilistic predictions rather than
  a single point pick, which is the batch-plus-interval shape the rest of this suite
  uses, arrived at independently.
- **Con, and it is the binding one** — **the public repository contains no source
  code.** It holds a README, two licence PDFs, and `data/` and `notebooks/`
  directories. The README says so in its third sentence. You cannot read it, vendor
  it, or check what it does.
- **Con** — the commercial licence is a paid ten-year term from Berkeley Lab's
  licensing office, priced by headcount. For an Apache-2.0 project with commercial
  users this is disqualifying, not inconvenient.
- **Con** — no PyPI package, no releases, no version numbers. There is nothing to pin,
  so a result produced with ART cannot be reproduced against a stated version.

Reference: Radivojević et al., *Nature Communications* 11:4879 (2020),
[10.1038/s41467-020-18008-4](https://doi.org/10.1038/s41467-020-18008-4).
:::

:::{dropdown} METIS — MIT
:animate: fade-in-slide-down

[amirpandi/METIS](https://github.com/amirpandi/METIS)

MIT. An active-learning workflow for optimizing genetic and metabolic networks, run
from Colab notebooks.

- **Pro** — the only permissively licensed recommender found in this slot, and it
  publishes the multi-round combination-and-yield data behind its own results, so you
  can benchmark against it rather than take its word.
- **Pro** — zero-install Colab is the right friction level for the wet-lab user who is
  the actual customer for this capability.
- **Con** — dormant. Last commit 2022-11-07. *(Checked 2026-08-18.)*
- **Con** — not a package: notebooks plus a loose `utils.py`, no PyPI, no releases, no
  tests, no API surface. Depending on it means adopting and repackaging it, which is
  `D10` territory only if you first establish the authors have stopped.

Reference: Pandi et al., *Nature Communications* (2022),
[10.1038/s41467-022-31245-z](https://doi.org/10.1038/s41467-022-31245-z).
:::

:::{dropdown} FluxRETAP — BSD-3-Clause
:animate: fade-in-slide-down

[JBEI/FluxRETAP](https://github.com/JBEI/FluxRETAP)

BSD-3-Clause (LBNL variant). Prioritises gene targets by correlating flux with product
formation across a COBRApy model.

- **Pro** — permissive, small and readable, and it answers the question a metabolic
  engineer actually asks: which reactions to push or delete.
- **Con** — it belongs to the slot above, not this one. It computes targets from a
  model; it does not read your previous cycle's measurements. Listed here because it
  is the near-miss a reader will find first and mistake for the thing.
- **Con** — dormant since January 2025, notebooks-plus-`core/` with no packaging, and
  the repository states the work is not yet published.
:::

**Adjacent infrastructure, both permissive, neither a recommender.**
[JBEI/EDD](https://github.com/JBEI/edd) (BSD-3-Clause, LBNL) is the Test-side data
repository ART reads from — genuinely deployable, with Docker and documented ops, but
it has cut no releases at all, so upgrades mean tracking `trunk` by hand, and it has
been quiet since January 2025. [JBEI/DIVA](https://github.com/JBEI/DIVA)
(BSD-3-Clause) is the Build-side construct designer, with commits through 2026 — but
its most recent is 2026-05-20 and it is a README edit, it is a Java web platform with
no releases and effectively no community, and it designs constructs rather than
choosing which to build. *(Both checked 2026-08-18; DIVA's activity re-checked
2026-08-20, when this entry called it "the most actively developed repository named on
this page" — seven repositories on this page had been pushed to within four days of
that check.)*

**Dead ends and traps.** The academic combinatorial-BO repositories that look like they
would fill this gap have all stopped: [COMBO](https://github.com/QUVA-Lab/COMBO) (2020),
[Casmopolitan](https://github.com/xingchenwan/Casmopolitan) (2023),
[Bounce](https://github.com/LeoIV/bounce) (2024). [BODi](https://github.com/aryandeshwal/BODi)
is worse than dead — a single AISTATS code-drop commit with **no LICENSE file at all**,
so it is all-rights-reserved and cannot be vendored whatever its state.

**The absence claim, and what backs it (`D15`, `D23`).** Searched 2026-08-18: GitHub and
PyPI for DBTL/strain-design recommenders, the JBEI and Agile BioFoundry organizations,
the AbeelLab simulated-DBTL line, and the 2024–2026 combinatorial-perturbation and
active-learning literature. **No maintained, permissively licensed, installable package
was found that recommends genetic designs from prior cycle results.** Rejected
near-misses and why: METIS is permissive and on-target but dormant and unpackaged;
FluxRETAP is permissive and packaged-adjacent but model-driven; ART is maintained and
on-target and not open; [AbeelLab/simulated-dbtl](https://github.com/AbeelLab/simulated-dbtl)
(MIT) is a benchmark harness for comparing recommenders, not one;
[BayBE](https://github.com/emdgroup/baybe) has the constraint vocabulary for the search
space but no notion of a genetic design. If you know of a counterexample, that
correction is worth more to this page than any entry on it.

**If you pick one:** for a commercial user, none of them — read the ART paper, take the
METIS data as a benchmark, and write it yourself. For an academic lab, ART, because the
non-commercial licence is free to you and nothing else here has been through six real
cycles.

---

(eco-routes)=

## Biosynthetic route enumeration

*Funnel stage: immediately upstream of `engin-pathway`.*

**Engin's position: explicitly does not build.** Route-finding tools exist and work.
The whitespace is *ranking* the routes they produce by manufacturability, not finding
them. `engin-pathway` consumes routes; it does not enumerate them.

:::{dropdown} DORAnet — Apache-2.0
:animate: fade-in-slide-down

[wsprague-nu/doranet](https://github.com/wsprague-nu/doranet)

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
- **Con** — **and it has stopped moving.** The last commit on `main` is 2026-02-04,
  and the newest published artifact is `0.5.7a1` from that same day; the repository has
  never cut a GitHub release at all. The two commits before it are 2026-01-29 and
  2025-06-13, so long quiet stretches are this project's normal rather than a new
  development — but a pre-alpha with an unstable API and no upstream movement in six
  months is a different recommendation from a pre-alpha under active development, and
  this entry read as the second. *(Commit list and an empty release list read from the
  GitHub API on 2026-08-26; version and date from PyPI the same day. Not a dead end:
  the January burst was substantive, and nothing here says it will not resume.)*

Reference: Zhang et al., *Digital Discovery* (2025),
[10.1039/d5dd00229j](https://doi.org/10.1039/d5dd00229j).
:::

:::{dropdown} RetroPath2.0 — MIT
:animate: fade-in-slide-down

[brsynth/retropath2-wrapper](https://github.com/brsynth/retropath2-wrapper)

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
:::

:::{dropdown} RetroBioCat 2 — CC BY-NC 4.0 — non-commercial
:animate: fade-in-slide-down

[willfinnigan/RetroBioCat-2](https://github.com/willfinnigan/RetroBioCat-2)

**CC BY-NC 4.0 — non-commercial, not an OSI licence.** Note the regression: version 1
was MIT. Listed because it is the most actively developed biocatalysis-specific route
finder, shipping template-based and template-free expanders plus MCTS search with
expert-curated enzyme rules. **Engin's commercial users cannot use it.** List it, don't
depend on it.
:::

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

**If you pick one:** DORAnet — still, because every alternative in this slot fails on
licence, on Python version, or on KNIME — but with both caveats stated loudly now. Pin
`0.5.7a1` exactly, budget for fixing your own bugs rather than waiting upstream, and
re-check the repository before you build anything load-bearing on it. RetroPath2.0 if
you need the publication-defensible answer and can eat KNIME.

---

(eco-protein)=

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

:::{dropdown} ESM-2 and the ESM family — MIT, with a caveat
:animate: fade-in-slide-down

[Biohub/esm](https://github.com/Biohub/esm)

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
:::

:::{dropdown} EVcouplings — MIT
:animate: fade-in-slide-down

[debbiemarkslab/EVcouplings](https://github.com/debbiemarkslab/EVcouplings)

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
:::

:::{dropdown} ProteinGym — MIT
:animate: fade-in-slide-down

[OATML-Markslab/ProteinGym](https://github.com/OATML-Markslab/ProteinGym)

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
:::

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

(eco-sim)=

## Mechanistic simulation and digital twins

*Funnel stage: `engin-core`'s fed-batch simulator.*

**Engin's position: builds a deliberately small one, and would rather not.** The
simulator exists to generate benchmark data with known ground truth, not to be a
credible process model — see [Limitations](limitations).

```{note}
**There is no dominant, actively maintained, open-source fermentation digital twin.**
The live candidates are generic ODE engines or flowsheet simulators that happen to
contain bioreactor units. Recent digital-twin work in this field publishes papers, not
maintained packages. That absence is a real finding and is stated here rather than
papered over (`D15`).

**Narrowed 2026-08-21, because "the purpose-built candidates are dead" had stopped being
true.** It is now false as written: `estim8` below is purpose-built for bioprocess models,
carries a JOSS paper published this month, and is releasing. The absence claim survives
only in its narrow form — nobody ships a maintained *fermentation model*. `estim8` ships
an estimator and expects you to bring the model. That is a different sentence, and `D15`
and `D23` both say an absence claim has to be the narrow one.

**The nearest miss, named because `D15` requires it.** [BiRD](https://github.com/NREL/BioReactorDesign)
(BSD-3-Clause) is purpose-built for bioreactors, actively developed — commits through
2026-07-31 — and its 2026 OpenFOAM-13 merge added kLa function objects and kLa
correlations, so it models the gas-liquid transfer the packages above have no
abstraction for. It is rejected for this slot on scope, not on health: it is an
OpenFOAM CFD toolbox solving hydrodynamics and interphase mass transfer, not a
fermentation kinetics model, and standing up a case is a meshing-and-solver project
rather than a `pip install`. Reach for it when the question is *transport inside a
specific vessel geometry*; it will not give you a titer trajectory. Note the repository
moved: `NREL/BioReactorDesign` now redirects to `NatLabRockies/BioReactorDesign`.
*(Checked 2026-08-17.)*
```

:::{dropdown} BASICO / COPASI — Artistic-2.0
:animate: fade-in-slide-down

[copasi/basico](https://github.com/copasi/basico)

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
:::

:::{dropdown} Tellurium / libRoadRunner — Apache-2.0
:animate: fade-in-slide-down

[sys-bio/tellurium](https://github.com/sys-bio/tellurium)

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
:::

:::{dropdown} estim8 / calibr8 / murefi — AGPL-3.0
:animate: fade-in-slide-down

[JuBiotech/estim8](https://github.com/JuBiotech/estim8),
[JuBiotech/calibr8](https://github.com/JuBiotech/calibr8),
[JuBiotech/murefi](https://github.com/JuBiotech/murefi)

AGPL-3.0, all three. A purpose-built bioprocess estimation stack from Forschungszentrum
Jülich: `estim8` estimates parameters of dynamic (bio)process models through the FMI
standard and ships uncertainty quantification; `calibr8` builds the likelihood-based
calibration model for the measurement layer; `murefi` fits multiple replicates under one
Bayesian model. Same group as `bletl` and `detl`, which this page already names under
[bioprocess data standards](eco-standards).

- **Pro** — this is the maintained answer to *"why conformal rather than Bayesian?"* in
  this exact domain, and Engin owes a reader that answer. It is not a generic UQ library
  pointed at biology: `estim8`'s own repository topics are `bioprocess-modeling`,
  `fmi-standard`, `parameter-estimation`.
- **Pro** — peer-reviewed and citable rather than a preprint drop. `estim8` has a JOSS
  paper; `calibr8` has a PLOS Computational Biology one.
- **Pro** — tagged releases, all recent: `estim8` v0.1.6 (2026-07-13), `calibr8` v7.3.0
  (2026-05-18), `murefi` v5.4.1 (2026-04-15).
- **Con, and it decides the matter for reuse here** — AGPL-3.0 on all three, read from
  each repository's `LICENSE` file on the date below. Engin is Apache-2.0 and its users
  are commercial; §13 reaches an adopter who modifies one of these and exposes it only as
  a hosted service. Read the code and cite the method; do not vendor it.
- **Con** — `estim8` brings no model. It consumes an FMU compiled elsewhere, so the real
  entry cost is an OpenModelica-or-equivalent toolchain rather than `pip install`. If what
  you wanted was a fermentation model, this is not where it is.
- **Con** — `estim8` is pre-1.0 and `murefi` is thinly used; `calibr8`'s recent commit
  stream is dependency bumps merged by a single maintainer rather than feature work.
  Judge the group as the unit of health, not any one repository.

Reference: Latour, Strohmeier, Osthege, Wiechert & Noack, *JOSS* 11(124):10147 (2026),
[10.21105/joss.10147](https://doi.org/10.21105/joss.10147); Helleckes, Osthege, Wiechert,
von Lieres & Oldiges, *PLOS Computational Biology* 18(3) (2022),
[10.1371/journal.pcbi.1009223](https://doi.org/10.1371/journal.pcbi.1009223).
*(Licences, releases and last-push dates read from the repositories on 2026-08-21.)*
:::

**Downstream has its own slot now.** This paragraph used to carry CADET here.
Recovery turned out to need more room than a paragraph — the licences move, the
permissive option does not cover protein recovery at all, and *selecting* a train is
a different capability from simulating one. See **Downstream processing and product
recovery**, below.

**Dead ends, and this one hurts less than it did.** [pyFOOMB](https://github.com/MicroPhen/pyFOOMB)
bundles a bioprocess ODE model with parameter estimation and uncertainty in one package,
and it has not moved since February 2021. Cite the paper for design ideas; do not send
users to install it. **The superlative this entry carried — "the closest thing … that has
ever existed" — is withdrawn**: `estim8` above now covers the estimation-and-uncertainty
half of that description, is releasing, and was peer-reviewed this month. What pyFOOMB
still has and `estim8` does not is the model in the same package.
*(Corrected 2026-08-21.)*
[PenSimPy](https://github.com/smpl-env/PenSimPy) has been dormant since 2021 and needs a
C++ extension built from source; the valuable artifact there is the IndPenSim dataset and
benchmark, not the Python port. [dfba](https://gitlab.com/davidtourigny/dynamic-fba)
remains the reference dynamic-FBA implementation and has not released since 2020.

**If you pick one:** BASICO, for the parameter estimation Engin's own simulator does not
attempt — and BioSTEAM alongside it for the economics half, because they solve different
problems. Say the quiet part: `estim8` is the better-targeted estimator of the two, and
AGPL-3.0 is why it is not the recommendation for a permissively licensed tree. If your own
project has no such constraint, reverse that.

---

(eco-dsp)=

## Downstream processing and product recovery

*Funnel stage: the second half of `engin_core.tea` — everything between the broth and
the saleable kilogram.*

**Engin's position: does not build, and prices the outcome rather than the route.**
`ParametricCostModel` reaches downstream cost through titer and a purity multiplier;
`BioSteamCostModel` will run a flowsheet the caller supplies, and its docstring says
why it presumes none. `D9` says compose rather than reimplement unit-operation
models, and the projects below are what there is to compose with. Their licences are
the whole problem, and the thing you would most want — *choosing* a recovery train
rather than simulating one you already chose — is not available from anybody.

:::{dropdown} CADET-Core — AGPL-3.0 today, GPL-3.0 in the current stable release
:animate: fade-in-slide-down

[cadet/CADET-Core](https://github.com/cadet/CADET-Core)

The reference solver for chromatography and downstream unit operations, C++ with a
Python interface, from Forschungszentrum Jülich.

- **Pro** — general rate model with real transport and binding physics, not a
  shortcut correlation. If the question is what a column actually does, this is the
  answer and there is no permissive equivalent.
- **Pro** — plainly alive: commits through August 2026, and a v6 line in development.
- **Con, and read this before pinning anything** — **the licence changed under it.**
  Commit
  [`3a6a9eb`](https://github.com/cadet/CADET-Core/commit/3a6a9ebb803e17ca89cdebd548c3fc6a2ea1272a),
  *"Update license to AGPL (#696)"*, landed on 2026-06-08. `LICENSE.txt` on `master`
  today opens "GNU AFFERO GENERAL PUBLIC LICENSE". At the tag `v5.1.1` — released
  2026-03-18, and still the newest **stable** release — the same file opens "GNU
  GENERAL PUBLIC LICENSE". So a reader who pinned stable is on GPL-3.0 and a reader
  tracking `master` is on AGPL-3.0, and nothing in the release notes announces the
  difference. AGPL §13 reaches an adopter who modifies CADET-Core and exposes it only
  as a hosted service, with no distribution involved; GPL-3.0 does not. *(Both files
  read at their respective refs on 2026-08-24; the previous version of this page
  stated AGPL flatly and treated it as a longstanding fact.)*
- **Con** — a C++ simulator, not a bioprocess library. Standing up a case means
  building or fetching binaries and writing the model configuration; there is no
  `pip install` that gets you a costed recovery step.
:::

:::{dropdown} CADET-Process — GPL-3.0
:animate: fade-in-slide-down

[fau-advanced-separations/CADET-Process](https://github.com/fau-advanced-separations/CADET-Process)

GPL-3.0. The Python modelling and optimization layer over CADET-Core: an
object-oriented model builder, cyclic-stationarity evaluation, fractionation
optimization, and performance indicators.

- **Pro** — it removes the worst of CADET-Core's configuration burden and adds the
  parts a process engineer wants — yield, purity and productivity as first-class
  outputs rather than post-processing.
- **Pro** — maintained on a real cadence, latest release v0.12.0 on 2026-05-05.
  *(Checked 2026-08-24.)*
- **Con, and it is the one that matters for this slot** — **the user constructs the
  flow sheet.** Optimization covers physico-chemical model parameters, event timings
  and fractionation *within* that structure. It will not tell you whether to lyse or
  secrete, whether to run one polishing step or two, or in what order. See its own
  [user guide](https://cadet-process.readthedocs.io/).
- **Con** — GPL-3.0, so for an Apache-2.0 project with commercial users this is a
  subprocess boundary at best, never a dependency.
:::

:::{dropdown} BioSTEAM's separations units — NCSA
:animate: fade-in-slide-down

[BioSTEAMDevelopmentGroup/biosteam](https://github.com/BioSTEAMDevelopmentGroup/biosteam)

The same project the techno-economics slot recommends, listed again because its
separations library is what a reader will reach for after being told BioSTEAM is the
permissive option — and it is the wrong shape for this job.

- **Pro** — permissive and Apache-2.0-compatible, which nothing else in this slot is,
  and the units carry costing correlations rather than only physics. For a bulk
  chemical recovered by distillation, evaporation or extraction it is genuinely the
  answer.
- **Con, and it is disqualifying for protein recovery** — listing `biosteam/units` on
  2026-08-24 gives `adsorption`, `distillation`, `liquid_liquid_extraction`,
  `solids_separation`, `_clarifier`, `_multi_effect_evaporator`, `drying`,
  `_batch_crystallizer`, `molecular_sieve`, `_flash`, `_vibrating_screen` and
  `size_reduction`. **There is no chromatography module, no cell-disruption module
  and no tangential-flow-filtration module.** The nearest neighbour to a capture step
  is a single-component adsorption column.
- **Con** — the library is biorefinery-shaped by design and by provenance. Reading it
  as a general bioseparations toolkit is a category error this page has previously
  invited.
:::

**Dead ends, and this one is unusual: the method is not dead, the code never
existed.** Recovery-train *selection* has been solved in the literature, twice, and
neither result is installable. Wu, Yenkie and Maravelias take fermentation broth
characteristics and formulate the choice of separation technologies as a
superstructure MINLP with binary activation variables — including a companion
treatment of intracellular products with cell disruption — and state that "the model
has been developed in GAMS 25.1.1 environment and solved using BARON", two commercial
products, with nothing released
([*BMC Chem. Eng.* 1:21, 2019](https://doi.org/10.1186/s42480-019-0022-8)). Keulen et
al. do the biopharma equivalent, selecting chromatography mode and buffer-exchange
method over a superstructure of thirty-nine flowsheets, deterministic, with data
available "from the corresponding author upon reasonable request"
([*Biotechnol. Prog.* 41(2):e3514, 2025](https://doi.org/10.1002/btpr.3514)).
Newer entrants do not close it either:
[BioProcessNexus](https://github.com/mmedl94/bioprocessnexus) trains surrogates of
proprietary-TEA output for a process you have already fixed, and CADET-Hub is a
JupyterHub environment unifying existing CADET simulators. Recording this because the
cost of surveying this field is mostly the afternoon spent discovering that the
obvious-looking capability exists only behind a solver licence.

**The absence claim, and what backs it (`D15`, `D23`).** Searched 2026-08-24: GitHub
and PyPI for bioseparation, downstream process synthesis, purification train
selection and separation-network superstructures; CADET-Core, CADET-Process, BioSTEAM
and Bioindustrial-Park, IDAES-PSE, PharmaPy, QSDsan; the Maravelias separation-network
line; and 2025–2026 releases in the slot. **No open-source implementation, permissive
or copyleft, was found that takes a broth specification and returns a ranked recovery
train.** Rejected near-misses and why: CADET-Process optimizes within a fixed
structure; BioSTEAM has no bioseparation units; IDAES-PSE is an equation-oriented
framework whose model library targets energy systems; PharmaPy is
API-and-crystallization shaped. Note that the closed incumbents do not fill this
either — SuperPro Designer and BioSolve Process are costing tools in which the
engineer specifies the train — so this is not a case of open source lagging a
commercial product. If you know of a counterexample, that correction is worth more to
this page than any entry on it.

**If you pick one:** CADET-Process, because it is the only thing here that will give
you a defensible number for a chromatographic step — but pin CADET-Core deliberately
and know which licence your pin carries, and do not expect either to choose the train
for you. If your product is a bulk chemical rather than a protein, BioSTEAM instead,
and the licence problem disappears.

References: Wu, Yenkie & Maravelias, *Synthesis and analysis of separation processes
for extracellular chemicals generated from microbial conversions*, BMC Chemical
Engineering (2019),
[10.1186/s42480-019-0022-8](https://doi.org/10.1186/s42480-019-0022-8);
Keulen, Apostolidi, Geldhof, Le Bussy, Pabst & Ottens, *Comparing in silico flowsheet
optimization strategies in biopharmaceutical downstream processes*, Biotechnology
Progress (2025), [10.1002/btpr.3514](https://doi.org/10.1002/btpr.3514).

---

(eco-standards)=

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

:::{dropdown} MIFE / MIFD — GPL-3.0-or-later
:animate: fade-in-slide-down

[bioindustry-4.0/mim_ontology](https://gitlab.com/bioindustry-4.0/mim_ontology)

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
:::

:::{dropdown} xarray and CF conventions — Apache-2.0
:animate: fade-in-slide-down

[pydata/xarray](https://github.com/pydata/xarray)

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
:::

:::{dropdown} Frictionless Data — MIT
:animate: fade-in-slide-down

[frictionlessdata/frictionless-py](https://github.com/frictionlessdata/frictionless-py)

MIT. A JSON descriptor that types columns and travels next to plain CSVs.

- **Pro** — radically lower adoption cost than anything else here. Runs stay as CSVs
  anyone can open, and validation is scriptable, so "pH is missing on three of forty runs"
  fails CI instead of failing silently in a model fit.
- **Con** — tabular only. Long-format CSV for high-frequency multichannel data is wasteful
  and does not scale.
- **Con** — types columns, carries no domain semantics. Two labs can produce valid and
  mutually incompatible packages, so it does not solve interchange without MIFE on top.
:::

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

(eco-featurization)=

## Molecular and graph featurization

*Funnel stage: `engin-graph`, and through it `engin-pathway` and `engin-materials`.*

**Engin's position: composes, and insists on the boring baseline.** `engin-graph` embeds
structured candidates and ranks them with a calibrated interval. The featurization and the
message passing are not Engin's contribution.

:::{dropdown} RDKit — BSD-3
:animate: fade-in-slide-down

[rdkit/rdkit](https://github.com/rdkit/rdkit)

BSD-3. The standard cheminformatics toolkit.

- **Pro** — it is the substrate. PyTorch Geometric's molecular featurizers, DeepChem and
  the descriptor packages all call it; depending on it directly is honest rather than new.
- **Pro** — sanitization and valence handling is the part everyone underestimates, and
  structures pulled from public databases are dirty.
- **Con** — polymers are a genuine weak spot for `engin-materials`: repeat-unit and
  molecular-weight-distribution semantics are not first-class.
- **Con** — C++ behind Python bindings, so stack traces stop being informative at the
  boundary. It gives you graphs and descriptors, never a model.
:::

:::{dropdown} PyTorch Geometric — MIT
:animate: fade-in-slide-down

[pyg-team/pytorch_geometric](https://github.com/pyg-team/pytorch_geometric)

MIT. The dominant GNN library.

- **Pro** — heterogeneous graph support maps directly onto metabolic routes, where
  reaction nodes and metabolite nodes are genuinely different types. This is the right
  primitive, not a workaround.
- **Pro** — correct batching of variable-sized graphs is subtle, easy to get wrong, and
  exactly the don't-reimplement case.
- **Con** — the optional compiled accelerator packages remain the most common install
  failure in this ecosystem, and the quality gradient across contributed layers is steep.
  Releases and commits both continue to land: 2.8.0 was published 2026-06-05, adding
  PyTorch 2.9–2.12 and Python 3.14 support and deprecating `torch-cluster` and
  `torch-spline-conv` in favour of `pyg-lib`. *(This bullet previously said no release
  had been cut since late 2025; corrected 2026-08-20 from the releases API.)*
- **Con, and Engin should say it out loud** — for ranking a few thousand candidates, a
  gradient-boosted model over descriptors is frequently the stronger baseline. Reach for a
  GNN after the simpler thing has been shown to lose, not before.

Reference: Fey & Lenssen, [arXiv:1903.02428](https://arxiv.org/abs/1903.02428).
:::

:::{dropdown} mordredcommunity — BSD-3
:animate: fade-in-slide-down

[JacksonBurns/mordred-community](https://github.com/JacksonBurns/mordred-community)

BSD-3. A maintained fork of Mordred computing a wide 2D and 3D descriptor block.

- **Pro** — the cheap, strong baseline any GNN claim should be measured against, which a
  self-critical project needs to have on hand.
- **Con** — a very wide descriptor block on a modest dataset is a p ≫ n overfitting trap,
  with many near-duplicate or NaN descriptors, and the library does not filter for you.
- **Con** — effectively one maintainer doing compatibility triage. Treat it as frozen
  functionality on life support. The original `mordred` has been dead since 2019.
:::

**Dead end, and this one surprises people.** [DGL](https://github.com/dmlc/dgl) is
effectively abandoned upstream: no release since September 2024, **no commit on `master`
at all since 2025-07-31** — this entry previously said "a single outside-contributor
commit in the last year", and that commit is now more than twelve months old with
nothing after it *(re-checked 2026-08-20)* — and a direct "is this still supported?" issue that received no
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

---

## Don't see what you need?

If you came here looking for something and this page didn't have it, that gap is the most
useful thing you could tell us. You read far enough to conclude the need is unmet and you
are still here, which is more signal than any amount of guessing on our end.

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} Publicly
:link: https://github.com/enginbio/engin-suite/issues/new?labels=unmet-need,task/tooling&title=Unmet+need:+

A prefilled issue. Best for a concrete gap: a stale entry, a changed licence, a maintained
tool that is missing.
:::

:::{grid-item-card} Privately
:link: mailto:maintainers@engin.bio?subject=Unmet+need

**maintainers@engin.bio** — for anyone without a GitHub account, or unwilling to describe
in public what they are building.
:::

::::

Three prompts are all it needs: **what you were trying to do**, **what you looked for**, and
**what you found instead**. Not a form.

If the need is vaguer than an issue wants to be — *"I need something for X and I don't know
what to ask for"* — [Discussions](https://github.com/enginbio/engin-suite/discussions) is
the better room. Filing that as an issue creates a backlog item nobody intends to close.

**What happens when you do.** This is read by one person (`D18`). You will get a reply where
there is something useful to say, and silence is not a verdict on the report — it is a solo
project with no support commitment, and saying so is better than implying otherwise.

**And what it becomes.** What arrives this way is **testimony, not evidence**
(`CONTRIBUTING.md` rule 2). Twelve people reporting the same gap is a strong signal about
demand and is not a measurement. If it reaches a public document it will be recorded as a
source and phrased *"practitioners report"* — never *"studies show"*.
