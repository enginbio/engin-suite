"""The three faces, each against the baseline it claims to beat.

Every assertion here is on the *synthetic* landscape. Read the package README before
quoting any of it: beating a constructed baseline shows the loop is wired, not that
the wedge holds against real pLDDT or a real campaign.
"""

from __future__ import annotations

import numpy as np
import pytest

from engin_protein import (
    CampaignPlanner,
    DesignEvaluator,
    LowNCopilot,
    make_landscape,
    random_campaign,
    transfer_benefit,
)
from engin_protein.evaluate import top_k_hit_rate

# --------------------------------------------------------------- evaluate [Plan 2]


def test_evaluate_beats_the_confidence_proxy_under_epistasis():
    # The mechanistically meaningful claim: a structure-confidence proxy is blind to
    # interactions, so the learned ranker's edge should be clearest when epistasis is
    # high. Averaged over seeds because a single split is noisy.
    gaps = []
    for seed in range(4):
        ls = make_landscape(epistasis=0.8, seed=seed)
        ev = DesignEvaluator().fit(ls.sample_campaign(80, seed=seed + 10))
        lib = ls.library(300, seed=seed + 20)
        r = ev.compare_to_baseline(lib, ls.true_fitness(lib), ls.confidence_scores(lib), k=10)
        gaps.append(r["model_spearman"] - r["baseline_spearman"])
    assert np.mean(gaps) > 0.1


def test_evaluate_beats_random_selection():
    # Averaged over seeds on purpose. A hit@10 computed from ten picks moves in steps
    # of 0.1 and swings between 0.10 and 0.30 seed to seed, so a single-seed assertion
    # is a coin flip dressed up as a test.
    #
    # Deliberately compared against *random*, not against the confidence proxy: at
    # moderate epistasis the proxy frequently wins on hit@10 (0.50 vs 0.20 on some
    # seeds) even where the model has the better rank correlation. Rank correlation
    # and top-k hit rate genuinely disagree here, and asserting the model wins both
    # would be asserting something false.
    rates = []
    for seed in range(5):
        ls = make_landscape(epistasis=0.5, seed=seed)
        ev = DesignEvaluator().fit(ls.sample_campaign(80, seed=seed + 1))
        lib = ls.library(300, seed=seed + 2)
        r = ev.compare_to_baseline(lib, ls.true_fitness(lib), ls.confidence_scores(lib), k=10)
        rates.append(r["model_hit_rate"])
    assert np.mean(rates) > 0.1  # 0.1 is random selection by construction


def test_rank_correlation_and_hit_rate_can_disagree():
    # Documents the finding above rather than leaving it as folklore: a model can rank
    # the whole library better while the baseline still lands more of the top-10. Both
    # numbers get reported because only one of them is what the buyer experiences.
    ls = make_landscape(epistasis=0.5, seed=1)
    ev = DesignEvaluator().fit(ls.sample_campaign(80, seed=2))
    lib = ls.library(300, seed=3)
    r = ev.compare_to_baseline(lib, ls.true_fitness(lib), ls.confidence_scores(lib), k=10)
    assert r["model_spearman"] > r["baseline_spearman"]
    assert r["model_hit_rate"] < r["baseline_hit_rate"]


def test_rank_is_sorted_and_complete():
    ls = make_landscape(seed=0)
    ev = DesignEvaluator().fit(ls.sample_campaign(60, seed=1))
    lib = ls.library(40, seed=2)
    ranked = ev.rank(lib, threshold=0.6)
    assert len(ranked) == len(lib)
    assert all(a.predicted >= b.predicted for a, b in zip(ranked, ranked[1:], strict=False))
    assert all(s.prob_above_threshold is not None for s in ranked)


def test_evaluator_rejects_a_campaign_too_small_to_split():
    ls = make_landscape(seed=0)
    with pytest.raises(ValueError, match="too small"):
        DesignEvaluator().fit(ls.sample_campaign(3, seed=1))


def test_top_k_hit_rate_bounds():
    scores = np.arange(100.0)
    truth = np.arange(100.0)
    assert top_k_hit_rate(scores, truth, k=10, quantile=0.9) == pytest.approx(1.0)
    with pytest.raises(ValueError, match="out of range"):
        top_k_hit_rate(scores, truth, k=0)


# ------------------------------------------------------------------- lown [Plan 5]


def test_lown_batch_beats_a_random_batch():
    # Same budget, same library. Averaged over seeds — a single 8-variant batch is
    # far too noisy to conclude anything from.
    gains = []
    for seed in range(5):
        ls = make_landscape(epistasis=0.5, seed=seed)
        cop = LowNCopilot().fit(ls.sample_campaign(48, seed=seed + 10))
        lib = ls.library(400, seed=seed + 20)
        picked = ls.true_fitness(cop.recommend(lib, k=8))
        rng = np.random.default_rng(seed)
        rand = ls.true_fitness([lib[int(i)] for i in rng.choice(len(lib), 8, replace=False)])
        gains.append(picked.mean() - rand.mean())
    assert np.mean(gains) > 0.0


def test_recommended_batch_is_diverse():
    # Greedy top-k EI returns near-duplicates, which wastes a round because they teach
    # nearly the same thing.
    ls = make_landscape(seed=0)
    cop = LowNCopilot().fit(ls.sample_campaign(48, seed=1))
    batch = cop.recommend(ls.library(400, seed=2), k=8, min_hamming=2)
    seqs = [b.sequence for b in batch]
    assert len(set(seqs)) == len(seqs)
    for i, a in enumerate(seqs):
        for b in seqs[i + 1 :]:
            assert sum(x != y for x, y in zip(a, b, strict=True)) >= 2


def test_recommend_requires_fit():
    ls = make_landscape(seed=0)
    with pytest.raises(RuntimeError, match="fit"):
        LowNCopilot().recommend(ls.library(10, seed=1))


def test_acquisition_is_non_negative():
    ls = make_landscape(seed=0)
    cop = LowNCopilot().fit(ls.sample_campaign(48, seed=1))
    assert np.all(cop.acquisition(ls.library(100, seed=2)) >= 0)


def test_lown_rejects_a_campaign_that_is_too_small():
    ls = make_landscape(seed=0)
    with pytest.raises(ValueError, match="at least 4"):
        LowNCopilot().fit(ls.sample_campaign(3, seed=1))


# ---------------------------------------------------------------- planner [Plan 9]


def test_planner_beats_a_random_campaign_on_the_same_budget():
    ls = make_landscape(epistasis=0.5, seed=0)
    lib = ls.library(500, seed=2)

    def oracle(vs):
        return ls.measure(vs, seed=len(vs) * 7)

    wins = 0
    for seed in range(4):
        seed_c = ls.sample_campaign(24, seed=seed + 30, campaign_id=f"s{seed}")
        planned = CampaignPlanner().run(seed_c, lib, oracle, rounds=2, batch_size=6)
        rand = random_campaign(lib, oracle, n=12, seed=seed)
        best_planned = ls.true_fitness(planned["acquired"]).max()
        best_random = ls.true_fitness(rand["acquired"]).max()
        wins += best_planned >= best_random
    assert wins >= 3  # allow one loss to noise; a coin flip would fail this


def test_planner_history_is_monotone():
    # Best-found can only improve as rounds accumulate.
    ls = make_landscape(seed=0)
    lib = ls.library(300, seed=2)
    res = CampaignPlanner().run(
        ls.sample_campaign(24, seed=1, campaign_id="s"),
        lib,
        lambda vs: ls.measure(vs, seed=len(vs)),
        rounds=3,
        batch_size=5,
    )
    bests = [h["best_acquired"] for h in res["history"]]
    assert all(a <= b for a, b in zip(bests, bests[1:], strict=False))
    assert len(res["acquired"]) == 15


def test_planner_never_reassays_a_variant():
    ls = make_landscape(seed=0)
    lib = ls.library(200, seed=2)
    res = CampaignPlanner().run(
        ls.sample_campaign(24, seed=1, campaign_id="s"),
        lib,
        lambda vs: ls.measure(vs, seed=len(vs)),
        rounds=3,
        batch_size=6,
    )
    ids = [v.variant_id for v in res["acquired"]]
    assert len(set(ids)) == len(ids)


def test_transfer_benefit_reports_both_arms():
    # Deliberately asserts structure, not lift. At M0 transfer is directionally
    # positive but noisy, and an *unrelated* prior shows a similar effect — i.e. most
    # of it is "more data", not transfer. Claiming a moat here would be dishonest.
    ls = make_landscape(epistasis=0.5, seed=0)
    lib = ls.library(300, seed=2)
    prior = ls.related(similarity=0.9, seed=11).sample_campaign(40, seed=9, campaign_id="p")
    out = transfer_benefit(
        ls.sample_campaign(12, seed=5, campaign_id="s"),
        lib,
        lambda vs: ls.measure(vs, seed=len(vs)),
        [prior],
        rounds=1,
        batch_size=6,
    )
    assert set(out) == {"with_priors", "without_priors", "lift"}
    assert out["lift"] == pytest.approx(out["with_priors"] - out["without_priors"])


def test_prior_campaigns_of_a_different_length_are_ignored():
    # Positional features can't align across targets of different sizes; silently
    # mis-aligning them would be worse than skipping.
    ls8 = make_landscape(length=8, seed=0)
    ls6 = make_landscape(length=6, seed=0)
    prior = ls6.sample_campaign(20, seed=3, campaign_id="p")
    lib = ls8.library(200, seed=2)
    res = CampaignPlanner(prior_campaigns=[prior]).run(
        ls8.sample_campaign(24, seed=1, campaign_id="s"),
        lib,
        lambda vs: ls8.measure(vs, seed=len(vs)),
        rounds=1,
        batch_size=5,
    )
    assert len(res["acquired"]) == 5
