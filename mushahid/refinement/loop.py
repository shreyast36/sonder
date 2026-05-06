from shared.schemas import Itinerary, UserProfile, ValidationResult, UpdateTripResponse
from shared.config import MAX_REFINEMENT_ATTEMPTS


async def run_refinement_loop(
    itinerary: Itinerary,
    user_profile: UserProfile,
    feedback: str,
    validation_result: ValidationResult,
) -> UpdateTripResponse:
    """
    Closed-loop regeneration. Iterates up to MAX_REFINEMENT_ATTEMPTS times until
    the validator approves or max attempts is reached.

    Loop — one iteration:
        1. [Gap 3] Update user profile signals from feedback text:
               user_profile = update_profile_from_feedback(user_profile, feedback)
               This updates compatibility_signals and re-embeds travel_style_embedding
               so the new signal reflects what the user actually wants.
               Write updated profile back to Firestore so future sessions are warm.

        2. [Gap 2] Re-embed with updated signals before re-querying Pinecone:
               refined_query = build_refined_query(user_profile, feedback)
               new_embedding = embed_text(refined_query)
               user_profile.travel_style_embedding = new_embedding
               Re-run search_destinations() + search_activities() with the new embedding —
               not just re-prompting the generator with the same retrieved candidates.

        3. Re-rank the new candidates (Shreyas ranking with updated profile)

        4. Re-generate itinerary (Ali generator, feedback + validation issues in prompt)

        5. Re-validate (rules → LLM critic)

        6. Write updated itinerary to Firestore after every attempt (live UI update)

        7. Yield "revision" SSE event with attempt number so frontend shows progress

        8. If approved → break. If max attempts reached → return best result so far.

    Expected input:
        itinerary         = Itinerary(...)
        user_profile      = UserProfile(...)
        feedback          = "I want more free time each day"
        validation_result = ValidationResult(status=REVISE, feedback="Too many activities on Day 3")

    Expected output (approved):
        UpdateTripResponse(
            itinerary             = Itinerary(...),
            validation            = ValidationResult(status=approved, score=0.96),
            refinement_attempts   = 2,
            reached_max_attempts  = False
        )

    Expected output (max attempts hit — return best result, do not raise):
        UpdateTripResponse(
            itinerary             = Itinerary(...),  # best itinerary seen across all attempts
            validation            = ValidationResult(status=revise, score=0.71),
            refinement_attempts   = MAX_REFINEMENT_ATTEMPTS,
            reached_max_attempts  = True             # frontend shows soft warning to user
        )
    """
    # TODO: for attempt in range(MAX_REFINEMENT_ATTEMPTS):
    #
    #   Gap 3 — update profile from feedback (call before re-embedding)
    #   user_profile = update_profile_from_feedback(user_profile, feedback)
    #   await update_user_profile(user_profile.user_id, user_profile.model_dump())
    #
    #   Gap 2 — re-embed with updated signals + feedback text
    #   refined_query = build_refined_query(user_profile, feedback)
    #   user_profile.travel_style_embedding = embed_text(refined_query)
    #
    #   Re-rank with updated profile
    #   dest_candidates = search_destinations(user_profile)
    #   ranked_destinations = rank_destinations(dest_candidates, user_profile)
    #   ranked_activities   = rank_activities(..., user_profile)
    #
    #   Re-generate with feedback baked into prompt
    #   itinerary = await generate_itinerary(user_profile, destination, ranked_activities, feedback=feedback)
    #
    #   Re-validate
    #   validation = await validate_with_llm(itinerary, user_profile)
    #   await write_itinerary(itinerary)        # live Firestore update
    #   yield format_event("revision", {"attempt": attempt + 1, "score": validation.score})
    #
    #   if validation.status == ValidationStatus.approved: break
    raise NotImplementedError
