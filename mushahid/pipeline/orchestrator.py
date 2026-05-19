import logging
import uuid
from typing import AsyncIterator

import sentry_sdk

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

logger = logging.getLogger(__name__)


def _destination_from_query(user_profile: UserProfile) -> Destination:
    """
    Build a Destination from the user's typed destination_query.
    Used until Shreyas's Pinecone retrieval wires in a real candidate list.
    The LLM generator can produce real activities for any city/country pair.
    """
    c = user_profile.constraints
    query = (c.destination_query if c else "").strip()
    if not query:
        query = (c.destination_type if c else "").strip() or "your destination"

    # Heuristic city/country split: "Tokyo, Japan" → city=Tokyo country=Japan.
    if "," in query:
        city, country = [p.strip() for p in query.split(",", 1)]
    else:
        city, country = query, ""

    return Destination(
        destination_id=f"user_dest_{uuid.uuid4().hex[:6]}",
        city=city or "your destination",
        country=country or "",
        avg_daily_cost_usd=0.0,
        tags=[],
        description=f"Trip destination as entered by the user: {query}",
    )


async def _get_destination_and_activities(user_profile: UserProfile):
    """
    Use the user's typed destination as the authoritative city/country, then
    query Pinecone's seeded 'activities' namespace for corpus-grounded
    candidates at that destination. If retrieval fails or returns nothing,
    fall back to an empty activities list — the LLM prompt is permissive
    enough to invent plausible activities in that case.
    """
    destination = _destination_from_query(user_profile)
    activities: list[Activity] = []
    try:
        from shreyas.retrieval.search import search_activities
        activities = await search_activities(
            destination.city, destination.country or None, user_profile, top_k=25,
        )
        logger.info("Pinecone returned %d activities for %s, %s",
                    len(activities), destination.city, destination.country or "—")
    except Exception as e:
        logger.warning("Pinecone activity retrieval failed (%s) — LLM will invent activities", e)
    return destination, activities


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
    sentry_sdk.set_user({"id": user_profile.user_id})
    try:
        # Step 1 — Persona inference (Jahnvi's module — use profile as-is if not ready)
        step = "persona_inferring"
        yield format_event("persona_inferring", {})
        try:
            from jahnvi.pipeline.module3_persona import infer_persona, infer_emotion
            persona = await infer_persona(user_profile.constraints, user_profile.persona_answers)
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
        destination, activities = await _get_destination_and_activities(user_profile)
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

        from mushahid.monitoring import capture
        capture(user_profile.user_id, "trip_planned", {
            "destination": f"{destination.city}, {destination.country}",
            "budget_usd": itinerary.total_budget_usd,
            "days": len(itinerary.days),
            "match_count": len(matches),
            "validation_score": validation.score,
        })

    except Exception as e:
        sentry_sdk.set_tag("pipeline_step", step)
        sentry_sdk.capture_exception(e)
        logger.error("plan-trip pipeline failed at step=%s: %s", step, e, exc_info=True)
        await write_itinerary_status(user_profile.user_id, "error")
        yield format_event("error", {
            "step": step,
            "message": f"{type(e).__name__} during {step}: {e}",
        })
