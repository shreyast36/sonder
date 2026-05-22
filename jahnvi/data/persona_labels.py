"""
Canonical natural-language labels for persona radio answers.

The frontend stores user selections as snake_case keys because those are
stable and small. Embedding those keys directly is wasteful — the semantic
signal lives in the original label copy. This module maps each key back to
its evocative natural-language form so the embedder sees the text the user
actually read.

The four radio questions are designed to surface latent travel psychology
without ever asking it directly:

- social_role       → social role + emotional regulation under chaos
- trip_feeling      → push/pull/motivation (the cleanest PPM signal we have)
- friction_response → resilience, control orientation, anxiety style
- ideal_atmosphere  → stimulation threshold, pacing, introvert/extrovert

The fifth question (small_thing, free text) is the gold ground-truth the
LLM uses for metaphor and emotional cadence — it lives on
PersonaQuestionAnswers, not in this radio map.

Must stay in sync with PERSONA_SCREENS in
jahnvi/frontend/src/pages/TripPreferences.jsx.
"""

PERSONA_LABELS: dict[str, dict[str, str]] = {
    "social_role": {
        "place_finder":  "Finding the place everyone talks about for years after",
        "social_bridge": "Talking to strangers nobody else would approach",
        "day_anchor":    "Keeping the day from completely falling apart",
        "pace_reader":   "Noticing when everyone needs to slow down",
    },
    "trip_feeling": {
        "brain_louder":    "Like your brain got louder in a good way",
        "disappeared":     "Like you disappeared from your normal life for a bit",
        "story_collector": "Like you collected stories you'll tell forever",
        "exhaled":         "Like you finally exhaled properly",
    },
    "friction_response": {
        "regroup":  "Find somewhere good to sit and regroup",
        "pivot":    "Turn the detour into the new plan",
        "fix_fast": "Fix it immediately before it gets worse",
        "mask":     "Pretend it's fine until someone notices",
    },
    "ideal_atmosphere": {
        "loud_anonymous":  "Loud enough that nobody notices your conversation",
        "quiet_attentive": "Quiet enough to hear glasses and footsteps",
        "lively_chaos":    "Slightly chaotic, but in a way that feels alive",
        "slow_sunlit":     "Slow, sunlit, and impossible to rush through",
    },
}


def label_for(field: str, key: str | None) -> str:
    """Look up the natural-language label for a (field, key) pair. Empty string if missing."""
    if not key:
        return ""
    return PERSONA_LABELS.get(field, {}).get(key, "")
