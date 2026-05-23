"""
Smoke tests for the ranking engine + features.

These don't try to assert exact scores — they assert invariants the engine
needs to preserve regardless of how the weights drift over time:
  - signatures matching gets a non-zero contribution from signature_proximity
  - final_score is always in [0, 1]
  - retrieval_score lands on RankedCandidate in its own slot
  - keyword-dense free text bumps small_thing salience
  - budget filter drops candidates whose daily cost exceeds the user's
"""

from __future__ import annotations

from datetime import date

from shared.schemas import (
    TripConstraints, PersonaQuestionAnswers, UserProfile,
    CoTravellerProfile, Destination, Activity,
    PacePreference, BudgetStyle, TravelStyle,
)


def _viewer(
    pace: PacePreference = PacePreference.relaxed,
    budget: BudgetStyle = BudgetStyle.mid_range,
    style: TravelStyle = TravelStyle.couple,
    small_thing: str = "",
    emotional_signature: str = "story_collector",
    top_interests: list[str] | None = None,
    budget_usd: float = 2000.0,
    days: int = 7,
) -> UserProfile:
    constraints = TripConstraints(
        destination_query="Lisbon, Portugal",
        start_date=date(2025, 6, 1),
        end_date=date(2025, 6, 1).replace(day=1) if days == 1 else date(2025, 6, days),
        budget_usd=budget_usd,
        group_size=2,
        who_travelling_with=style,
        pace=pace,
        social_role="place_finder",
        trip_feeling="story_collector",
        friction_response="pivot",
        ideal_atmosphere="lively_chaos",
        avoid_list=[],
    )
    return UserProfile(
        user_id="test_user",
        display_name="Tester",
        constraints=constraints,
        persona_answers=PersonaQuestionAnswers(small_thing=small_thing),
        compatibility_signals={
            "top_interests": top_interests or ["food_drink", "culture_history"],
            "emotional_signature": emotional_signature,
        },
    )


def _candidate_profile(
    profile_id: str = "ct_1",
    pace: PacePreference = PacePreference.relaxed,
    budget: BudgetStyle = BudgetStyle.mid_range,
    style: TravelStyle = TravelStyle.couple,
    interests: list[str] | None = None,
    emotional_signature: str = "story_collector",
    persona_answers: dict | None = None,
) -> CoTravellerProfile:
    return CoTravellerProfile(
        profile_id=profile_id,
        display_name="Other",
        age=28,
        location="Lisbon, Portugal",
        archetype="Story Collector",
        interests=interests or ["food_drink", "culture_history"],
        pace=pace,
        budget_style=budget,
        travel_style=style,
        compatibility_signals={"emotional_signature": emotional_signature},
        persona_answers=persona_answers or {
            "social_role": "place_finder",
            "trip_feeling": "story_collector",
            "friction_response": "pivot",
            "ideal_atmosphere": "lively_chaos",
            "small_thing": "",
        },
    )


# ── Engine + features ────────────────────────────────────────────────────────


def test_final_score_in_unit_interval():
    """Engine clipping holds whatever the inputs are."""
    from shreyas.ranking.engine import rank
    from shreyas.ranking.policies import load_policy

    viewer = _viewer()
    candidate = _candidate_profile()
    policy = load_policy("cotraveller")

    ranked = rank(viewer, [(candidate, 0.85)], policy)
    assert len(ranked) == 1
    assert 0.0 <= ranked[0].final_score <= 1.0


def test_retrieval_score_lives_in_own_slot():
    """retrieval_score is set from the tuple and stored on RankedCandidate
    independently of feature_scores."""
    from shreyas.ranking.engine import rank
    from shreyas.ranking.policies import load_policy

    viewer = _viewer()
    candidate = _candidate_profile()
    policy = load_policy("cotraveller")

    ranked = rank(viewer, [(candidate, 0.73)], policy)
    assert ranked[0].retrieval_score == 0.73


def test_signature_match_scores_higher_than_mismatch():
    """signature_proximity is identity (1.0/0.0) — a same-signature
    candidate should outscore a different-signature one when everything
    else is equal."""
    from shreyas.ranking.engine import rank
    from shreyas.ranking.policies import load_policy

    viewer = _viewer(emotional_signature="story_collector")
    matched = _candidate_profile(profile_id="match", emotional_signature="story_collector")
    different = _candidate_profile(profile_id="diff", emotional_signature="quiet_observer")
    policy = load_policy("cotraveller")

    ranked = rank(viewer, [(matched, 0.5), (different, 0.5)], policy)
    matched_score    = next(rc.final_score for rc in ranked if rc.candidate.profile_id == "match")
    different_score  = next(rc.final_score for rc in ranked if rc.candidate.profile_id == "diff")
    assert matched_score > different_score


def test_explanation_summary_returns_snippets():
    from shreyas.ranking.engine import rank
    from shreyas.ranking.policies import load_policy

    viewer = _viewer()
    candidate = _candidate_profile()
    policy = load_policy("cotraveller")
    ranked = rank(viewer, [(candidate, 0.5)], policy)

    snippets = ranked[0].explanation_summary(top_k=3)
    assert isinstance(snippets, list)
    assert len(snippets) <= 3
    assert all(isinstance(s, str) for s in snippets)


# ── Salience ────────────────────────────────────────────────────────────────


def test_salience_distribution_sums_to_one():
    """No matter the inputs, salience normalises to a distribution."""
    from shreyas.ranking.salience import compute_answer_salience

    viewer = _viewer(small_thing="i love quiet morning markets and slow espresso")
    dist = compute_answer_salience(viewer.persona_answers, viewer.constraints)
    total = sum(dist.values())
    assert abs(total - 1.0) < 1e-6
    # Five questions tracked.
    assert set(dist.keys()) == {"social_role", "trip_feeling", "friction_response", "ideal_atmosphere", "small_thing"}


def test_salience_fallback_to_uniform_when_no_signal():
    """User who answered nothing → uniform 1/5 distribution (no zero-multiply)."""
    from shreyas.ranking.salience import compute_answer_salience

    empty_viewer = UserProfile(
        user_id="u",
        display_name="u",
        constraints=TripConstraints(),
        persona_answers=PersonaQuestionAnswers(small_thing=""),
    )
    dist = compute_answer_salience(empty_viewer.persona_answers, empty_viewer.constraints)
    assert all(abs(v - 0.2) < 1e-6 for v in dist.values())


# ── Budget filter ───────────────────────────────────────────────────────────


def test_destination_filter_drops_over_budget():
    """daily_budget = 2000/7 ≈ 285. Destination at 500/day should drop."""
    from shreyas.ranking.filters import apply_destination_filters

    viewer = _viewer(budget_usd=2000.0, days=7)
    affordable = Destination(
        destination_id="d_ok",
        city="Lisbon",
        country="Portugal",
        avg_daily_cost_usd=100.0,
        tags=[],
        description="",
    )
    too_expensive = Destination(
        destination_id="d_bad",
        city="Monaco",
        country="Monaco",
        avg_daily_cost_usd=500.0,
        tags=[],
        description="",
    )
    kept = apply_destination_filters([affordable, too_expensive], viewer.constraints)
    ids = {d.destination_id for d in kept}
    assert "d_ok" in ids
    assert "d_bad" not in ids


def test_activity_filter_drops_over_budget():
    from shreyas.ranking.filters import apply_activity_filters

    viewer = _viewer(budget_usd=700.0, days=7)  # daily ≈ 100
    cheap = Activity(
        activity_id="a_ok",
        name="Walk",
        category="walking",
        cost_usd=20.0,
        duration_hours=2.0,
        tags=[],
        description="",
    )
    pricey = Activity(
        activity_id="a_bad",
        name="Helicopter tour",
        category="tour",
        cost_usd=500.0,
        duration_hours=1.0,
        tags=[],
        description="",
    )
    kept = apply_activity_filters([cheap, pricey], viewer.constraints)
    ids = {a.activity_id for a in kept}
    assert "a_ok" in ids
    assert "a_bad" not in ids


def test_activity_filter_drops_avoid_list_tags():
    from shreyas.ranking.filters import apply_activity_filters

    viewer = _viewer(budget_usd=2000.0, days=7)
    viewer.constraints.avoid_list.append("nightclub")
    nightclub = Activity(
        activity_id="a_bad",
        name="Lux Frágil",
        category="nightlife",
        cost_usd=20.0,
        duration_hours=4.0,
        tags=["nightclub"],
        description="",
    )
    kept = apply_activity_filters([nightclub], viewer.constraints)
    assert kept == []


# ── Per-user weight override path ───────────────────────────────────────────


def test_user_weights_override_policy_defaults():
    """When compatibility_signals.ranker_weights[surface] is set, the engine
    uses those instead of the policy defaults."""
    from shreyas.ranking.engine import rank
    from shreyas.ranking.policies import load_policy

    viewer = _viewer()
    # Heavily weight signature proximity, zero everything else (renormalised
    # to keep the math sane).
    viewer.compatibility_signals["ranker_weights"] = {
        "cotraveller": {
            "pinecone_passthrough":               0.05,
            "salience_weighted_question_overlap": 0.05,
            "signature_proximity":                0.70,
            "pace_ordinal_fit":                   0.05,
            "budget_ordinal_fit":                 0.05,
            "style_match":                        0.10,
        },
    }

    matched   = _candidate_profile(profile_id="match",  emotional_signature="story_collector")
    different = _candidate_profile(profile_id="diff",   emotional_signature="quiet_observer")
    policy = load_policy("cotraveller")
    ranked = rank(viewer, [(matched, 0.5), (different, 0.5)], policy)

    # signature_proximity weight is dominant — the gap between matched
    # and different should reflect that.
    matched_rc   = next(rc for rc in ranked if rc.candidate.profile_id == "match")
    different_rc = next(rc for rc in ranked if rc.candidate.profile_id == "diff")
    assert matched_rc.final_score - different_rc.final_score > 0.4
