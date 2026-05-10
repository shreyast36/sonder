from typing import AsyncIterator
from shared.schemas import (
    Itinerary, UserProfile, ValidationResult, ValidationStatus,
    ActivityFeedback,
)
from shared.config import MAX_REFINEMENT_ATTEMPTS
from mushahid.realtime.sse import format_event
from mushahid.realtime.firestore import write_itinerary, update_user_profile
from mushahid.validation.critic import validate_large_output
from mushahid.validation.rules import run_all_checks
from ali.generation.itinerary_generator import generate_refined_itinerary
from ali.generation.output_parser import parse_itinerary
from ali.vector.embeddings import build_refined_query, embed_text


async def run_refinement_loop(
    itinerary: Itinerary,
    user_profile: UserProfile,
    feedback: str,
    validation_result: ValidationResult,
    activity_feedback: list[ActivityFeedback] | None = None,
) -> AsyncIterator[str]:
    best_itinerary = itinerary
    best_validation = validation_result

    # Merge per-activity feedback into the feedback string
    if activity_feedback:
        act_lines = "; ".join(
            f"{af.activity_id} ({af.action})" + (f": {af.reason}" if af.reason else "")
            for af in activity_feedback
        )
        feedback = f"{feedback} | Activity feedback: {act_lines}".strip(" |")

    for attempt in range(1, MAX_REFINEMENT_ATTEMPTS + 1):
        # Re-embed with updated signals + feedback
        try:
            refined_query = build_refined_query(user_profile, feedback)
            user_profile = user_profile.model_copy(update={
                "travel_style_embedding": await embed_text(refined_query)
            })
            await update_user_profile(user_profile.user_id, {
                "travel_style_embedding": user_profile.travel_style_embedding,
                "compatibility_signals": user_profile.compatibility_signals,
            })
        except Exception:
            pass  # embedding update is best-effort

        # Re-generate with feedback baked in
        combined_feedback = (
            f"{feedback}\n\nValidator feedback: {best_validation.feedback}"
        )
        if best_validation.improvement_suggestions:
            combined_feedback += "\nSuggestions: " + "; ".join(
                best_validation.improvement_suggestions
            )

        try:
            chunks = []
            async for chunk in generate_refined_itinerary(best_itinerary, combined_feedback, best_validation):
                chunks.append(chunk)
            raw = "".join(chunks)
            new_itinerary = parse_itinerary(
                raw, user_profile,
                destination=itinerary.destination,
                activities=[ia.activity for day in itinerary.days for ia in day.activities],
            )
        except Exception:
            new_itinerary = best_itinerary

        # Re-validate
        try:
            if user_profile.constraints:
                checks = run_all_checks(new_itinerary, user_profile.constraints)
                if not checks.budget_ok or not checks.must_haves_ok or not checks.avoid_list_ok:
                    new_validation = ValidationResult(
                        itinerary_id=new_itinerary.itinerary_id,
                        status=ValidationStatus.revise,
                        score=0.5,
                        feedback="Constraint check failed after regeneration.",
                        improvement_suggestions=[],
                    )
                else:
                    new_validation = await validate_large_output(new_itinerary, user_profile)
            else:
                new_validation = await validate_large_output(new_itinerary, user_profile)
        except Exception:
            new_validation = ValidationResult(
                itinerary_id=new_itinerary.itinerary_id,
                status=ValidationStatus.revise,
                score=0.0,
                feedback="Validation error — flagging for revision.",
            )

        if new_validation.score > best_validation.score:
            best_itinerary = new_itinerary
            best_validation = new_validation

        await write_itinerary(best_itinerary)
        yield format_event("revision", {
            "attempt": attempt,
            "score": new_validation.score,
            "reason": new_validation.feedback,
        })

        if best_validation.status == ValidationStatus.approved:
            break

    # Yield the final best result so the orchestrator can pick it up
    yield format_event("refinement_result", {
        "itinerary": best_itinerary.model_dump(mode="json"),
        "validation": best_validation.model_dump(mode="json"),
        "refinement_attempts": attempt,
        "reached_max_attempts": best_validation.status != ValidationStatus.approved,
    })
