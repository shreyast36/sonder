"""
Canonical natural-language labels for persona radio answers.

The frontend stores user selections as snake_case keys (e.g. 'find_familiar')
because those are stable and small. Embedding those keys directly is wasteful
— the semantic signal lives in the original label copy. This module maps each
key back to its evocative natural-language form so the embedder sees the
text the user actually read.

Must stay in sync with PERSONA_SCREENS in jahnvi/frontend/src/pages/TripPreferences.jsx.
"""

PERSONA_LABELS: dict[str, dict[str, str]] = {
    "friends_would_say": {
        "knows_someone":      "Knows someone everywhere",
        "line_friends":       "Makes new friends in every line they stand in",
        "vanishes_for_story": "Vanishes for an hour and comes back with a story",
        "planner":            "Has the spreadsheet, the playlist, and the backup plan",
    },
    "restaurant_order": {
        "cant_miss":        "Ask the server what you absolutely can't miss",
        "order_for_table":  "Order for the table before anyone else is ready",
        "drink_and_sides":  "Get a drink and three sides, somehow that's dinner",
        "find_familiar":    "Find the one familiar thing and commit to it",
    },
    "what_you_notice": {
        "light_feel":  "The light and the way the room feels",
        "sounds":      "The sounds — music, voices, kitchen clatter",
        "smell":       "The smell — bread, candles, something on the fire",
        "people_move": "What people are wearing and how they move",
    },
    "ideal_atmosphere": {
        "wood_bar":       "Wood-panelled bar, low lighting, nobody rushing you out",
        "loud_lunch":     "Bright sun, loud lunch, two bottles already on the table",
        "concrete_neon":  "Concrete, neon, music you feel in your ribs",
        "quiet_morning":  "Quiet morning, open windows, nowhere to be for hours",
    },
}


def label_for(field: str, key: str | None) -> str:
    """Look up the natural-language label for a (field, key) pair. Empty string if missing."""
    if not key:
        return ""
    return PERSONA_LABELS.get(field, {}).get(key, "")
