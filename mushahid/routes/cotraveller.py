"""
Co-traveller matching endpoints.

These are user-triggered (Dashboard "Find companions" / "Show different
matches"); the orchestrator pipeline also computes matches at the end of
plan-trip and stuffs them into the `done` SSE payload.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from shared.schemas import CoTravellerMatch, UserProfile, TripConstraints, PersonaQuestionAnswers
from mushahid.auth import verify_token
from mushahid.realtime.firestore import get_user_profile, get_itinerary, get_companion_prefs
from mushahid.utils.sanitize import sanitize_user_input

router = APIRouter()
logger = logging.getLogger(__name__)


async def _load_user_profile(uid: str, itinerary_id: str | None = None) -> UserProfile:
    """Rehydrate a UserProfile from Firestore so matching has the same signals
    the user fed into plan-trip. Falls back to a near-empty profile when
    Firestore is unavailable so matching can still run with whatever we have."""
    raw = await get_user_profile(uid) or {}
    constraints = None
    persona_answers = None
    if raw.get("constraints"):
        try: constraints = TripConstraints.model_validate(raw["constraints"])
        except Exception as e: logger.warning("constraints rehydrate failed: %s", e)
    if raw.get("persona_answers"):
        try: persona_answers = PersonaQuestionAnswers.model_validate(raw["persona_answers"])
        except Exception as e: logger.warning("persona_answers rehydrate failed: %s", e)
    profile = UserProfile(
        user_id=uid,
        display_name=raw.get("display_name") or "Traveller",
        constraints=constraints,
        persona_answers=persona_answers,
        compatibility_signals=raw.get("compatibility_signals") or {},
        travel_style_embedding=raw.get("travel_style_embedding") or [],
    )
    # If an itinerary_id was given, prefer that trip's constraints over the
    # profile-level ones — matches should reflect the trip the user is on.
    if itinerary_id:
        try:
            it = await get_itinerary(itinerary_id)
            if it and it.user_id == uid:
                # Itinerary doesn't carry constraints directly today; placeholder
                # for when we do attach them.
                pass
        except Exception as e:
            logger.warning("itinerary rehydrate failed: %s", e)
    return profile


def _extra_text_from_prefs(prefs: dict | None) -> str:
    """Turn the four companion-intake answers into a short natural-language
    string that gets appended to the user's persona text before embedding.
    The phrasing here matters: it has to live in the same lexical space as
    seeded co-traveller bios so cosine retrieval skews the right way."""
    if not prefs:
        return ""
    bits: list[str] = []
    party = (prefs.get("party_arrival") or "").strip()
    if party == "close":
        bits.append("at a party, sticks close to one familiar person")
    elif party == "explore":
        bits.append("at a party, makes a lap and meets new people")
    elif party == "anchored":
        bits.append("at a party, anchors somewhere and lets people come over")
    chat = (prefs.get("chat_lull") or "").strip()
    if chat == "revive":
        bits.append("actively revives quiet group chats")
    elif chat == "hands_off":
        bits.append("hands-off about group chats, lets them breathe")
    elif chat == "direct":
        bits.append("prefers direct one-to-one messages over group chats")
    spo = (prefs.get("spontaneity") or "").strip()
    if spo == "yes":
        bits.append("open to last-minute plans with people they barely know")
    elif spo == "depends":
        bits.append("considers last-minute plans based on who else is in")
    elif spo == "pass":
        bits.append("prefers planned over spontaneous social moves")
    free = (prefs.get("companion_text") or "").strip()
    if free:
        bits.append(free)
    return ". ".join(bits)


class MatchesRequest(BaseModel):
    itinerary_id: str | None = None
    # Optional client-side fallback: persona signals from the user's cached
    # persona-infer response. Used when the Firestore user_profile has no
    # signals (e.g. user inferred their persona before we started persisting
    # them server-side). Server-persisted signals always take precedence.
    top_push:      list[str] | None = None
    top_interests: list[str] | None = None


@router.post("/cotraveller", response_model=list[CoTravellerMatch])
async def get_cotraveller_matches(body: MatchesRequest, uid: str = Depends(verify_token)):
    """Top matches for the signed-in user. When itinerary_id is set, load
    any companion preferences saved for that trip and fold them into the
    retrieval vector so the candidate pool reflects what the user actually
    wants in a companion for *this* trip."""
    from shreyas.retrieval.search import search_cotravellers
    from shreyas.cotraveller.matching import get_top_matches
    from mushahid.monitoring import capture
    try:
        profile = await _load_user_profile(uid, body.itinerary_id)
        # Backfill missing signals from the request if Firestore didn't have
        # them (older persona inferences predate server-side persistence).
        cs = dict(profile.compatibility_signals or {})
        if not cs.get("top_interests") and body.top_interests:
            cs["top_interests"] = body.top_interests
        if not cs.get("top_push") and body.top_push:
            cs["top_push"] = body.top_push
        if cs != (profile.compatibility_signals or {}):
            profile = profile.model_copy(update={"compatibility_signals": cs})
        prefs = None
        if body.itinerary_id:
            try:
                prefs = await get_companion_prefs(body.itinerary_id)
            except Exception as e:
                logger.warning("companion_prefs load failed for %s: %s", body.itinerary_id, e)
        extra = _extra_text_from_prefs(prefs)
        candidates = await search_cotravellers(profile, extra_text=extra)
        matches = get_top_matches(profile, candidates)
        capture(uid, "match_found", {
            "match_count": len(matches),
            "itinerary_id": body.itinerary_id,
            "had_prefs": bool(prefs),
        })
        return matches
    except Exception as e:
        logger.error("cotraveller match failed for %s: %s", uid, e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"matching failed: {type(e).__name__}: {e}") from e


@router.get("/cotraveller/profile/{profile_id}", response_model=CoTravellerMatch)
async def get_cotraveller_profile(
    profile_id: str,
    itinerary_id: str | None = Query(None),
    top_push:      list[str] = Query(default_factory=list),
    top_interests: list[str] = Query(default_factory=list),
    uid: str = Depends(verify_token),
):
    """Fetch a single co-traveller by id and score it against the signed-in
    user. Returns the full CoTravellerMatch so the detail page can show
    score, reasons, and compatibility breakdown without recomputing."""
    from shreyas.retrieval.search import get_cotraveller_by_id
    from shreyas.cotraveller.matching import score_compatibility
    try:
        candidate = await get_cotraveller_by_id(profile_id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="Co-traveller not found")
        profile = await _load_user_profile(uid, itinerary_id)
        # Same fallback path as the match list: backfill signals from query
        # params (cached persona on the client) if Firestore doesn't have them.
        cs = dict(profile.compatibility_signals or {})
        if not cs.get("top_interests") and top_interests:
            cs["top_interests"] = top_interests
        if not cs.get("top_push") and top_push:
            cs["top_push"] = top_push
        if cs != (profile.compatibility_signals or {}):
            profile = profile.model_copy(update={"compatibility_signals": cs})
        return score_compatibility(profile, candidate)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("get_cotraveller_profile failed for %s: %s", profile_id, e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"profile fetch failed: {type(e).__name__}: {e}") from e


class RegenerateMatchesRequest(BaseModel):
    excluded_profile_ids: list[str] = []
    feedback: str = ""


@router.post("/cotraveller/regenerate", response_model=list[CoTravellerMatch])
async def regenerate_cotraveller_matches(body: RegenerateMatchesRequest, uid: str = Depends(verify_token)):
    """Fresh batch skipping already-shown profiles. Feedback (sanitised) refines
    the user's persona vector before re-querying so 'someone more adventurous'
    actually pulls different candidates instead of just rolling the dice."""
    from shreyas.cotraveller.matching import regenerate_matches
    try:
        profile = await _load_user_profile(uid)
        feedback = sanitize_user_input(body.feedback)
        return await regenerate_matches(profile, body.excluded_profile_ids, feedback=feedback)
    except Exception as e:
        logger.error("cotraveller regenerate failed for %s: %s", uid, e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"matching failed: {type(e).__name__}: {e}") from e
