# Running Engin without a lab

You have run Engin, it has told you what to try next, and you do not have a bench.
This page says how far you can get anyway, where the physical boundary actually
falls, and what governs crossing it.

```{important}
**Every entry below is dated, and the date is the point.** A provider's marketing
site outlives the service behind it, so what is checked here is coverage and
liveness rather than price — a provider whose menu excludes your organism is not a
cheaper option, it is not an option. Prices appear only where the provider publishes
one and it could be quoted directly.

Kept current by a weekly pass
([`.github/prompts/lab-access-maintenance.md`](https://github.com/enginbio/engin-suite/blob/main/.github/prompts/lab-access-maintenance.md)),
because a page that sends someone to a lab that closed is worse than no page.
```

## The whole tool runs on public data, today

**This is the part most readers miss, and it is not a demo mode.**
[Quickstart](quickstart) fetches **406 real batches from a working pharmaceutical
plant**, checksum-verified with a provenance manifest, and takes them through the
same fit → calibrate → forecast path the rest of the documentation describes. No
bench, no samples, no institution, no account.

What you get from it is not a toy: it is the project's own
[tier-3 validation](methods/real-data-calibration) — the calibration numbers on this
site come from that dataset. A reader with a laptop is running the same measurement
the maintainers publish.

What it does **not** give you is a forecast about *your* process. That is the
boundary, and it is worth being precise about where it sits:

| you can do this with no lab | you cannot |
|---|---|
| run the full loop on published batches | forecast a strain or process you have not run |
| reproduce every published number | generate the run history a forecast needs |
| [contribute a benchmark](contributing-a-benchmark) — including one where Engin loses | verify a recommendation physically |
| compare hosts, rank routes, price a hypothetical process | |

`engin-process` will happily *simulate* runs from a vessel you describe. That is a
different thing from reading a run history, the quickstart says so, and it is the
distinction that matters most to a reader with no bench.

## Where the physical boundary falls

Four categories cover essentially every route from a design to a measurement. Which
one you need depends on what the design is, not on how much you want to spend.

:::{dropdown} Remote execution — someone else's robots run your protocol
:animate: fade-in-slide-down

Cloud-lab providers execute a protocol you specify on their hardware. The category
is real and a handful of providers operate in it.

**What decides whether it helps you is coverage, not price.** Providers specialise
narrowly — cell-free reactions, or protein expression, or bioprocess — and a
provider whose menu does not include your organism is not a cheaper option, it is
not an option. Check the menu before the price list.

**Who operates in it** *(checked 2026-08-30, from each provider's own site)*:

| provider | covers | price |
|---|---|---|
| [Adaptyv Bio](https://www.adaptyvbio.com) | proteins only — binding, expression, thermostability | **"From $149 / protein"**, publishes "Price includes 2 replicates" |
| [Culture Biosciences](https://www.culturebiosciences.com) | **the bioprocess option** — bioreactors, fermentation | none published; quote-based |
| [Ginkgo Cloud Lab](https://cloud.ginkgo.bio) | "Run Autonomous Lab Protocols On Demand" | none published |

**Adaptyv is the only one of the three publishing a unit price.** The Ginkgo and
Culture pages render their detail through JavaScript, so a plain fetch reaches the
title and no more; both were confirmed live and neither could be read for terms.
That is recorded rather than filled in from memory.

**This category has a well-populated graveyard**, which is the reason to check dates
rather than reputation — see [dead ends](#dead-ends) below.
:::

:::{dropdown} Buying the work — sequencing, synthesis, assays as a service
:animate: fade-in-slide-down

The most accessible category, and the one where an individual can transact at all.
Sequencing in particular is sold per sample rather than per project —
[Plasmidsaurus](https://plasmidsaurus.com) covers whole-plasmid, amplicon, whole-genome,
AAV, microbiome and RNA-seq *(menu read 2026-08-30; its per-sample prices sit behind
an ordering flow and are not quoted here)*.

**Gene synthesis is gated on identity rather than on price**, and that gate is the
subject of [the governance section below](#what-governs-crossing-it). Budget for
being asked who you are.
:::

:::{dropdown} Shared and public capacity — user facilities and funded networks
:animate: fade-in-slide-down

Some national facilities provide sequencing and synthesis at no cost to accepted
proposals. The [JGI Community Science Program](https://jgi.doe.gov/user-programs/program-info/community-science-program/)
states it plainly — work "will be performed by the JGI **at no cost to the user**"
*(read 2026-08-30)*. The recurring gate is **institutional** rather than financial:
an accepted proposal, and a signatory on a user agreement that an unaffiliated
individual does not have.

**One correction worth having before you go looking.** NSF's Programmable Cloud
Laboratories network is widely described as a national cloud lab for biology. Read
from [NSF's own awards API](https://api.nsf.gov/) on 2026-08-30, the test-bed awards
obligated 2026-08-01 are *AI for Materials Design*, *PoLARIS* (a polymer laboratory),
*SPEED*, and an *AI Materials and Manufacturing* pilot facility.
<!-- not-a-claim: read from NSF's public awards API on the date given -->
It is a materials and chemistry network with biology at the margin. That may change;
the point is to check rather than to plan around the coverage.
:::

:::{dropdown} Community labs and teaching space
:animate: fade-in-slide-down

Membership-based labs exist in many cities and are the only category offering bench
access to an unaffiliated person.

**A membership is not a project.** Several gate bench work on an accepted proposal,
so joining without a starting point buys you a keycard and nothing else. Arrive with
the specific thing you intend to measure.

If you are heading this way, read the
[Community Biology Biosafety Handbook](https://www.genspace.org/community-biology-biosafety-handbook)
first. It is written for exactly this reader and it is better to meet it on the way
in than after a question comes up.
:::

(what-governs-crossing-it)=

## What governs crossing it

Gene synthesis providers screen orders, and the screening covers who is ordering as
well as what is being ordered. Members of the International Gene Synthesis
Consortium apply a shared protocol; **v3.1 is dated 1 June 2026**, and §1.1 reads:

> "We do not ship to residential addresses or to PO Boxes."
<!-- ref: 2026-igsc-harmonized-screening-protocol -->

That sentence is the actual reason a home address fails, and it is worth stating
plainly rather than leaving someone to discover it as an unexplained rejection.

**It is a governance feature, and the ordinary answer is an institution or an
incorporated entity** — not a workaround. Engin's own
[BIOSECURITY](https://github.com/enginbio/engin-suite/blob/main/BIOSECURITY.md) §5
declines to model physiological activity, toxicity or pathogenicity, and this page
keeps the same posture one level down: it describes *access and governance*, and
contains no protocol, no method and no operational detail.

```{warning}
Nothing here is legal advice, and export-control and screening rules change. Verify
against the provider's current terms before relying on any of it.
```

(dead-ends)=

## Dead ends, recorded on purpose

Half the cost of surveying a field is rediscovering that the obvious-looking option
stopped operating. Both of these are still routinely cited as cloud-lab options.

**Strateos** — [strateos.com](https://www.strateos.com) resolves and the site loads.
The most recent dated content on the front page is a conference held **5–6 November
2024**, and the banner advertises a pivot: *"Strateos Launches Rapid Idea-to-Data
Solution for Small Molecule Discovery."* <!-- not-a-claim: read from the provider's own front page on the date given -->
Read 2026-08-30. **A live homepage is not a live service**, and nearly two years
without a dated update is the signal here.

**Emerald Cloud Lab** — [emeraldcloudlab.com](https://www.emeraldcloudlab.com) loads
and its footer reads **"© 2026 Emerald Cloud Lab, Inc."** *(read 2026-08-30)*.
<!-- not-a-claim: read from the provider's own footer on the date given -->

```{note}
**#240 lists Emerald as a dead end and this page does not.** The issue reports it as
having published nothing since April 2024; a current copyright year is weak evidence
of life, but it is evidence, and it is the opposite of what a lapsed site looks like.
Neither the claim nor its negation is established here, so Emerald is recorded as
*unverified* rather than dead. Calling a company defunct is not a thing to get wrong
on a page whose whole argument is that stale entries are worse than none.
```

(what-this-leaves-out)=

## What this leaves out, and why

**Most prices, and every community-lab listing.** A price behind an ordering flow or
a JavaScript configurator cannot be quoted from a check, and a quoted price that has
moved is worse than none — so prices appear only where a provider publishes one on a
page that can be read. Community labs are omitted entirely: their operating status is
the least checkable fact on this page, and #240's own research turned up two lapsed
domains and one site whose homepage and classes page contradicted each other.

**Several specifics from #240 that did not verify.** It gives an entry price and a
cell-free-only restriction for Ginkgo Cloud Lab, a ~60-protein minimum for Adaptyv,
and per-sample prices for two sequencing providers. None of those could be read from
the providers' own pages on 2026-08-30 — the pages render through JavaScript or put
the number behind an ordering flow. They may well be right; they are not published
here, because this page's value is that its entries were checked.

**One claim that did not survive checking.** #240 attributes an October 2026
threshold change, 200 → 50 nucleotides, to the IGSC protocol. It is not in that
document — the full v3.1 text contains no length threshold at either value. The
change is a government screening-framework matter rather than an IGSC one, and it is
omitted here rather than repeated from the wrong source.

## Related

- [Quickstart](quickstart) — the thing you can run right now
- [Real-data calibration](methods/real-data-calibration) — what those 406 batches establish
- [Contributing a benchmark](contributing-a-benchmark) — the contribution that needs no lab
- [Ecosystem](ecosystem) — the same method applied to software
