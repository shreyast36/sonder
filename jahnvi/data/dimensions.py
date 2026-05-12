"""
Travel dimension vocabulary for scoring user persona answers.
Each dimension maps to the words and phrases that signal it.

Owned by Jahnvi — add or remove terms here as the product evolves.
Module 3 reads these to produce dimension scores; nothing is hardcoded in business logic.
"""

TRAVEL_DIMENSIONS: dict[str, list[str]] = {
    "adventure": [
        "adventure", "adrenaline", "hike", "hiking", "trek", "trekking",
        "climb", "climbing", "surf", "surfing", "dive", "diving", "rafting",
        "extreme", "outdoor", "active", "wild", "thrill", "challenge", "brave",
        "spontaneous", "impulsive", "unpredictable", "off the beaten",
    ],
    "culture": [
        "culture", "cultural", "history", "historical", "art", "arts", "museum",
        "gallery", "heritage", "architecture", "temple", "tradition", "local",
        "community", "learn", "understand", "meaning", "story", "storytelling",
        "ritual", "ceremony", "neighbourhood", "neighbourhood",
    ],
    "food": [
        "food", "eat", "eating", "cuisine", "restaurant", "culinary", "cook",
        "cooking", "taste", "flavour", "flavor", "street food", "wine", "market",
        "chef", "meal", "lunch", "dinner", "breakfast", "snack", "ingredients",
        "recipe", "local food", "foodie", "gastronomy", "tasting",
    ],
    "nature": [
        "nature", "beach", "mountain", "forest", "wildlife", "landscape", "scenic",
        "countryside", "ocean", "lake", "river", "park", "coast", "island",
        "sunset", "sunrise", "sky", "stars", "green", "trees", "fresh air",
        "animals", "bird", "sea", "water", "natural",
    ],
    "nightlife": [
        "nightlife", "party", "parties", "club", "clubbing", "bar", "festival",
        "music", "dance", "dancing", "social", "vibrant", "lively", "night",
        "evening", "cocktail", "drinks", "concert", "gig", "live music",
    ],
    "wellness": [
        "wellness", "yoga", "spa", "retreat", "mindful", "mindfulness", "peaceful",
        "meditation", "relax", "relaxation", "slow", "quiet", "recharge", "rest",
        "breathe", "calm", "serene", "tranquil", "detox", "unwind", "balance",
    ],
    "social": [
        "together", "shared", "companion", "friends", "group", "meet", "connect",
        "people", "conversation", "community", "talk", "laugh", "bond", "couple",
        "relationship", "together", "someone", "other people", "share",
    ],
    "discovery": [
        "discover", "explore", "hidden", "off the beaten", "unexpected", "unknown",
        "stumble", "wander", "new", "first time", "never been", "surprise",
        "curious", "wonder", "find", "secret", "undiscovered", "under the radar",
    ],
    "photography": [
        "photo", "photograph", "photography", "camera", "capture", "picture",
        "shoot", "visual", "image", "document", "memory", "instagram",
    ],
    "luxury": [
        "luxury", "luxurious", "five star", "5 star", "high end", "premium",
        "boutique", "exclusive", "splurge", "treat", "indulge", "finest",
        "champagne", "private", "concierge",
    ],
    "budget": [
        "budget", "cheap", "affordable", "backpack", "hostel", "frugal",
        "save money", "cost-effective", "value", "economical", "cheap eats",
        "free", "walking", "local transport",
    ],
    "slow_travel": [
        "slow", "linger", "settle", "stay", "weeks", "month", "longer", "deep",
        "one place", "really know", "roots", "immersed", "immerse", "really feel",
        "not rush", "no rush", "unhurried",
    ],
}

# Pace vocabulary — used to infer pace preference from free text
PACE_SIGNALS: dict[str, list[str]] = {
    "relaxed": ["slow", "leisurely", "linger", "wander", "unhurried", "gentle",
                "easy", "relaxed", "casual", "no rush", "quiet mornings"],
    "packed":  ["packed", "fast", "busy", "fit in", "see everything", "full day",
                "non-stop", "every hour", "squeeze", "as much as possible"],
}
