# Standing check: `docs/lab-access.md`

A recurring maintenance pass over the lab-access directory. Sibling of the
ecosystem-map check that maintains `docs/ecosystem.md`; same conventions, different
decay profile — and the difference is the whole reason this file exists.

**Cadence: weekly.** Not daily. A GitHub repository's health changes on a commit;
a provider's terms and a community lab's opening hours do not, and a daily pass
would produce twelve no-op runs for each real finding. Monthly is too slow for a
lapsed domain.

---

## Why this one is harder than the ecosystem map

`ecosystem.md` entries are checkable in one call: last commit, latest release,
`LICENSE` at a tag. Nothing here is. A provider's marketing site stays up long after
the service behind it stops, and **a page that sends someone to a lab that closed is
worse than no page** — that is the standard this check is held to, from #240.

So the failure you are looking for is rarely a changed fact. It is **a fact that is
still displayed and no longer true.**

## What to check, in priority order

**1. Is it alive?** For every named provider and lab:
   - a dated signal from the last 12 months — a post, a release, a changelog, a
     status page, a job listing, a shipped order confirmation someone reported
   - the domain resolves and is not parked
   - the pricing or booking page loads, rather than the marketing page loading and
     the booking page 404ing

   **A live homepage is not a live service.** Check the page a customer would
   actually have to reach.

**2. Did the terms move?** Prices, minimums, order units, geographic restrictions,
   identity requirements. Quote-only providers: confirm they are still quote-only
   rather than assuming.

**3. Did the governance move?** The screening-protocol version, its effective date,
   and the specific quoted sentences. These are the slowest-moving facts on the page
   and the ones a reader is most likely to act on.

**4. Is anything newly dead?** Record it rather than deleting it. Half the cost of
   surveying a field is rediscovering that the obvious-looking option stopped
   operating, and a reader who has heard of a defunct provider is better served
   meeting it in the dead-ends list than not at all.

## Rules this check inherits

- **Read the primary source.** The provider's own page, the protocol PDF, the
  funder's own API. Not coverage of it, not a summary, not this page's own previous
  wording. Where a number is quoted, quote it.
- **State the date of every check**, per entry, in the page text.
- **Anything from a practitioner account rather than a measurement gets
  `CONTRIBUTING.md` rule 2 treatment** — labelled testimony, not fact.
- **Editorial judgement is labelled**, per `CONTRIBUTING.md` rule 3.
- **`D23` applies**: a claim about the world gets a `sources.yaml` row, and the row
  says what was verified and what was not.
- **Record what you could not check.** A provider you could not reach is a finding,
  not a silence. Say whether the block was a paywall, a login wall, bot detection or
  a dead host — they mean different things.

## Scope limits, which are not negotiable in a maintenance pass

`docs/lab-access.md` carries **capability, access and governance only**. No
protocols, no methods, no operational detail. This is `BIOSECURITY.md` §5's posture
applied one level down, and a maintenance pass is exactly where it would erode by
accident — a provider's page will describe what it does, and summarising the
capability is in scope while reproducing the method is not.

Nothing in this check touches `D19`'s declined-scope list. If a change would require
ranking pathways, modelling activity, or saying what to make, stop and file an issue
instead.

## Output

**If nothing moved**, say so and stop. A no-op run that reports "checked N entries,
all current, here are the dates" is a successful run and should not manufacture an
edit.

**If something moved**, open one PR with:
- the corrected page, dates updated per entry
- `sources.yaml` rows added or amended for anything that changed
- the regenerated `docs/references.md`
- a PR body naming, for each change: **what it said, what is true, and how that was
  checked** — with the primary-source URL and the date

**If a provider or lab has died**, do not delete the entry. Move it to the dead-ends
section with the date of the last signal you could find and what that signal was.

**If a check could not be completed**, say so on the PR, and say what it would take.
Per `CLAUDE.md`: if a source is paywalled and reaching it would change what the page
can claim, name the price and ask rather than quietly weakening the claim.

## Gates before opening the PR

```bash
python scripts/evidence/render.py --check
python scripts/evidence/check_claims.py
python scripts/evidence/check_corrections.py
sphinx-build -E -a -W --keep-going -b html docs /tmp/lab-cold
```

The `-E -a` matters. An incremental Sphinx build reuses doctrees and reports no
warning where a cold build fails, and that has shipped a broken cross-reference to
CI at least once.

Then, per `CLAUDE.md`: `gh pr list` immediately before opening, because `main` moves
in hours. Rebase and re-run rather than trusting a green check from yesterday.
