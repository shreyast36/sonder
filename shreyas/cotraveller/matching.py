from shared.schemas import UserProfile, CoTravellerProfile, CoTravellerMatch


def score_compatibility(user_profile: UserProfile, candidate: CoTravellerProfile) -> CoTravellerMatch:
    """
    Score compatibility between a user and a co-traveller candidate.

    Signals to factor in (weights are your decision):
        - Shared interests (overlap between user tags and candidate interests)
        - Pace match (both relaxed, both packed, etc.)
        - Budget range overlap
        - Travel style fit (solo vs. couple vs. group)
        - Itinerary overlap (if user already has an itinerary generated)

    Expected input:
        user_profile = UserProfile(
            persona_answers=PersonaQuestionAnswers(food_interest=5, culture_interest=4, pace_preference="relaxed"),
            constraints=TripConstraints(budget_usd=2000, travel_style="couple")
        )
        candidate = CoTravellerProfile(
            profile_id="maya_001",
            display_name="Maya Sharma",
            interests=["food", "culture", "photography"],
            pace=PacePreference.relaxed,
            budget_style=BudgetStyle.mid_range
        )

    Expected output:
        CoTravellerMatch(
            profile=candidate,
            match_score=0.92,
            match_reasons=["Similar interests in food and culture", "Same travel pace", "Similar budget range"],
            compatibility_breakdown={"interests": 0.95, "pace": 1.0, "budget": 0.85}
        )
    """
    # TODO: compute per-signal scores, combine, build match_reasons from top signals
    raise NotImplementedError


def get_top_matches(
    user_profile: UserProfile,
    candidates: list[CoTravellerProfile],
    top_n: int = 3,
) -> list[CoTravellerMatch]:
    """
    Score all candidates and return the top_n sorted by match_score descending.

    Expected input:  50 candidate profiles from Pinecone search
    Expected output: 3 CoTravellerMatch objects, best match first
    """
    # TODO: score each candidate, sort, return top_n
    raise NotImplementedError


def regenerate_matches(
    user_profile: UserProfile,
    excluded_profile_ids: list[str],
    feedback: str = "",
    top_n: int = 3,
) -> list[CoTravellerMatch]:
    """
    Find a fresh batch of co-traveller matches, skipping already-shown profiles.
    Called when a user denies all current matches or explicitly asks for new ones.

    If feedback is provided (e.g. "someone more adventurous"), update the user's
    compatibility signals before re-querying Pinecone so the new batch reflects
    what the user actually wants — not just a different random slice.

    Expected input:
        user_profile         = UserProfile(...)
        excluded_profile_ids = ["maya_001", "raj_002", "sarah_003"]  # already shown
        feedback             = "I want someone more adventurous"      # optional

    Expected output:  3 new CoTravellerMatch objects, none in excluded_profile_ids

    Steps:
        1. If feedback provided: update_profile_from_feedback(user_profile, feedback)
           and re-embed travel_style_embedding (same as refinement loop Gap 2+3)
        2. search_cotravellers(user_profile) → new Pinecone query with updated embedding
        3. Filter out excluded_profile_ids from candidates
        4. get_top_matches(user_profile, remaining_candidates, top_n)
    """
    # TODO: optionally update profile signals from feedback
    # TODO: search_cotravellers(user_profile) — fresh Pinecone query
    # TODO: filter candidates where profile_id not in excluded_profile_ids
    # TODO: return get_top_matches(user_profile, filtered_candidates, top_n)
    raise NotImplementedError
