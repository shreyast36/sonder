"""
Deterministic reveal copy for the persona screen.

The persona reveal screen renders four pieces of text, all derived from the
HF-scored top_push + top_interests + the user's own radio answer keys. No LLM
is involved — the persona reveal stays interpretable, stable, and free.

Voice rule: observational, low-ego, concrete nouns. Not horoscope, not MBTI.
"""

# ── Headline descriptor — short observational phrase ──────────────────────────
# Composed from top_push[0] (texture) + top_interests[0] (anchor). 6 × 6 = 36
# combos; composition keeps each combo readable without writing 36 unique strings.

_PUSH_TEXTURE = {
    "escape_reset":      "Quiet disconnection",
    "adventure_novelty": "Restless curiosity",
    "connection":        "Closeness in motion",
    "reflection":        "Slow thinking",
    "curiosity":         "Slow curiosity",
    "prestige_reward":   "Earned-it ceremony",
}

_PULL_ANCHOR = {
    "nature_outdoors":   "long days outside",
    "culture_history":   "old stones and slow museums",
    "food_drink":        "good food and long tables",
    "nightlife_social":  "loud rooms and late nights",
    "comfort_luxury":    "soft beds and zero friction",
    "exploration_local": "hidden corners and locals' tips",
}


def descriptor(top_push: str | None, top_interest: str | None) -> str:
    """Compose the headline descriptor from top_push[0] + top_interests[0]."""
    texture = _PUSH_TEXTURE.get(top_push or "", "")
    anchor  = _PULL_ANCHOR.get(top_interest or "", "")
    if texture and anchor:
        return f"{texture}, {anchor}"
    return texture or anchor or "Your travel persona"


# ── Paragraph — one per top_push primary ──────────────────────────────────────

_PARAGRAPH_BY_PUSH = {
    "escape_reset": (
        "You travel to feel slightly removed from your real life — enough "
        "structure to feel held, enough unpredictability to feel awake again."
    ),
    "adventure_novelty": (
        "You travel for the moments that don't yet have a script — the parts "
        "of the trip where you don't know how the day will end."
    ),
    "connection": (
        "You travel to be in the same room as the people who matter. "
        "Everything else — the food, the place, the pace — is the stage."
    ),
    "reflection": (
        "You travel to think more clearly. Distance from the routine, "
        "fewer voices in the room, mornings where the day hasn't decided itself yet."
    ),
    "curiosity": (
        "You travel because there's always more to understand — about a place, "
        "a cuisine, a way of living that isn't your own. Depth over breadth."
    ),
    "prestige_reward": (
        "This trip means something. Not just a holiday — a marker. A version "
        "of yourself you've been working toward gets to show up."
    ),
}


def paragraph(top_push: str | None) -> str:
    return _PARAGRAPH_BY_PUSH.get(top_push or "", _PARAGRAPH_BY_PUSH["curiosity"])


# ── Bullets — one per radio answer key (paraphrased into "drawn to" form) ─────

BULLET_BY_KEY: dict[str, str] = {
    # friends_would_say
    "knows_someone":      "people who feel like neighbours wherever you are",
    "line_friends":       "small talk that turns into a real conversation",
    "vanishes_for_story": "an hour that turns into a story",
    "planner":            "knowing what's next, with room to drift",

    # restaurant_order
    "cant_miss":         "the dish the server insists you have to try",
    "order_for_table":   "ordering for the table, sharing everything",
    "drink_and_sides":   "three appetizers and a drink, no main",
    "find_familiar":     "the one familiar thing in an unfamiliar place",

    # what_you_notice
    "light_feel":  "rooms with the right light",
    "sounds":      "music coming from somewhere you can't quite place",
    "smell":       "bread, candles, something on the fire",
    "people_move": "the way locals move through their city",

    # ideal_atmosphere
    "wood_bar":      "wood-panelled bars where no one's rushing you out",
    "loud_lunch":    "long, loud lunches that bleed into the afternoon",
    "concrete_neon": "rooms where the music hits you in the ribs",
    "quiet_morning": "mornings with nowhere to be",
}


def bullets_from_keys(keys: list[str | None]) -> list[str]:
    """Map a list of radio-answer keys to their bullet phrasings (drops empties)."""
    out = []
    for k in keys:
        phrase = BULLET_BY_KEY.get(k or "", "")
        if phrase:
            out.append(phrase)
    return out


SOFTENER = "Our read on you"
