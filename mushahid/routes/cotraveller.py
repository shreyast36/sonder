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


async def _session_filters(uid: str, itinerary_id: str | None) -> tuple[set[str], dict | None]:
    """Walk this user's chat sessions and derive two filters used by the
    matches endpoint:

    - denied_profile_ids: every persona where EITHER side denied. Once
      either side passes, the match is dead — don't keep surfacing them
      on future searches, even across other trips.
    - active_pair: if this user already has a fully-approved match for
      the current itinerary, return its summary so the frontend can
      redirect to /shared/{itinerary_id} instead of paging through new
      matches the user can't act on anyway.
    """
    from mushahid.realtime.firestore import list_chat_sessions_for_user
    sessions = await list_chat_sessions_for_user(uid)
    denied: set[str] = set()
    active_pair: dict | None = None
    for s in sessions:
        profile_id = s.get("profile_id")
        if not profile_id:
            continue
        approval   = s.get("approval_status")
        user_dec   = s.get("user_decision")    or "pending"
        prof_dec   = s.get("profile_decision") or "pending"
        # Either side denying drops the persona for good.
        if approval == "denied" or user_dec == "denied" or prof_dec == "denied":
            denied.add(profile_id)
            continue
        if (
            approval == "approved"
            and itinerary_id
            and s.get("itinerary_id") == itinerary_id
            and active_pair is None
        ):
            active_pair = {
                "profile_id":   profile_id,
                "session_id":   s.get("session_id"),
                "itinerary_id": s.get("itinerary_id"),
            }
    return denied, active_pair


@router.post("/cotraveller")
async def get_cotraveller_matches(body: MatchesRequest, uid: str = Depends(verify_token)):
    """Top matches for the signed-in user. When itinerary_id is set, load
    any companion preferences saved for that trip and fold them into the
    retrieval vector so the candidate pool reflects what the user actually
    wants in a companion for *this* trip.

    Two suppression layers run before scoring:
      1. Personas that the user OR persona side previously denied are
         removed entirely (across all trips — a denial is final).
      2. If the user already has an approved pair for this itinerary,
         skip retrieval altogether and return active_pair instead so
         the frontend can redirect to the shared-itinerary surface.
    """
    from shreyas.retrieval.search import search_cotravellers
    from shreyas.cotraveller.matching import get_top_matches
    from mushahid.monitoring import capture
    try:
        denied_ids, active_pair = await _session_filters(uid, body.itinerary_id)
        if active_pair is not None:
            return {"matches": [], "active_pair": active_pair, "denied_count": len(denied_ids)}

        profile = await _load_user_profile(uid, body.itinerary_id)

        # Skip matching entirely for family + friends trips — they
        # already have their party, and authoring a coherent "friend
        # group" persona to match against is a much harder writing
        # problem we're not solving in V1. Solo / couple matter most
        # for matching; everyone else heads straight to the shared-
        # itinerary surface.
        constraints = getattr(profile, "constraints", None)
        style = getattr(constraints, "who_travelling_with", None)
        style_value = getattr(style, "value", None) if style else None
        if style_value in ("family", "friends"):
            return {
                "matches": [], "active_pair": None,
                "denied_count": len(denied_ids),
                "matching_disabled": True,
                "matching_disabled_reason": f"{style_value}_trip",
            }
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
        # search_cotravellers now returns (profile, pinecone_cosine) tuples.
        # We keep the score next to the profile through every filter step so
        # the ranker's pinecone_passthrough feature reads a real signal
        # instead of the previous-deployment regression where the cosine was
        # silently discarded and every match_score lost 1/6 of its weight.
        scored = await search_cotravellers(profile, extra_text=extra)
        if denied_ids:
            scored = [(c, s) for (c, s) in scored if getattr(c, "profile_id", None) not in denied_ids]

        # Hard travel-style filter — a couple should never see solo
        # personas surfaced as matches, a friends-group should see
        # other friends-style personas, and solo travellers see solo.
        # The ranker has a style_match feature but it only nudges the
        # score; without this hard filter cross-style candidates slip
        # through because of high embedding similarity on other axes.
        # We log the drop count instead of silently filtering so we
        # can spot a seed-pool gap (e.g. zero couple personas left
        # after filter).
        if style_value in ("solo", "couple"):
            before = len(scored)
            scored = [
                (c, s) for (c, s) in scored
                if (getattr(getattr(c, "travel_style", None), "value", None) or
                    getattr(c, "travel_style", None)) == style_value
            ]
            dropped = before - len(scored)
            if dropped:
                logger.info(
                    "cotraveller: dropped %d candidates outside style=%s (kept %d)",
                    dropped, style_value, len(scored),
                )

        # Same-gender hard filter for SOLO travellers — solo women
        # match only women, solo men only men. Safety default for
        # cold-strangers matching. Couples are already gender-locked
        # at the seed level (male+female pairs only), so this only
        # gates solo. If the user hasn't told us their gender, we
        # fall back to mixed matching — no gender = no filter —
        # rather than returning zero matches.
        user_gender = (getattr(constraints, "gender", "") or "").strip().lower()
        if style_value == "solo" and user_gender in ("male", "female"):
            filtered = [
                (c, s) for (c, s) in scored
                if (getattr(c, "gender", "") or "").strip().lower() == user_gender
            ]
            # Fail-open: if the candidate pool has no gender metadata
            # populated yet (e.g. Pinecone seeded before we started
            # writing the gender field), the filter would empty the
            # pool. Rather than dead-end the user with "no matches",
            # we log and skip the filter so something surfaces. Once
            # the pool is re-seeded with gender, this path stops
            # firing on its own.
            with_gender = sum(
                1 for (c, _s) in scored
                if (getattr(c, "gender", "") or "").strip()
            )
            if not filtered and with_gender == 0 and scored:
                logger.warning(
                    "cotraveller: gender filter would empty pool — "
                    "no candidates have gender metadata (re-seed needed). "
                    "Falling back to mixed matching for solo=%s.",
                    user_gender,
                )
            else:
                dropped = len(scored) - len(filtered)
                if dropped:
                    logger.info(
                        "cotraveller: dropped %d candidates outside gender=%s (kept %d)",
                        dropped, user_gender, len(filtered),
                    )
                scored = filtered

        # Cap the surfaced list at the top 3. When the user denies one,
        # _session_filters drops it from `denied_ids` on the next call
        # and the next-best candidate slides into the third slot — so
        # the user always sees three live options to consider.
        matches = get_top_matches(profile, scored, top_n=3)
        capture(uid, "match_found", {
            "match_count":  len(matches),
            "itinerary_id": body.itinerary_id,
            "had_prefs":    bool(prefs),
            "denied_count": len(denied_ids),
        })
        return {
            "matches":      [m.model_dump(mode="json") for m in matches],
            "active_pair":  None,
            "denied_count": len(denied_ids),
        }
    except Exception as e:
        logger.error("cotraveller match failed for %s: %s", uid, e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"matching failed: {type(e).__name__}: {e}") from e


@router.get("/cotraveller/profile/{profile_id}", response_model=CoTravellerMatch)
async def get_cotraveller_profile(
    profile_id: str,
    itinerary_id: str | None = Query(None),
    top_push:      list[str] = Query(default_factory=list),
    top_interests: list[str] = Query(default_factory=list),
    # The Pinecone cosine the frontend already saw on /matches. Forwarded so
    # the detail page's recompute honours the same retrieval signal — without
    # it pinecone_passthrough scores 0 and the detail-page match_score lands
    # ~1/6 below what /matches showed for the exact same candidate.
    retrieval_score: float | None = Query(None),
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
        match = score_compatibility(
            profile, candidate,
            retrieval_score=float(retrieval_score) if retrieval_score is not None else 0.0,
        )
        # Has the viewer already passed mutual approval with this profile?
        # If yes, the detail page hides the "Chat to vibe-check" CTA — that
        # button only makes sense for evaluation chats, not for relationships
        # the user has already committed to on the shared-itinerary surface.
        # Re-uses _session_filters which already walks every chat session
        # for this user; we just check if profile_id ever showed up as the
        # approved counterpart on any trip.
        try:
            from mushahid.realtime.firestore import list_chat_sessions_for_user
            sessions = await list_chat_sessions_for_user(uid)
            is_locked = any(
                s.get("profile_id") == profile_id
                and s.get("approval_status") == "approved"
                for s in sessions
            )
            if is_locked:
                match = match.model_copy(update={"is_locked_in": True})
        except Exception as e:
            logger.warning("locked-in lookup failed for %s/%s: %s", uid, profile_id, e)

        # Analytics: detail-page click-through. Combined with match_found
        # (impressions) this gives match CTR.
        try:
            from mushahid.monitoring import capture, EVENT_MATCH_PROFILE_VIEWED
            capture(uid, EVENT_MATCH_PROFILE_VIEWED, {
                "profile_id":  profile_id,
                "match_score": round(match.match_score, 3),
            })
        except Exception:
            pass
        return match
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
        # Apply the same denial filter as the main matches endpoint — any
        # persona either side previously denied is dead, regenerate
        # shouldn't resurrect them.
        denied_ids, _active = await _session_filters(uid, None)
        excluded = list({*(body.excluded_profile_ids or []), *denied_ids})
        # Same top-3 cap as the main /cotraveller endpoint — keeps the
        # "always show 3 live candidates" invariant after regenerate too.
        # Over-fetch then style-filter, so the top_n=3 contract still
        # holds after dropping cross-style candidates. Mirrors the hard
        # filter in /cotraveller above so couples never see solos etc.
        constraints = getattr(profile, "constraints", None)
        style = getattr(constraints, "who_travelling_with", None)
        style_value = getattr(style, "value", None) if style else None
        user_gender = (getattr(constraints, "gender", "") or "").strip().lower()
        # Over-fetch when filters apply so the top-3 contract still
        # holds after dropping cross-style and cross-gender candidates.
        # Solo with gender filter has the thinnest pool — bump higher.
        if style_value == "solo" and user_gender in ("male", "female"):
            raw_top_n = 24
        elif style_value in ("solo", "couple"):
            raw_top_n = 12
        else:
            raw_top_n = 3
        matches = await regenerate_matches(profile, excluded, feedback=feedback, top_n=raw_top_n)
        if style_value in ("solo", "couple"):
            matches = [
                m for m in matches
                if (getattr(getattr(m.profile, "travel_style", None), "value", None) or
                    getattr(m.profile, "travel_style", None)) == style_value
            ]
        if style_value == "solo" and user_gender in ("male", "female"):
            filtered = [
                m for m in matches
                if (getattr(m.profile, "gender", "") or "").strip().lower() == user_gender
            ]
            with_gender = sum(
                1 for m in matches
                if (getattr(m.profile, "gender", "") or "").strip()
            )
            # Fail-open identical to /cotraveller — don't dead-end on
            # pre-gender seeded data.
            if not filtered and with_gender == 0 and matches:
                logger.warning(
                    "cotraveller regenerate: gender filter would empty pool "
                    "— no candidates have gender metadata (re-seed needed). "
                    "Falling back to mixed matching for solo=%s.",
                    user_gender,
                )
            else:
                matches = filtered
        matches = matches[:3]
        # Analytics: regenerate is the "show me different matches" signal —
        # high rate means current matches aren't resonating. Excluded count
        # tells us how deep the user has dug.
        try:
            from mushahid.monitoring import capture, EVENT_MATCH_REGENERATED
            capture(uid, EVENT_MATCH_REGENERATED, {
                "excluded_count": len(body.excluded_profile_ids or []),
                "has_feedback":   bool(feedback),
                "match_count":    len(matches),
            })
        except Exception:
            pass
        return matches
    except Exception as e:
        logger.error("cotraveller regenerate failed for %s: %s", uid, e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"matching failed: {type(e).__name__}: {e}") from e
