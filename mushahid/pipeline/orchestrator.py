from typing import AsyncIterator
from shared.schemas import UserProfile, PlanTripResponse
from mushahid.realtime.sse import format_event


async def run_plan_trip_pipeline(user_profile: UserProfile) -> AsyncIterator[str]:
    """
    Full pipeline orchestrator. Runs all 6 modules in sequence and streams SSE events.
    This is called by mushahid/routes/plan_trip.py.

    Steps and events emitted:
        1. Jahnvi's module3_persona   → "persona_inferring" → "persona_inferred"
        2. Shreyas's search           → "retrieving"        → "retrieval_done"
        3. Shreyas's ranking          → "ranking"           → "ranked"
        4. Ali's itinerary_generator  → "generating"        → "itinerary_generated"
        5. Ali's explainer            → "explaining"
        6. Mushahid's validation      → "validating"
              if REVISE → trigger refinement loop → "revision" (repeat up to MAX_REFINEMENT_ATTEMPTS)
           → "validated"
        7. Shreyas's matching         → "matching_cotravellers" → "matched"
        8. Final                      → "done" with full PlanTripResponse

    Starter structure:
    """
    # Step 1 — Persona inference
    yield format_event("persona_inferring", {})
    # TODO: persona = infer_persona(user_profile.persona_answers)
    # TODO: emotion = infer_emotion(signals)
    # TODO: user_profile.compatibility_signals = build_compatibility_signals(user_profile)
    # TODO: user_profile.travel_style_embedding = build_travel_style_embedding(user_profile)
    yield format_event("persona_inferred", {})  # TODO: include archetype + emotion in payload

    # Step 2 — Retrieval
    yield format_event("retrieving", {})
    # TODO: dest_candidates = search_destinations(user_profile)
    # TODO: activity_candidates = search_activities(top_destination_id, user_profile)
    yield format_event("retrieval_done", {})  # TODO: include counts in payload

    # Step 3 — Ranking
    yield format_event("ranking", {})
    # TODO: ranked_destinations = rank_destinations(dest_candidates, user_profile)
    # TODO: ranked_activities   = rank_activities(activity_candidates, user_profile)
    yield format_event("ranked", {})  # TODO: include top destination name

    # Step 4 — Itinerary generation (streaming)
    yield format_event("generating", {})
    # TODO: async for chunk in generate_itinerary(user_profile, destination, activities): yield chunk
    yield format_event("itinerary_generated", {})

    # Step 5 — RAG explanations
    yield format_event("explaining", {})
    # TODO: itinerary = await explain_itinerary(itinerary, user_profile)

    # Step 6 — Validation + refinement loop
    yield format_event("validating", {})
    # TODO: constraint_check = run_all_checks(itinerary, user_profile.constraints)
    # TODO: validation = await validate_with_llm(itinerary, user_profile)
    # TODO: if validation.status == ValidationStatus.revise: run refinement loop, emit "revision" events
    yield format_event("validated", {})  # TODO: include score

    # Step 7 — Co-traveller matching
    yield format_event("matching_cotravellers", {})
    # TODO: ct_candidates = search_cotravellers(user_profile)
    # TODO: matches = get_top_matches(user_profile, ct_candidates)
    yield format_event("matched", {})  # TODO: include match count

    # Final — done
    # TODO: yield format_event("done", PlanTripResponse(...).model_dump())
    raise NotImplementedError
