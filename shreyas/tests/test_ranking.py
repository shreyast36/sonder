import pytest
from shreyas.ranking.destination_ranker import rank_destinations, score_destination
from shreyas.ranking.activity_ranker import rank_activities, score_activity


# ── score_destination — stub ──────────────────────────────────────────────────

def test_score_destination_stub(destination, user_profile):
    with pytest.raises(NotImplementedError):
        score_destination(destination, user_profile, pinecone_score=0.91)
    # TODO: returns float 0.0–1.0
    # Suggested weights: 60% pinecone_score, 20% budget fit, 20% tag-interest bonus


def test_rank_destinations_stub(destination, user_profile):
    candidates = [(destination, 0.91)]
    with pytest.raises(NotImplementedError):
        rank_destinations(candidates, user_profile)
    # TODO: returns list[Destination] sorted by final score, descending


def test_rank_destinations_respects_budget_stub(destination, user_profile):
    # destination.avg_daily_cost_usd=120, constraints.budget_usd=2000 (7-day trip → 840 budget)
    # 120/day * 7 days = 840 → within budget
    with pytest.raises(NotImplementedError):
        rank_destinations([(destination, 0.91)], user_profile)
    # TODO: destinations that blow the budget should score lower, not be hard-filtered


# ── score_activity — stub ─────────────────────────────────────────────────────

def test_score_activity_stub(activity, user_profile):
    with pytest.raises(NotImplementedError):
        score_activity(activity, user_profile, pinecone_score=0.85)
    # TODO: returns float 0.0–1.0; culture tag should boost score for culture_interest=4


def test_rank_activities_stub(activity, user_profile):
    candidates = [(activity, 0.85)]
    with pytest.raises(NotImplementedError):
        rank_activities(candidates, user_profile)
    # TODO: returns list[Activity] sorted by final score, descending
