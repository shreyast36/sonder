"""
Canonical persona archetypes for Sonder.

Owned by Jahnvi. Two consumers:
  - jahnvi/pipeline/module3_persona.py  — infer_persona() classifies a user into one of these
  - scripts/seed_pinecone.py            — generates synthetic warm-start profiles for launch

A PersonaTemplate defines the *signal profile* of an archetype: which interests, paces,
budget styles, and travel styles are typical, plus the keywords used to build the embed_text
string that goes into Pinecone.

build_embed_text() produces a deterministic embed string from a template + a specific
(pace, budget_style, travel_style) combination — this is what gets embedded and stored
as the Pinecone vector for a synthetic co-traveller profile.
"""

from typing import TypedDict


class PersonaTemplate(TypedDict):
    archetype:     str        # canonical archetype name
    interests:     list[str]  # typical top interests
    pace:          list[str]  # typical PacePreference values (subset of relaxed/moderate/packed)
    budget_styles: list[str]  # typical BudgetStyle values
    travel_styles: list[str]  # typical TravelStyle values
    energy:        int        # 1 (very low) to 5 (very high) — used to build embed text + infer_emotion
    embed_keywords: list[str] # domain vocabulary for this archetype; used in build_embed_text()
    label:         str        # short user-facing description (shown on match cards)


PERSONA_TEMPLATES: list[PersonaTemplate] = [
    {
        "archetype":      "Cultural Explorer",
        "interests":      ["culture", "food", "photography", "history", "art"],
        "pace":           ["relaxed", "moderate"],
        "budget_styles":  ["budget", "mid_range"],
        "travel_styles":  ["solo", "couple"],
        "energy":         2,
        "embed_keywords": ["culture", "food", "photography", "history", "art", "temples", "markets", "local"],
        "label":          "Discovers local culture through food, art, and photography at a relaxed pace.",
    },
    {
        "archetype":      "Adventure Seeker",
        "interests":      ["adventure", "nature", "hiking", "extreme sports"],
        "pace":           ["packed"],
        "budget_styles":  ["mid_range", "luxury"],
        "travel_styles":  ["solo", "group"],
        "energy":         5,
        "embed_keywords": ["adventure", "nature", "hiking", "extreme", "adrenaline", "outdoor", "active", "sports"],
        "label":          "Chases adrenaline through outdoor adventure and extreme sports.",
    },
    {
        "archetype":      "Relaxed Wanderer",
        "interests":      ["wellness", "nature", "yoga", "slow travel"],
        "pace":           ["relaxed"],
        "budget_styles":  ["budget", "mid_range"],
        "travel_styles":  ["solo", "couple"],
        "energy":         1,
        "embed_keywords": ["wellness", "nature", "yoga", "relaxed", "peaceful", "slow", "mindful", "retreat"],
        "label":          "Travels slowly, prioritising rest, nature, and mindful experiences.",
    },
    {
        "archetype":      "Party Traveller",
        "interests":      ["nightlife", "music", "festivals", "social"],
        "pace":           ["packed"],
        "budget_styles":  ["mid_range", "luxury"],
        "travel_styles":  ["group"],
        "energy":         5,
        "embed_keywords": ["nightlife", "music", "festivals", "parties", "social", "vibrant", "clubs", "events"],
        "label":          "Seeks vibrant nightlife, music festivals, and social experiences.",
    },
    {
        "archetype":      "Foodie",
        "interests":      ["food", "cooking", "markets", "wine"],
        "pace":           ["moderate"],
        "budget_styles":  ["mid_range", "luxury"],
        "travel_styles":  ["couple", "group"],
        "energy":         3,
        "embed_keywords": ["food", "culinary", "cooking", "cuisine", "markets", "restaurants", "street food", "wine"],
        "label":          "Travels to eat — culinary experiences drive every destination choice.",
    },
]

# Quick lookup by archetype name — used by infer_persona() and the seed script
TEMPLATES_BY_ARCHETYPE: dict[str, PersonaTemplate] = {
    t["archetype"]: t for t in PERSONA_TEMPLATES
}


def build_embed_text(
    template: PersonaTemplate,
    pace: str,
    budget_style: str,
    travel_style: str,
) -> str:
    """
    Build the embed_text string for a synthetic co-traveller profile.

    Expected input:
        template     = TEMPLATES_BY_ARCHETYPE["Cultural Explorer"]
        pace         = "relaxed"
        budget_style = "mid_range"
        travel_style = "couple"

    Expected output:
        "Cultural Explorer relaxed mid_range couple culture food photography history art temples markets local travel"
    """
    parts = [
        template["archetype"],
        pace,
        budget_style,
        travel_style,
        *template["embed_keywords"],
        "travel",
    ]
    return " ".join(parts)
