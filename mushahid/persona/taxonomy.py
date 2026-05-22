"""
Emotional signature taxonomy + persona-question catalog.

The taxonomy is the closed set of emotional-travel motivations the LLM is
allowed to pick from when inferring a user's signature. Keys are stable
machine identifiers (used in compatibility_signals); descriptions are LLM
ground truth — they shape what each key means without ever surfacing to
the user.

The question catalog gives the signature inferrer human-readable prompts
for each frontend answer field so it can build evidence rows. Keep this
in sync with PERSONA_SCREENS in TripPreferences.jsx.

GLOBAL CONSUMER RULE — emotional_signature is private framing only:
- Never mention the raw signature key in user-facing text.
- Never describe the user as "a {signature}".
- Never expose taxonomy vocabulary to the LLM's output stream.
Use emotional_tone (the short generated phrase) and signature-derived
framing/scene/cadence instead.
"""

EMOTIONAL_SIGNATURE_TAXONOMY: dict[str, str] = {
    "reset_seeker":
        "travels to decompress, soften, and feel distance from ordinary pressure",
    "stimulation_seeker":
        "travels to feel energized, overwhelmed, surprised, and fully awake",
    "story_collector":
        "travels to accumulate memorable moments, detours, and stories worth retelling",
    "connection_seeker":
        "travels to feel emotionally close to people through shared experiences",
    "belonging_seeker":
        "travels to feel temporarily at home in unfamiliar places and environments",
    "quiet_observer":
        "travels to notice, absorb, and move through places without needing constant intensity",
    "aesthetic_hunter":
        "travels for atmosphere, beauty, sensory texture, and strong mood",
    "self_expander":
        "travels to feel more capable, confident, interesting, or transformed",
}


# Maps each frontend persona-answer field to its human-readable question
# prompt. The emotional-signature inferrer joins these with user answers to
# build evidence rows the LLM can ground in.
PERSONA_QUESTION_CATALOG: dict[str, dict[str, str]] = {
    "social_role": {
        "prompt": "On a trip, people usually end up relying on you for:",
    },
    "trip_feeling": {
        "prompt": "The best trips usually leave you feeling:",
    },
    "friction_response": {
        "prompt": "Something goes wrong halfway through the day. Your instinct is to:",
    },
    "ideal_atmosphere": {
        "prompt": "You instantly feel at home in places that are:",
    },
    "small_thing": {
        "prompt": "What's a tiny thing that made life feel unusually good recently?",
        "kind": "free_text",
    },
}
