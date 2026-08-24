# 0012 — Target market selects which regulator is even speaking, not a weight on a score

**Status:** Proposed (2026-08-23)

## Context

[ADR 0010](0010-regulatory-status-is-two-facts-not-a-scalar.md) retired the `gras` scalar and
encoded EFSA QPS status instead, displayed and not scored. It deferred the ranking question to
[#22](https://github.com/enginbio/engin-suite/issues/22), which then named its own precondition:

> Scoring a regulatory status without knowing which regulatory regime the product falls under is
> how the encoding becomes misleading rather than merely incomplete.

That precondition was written as *"add a target-market input"* — a design task. This record treats
it the way [#188](https://github.com/enginbio/engin-suite/issues/188) treated the encoding question:
as a factual one first. **Which regimes govern a fermentation-derived product, and which of them
does QPS actually reach?**

It enumerates.

## What QPS reaches

QPS exists "in support of EFSA risk assessments", so its reach is EFSA's remit — and EFSA states
that positively:

> EFSA assesses the safety of microorganisms in the applications it receives for market
> authorisation of feed additives, food additives, food enzymes, food flavourings, novel food, and
> plant protection products.  # ref: 2026-efsa-qps-topic-page

Six categories, plus food contact materials, which appears in the notification breakdown rather
than in that sentence.

| Intended use | EU instrument | Does QPS speak? |
|---|---|---|
| Feed additive | Reg. 1831/2003 | **yes** |
| Food additive | via EFSA | **yes** |
| Food enzyme | Reg. 1332/2008 | **yes** |
| Food flavouring | via EFSA | **yes** |
| Novel food | Reg. 2015/2283 | **yes** |
| Plant protection product | via EFSA | **yes** |
| Food contact material | via EFSA | yes, by notification practice |
| Technical / industrial enzyme — detergent, textile, biofuel, pulp & paper | **REACH 1907/2006**, CLP 1272/2008, BPR 528/2012 | **no** |
| Human medicine | EMA / national, not EFSA | **no** |
| Cosmetic | Reg. 1223/2009 | **no** |

**Plant protection products are the row that breaks the received framing.** ADR 0010 and #22 both
say "QPS is about food and feed". That is nearly right and it is not the boundary: a
crop-protection microorganism is neither food nor feed and QPS reaches it. The boundary is *EFSA's
remit*, which is wider.

**The "production purposes only" qualification widens it again.** The QPS list carries, verbatim:

> QPS applies for 'production purposes only' (the qualification 'for production purpose only'
> implies the absence of viable cells of the production organism in the final product and can also
> be applied for food and feed products based on microbial biomass).
> # ref: 2026-efsa-qps-list

So QPS can attach to a *production organism* whose cells never appear in the product. "Is the
organism in the food?" is the wrong question; "is EFSA assessing this application?" is the right
one.

## The decision

**1. Target market is a categorical input naming the regulated-product category, not a weight.**
It selects which regulator is speaking. A number cannot express "this regime does not apply to
you", and that is the most common case for the products this suite is aimed at.

**2. Where the market is out of EFSA's remit, QPS status is suppressed rather than scored at
zero.** A suppressed field and a zero are different claims. Engin's own worked data is
erythromycin — a human medicine, EMA's remit, where QPS is silent — and its TEA defaults describe
specialty/enzyme-class economics, much of which is REACH territory. **For the suite's own flagship
examples, the honest display is nothing at all.**

**3. Do not add a US axis alongside it.** ADR 0010 decision 3 refused a GRAS *score* and this
record does not reopen it. A jurisdiction input is a second categorical dimension with its own
enumeration, and nothing in the funnel consumes one yet.

**4. This record does not decide what a status does to an ordering.** That is #22 item 2 —
demotion, hard constraint, or displayed-only-forever — and it is now answerable *per regime*
instead of in the abstract, which is what it needed. It remains a founder call.

## Consequences

`HostQuery` gains an optional target-market category. `render_memo` shows the QPS block when the
market is inside EFSA's remit and states that QPS does not apply when it is outside, rather than
hiding the field silently — a reader who saw the status yesterday should be told why it is gone.
Scoring is unchanged either way until #22 item 2 is decided.

The enumeration will drift. Regulation numbers change and EFSA's remit is periodically extended;
the rows above are dated and cite their sources so a re-check is a lookup rather than a re-survey.

## Why this might be wrong

**The strongest objection is that this is a taxonomy nobody asked for a product to sit in.**
Engin's user supplies a molecule, not a regulated-product category, and asking them to pick one
imports a compliance vocabulary into a process-development tool. That is a real cost, and it is why
the input is optional and its absence means "no regulatory display" rather than "assume food".

**The scope boundary is asserted more sharply than any single source states it.** EFSA defines its
remit positively — what it assesses — and does not publish a list of things QPS excludes. That
technical enzymes are outside is an *inference* from the positive remit plus the separate REACH
pathway (AMFEP maintains distinct regulatory pages for technical, food and feed enzymes,
consistent with the boundary but not a statement of it). No source found says "QPS does not apply
to detergent enzymes" in those words. The inference is well-supported and it is an inference.

**The table is EU-first because QPS is.** A US reader gets a table whose right-hand column is
mostly irrelevant, and the FDA equivalents are not symmetric — GRAS is substance-and-use scoped
where QPS is organism scoped, which is the whole finding of
[#188](https://github.com/enginbio/engin-suite/issues/188). Adding a US column would invite exactly
the averaging ADR 0010 decision 4 refuses.

**And the enumeration could be a false floor.** Six categories plus three exclusions is tidy enough
to be suspicious. Products exist that sit awkwardly — a feed enzyme sold into both feed and
technical channels, a biostimulant that is neither PPP nor fertiliser in every member state. The
categories are the *regulatory* ones, not a partition of everything a fermenter can make, and a
product that spans two of them has two answers rather than one.
