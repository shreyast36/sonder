import asyncio
from typing import AsyncIterator
from shared.schemas import UserProfile, PlanTripResponse
from mushahid.realtime.sse import format_event


async def run_plan_trip_pipeline(user_profile: UserProfile) -> AsyncIterator[str]:
    """
    Full pipeline orchestrator. Runs all modules in sequence and streams SSE events.
    Called by mushahid/routes/plan_trip.py → wrapped in stream_pipeline_events().

    SSE event sequence:
        "persona_inferring" → "persona_inferred"   (Jahnvi — module3_persona)
        "retrieving"        → "retrieval_done"      (Shreyas — search)
        "ranking"           → "ranked"              (Shreyas — ranking)
        "generating"        → token chunks          (Ali — itinerary_generator, Gap 1)
        "day_ready"                                  (Ali — per-day as each day completes, Gap 4)
        "itinerary_generated"
        "explaining"                                 (Ali — explain_day per day, concurrent, Gap 4)
        "validating"        → "validated"           (Mushahid — rules + LLM critic)
        "revision"                                   (Mushahid — refinement loop, may repeat)
        "matching_cotravellers" → "matched"          (Shreyas — cotraveller search)
        "done"                                       (full PlanTripResponse payload)
    """
    # Step 1 — Persona inference
    yield format_event("persona_inferring", {})
    # TODO: persona = infer_persona(user_profile.persona_answers)
    # TODO: emotion = infer_emotion(signals)
    # TODO: user_profile.compatibility_signals = build_compatibility_signals(user_profile)
    # TODO: user_profile.travel_style_embedding = build_travel_style_embedding(user_profile)
    yield format_event("persona_inferred", {})  # TODO: {"archetype": ..., "emotion": ...}

    # Step 2 — Retrieval
    yield format_event("retrieving", {})
    # TODO: dest_candidates = search_destinations(user_profile)
    # TODO: activity_candidates = search_activities(top_destination_id, user_profile)
    yield format_event("retrieval_done", {})  # TODO: {"destination_count": n, "activity_count": m}

    # Step 3 — Ranking
    yield format_event("ranking", {})
    # TODO: ranked_destinations = rank_destinations(dest_candidates, user_profile)
    # TODO: ranked_activities   = rank_activities(activity_candidates, user_profile)
    yield format_event("ranked", {})  # TODO: {"top_destination": city}

    # Steps 4+5 — Itinerary generation (token streaming) + per-day explanation (Gap 1 + Gap 4)
    #
    # Gap 1: every token chunk is forwarded immediately as a "generating" SSE event so the
    # frontend can render text appearing in real time — do NOT buffer and send at the end.
    #
    # Gap 4: as each ItineraryDay is parsed complete from the token stream, immediately
    # call explain_day() for that day without waiting for all days to finish. Use
    # generate_itinerary_by_day() which yields ItineraryDay objects one at a time.
    # Explanation tasks for each day are launched concurrently with asyncio.gather.
    yield format_event("generating", {})
    days = []
    explanation_tasks = []
    # TODO: async for day in generate_itinerary_by_day(user_profile, destination, ranked_activities):
    #           yield format_event("generating", {"chunk": day.raw_tokens})   # Gap 1: forward tokens
    #           yield format_event("day_ready", {"day_number": day.day_number, "theme": day.theme})
    #           explanation_tasks.append(explain_day(day, user_profile))      # Gap 4: start immediately
    #           days.append(day)
    yield format_event("itinerary_generated", {})

    yield format_event("explaining", {})
    # TODO: explained_days = await asyncio.gather(*explanation_tasks)         # Gap 4: all run concurrently
    # TODO: itinerary.days = list(explained_days)

    # Step 6 — Validation + refinement loop
    yield format_event("validating", {})
    # TODO: constraint_check = run_all_checks(itinerary, user_profile.constraints)
    # TODO: validation = await validate_with_llm(itinerary, user_profile)
    # TODO: if validation.status == ValidationStatus.revise:
    #           async for event in run_refinement_loop(itinerary, user_profile, validation):
    #               yield event   # forwards "revision" events with live Firestore updates
    yield format_event("validated", {})  # TODO: {"score": validation.score}

    # Step 7 — Co-traveller matching
    yield format_event("matching_cotravellers", {})
    # TODO: ct_candidates = search_cotravellers(user_profile)
    # TODO: matches = get_top_matches(user_profile, ct_candidates)
    yield format_event("matched", {})  # TODO: {"match_count": len(matches)}

    # Final — done
    # TODO: yield format_event("done", PlanTripResponse(...).model_dump())
    raise NotImplementedError
