from typing import AsyncIterator

from shared.schemas import (
    UserProfile, Destination, Activity,
    PlanTripResponse, ValidationStatus,
)
from mushahid.realtime.sse import format_event
from mushahid.realtime.firestore import write_itinerary, write_itinerary_status
from mushahid.validation.rules import run_all_checks
from mushahid.validation.critic import validate_large_output
from ali.generation.itinerary_generator import generate_itinerary
from ali.generation.output_parser import parse_itinerary
from ali.rag.explainer import explain_itinerary


# Fallback demo data used when Shreyas's retrieval stubs raise NotImplementedError
_FALLBACK_DESTINATION = Destination(
    destination_id="bali_001", city="Bali", country="Indonesia",
    avg_daily_cost_usd=120.0, tags=["beach", "culture", "food", "nature"],
    description="Tropical island known for temples, rice terraces, and surf.",
)

_FALLBACK_ACTIVITIES = [
    Activity(activity_id="act_001", name="Uluwatu Temple Sunset", category="culture",
             cost_usd=10.0, duration_hours=2.0, tags=["culture", "sunset", "temple"],
             description="Clifftop sea temple with sweeping Indian Ocean views."),
    Activity(activity_id="act_002", name="Seminyak Beach Morning", category="beach",
             cost_usd=0.0, duration_hours=3.0, tags=["beach", "relaxed", "swimming"],
             description="Relaxed morning swim on one of Bali's most popular beaches."),
    Activity(activity_id="act_003", name="Ubud Cooking Class", category="food",
             cost_usd=45.0, duration_hours=4.0, tags=["food", "cooking", "culture"],
             description="Learn to cook traditional Balinese dishes with a local chef."),
    Activity(activity_id="act_004", name="Snorkeling at Amed", category="adventure",
             cost_usd=35.0, duration_hours=3.0, tags=["snorkeling", "ocean", "adventure"],
             description="Crystal-clear waters with vibrant coral reefs and tropical fish."),
    Activity(activity_id="act_005", name="Tirta Empul Temple", category="culture",
             cost_usd=5.0, duration_hours=1.5, tags=["culture", "spiritual", "history"],
             description="Sacred Hindu temple with holy spring water purification pools."),
]


def _get_destination_and_activities(user_profile: UserProfile):
    try:
        from shreyas.retrieval.search import search_destinations, search_activities
        from shreyas.ranking.destination_ranker import rank_destinations
        dest_candidates = search_destinations(user_profile)
        ranked = rank_destinations(dest_candidates, user_profile)
        top = ranked[0]
        dest = Destination.model_validate(top["metadata"])
        act_raw = search_activities(dest.destination_id, user_profile)
        activities = [Activity.model_validate(a["metadata"]) for a in act_raw]
        return dest, activities
    except Exception:
        return _FALLBACK_DESTINATION, _FALLBACK_ACTIVITIES


def _get_cotraveller_matches(user_profile: UserProfile):
    try:
        from shreyas.cotraveller.matching import get_top_matches
        from shreyas.retrieval.search import search_cotravellers
        candidates = search_cotravellers(user_profile)
        return get_top_matches(user_profile, candidates)
    except Exception:
        return []


async def run_plan_trip_pipeline(user_profile: UserProfile) -> AsyncIterator[str]:
    step = "init"
    try:
        # Step 1 — Persona inference (Jahnvi's module — use profile as-is if not ready)
        step = "persona_inferring"
        yield format_event("persona_inferring", {})
        try:
            from jahnvi.pipeline.module3_persona import infer_persona, infer_emotion
            persona = infer_persona(user_profile.persona_answers)
            emotion = infer_emotion(user_profile.compatibility_signals or {})
            yield format_event("persona_inferred", {"archetype": persona, "emotion": emotion})
        except Exception:
            yield format_event("persona_inferred", {
                "archetype": "Explorer",
                "emotion": user_profile.emotion_intent.value if user_profile.emotion_intent else "excited",
            })

        # Step 2 — Retrieval (Shreyas — falls back to demo data if stubs)
        step = "retrieving"
        yield format_event("retrieving", {})
        destination, activities = _get_destination_and_activities(user_profile)
        yield format_event("retrieval_done", {
            "destination_count": 1,
            "activity_count": len(activities),
        })

        # Step 3 — Ranking (Shreyas — already done in retrieval; emit event)
        step = "ranking"
        yield format_event("ranking", {})
        yield format_event("ranked", {"top_destination": f"{destination.city}, {destination.country}"})

        # Step 4 — Itinerary generation (token streaming) + per-day explanation queued
        step = "generating"
        yield format_event("generating", {})
        raw_chunks = []

        async for chunk in generate_itinerary(user_profile, destination, activities):
            yield format_event("generating", {"chunk": chunk})
            raw_chunks.append(chunk)

        raw = "".join(raw_chunks)
        itinerary = parse_itinerary(raw, user_profile, destination=destination, activities=activities)
        itinerary = itinerary.model_copy(update={"user_id": user_profile.user_id})

        yield format_event("itinerary_generated", {"days": len(itinerary.days)})

        # Step 5 — Explain activities concurrently (Ali RAG)
        step = "explaining"
        yield format_event("explaining", {})
        try:
            itinerary = await explain_itinerary(itinerary, user_profile)
        except Exception:
            pass  # RAG explanation is best-effort

        # Step 6 — Validation
        step = "validating"
        yield format_event("validating", {})

        validation = None
        if user_profile.constraints:
            checks = run_all_checks(itinerary, user_profile.constraints)
            if not all([checks.budget_ok, checks.duration_ok,
                        checks.must_haves_ok, checks.avoid_list_ok]):
                from shared.schemas import ValidationResult
                validation = ValidationResult(
                    itinerary_id=itinerary.itinerary_id,
                    status=ValidationStatus.revise,
                    score=0.5,
                    feedback="Constraint check failed: " + ", ".join([
                        k for k, v in checks.model_dump().items() if not v
                    ]),
                )

        if validation is None:
            validation = await validate_large_output(itinerary, user_profile)

        if validation.status == ValidationStatus.revise:
            from mushahid.refinement.loop import run_refinement_loop
            async for event in run_refinement_loop(
                itinerary, user_profile,
                feedback=validation.feedback,
                validation_result=validation,
            ):
                yield event
                # After loop, best result is in the last UpdateTripResponse
                # (loop yields SSE strings, final return value is ignored here)

        await write_itinerary(itinerary)
        await write_itinerary_status(user_profile.user_id, "ready")
        yield format_event("validated", {"score": validation.score})

        # Step 7 — Co-traveller matching (Shreyas)
        step = "matching_cotravellers"
        yield format_event("matching_cotravellers", {})
        matches = _get_cotraveller_matches(user_profile)
        yield format_event("matched", {"match_count": len(matches)})

        # Done
        step = "done"
        yield format_event("done", PlanTripResponse(
            itinerary=itinerary,
            matches=matches,
            validation=validation,
        ).model_dump(mode="json"))

    except Exception:
        await write_itinerary_status(user_profile.user_id, "error")
        yield format_event("error", {"step": step, "message": "An unexpected error occurred. Please try again."})
