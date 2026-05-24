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
from ali.generation.itinerary_generator import (
    generate_refined_itinerary, generate_refined_days,
    stream_refined_itinerary_by_day, stream_refined_days_by_day,
)
from ali.generation.output_parser import parse_itinerary
from ali.vector.embeddings import build_refined_query, embed_text


async def stream_single_revision(
    itinerary: Itinerary,
    user_profile: UserProfile,
    feedback: str,
    seed_validation: ValidationResult,
    *,
    activity_feedback: list[ActivityFeedback] | None = None,
    target_day_numbers: list[int] | None = None,
    scope: str = "large",
    classifier_summary: str = "",
) -> AsyncIterator[str]:
    """Streaming version of `run_single_revision` — yields SSE-formatted
    events so the frontend can splice in revised days as soon as the LLM
    finishes each one, instead of waiting on a 60s POST.

    Event sequence:
      revising      → start, with scope / target_days / hint copy
      day_revised   → one per day as it parses (frontend splices into UI)
      validating    → all days streamed, running validator
      revision_done → final itinerary + validation + dropped/added titles
      revision_failed → on any unrecoverable error (with message)

    Caller (route) is responsible for:
      - building feedback (with PRESERVE / dedupe / FOCUS hints)
      - writing revision_history + ranker weight delta
      - persisting the final itinerary

    This function persists the regenerated itinerary itself via
    write_itinerary at the end (same as the non-streaming variant) so
    the route's later model_copy with history fields still finds the
    latest doc.
    """
    # Merge per-activity feedback into the feedback string (same as the loop).
    if activity_feedback:
        act_lines = "; ".join(
            f"{af.activity_id} ({af.action})" + (f": {af.reason}" if af.reason else "")
            for af in activity_feedback
        )
        feedback = f"{feedback} | Activity feedback: {act_lines}".strip(" |")

    combined_feedback = f"{feedback}\n\nValidator feedback: {seed_validation.feedback}"
    if seed_validation.improvement_suggestions:
        combined_feedback += "\nSuggestions: " + "; ".join(
            seed_validation.improvement_suggestions
        )

    use_targeted = bool(target_day_numbers)
    hint = (
        f"Rewriting day {', '.join(str(d) for d in target_day_numbers)}…"
        if use_targeted else "Rewriting the trip…"
    )
    yield format_event("revising", {
        "scope": scope,
        "target_days": list(target_day_numbers or []),
        "hint": hint,
        "summary": classifier_summary[:160] if classifier_summary else "",
    })

    # ── Stream the regen, yield each day as it parses ─────────────────
    revised_day_map: dict[int, "ItineraryDay"] = {}  # noqa: F821
    last_raw = ""
    try:
        if use_targeted:
            day_stream = stream_refined_days_by_day(
                itinerary, target_day_numbers, combined_feedback, seed_validation,
            )
        else:
            day_stream = stream_refined_itinerary_by_day(
                itinerary, combined_feedback, seed_validation,
            )

        async for day_obj, raw in day_stream:
            last_raw = raw
            revised_day_map[day_obj.day_number] = day_obj
            yield format_event("day_revised", {
                "day_number": day_obj.day_number,
                "day": day_obj.model_dump(mode="json"),
            })
    except Exception as e:
        yield format_event("revision_failed", {
            "message": f"Regeneration failed — please try again. ({type(e).__name__})",
        })
        return

    # ── Stitch the result ─────────────────────────────────────────────
    if not revised_day_map:
        # Streaming detector found nothing — try a fallback whole-buffer
        # parse so a JSON-fenced or odd-key-order response still works.
        if last_raw.strip():
            try:
                whole = parse_itinerary(
                    last_raw, user_profile,
                    destination=itinerary.destination,
                    activities=[ia.activity for day in itinerary.days for ia in day.activities],
                )
                for d in whole.days:
                    revised_day_map[d.day_number] = d
                    yield format_event("day_revised", {
                        "day_number": d.day_number,
                        "day": d.model_dump(mode="json"),
                    })
            except Exception:
                pass

    if not revised_day_map:
        yield format_event("revision_failed", {
            "message": "Model returned no revised days — please try again.",
        })
        return

    new_days = [revised_day_map.get(d.day_number, d) for d in itinerary.days]
    revised = itinerary.model_copy(update={
        "days": new_days,
        "itinerary_id": itinerary.itinerary_id,  # preserve id
    })

    # ── Validate ──────────────────────────────────────────────────────
    yield format_event("validating", {})
    try:
        if user_profile.constraints:
            checks = run_all_checks(revised, user_profile.constraints)
            if not checks.budget_ok or not checks.must_haves_ok or not checks.avoid_list_ok:
                validation = ValidationResult(
                    itinerary_id=revised.itinerary_id,
                    status=ValidationStatus.revise,
                    score=0.5,
                    feedback="Constraint check failed after revision.",
                    improvement_suggestions=[],
                )
            else:
                validation = await validate_large_output(revised, user_profile)
        else:
            validation = await validate_large_output(revised, user_profile)
    except Exception:
        validation = ValidationResult(
            itinerary_id=revised.itinerary_id,
            status=ValidationStatus.revise,
            score=0.0,
            feedback="Validation error — flagging for revision.",
        )

    await write_itinerary(revised)

    # ── Diff ──────────────────────────────────────────────────────────
    before_titles = {ia.activity.name.strip() for day in (itinerary.days or [])
                                                for ia in (day.activities or [])
                                                if getattr(getattr(ia, "activity", None), "name", "")}
    after_titles  = {ia.activity.name.strip() for day in (revised.days or [])
                                               for ia in (day.activities or [])
                                               if getattr(getattr(ia, "activity", None), "name", "")}
    dropped = sorted(before_titles - after_titles)
    added   = sorted(after_titles - before_titles)

    yield format_event("revision_done", {
        "itinerary":      revised.model_dump(mode="json"),
        "validation": {
            "status":     validation.status.value,
            "score":      validation.score,
            "feedback":   validation.feedback,
            "suggestions": validation.improvement_suggestions or [],
        },
        "dropped_titles": dropped,
        "added_titles":   added,
        "scope":          scope,
        "target_days":    list(target_day_numbers or []),
    })


async def run_single_revision(
    itinerary: Itinerary,
    user_profile: UserProfile,
    feedback: str,
    seed_validation: ValidationResult,
    activity_feedback: list[ActivityFeedback] | None = None,
    target_day_numbers: list[int] | None = None,
) -> tuple[Itinerary, ValidationResult]:
    """One-pass user-initiated revision.

    Difference from `run_refinement_loop`:
      - Runs the LLM regen EXACTLY ONCE (no MAX_REFINEMENT_ATTEMPTS loop).
        The user asked for this change — we apply it and surface validator
        verdict back to them, instead of burning 2-3 more minutes silently
        trying to satisfy the critic.
      - When `target_day_numbers` is provided (classifier identified specific
        days), uses a day-scoped prompt and generates only those days, then
        stitches them back. This keeps output tokens small (~1-4k instead of
        10-16k) and reliably fits within the 75s timeout.

    Raises on regen/parse failure so the caller can surface a real error
    instead of silently returning the unchanged original.

    Returns (revised_itinerary, validation_result). The caller persists +
    enriches with history bookkeeping.
    """
    import json

    # Merge per-activity feedback into the feedback string (same as the loop).
    if activity_feedback:
        act_lines = "; ".join(
            f"{af.activity_id} ({af.action})" + (f": {af.reason}" if af.reason else "")
            for af in activity_feedback
        )
        feedback = f"{feedback} | Activity feedback: {act_lines}".strip(" |")

    combined_feedback = f"{feedback}\n\nValidator feedback: {seed_validation.feedback}"
    if seed_validation.improvement_suggestions:
        combined_feedback += "\nSuggestions: " + "; ".join(
            seed_validation.improvement_suggestions
        )

    # Choose targeted day-level regen vs. full itinerary regen.
    use_targeted = bool(target_day_numbers)

    chunks: list[str] = []
    if use_targeted:
        # Fast path: generate only the targeted days, then stitch back.
        async for chunk in generate_refined_days(
            itinerary, target_day_numbers, combined_feedback, seed_validation,
        ):
            chunks.append(chunk)
        raw = "".join(chunks)

        # Parse the LLM output as a JSON array of day objects.
        try:
            # Strip markdown fences if present.
            raw_stripped = raw.strip()
            if raw_stripped.startswith("```"):
                raw_stripped = raw_stripped.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            revised_days_data = json.loads(raw_stripped)
            if isinstance(revised_days_data, dict) and "days" in revised_days_data:
                revised_days_data = revised_days_data["days"]
            if not isinstance(revised_days_data, list):
                raise ValueError("Expected a JSON array of days")
        except Exception as e:
            raise ValueError(f"Failed to parse targeted day revision output: {e}") from e

        # Build a map of revised days by day_number, then replace in original.
        from shared.schemas import ItineraryDay
        revised_day_map: dict[int, ItineraryDay] = {}
        for day_data in revised_days_data:
            try:
                revised_day_map[day_data["day_number"]] = ItineraryDay.model_validate(day_data)
            except Exception:
                pass  # keep original day if parse fails

        new_days = [
            revised_day_map.get(day.day_number, day)
            for day in itinerary.days
        ]
        revised = itinerary.model_copy(update={"days": new_days})
    else:
        # Full itinerary regen (fallback for global/broad scope changes).
        async for chunk in generate_refined_itinerary(
            itinerary, combined_feedback, seed_validation,
            task_type="complex_refinement",
        ):
            chunks.append(chunk)
        raw = "".join(chunks)
        revised = parse_itinerary(
            raw, user_profile,
            destination=itinerary.destination,
            activities=[ia.activity for day in itinerary.days for ia in day.activities],
        )

    # Preserve the original itinerary_id so the route's bookkeeping
    # (history append, current-trip pointer, dedupe) keeps targeting the
    # same document instead of forking a new id on every revise.
    revised = revised.model_copy(update={"itinerary_id": itinerary.itinerary_id})

    # Single validate pass — same gates as the loop, no retry.
    try:
        if user_profile.constraints:
            checks = run_all_checks(revised, user_profile.constraints)
            if not checks.budget_ok or not checks.must_haves_ok or not checks.avoid_list_ok:
                validation = ValidationResult(
                    itinerary_id=revised.itinerary_id,
                    status=ValidationStatus.revise,
                    score=0.5,
                    feedback="Constraint check failed after revision.",
                    improvement_suggestions=[],
                )
            else:
                validation = await validate_large_output(revised, user_profile)
        else:
            validation = await validate_large_output(revised, user_profile)
    except Exception:
        validation = ValidationResult(
            itinerary_id=revised.itinerary_id,
            status=ValidationStatus.revise,
            score=0.0,
            feedback="Validation error — flagging for revision.",
        )

    await write_itinerary(revised)
    return revised, validation


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
