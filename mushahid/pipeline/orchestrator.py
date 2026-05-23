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
from ali.generation.itinerary_generator import generate_itinerary, generate_itinerary_by_day
from ali.generation.output_parser import parse_itinerary
from ali.rag.explainer import explain_day, explain_itinerary
from shared.schemas import Itinerary

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
    query the seeded Pinecone corpus (hotels + restaurants + activities) for
    candidates at that destination, hard-filter for budget feasibility +
    avoid_list, then rank by the configurable activity policy. If retrieval
    or filtering fails, fall back to an empty pool — the LLM prompt is
    permissive enough to invent plausible venues in that case.
    """
    destination = _destination_from_query(user_profile)
    activities: list[Activity] = []
    try:
        from shreyas.retrieval.search import search_activities
        # top_k is the combined budget across hotels/restaurants/activities;
        # search_activities splits it internally (~15/40/45).
        activities = await search_activities(
            destination.city, destination.country or None, user_profile, top_k=40,
        )
    except Exception as e:
        logger.warning("Pinecone retrieval failed (%s) — LLM will invent venues", e)

    # Hard pre-ranking filter (budget feasibility + avoid_list) — drops
    # candidates that literally can't fit so the ranker doesn't waste
    # positive contributions on them. Every drop is logged.
    try:
        if user_profile.constraints and activities:
            from shreyas.ranking.filters import apply_activity_filters
            activities = apply_activity_filters(activities, user_profile.constraints)
    except Exception as e:
        logger.warning("activity filter failed (%s) — keeping unfiltered pool", e)

    # Rank the surviving candidates via the configurable activity policy.
    # search_activities doesn't return per-candidate Pinecone scores yet;
    # pass 0.0 retrieval scores and let other features carry the signal.
    try:
        if user_profile.constraints and activities:
            from shreyas.ranking.activity_ranker import rank_activities
            activities = rank_activities([(a, 0.0) for a in activities], user_profile, top_n=40)
    except Exception as e:
        logger.warning("activity ranking failed (%s) — keeping retrieval order", e)

    return destination, activities


async def _get_cotraveller_matches(user_profile: UserProfile):
    try:
        from shreyas.cotraveller.matching import get_top_matches
        from shreyas.retrieval.search import search_cotravellers
        candidates = await search_cotravellers(user_profile)
        return get_top_matches(user_profile, candidates)
    except Exception as e:
        logger.warning("cotraveller matching failed (%s) — returning no matches", e)
        return []


async def run_plan_trip_pipeline(user_profile: UserProfile) -> AsyncIterator[str]:
    step = "init"
    sentry_sdk.set_user({"id": user_profile.user_id})
    # Top of the funnel — every trip generation attempt fires this, so
    # trip_done / trip_done can be divided by it to get completion rate.
    try:
        from mushahid.monitoring import capture, EVENT_TRIP_PLAN_STARTED
        c = user_profile.constraints
        capture(user_profile.user_id, EVENT_TRIP_PLAN_STARTED, {
            "destination":   (c.destination_query if c else "") or "",
            "budget_usd":    (c.budget_usd if c else 0),
            "duration_days": ((c.end_date - c.start_date).days + 1) if (c and c.start_date and c.end_date) else None,
            "pace":          (c.pace.value if (c and c.pace) else None),
            "group_size":    (c.group_size if c else None),
        })
    except Exception:
        pass
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
        # Analytics — retrieval quality dashboards. activity_count == 0 means
        # Pinecone returned nothing for the destination (or filters dropped
        # everything) and the LLM had to invent venues. Track this so we can
        # see how often we're flying blind.
        try:
            from mushahid.monitoring import capture, EVENT_RETRIEVAL_DONE
            capture(user_profile.user_id, EVENT_RETRIEVAL_DONE, {
                "destination":    f"{destination.city}, {destination.country}",
                "activity_count": len(activities),
                "used_corpus":    len(activities) > 0,
            })
        except Exception:
            pass

        # Step 3 — Ranking (Shreyas — already done in retrieval; emit event)
        step = "ranking"
        yield format_event("ranking", {})
        yield format_event("ranked", {"top_destination": f"{destination.city}, {destination.country}"})

        # Step 4 — Itinerary generation (token streaming) + per-day explanation
        step = "generating"
        yield format_event("generating", {})
        days = []

        # Day-by-day streaming with inline explanation: as soon as each day's
        # JSON closes we run explain_day (parallel Haiku calls per activity)
        # and emit day_ready with why_this already populated. The user sees
        # Day 1 with its rationale within ~15-20s instead of waiting for all
        # days to stream AND a separate explanation pass to finish.
        async for day in generate_itinerary_by_day(user_profile, destination, activities):
            try:
                day = await explain_day(day, user_profile)
            except Exception as e:
                logger.warning("explain_day failed for day %s (%s) — emitting without why_this", day.day_number, e)
            days.append(day)
            yield format_event("day_ready", {"day": day.model_dump(mode="json")})

        if not days:
            raise RuntimeError("generator produced no days")

        itinerary = Itinerary(
            itinerary_id=f"itin_{uuid.uuid4().hex[:8]}",
            user_id=user_profile.user_id,
            destination=destination,
            days=days,
            total_budget_usd=sum((d.daily_cost_usd or 0) for d in days),
            notes=[],
            co_traveller_ids=[],
        )

        # Persist BEFORE validation/matching so the user can save it from the
        # UI as soon as the days are visible. If anything downstream fails or
        # hangs, the itinerary is still recoverable from Firestore.
        try:
            await write_itinerary(itinerary)
        except Exception as e:
            logger.warning("early write_itinerary failed: %s", e)

        # itinerary_generated carries the full payload now — the frontend uses
        # this to expose the Save button without waiting for the validation /
        # matching / done events at the end of the pipeline.
        yield format_event("itinerary_generated", {
            "itinerary": itinerary.model_dump(mode="json"),
            "days": len(itinerary.days),
        })

        # Step 6 — Validation (best-effort enhancement past this point)
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
            # Refinement may have modified the itinerary — rewrite to Firestore.
            try:
                await write_itinerary(itinerary)
            except Exception as e:
                logger.warning("post-refinement write_itinerary failed: %s", e)

        await write_itinerary_status(user_profile.user_id, "ready")
        yield format_event("validated", {"score": validation.score})

        # Step 7 — Co-traveller matching (Shreyas)
        step = "matching_cotravellers"
        yield format_event("matching_cotravellers", {})
        matches = await _get_cotraveller_matches(user_profile)
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
        # Analytics — pipeline-failure rate, broken down by step. Lets us see
        # which step fails most often (retrieval, generation, validation, …).
        try:
            from mushahid.monitoring import capture, EVENT_PIPELINE_ERROR
            capture(user_profile.user_id, EVENT_PIPELINE_ERROR, {
                "step":  step,
                "error": type(e).__name__,
            })
        except Exception:
            pass
        yield format_event("error", {
            "step": step,
            "message": f"{type(e).__name__} during {step}: {e}",
        })
