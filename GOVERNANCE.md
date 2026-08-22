# Governance

**Version 1.0 · Effective 2026-08-07 · Next scheduled review 2027-02-07**

Maintainer contact: **maintainers@engin.bio**

This document states how decisions are made in Engin, who makes them, how people take on and leave those roles, and what happens when there is disagreement. It follows the structure recommended by [Scientific Python SPEC 9](https://scientific-python.org/specs/spec-0009/).

Conduct expectations are in [CODE_OF_CONDUCT.md](https://github.com/enginbio/engin-suite/blob/main/CODE_OF_CONDUCT.md). Contribution mechanics are in [CONTRIBUTING.md](https://github.com/enginbio/engin-suite/blob/main/CONTRIBUTING.md). The record of what has been decided and why is [DECISIONS.md](https://github.com/enginbio/engin-suite/blob/main/DECISIONS.md).

---

## 1. Current state

**Engin has one maintainer. The project is actively seeking a co-founder.**

Under the standard taxonomy this is a **BDFL** model — a single person holds final say — which is the default for a project of this size rather than a considered preference. The intended destination is a **liberal contribution** model, where decisions are made by consensus-seeking among people who do the work.

The transition trigger is stated in §4.3. This document is written now, before there is anyone to govern, because a project asking others to depend on it owes them an answer to *what happens if the maintainer disappears* before rather than after they have committed.

---

## 2. Roles

| Role | How obtained | Authority | Obligations |
|---|---|---|---|
| **User** | Use the software | Open issues, participate in discussion, fork | Follow the Code of Conduct |
| **Contributor** | Have a pull request merged | All of the above; listed in release notes | DCO sign-off on commits; follow [CONTRIBUTING.md](https://github.com/enginbio/engin-suite/blob/main/CONTRIBUTING.md) |
| **Maintainer** | Invitation under §4.1 | Commit access; merge PRs; triage; release | Uphold [DECISIONS.md](https://github.com/enginbio/engin-suite/blob/main/DECISIONS.md); keep calibration and benchmark tests honest; respond to review requests within 10 working days or say they cannot |
| **Lead maintainer** | Currently the founder; see §4.3 | Final say on decisions not reaching consensus; holds infrastructure credentials | Publish reasoning for every decision made over unresolved disagreement |
| **Co-founder** | Direct agreement; see §4.2 | Peer to the lead maintainer on direction, scope and DECISIONS.md | As maintainer, plus shared responsibility for project direction |

**Infrastructure credentials** — PyPI, the `engin.bio` domain, Read the Docs, the GitHub organization — are currently held by the lead maintainer alone. This is a single point of failure and is acknowledged as one; §5 covers what happens if it fails.

A **continuity runbook** is maintained privately, recording where each credential lives, how it is recovered and who to contact. It holds no secrets — it is kept private because recovery paths are worth nothing to a reader and something to an attacker. It does not remove the single point of failure; it means the project's recovery does not depend on one person's memory. A second credential holder is the real fix and follows a co-founder (§4.2) rather than preceding one.

---

## 3. How decisions are made

### 3.1 Decision classes

| Class | Examples | Process |
|---|---|---|
| **Routine** | Bug fixes, tests, documentation, dependency bumps | Any maintainer merges after review. No discussion required. |
| **Substantive** | Public API changes, new dependencies, changes to defaults or model behaviour, anything affecting published results | Issue opened first. Minimum 72 hours for comment. Consensus among maintainers, or lead maintainer decides with published reasoning. Recorded in `DECISIONS.md` with an ID. |
| **Foundational** | Licence, contributor agreement policy, governance, biosecurity policy, commercial posture | Issue opened first. Minimum 14 days for comment. Requires lead maintainer plus, once they exist, majority of maintainers. Recorded in `DECISIONS.md`. |

If it is unclear which class a change falls into, it is treated as the higher one.

### 3.2 Consensus

Consensus means no maintainer sustains a blocking objection — not unanimity, and not a vote. A maintainer blocking a change states the reason in the issue. Where a blocking objection cannot be resolved, §6 applies.

### 3.3 Recording

Every substantive and foundational decision is recorded in [DECISIONS.md](https://github.com/enginbio/engin-suite/blob/main/DECISIONS.md) with an identifier, the reasoning, and its status. Code, issues and pull requests cite decision identifiers rather than restating arguments.

**Superseded decisions are retained**, not deleted. A record showing what changed and why is more useful than one presenting a clean narrative, and it is what makes the commitment in §3.4 verifiable.

### 3.4 Transparency commitment

Decisions are made in public. Specifically: the roadmap is a public project board (<https://github.com/orgs/enginbio/projects/1>); reasoning is written down before implementation; and a decision made over unresolved disagreement is published with the reasoning that produced it.

With one maintainer, not every decision can be consensus. What is promised is that the reasoning is visible and contestable — not that every contributor holds a veto.

---

## 4. Joining and leaving

### 4.1 Becoming a maintainer

There is no application. An existing maintainer extends an invitation when a contributor has demonstrated:

- **Sustained contribution** over at least three months.
- **Judgement, not volume.** Reviewing others' work, identifying problems before they ship, and disagreeing well count for more than commit count.
- **Adherence to the decision record** — recognising when a change would contradict a recorded decision, and raising it rather than working around it.

Invitation requires agreement of existing maintainers under §3.1 (substantive). The invitation and its acceptance are recorded in `DECISIONS.md`.

### 4.2 Becoming a co-founder

A distinct route, not a senior form of the above. A co-founder joins at peer level with shared authority over direction, scope and the decision record from the start, rather than accumulating it through contribution.

**The project is actively looking for one.** The gap most worth filling is bench-side: Engin is built by someone strong on modelling and forecasting who has read widely on bioprocess, not by someone who has run a fermentation campaign, watched a scale-up fail, or negotiated with a contract manufacturer over a feeding line. That perspective would change what gets built, not only how fast.

If that describes you, write to **maintainers@engin.bio**. Expect a conversation, not an application process.

### 4.3 Transition away from BDFL

When there are **three or more maintainers from at least two organizations**, this document is revised: §3 moves to consensus-seeking among maintainers with no individual holding final say, and §1's BDFL designation is removed. The revision is itself a foundational decision under §3.1.

### 4.4 Stepping down

A maintainer may step down at any time by saying so in an issue. Commit access is removed; they are listed as an emeritus maintainer in release notes.

### 4.5 Inactivity

A maintainer who is unresponsive for **12 months** — no commits, reviews, or issue participation — has commit access removed, after an attempt to make contact and 30 days' notice in a public issue. This is administrative, not a judgement, and access is restored on request if they return.

### 4.6 Removal

A maintainer may be removed for sustained Code of Conduct violation or for actions that damage the project's integrity — for example, knowingly publishing results that misrepresent model performance. Removal requires agreement of all other maintainers, or, where only the lead maintainer remains, the lead maintainer's decision with published reasoning. The person is notified before the decision is made and may respond.

---

## 5. Succession and continuity

The realistic failure mode for a one-maintainer project is not conflict. It is silence.

**5.1 The project cannot be captured.** Engin is Apache-2.0 with no contributor licence agreement (see `D3`, `D4` in [DECISIONS.md](https://github.com/enginbio/engin-suite/blob/main/DECISIONS.md)). Copyright is distributed across contributors, so the existing code cannot be relicensed — by the current maintainer or anyone who succeeds them. Anyone may fork at any time, permanently. **That is the real continuity guarantee: it is enforceable by you, not promised by us.**

**5.2 Unresponsiveness is a legitimate fork trigger.** If the maintainers are unreachable for six months while issues go unaddressed, the community is entitled to continue the work elsewhere. The project will not treat that as hostile, and will redirect to a fork that has taken up maintenance if asked.

**5.3 Planned handover.** A maintainer intending to stop will announce it in a public issue with at least 30 days' notice, and will transfer commit rights, PyPI publishing rights and documentation access to willing contributors where transferable.

**5.4 Names and infrastructure.** The `engin.bio` domain is held by EnginBio.

**Every `engin-*` distribution name is registered to this project**, as placeholder reservations rather than releases — each a `0.0.1.dev0` stub whose description points back at this repository. `enginbio` is not registered. The bare name `engin` belongs to an unrelated dependency-injection framework and is not obtainable.

This paragraph has been wrong about the count four times, because it restated an index state that kept moving. It no longer carries a count: the names are discovered from `packages/*/pyproject.toml` and checked against the live index by `python scripts/pypi/reserve_names.py --verify`, which CI runs. If that check passes, this sentence is true; if a name is ever unclaimed, CI says so rather than this paragraph going quietly stale a fifth time.

**Nothing has been *released*.** A reservation stub is not a distribution: `pip install engin-core` succeeds and gives you an empty placeholder, which is a more confusing outcome than failing outright. Install from the repository.

This section has now been wrong in both directions. An early version claimed the names were held when none were; it was corrected on 2026-08-13 to say none were registered, and that in turn went stale when four were taken on 2026-08-14. Corrected again 2026-08-16 rather than quietly amended — checked against PyPI on that date, name by name.

The practical consequence for anyone depending on this: **install from the repository, and do not assume a PyPI name is ours until this section says it is.** On handover, whatever is held transfers with the project where transferable. Where not, a fork is free to rename, and this project will link to it.

---

## 6. Disagreement and conflict

**6.1 Technical disagreement.** Raise it in the issue. If it cannot be resolved and the decision is substantive or foundational, the lead maintainer decides and publishes the reasoning. A contributor who believes a decision is wrong may open an issue arguing against the recorded reasoning — that is a legitimate contribution and sometimes the most valuable kind.

**6.2 Conduct concerns.** Report to **conduct@engin.bio** under [CODE_OF_CONDUCT.md](https://github.com/enginbio/engin-suite/blob/main/CODE_OF_CONDUCT.md).

**6.3 The limitation of a one-person project, stated plainly.** Reporting a conduct concern about the sole maintainer means reporting it to that maintainer. There is no independent body, and this document does not pretend otherwise. Someone uncomfortable with that may raise the concern publicly in an issue, or contact the conduct body of a project in the surrounding ecosystem. This is one of several reasons §4.2 and §4.3 matter.

**6.4 Escalation beyond the project.** Where a concern cannot be resolved internally and the project has a fiscal host or foundation affiliation, that body's process applies. **Engin has neither, and is not currently seeking one** — a deliberate decision with written triggers rather than an open item (`D25`). The honest consequence is that this escalation route does not exist today, and §6.3 is the whole of the answer until it does.

---

## 7. Changing this document

Amendments are foundational decisions under §3.1: an issue, a minimum 14-day comment period, and a record in `DECISIONS.md`.

Changes that would reduce transparency or concentrate authority are argued in public before they are made, not after.

Reviewed every six months, or on any change to the number of maintainers.

---

## 8. What this document does not cover

- **Conduct expectations** — [CODE_OF_CONDUCT.md](https://github.com/enginbio/engin-suite/blob/main/CODE_OF_CONDUCT.md)
- **How to contribute** — [CONTRIBUTING.md](https://github.com/enginbio/engin-suite/blob/main/CONTRIBUTING.md)
- **What has been decided and why** — [DECISIONS.md](https://github.com/enginbio/engin-suite/blob/main/DECISIONS.md)
- **Dual-use and biosecurity** — [BIOSECURITY.md](https://github.com/enginbio/engin-suite/blob/main/BIOSECURITY.md)
- **Software vulnerabilities** — [SECURITY.md](https://github.com/enginbio/engin-suite/blob/main/SECURITY.md)
- **API stability and release policy** — [docs/api-stability.md](https://github.com/enginbio/engin-suite/blob/main/docs/api-stability.md)
