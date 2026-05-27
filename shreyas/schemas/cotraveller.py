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
    # "male" | "female" — used by the same-gender hard filter for solo
    # travellers in mushahid/routes/cotraveller.py. Sidecar field on
    # Pinecone metadata for seeded personas; optional on the schema.
    gender:       Optional[str] = None
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

    # ── Couple-only fields (travel_style == "couple") ──────────────────────
    # Couple personas are written as a PAIR. `display_name` is "Mira & Theo";
    # `protagonist_name` is the side that drives chat (e.g. Mira) and
    # `partner_name` is the other (e.g. Theo). Speaker prompts use these
    # to give the LLM a clear identity ("you ARE Mira, your partner is
    # Theo") and a "we" voice for shared plans — without them, the model
    # interprets "Mira & Theo" as two people and hallucinates between
    # them turn to turn. Both default None so solo personas don't have
    # to care.
    protagonist_name: Optional[str] = None
    partner_name:     Optional[str] = None
    partner_age:      Optional[int] = None


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
    # Raw Pinecone cosine for this candidate, surfaced so /chat/start can
    # persist it on ChatSession and the in-chat live re-rank can honour the
    # same retrieval signal that produced the original match_score. Without
    # this, score_compatibility re-runs with retrieval_score=0 and silently
    # deflates the persona's reciprocal-approval probability.
    retrieval_score:         float = 0.0
    # True iff the signed-in viewer has already passed mutual approval
    # with this profile on any trip (i.e. there exists a ChatSession
    # between them with approval_status=approved). The detail page reads
    # this to hide the "Chat to vibe-check" CTA — once you're locked in,
    # the chat surface that exists to evaluate compatibility is done
    # doing its job, and the relationship lives on the shared-itinerary
    # surface instead. Returned only by /cotraveller/profile/{id}; the
    # /matches route never surfaces locked-in personas in the first place
    # (the active_pair short-circuit blocks the list).
    is_locked_in:            bool  = False
