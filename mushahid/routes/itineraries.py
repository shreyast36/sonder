"""
GET  /api/itineraries/current        → user's saved itinerary (dashboard card)
POST /api/itineraries/{id}/save      → mark this itinerary as the user's active trip

The orchestrator already writes every generated itinerary to Firestore via
write_itinerary on `done`. These routes layer a "current trip" pointer on top:
the user explicitly chooses which generated itinerary shows on their dashboard.
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from datetime import datetime, timezone

from mushahid.auth import verify_token
from mushahid.realtime.firestore import (
    get_itinerary, get_user_profile, update_user_profile, write_itinerary,
    get_companion_prefs, write_companion_prefs,
    delete_itinerary_and_related,
)
from mushahid.utils.sanitize import sanitize_user_input
from shared.config import LOCAL_MODE

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/itineraries/current")
async def get_current_itinerary(uid: str = Depends(verify_token)):
    """Return the itinerary the user marked as their active dashboard trip.
    204-equivalent {"itinerary": null} when nothing is saved yet, so the
    dashboard can render an empty state without treating 404 as an error."""
    try:
        profile = await get_user_profile(uid)
    except Exception as e:
        logger.warning("get_current_itinerary profile read failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e

    current_id = (profile or {}).get("current_itinerary_id")
    if not current_id:
        return {"itinerary": None}

    try:
        itinerary = await get_itinerary(current_id)
    except Exception as e:
        logger.warning("get_current_itinerary itinerary read failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e

    if itinerary is None:
        # Pointer is stale (itinerary was deleted). Treat as no current trip
        # rather than 500; the next save will overwrite the pointer.
        return {"itinerary": None}

    # Analytics: dashboard hero render. Fires every load, so dedupe to
    # unique-users-per-day in the dashboard side. Powers retention proxy
    # (DAU on the dashboard with a real saved trip).
    try:
        from mushahid.monitoring import capture, EVENT_TRIP_VIEWED
        capture(uid, EVENT_TRIP_VIEWED, {
            "itinerary_id": itinerary.itinerary_id,
            "destination":  f"{itinerary.destination.city}, {itinerary.destination.country}",
        })
    except Exception:
        pass

    return {"itinerary": itinerary.model_dump(mode="json")}


@router.post("/itineraries/{itinerary_id}/save")
async def save_itinerary_as_current(itinerary_id: str, uid: str = Depends(verify_token)):
    """Append the itinerary to the user's saved history AND mark it current
    (the dashboard hero card). Past trips remain queryable via /itineraries/list.
    Re-saving the same id is a no-op for the history (no duplicate)."""
    try:
        itinerary = await get_itinerary(itinerary_id)
    except Exception as e:
        logger.warning("save_itinerary read failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e

    if itinerary is None:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary.user_id != uid:
        raise HTTPException(status_code=403, detail="Not authorised to save this itinerary")

    try:
        profile = await get_user_profile(uid) or {}
        saved_ids = list(profile.get("saved_itinerary_ids") or [])
        first_save = itinerary_id not in saved_ids
        if first_save:
            saved_ids.append(itinerary_id)
        await update_user_profile(uid, {
            "current_itinerary_id": itinerary_id,
            "saved_itinerary_ids":  saved_ids,
        })
    except Exception as e:
        logger.warning("save_itinerary profile update failed: %s", e)
        if LOCAL_MODE:
            raise HTTPException(status_code=503, detail=f"Profile update failed: {type(e).__name__}") from e
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e

    # Analytics: end of the itinerary funnel — save rate is the conversion
    # metric the rest of the app's growth depends on. first_save flag lets
    # us distinguish a brand-new trip from re-saving an existing one.
    try:
        from mushahid.monitoring import capture, EVENT_TRIP_SAVED
        capture(uid, EVENT_TRIP_SAVED, {
            "itinerary_id":     itinerary_id,
            "first_save":       first_save,
            "destination":      f"{itinerary.destination.city}, {itinerary.destination.country}",
            "day_count":        len(itinerary.days or []),
            "total_budget_usd": itinerary.total_budget_usd,
        })
    except Exception:
        pass

    return {"saved": True, "itinerary_id": itinerary_id}


@router.get("/itineraries/list")
async def list_saved_itineraries(uid: str = Depends(verify_token)):
    """All of the user's saved itineraries, newest-saved first. Each entry
    is a slim summary (id, destination, day count, total budget, dates) for
    rendering a 'Past trips' carousel — full itinerary fetched on-demand
    via /api/itineraries/current after switching."""
    try:
        profile = await get_user_profile(uid) or {}
    except Exception as e:
        logger.warning("list_saved_itineraries profile read failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e

    saved_ids = list(profile.get("saved_itinerary_ids") or [])
    current_id = profile.get("current_itinerary_id")

    # Backfill: older users have a current_id but no saved list.
    if current_id and current_id not in saved_ids:
        saved_ids.append(current_id)

    summaries = []
    for iid in reversed(saved_ids):   # newest-saved first
        try:
            it = await get_itinerary(iid)
        except Exception as e:
            logger.warning("itinerary fetch failed for %s: %s", iid, e)
            continue
        if it is None or it.user_id != uid:
            continue
        days = it.days or []
        summaries.append({
            "itinerary_id":    it.itinerary_id,
            "is_current":      it.itinerary_id == current_id,
            "city":            it.destination.city,
            "country":         it.destination.country,
            "day_count":       len(days),
            "trip_start":      str(days[0].trip_date) if days and days[0].trip_date else None,
            "trip_end":        str(days[-1].trip_date) if days and days[-1].trip_date else None,
            "total_budget_usd": it.total_budget_usd,
        })
    return {"trips": summaries}


class SetCurrentBody(BaseModel):
    itinerary_id: str


@router.post("/itineraries/set-current")
async def set_current_itinerary(body: SetCurrentBody, uid: str = Depends(verify_token)):
    """Switch which saved trip is the dashboard hero. Trip must already be
    in the user's saved list (i.e. previously saved). Doesn't add to history."""
    itinerary = await get_itinerary(body.itinerary_id)
    if itinerary is None:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary.user_id != uid:
        raise HTTPException(status_code=403, detail="Not authorised")
    try:
        profile = await get_user_profile(uid) or {}
        saved_ids = list(profile.get("saved_itinerary_ids") or [])
        if body.itinerary_id not in saved_ids:
            raise HTTPException(status_code=409, detail="Save the itinerary first before switching to it")
        await update_user_profile(uid, {"current_itinerary_id": body.itinerary_id})
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("set_current_itinerary failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e

    # Analytics: user switched between past saved trips — engagement signal,
    # also tells us how often the past-trips carousel is actually used.
    try:
        from mushahid.monitoring import capture, EVENT_TRIP_SET_CURRENT
        capture(uid, EVENT_TRIP_SET_CURRENT, {"itinerary_id": body.itinerary_id})
    except Exception:
        pass

    return {"current_itinerary_id": body.itinerary_id}


@router.delete("/itineraries/{itinerary_id}")
async def delete_itinerary(itinerary_id: str, uid: str = Depends(verify_token)):
    """Hard-delete a saved trip and its attached docs.

    Removes:
      - the itinerary doc
      - the shared-itinerary twin (if collaboration was started)
      - the companion_prefs intake answers for this trip
      - all journal_entries tagged to this trip
      - the itinerary_id from the user's saved_itinerary_ids
      - the current_itinerary_id pointer if it pointed here

    Chats are intentionally preserved — they're records of conversations
    with people, not data about the trip. If we deleted chat sessions
    on trip delete the user would lose history with co-travellers they
    actually matched with.

    Returns a count breakdown so the dashboard can show "Removed N
    journal entries with this trip." if it wants to."""
    itinerary = await get_itinerary(itinerary_id)
    if itinerary is None:
        # Idempotent — if the doc is already gone (race / double-click),
        # still scrub the user profile pointers and return success.
        pass
    elif itinerary.user_id != uid:
        raise HTTPException(status_code=403, detail="Not authorised to delete this itinerary")

    removed = await delete_itinerary_and_related(itinerary_id)

    # Purge user-profile pointers.
    try:
        profile = await get_user_profile(uid) or {}
        saved_ids = [i for i in (profile.get("saved_itinerary_ids") or []) if i != itinerary_id]
        updates: dict = {"saved_itinerary_ids": saved_ids}
        # Clear current pointer if it was this trip — dashboard will fall
        # back to the empty state until the user picks a new current.
        if profile.get("current_itinerary_id") == itinerary_id:
            updates["current_itinerary_id"] = None
        await update_user_profile(uid, updates)
    except Exception as e:
        logger.warning("delete_itinerary profile cleanup failed: %s", e)
        # We've already deleted the docs at this point; the pointer
        # cleanup is best-effort. The next /itineraries/list call will
        # naturally skip the dangling id (get_itinerary returns None).

    try:
        from mushahid.monitoring import capture
        capture(uid, "itinerary_deleted", {
            "itinerary_id":    itinerary_id,
            "removed":         removed,
        })
    except Exception:
        pass

    return {"deleted": True, "itinerary_id": itinerary_id, "removed": removed}


# ── Approval lifecycle (draft → finalized) ────────────────────────────────────
#
# Every generated itinerary lands as a draft. The user reviews it on
# /itinerary and either approves (locks the itinerary, snapshots the
# ranker weights, transitions to shared-itinerary mode) or revises
# (loops through targeted edits until satisfied). Until approval, the
# itinerary is mutable and ranker weights keep updating per user
# feedback. After approval it's frozen.


class ReviseBody(BaseModel):
    feedback: str
    # Optional structured per-activity feedback. When set, the targeted
    # revision path uses these instead of free-text classification.
    targets: Optional[list[dict]] = None


@router.post("/itineraries/{itinerary_id}/approve")
async def approve_itinerary(itinerary_id: str, uid: str = Depends(verify_token)):
    """User signs off on the draft. Locks the itinerary, snapshots the
    user's current ranker weights as 'finalized' (frozen — no more
    online updates from feedback), and clears any in-flight revision
    state. The trip is now the canonical shared-itinerary state.

    Idempotent: re-calling on an already-finalized itinerary is a no-op."""
    itinerary = await _verify_itinerary_owner(itinerary_id, uid)

    if getattr(itinerary, "approval_status", "draft") == "finalized":
        return {
            "itinerary_id":   itinerary_id,
            "approval_status": "finalized",
            "finalized_at":    getattr(itinerary, "finalized_at", None),
            "already_finalized": True,
        }

    finalized_at = datetime.now(timezone.utc).isoformat()
    updated = itinerary.model_copy(update={
        "approval_status": "finalized",
        "finalized_at":    finalized_at,
    })
    await write_itinerary(updated)

    # Reinforce the most-recent revision's boosted features one final
    # time — explicit user acceptance is a stronger signal than a
    # mid-loop revision, so we apply a small confirming nudge before
    # freezing. Then snapshot the resulting weights to
    # finalized_ranker_weights so the NEXT trip starts from them
    # instead of the uniform 1/N baseline.
    try:
        from shreyas.ranking import feedback as ranker_feedback
        from shreyas.ranking.policies import activity as activity_policy

        prof = await get_user_profile(uid) or {}
        signals = dict(prof.get("compatibility_signals") or {})
        rw = dict(signals.get("ranker_weights") or {})

        # Confirming nudge on the last revision turn's feedback.
        history = list(getattr(itinerary, "revision_history", []) or [])
        last_applied = next((h for h in reversed(history) if h.get("status") == "applied" and h.get("feedback")), None)
        if last_applied:
            current_act = dict(rw.get("activity") or {})
            new_act, boosted = ranker_feedback.apply_text_feedback(
                current_act, last_applied.get("feedback", ""),
                activity_policy, boost_multiplier=0.5,  # half-strength confirm
            )
            if boosted:
                rw["activity"] = new_act
                logger.info("approve reinforcement: boosted %s on confirm", boosted)

        if rw:
            signals["ranker_weights"] = rw
            signals["finalized_ranker_weights"] = rw
            await update_user_profile(uid, {"compatibility_signals": signals})
    except Exception as e:
        logger.warning("approve_itinerary: weight snapshot failed: %s", e)

    try:
        from mushahid.monitoring import capture
        capture(uid, "itinerary_finalized", {
            "itinerary_id": itinerary_id,
            "revision_turns": len(getattr(itinerary, "revision_history", []) or []),
        })
    except Exception:
        pass

    return {
        "itinerary_id":    itinerary_id,
        "approval_status": "finalized",
        "finalized_at":    finalized_at,
        "already_finalized": False,
        "shared_url":      f"/shared/{itinerary_id}",
    }


@router.post("/itineraries/{itinerary_id}/revise")
async def revise_itinerary(itinerary_id: str, body: ReviseBody, uid: str = Depends(verify_token)):
    """User wants changes. Runs the targeted-revision pipeline:

      1. Classify feedback as SMALL (targeted edit) or LARGE (rewrite)
         via mushahid.refinement.classifier.
      2. Run the validator-gated refinement loop with classifier hints
         + dedupe memory (titles the user already rejected this session
         are explicitly blacklisted in the revision prompt).
      3. On revision success: persist the new itinerary, append the
         turn to revision_history with status='applied' + verdict,
         return the updated draft.

    The classifier decides which LLM tier the revision uses — small
    edits stay on quick_edit (cheap, fast), large rewrites get
    complex_refinement head-room. Both run through the same validator
    gate before returning to the user.

    409 if the itinerary is already finalized."""
    import json as _json
    from mushahid.refinement.classifier import classify_revision_feedback
    from mushahid.refinement.loop import stream_single_revision
    from mushahid.realtime.sse import format_event, stream_pipeline_events
    from shared.schemas import (
        ActivityFeedback, UserProfile, ValidationResult, ValidationStatus,
    )

    itinerary = await _verify_itinerary_owner(itinerary_id, uid)

    if getattr(itinerary, "approval_status", "draft") == "finalized":
        raise HTTPException(
            status_code=409,
            detail="Itinerary is finalised. Revisions need a new edit session via /shared.",
        )

    feedback = sanitize_user_input(body.feedback or "")[:1000].strip()
    if not feedback and not body.targets:
        raise HTTPException(status_code=400, detail="Feedback or targets required")

    history = list(getattr(itinerary, "revision_history", []) or [])
    turn_number = len(history) + 1

    # ── 1. Classify the feedback (scope + targets + preserve hints) ──
    summary_lines: list[str] = []
    for day in (itinerary.days or [])[:5]:
        names = [str(getattr(getattr(ia, "activity", None), "name", "") or "").strip()
                 for ia in (day.activities or [])[:4]]
        names = [n for n in names if n]
        if names:
            summary_lines.append(f"Day {day.day_number}: {' / '.join(names)}")
    itin_summary = "\n".join(summary_lines)
    verdict = await classify_revision_feedback(feedback or "edits via targets", itin_summary)
    logger.info("revise classifier: turn=%d scope=%s targets=%s",
                turn_number, verdict["scope"], verdict["target_day_numbers"])

    # ── 2. Build dedupe blacklist from prior rejected titles ──
    rejected_titles: list[str] = []
    for h in history:
        for t in (h.get("dropped_titles") or []):
            if t and t not in rejected_titles:
                rejected_titles.append(t)
    # Stitch dedupe hints + preserve hints + classifier summary into the
    # feedback string the refinement loop sees. The loop already knows
    # how to weave these into the LLM prompt + revalidate after.
    feedback_for_loop = feedback or verdict["summary"]
    if verdict["preserve"]:
        feedback_for_loop += "\n\nPRESERVE: " + " | ".join(verdict["preserve"])
    if rejected_titles:
        feedback_for_loop += "\n\nDO NOT RE-INTRODUCE these previously-rejected titles: " + ", ".join(rejected_titles[:20])
    if verdict["target_day_numbers"]:
        feedback_for_loop += f"\n\nFOCUS on day(s): {verdict['target_day_numbers']}. Preserve other days unchanged."

    # ── 3. Run the validator-gated refinement loop ──
    profile = await get_user_profile(uid) or {}
    user_profile = UserProfile(
        user_id=uid,
        display_name=profile.get("display_name") or "Traveller",
        constraints=profile.get("constraints"),
        persona_answers=profile.get("persona_answers"),
        compatibility_signals=profile.get("compatibility_signals"),
        travel_style_embedding=profile.get("travel_style_embedding") or [],
    )
    seed_validation = ValidationResult(
        itinerary_id=itinerary.itinerary_id,
        status=ValidationStatus.revise,
        score=0.6,
        feedback="User-requested revision",
        improvement_suggestions=[],
    )

    structured_targets = None
    if body.targets:
        structured_targets = [ActivityFeedback(**t) for t in body.targets
                              if isinstance(t, dict) and t.get("activity_id")]

    # STREAMING single-pass revision. The route returns SSE events so the
    # frontend can splice in revised days as soon as the LLM finishes
    # each one — no more staring at a frozen button for 60s.
    target_days = verdict.get("target_day_numbers") or []

    async def _event_stream():
        # Forward the inner stream and capture the final result so we can
        # append revision_history + boost ranker weights after the user
        # already has the visible diff.
        final_payload: dict = {}
        try:
            async for sse in stream_single_revision(
                itinerary, user_profile, feedback_for_loop,
                seed_validation,
                activity_feedback=structured_targets,
                target_day_numbers=target_days,
                scope=verdict["scope"],
                classifier_summary=verdict.get("summary") or "",
            ):
                # Sniff the final event so the outer route can do its
                # bookkeeping without re-parsing every chunk.
                if sse.startswith("event: revision_done\n"):
                    try:
                        data_line = next(
                            line for line in sse.split("\n") if line.startswith("data: ")
                        )
                        final_payload = _json.loads(data_line[6:])
                    except Exception:
                        final_payload = {}
                yield sse
        except Exception as e:
            logger.warning("revise: stream failed: %s", e)
            yield format_event("revision_failed", {
                "message": f"Revision failed — please try again. ({type(e).__name__})",
            })
            return

        # ── Post-stream bookkeeping (after the user has the diff) ──
        if not final_payload:
            return  # nothing to record — failure event already sent

        dropped = final_payload.get("dropped_titles") or []
        added   = final_payload.get("added_titles") or []
        validation_payload = final_payload.get("validation") or {}

        # Ranker weight delta with decay (same as the non-streaming version).
        weight_delta_logged: dict = {"boosted": [], "multiplier": 0.0}
        try:
            from shreyas.ranking import feedback as ranker_feedback
            from shreyas.ranking.policies import activity as activity_policy
            multiplier = max(0.125, 0.5 ** (turn_number - 1))
            signals = dict(profile.get("compatibility_signals") or {})
            rw = dict(signals.get("ranker_weights") or {})
            current_act = dict(rw.get("activity") or {})
            new_act, boosted = ranker_feedback.apply_text_feedback(
                current_act, feedback, activity_policy,
                boost_multiplier=multiplier,
            )
            if boosted:
                rw["activity"] = new_act
                signals["ranker_weights"] = rw
                await update_user_profile(uid, {"compatibility_signals": signals})
                weight_delta_logged = {"boosted": boosted, "multiplier": multiplier}
                logger.info("revise turn %d → boosted %s (mult %.3f)",
                            turn_number, boosted, multiplier)
        except Exception as e:
            logger.warning("revise: weight update failed: %s", e)

        # Append to revision_history + persist with approval_status=draft.
        history.append({
            "turn":           turn_number,
            "feedback":       feedback,
            "targets":        body.targets or [],
            "scope":          verdict["scope"],
            "target_days":    verdict["target_day_numbers"],
            "preserve":       verdict["preserve"],
            "dropped_titles": dropped,
            "added_titles":   added,
            "boosted_features": weight_delta_logged["boosted"],
            "boost_multiplier": weight_delta_logged["multiplier"],
            "validation_score":   validation_payload.get("score"),
            "validation_status":  validation_payload.get("status", "revise"),
            "validation_feedback": validation_payload.get("feedback", ""),
            "created_at":     datetime.now(timezone.utc).isoformat(),
            "status":         "applied",
        })

        # Re-read the freshly-written revised itinerary, attach history,
        # persist again. (stream_single_revision already wrote the days.)
        try:
            from shared.schemas import Itinerary as _Itin
            revised = _Itin.model_validate(final_payload["itinerary"])
            final_itin = revised.model_copy(update={
                "revision_history": history,
                "approval_status":  "draft",
            })
            await write_itinerary(final_itin)
        except Exception as e:
            logger.warning("revise: history persist failed: %s", e)

        try:
            from mushahid.monitoring import capture
            capture(uid, "itinerary_revision_applied", {
                "itinerary_id": itinerary_id,
                "turn":         turn_number,
                "scope":        verdict["scope"],
                "dropped":      len(dropped),
                "added":        len(added),
            })
        except Exception:
            pass

        # Final closing event so the frontend knows bookkeeping finished
        # and can flip the modal closed even if the network is slow.
        yield format_event("revision_persisted", {"turn": turn_number})

    return stream_pipeline_events(_event_stream())


# ── Companion preferences (per-trip) ──────────────────────────────────────────

class CompanionPrefsBody(BaseModel):
    party_arrival:  Optional[str] = None
    chat_lull:      Optional[str] = None
    spontaneity:    Optional[str] = None
    companion_text: Optional[str] = None


async def _verify_itinerary_owner(itinerary_id: str, uid: str):
    try:
        itinerary = await get_itinerary(itinerary_id)
    except Exception as e:
        logger.warning("itinerary read failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e
    if itinerary is None:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    if itinerary.user_id != uid:
        raise HTTPException(status_code=403, detail="Not authorised")
    return itinerary


@router.get("/itineraries/{itinerary_id}/companion-prefs")
async def get_companion_prefs_route(itinerary_id: str, uid: str = Depends(verify_token)):
    """Return the user's saved companion preferences for this trip, or
    {"prefs": null} when they haven't answered the intake yet."""
    await _verify_itinerary_owner(itinerary_id, uid)
    try:
        prefs = await get_companion_prefs(itinerary_id)
    except Exception as e:
        logger.warning("get_companion_prefs failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e
    return {"prefs": prefs}


@router.post("/itineraries/{itinerary_id}/companion-prefs")
async def save_companion_prefs(
    itinerary_id: str,
    body: CompanionPrefsBody,
    uid: str = Depends(verify_token),
):
    """Persist intake answers. Free-text companion_text is sanitised + capped
    at 200 chars before storage so it's safe to embed into the persona text."""
    await _verify_itinerary_owner(itinerary_id, uid)

    raw = body.model_dump()
    cleaned = {
        "party_arrival":  (raw.get("party_arrival")  or None),
        "chat_lull":      (raw.get("chat_lull")      or None),
        "spontaneity":    (raw.get("spontaneity")    or None),
        "companion_text": None,
        "itinerary_id":   itinerary_id,
        "user_id":        uid,
    }
    if raw.get("companion_text"):
        cleaned["companion_text"] = sanitize_user_input(raw["companion_text"])[:200]

    try:
        await write_companion_prefs(itinerary_id, cleaned)
    except Exception as e:
        logger.warning("write_companion_prefs failed: %s", e)
        raise HTTPException(status_code=503, detail=f"Firestore unavailable: {type(e).__name__}") from e
    return {"saved": True, "prefs": cleaned}
