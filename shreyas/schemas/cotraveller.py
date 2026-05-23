from pydantic import BaseModel, Field
from typing import Optional
from jahnvi.schemas.enums import PacePreference, BudgetStyle, TravelStyle


class CoTravellerProfile(BaseModel):
    """
    A synthetic or real co-traveller profile stored in Pinecone and Firestore.

    The original v1 fields (archetype + interests + pace/budget/style) were
    the thin schema we built from randomuser.me identities. Real users now
    produce richer signals (PPM dimensions, an emotional signature, a
    free-text small_thing, etc.), so the extended fields below were added
    so synthetic profiles can compete symmetrically in matching + grounding
    the chat reply LLM in the same persona shape as a real user.

    Persona answer keys must align with PERSONA_QUESTION_CATALOG in
    mushahid/persona/taxonomy.py. compatibility_signals follows the same
    shape user_profile.compatibility_signals does (top_push, top_interests,
    emotional_signature, emotional_tone, etc).

    Example:
        CoTravellerProfile(
            profile_id   = "maya_001",
            display_name = "Maya Sharma",
            age          = 24,
            location     = "Delhi, India",
            archetype    = "Cultural Explorer",
            interests    = ["food", "culture", "photography"],
            pace         = PacePreference.relaxed,
            budget_style = BudgetStyle.mid_range,
            travel_style = TravelStyle.couple,
            avatar_url   = "https://...",
            preferred_destination = "Lisbon, Portugal",
            persona_answers = {"social_role": "place_finder", ...},
            voice_anchor    = "Just got back from 3 days in Lisbon — still dream "
                              "about the egg tarts at Manteigaria.",
            quirks          = ["allergic to crowded beaches", "always ends up in markets"],
            voice_id        = "shimmer",
            compatibility_signals = {
                "top_push": ["...", "..."], "top_interests": [...],
                "emotional_signature": "story_collector",
                "emotional_tone": "soft chaos energy",
            },
            embedding    = [0.031, ...]
        )
    """
    profile_id:   str
    display_name: str
    age:          int
    location:     str
    archetype:    str
    interests:    list[str]
    pace:         PacePreference
    budget_style: BudgetStyle
    travel_style: TravelStyle
    avatar_url:   Optional[str] = None
    embedding:    Optional[list[float]] = None

    # ── Extended fields for symmetric matching + multi-turn chat grounding ──
    preferred_destination: Optional[str] = None
    persona_answers:       dict          = Field(default_factory=dict)
    voice_anchor:          Optional[str] = None
    quirks:                list[str]     = Field(default_factory=list)
    voice_id:              Optional[str] = None
    compatibility_signals: dict          = Field(default_factory=dict)

    # Disclosure flag — True when the profile came from seed_cotravellers.py.
    # The frontend reads this to render the "Sonder Curated" badge on every
    # surface where a synthetic persona could be mistaken for a real user.
    is_seed: bool = False


class CompanionPrefs(BaseModel):
    """
    Per-trip companion preferences captured by 4 fun, non-travel questions
    on /companions before matches render. Stored in Firestore at
    companion_prefs/{itinerary_id}; influences both the embedding (free text
    appended to persona) and the candidate pool (question keywords nudge
    cosine retrieval).

    Field values are picker keys; the frontend renders the human labels:
      party_arrival:  close | explore | anchored
      chat_lull:      revive | hands_off | direct
      spontaneity:    yes | depends | pass
      companion_text: ≤ 200 chars free text
    """
    party_arrival:  Optional[str] = None
    chat_lull:      Optional[str] = None
    spontaneity:    Optional[str] = None
    companion_text: Optional[str] = None


class CoTravellerMatch(BaseModel):
    """
    The result of Shreyas's compatibility scoring — shown on Screen 4.

    Example:
        CoTravellerMatch(
            profile         = CoTravellerProfile(display_name="Maya Sharma", ...),
            match_score     = 0.92,
            match_reasons   = [
                "Similar interests in food and culture",
                "Same travel pace",
                "Overlapping itinerary preferences",
                "Similar budget range"
            ],
            compatibility_breakdown = {
                "interests": 0.95,
                "pace":      1.0,
                "budget":    0.85,
                "itinerary": 0.88
            }
        )
    """
    profile:                 CoTravellerProfile
    match_score:             float = Field(ge=0.0, le=1.0)
    match_reasons:           list[str]
    compatibility_breakdown: dict
