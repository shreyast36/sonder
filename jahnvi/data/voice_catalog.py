"""
Curated ElevenLabs voice catalog for synthetic co-travellers.

Hand-picked 16-voice slate, balanced 8 male / 8 female across 8 accent
regions. Selected to match the 16-city diversity matrix in the seed
script — no Anglo bias, no city→accent hardcode in the seed itself
(the mapping below is keyed on accent buckets, and personas land in a
bucket via `appearance_descriptor` rather than home city).

Voice assignment flow in the seed script:
    persona.appearance_descriptor → accent bucket → (gender) → voice_id

Add voices by appending to the right bucket; remove by dropping the
voice_id. The seed script reads this list directly, no script edits
needed.

Guardrails baked into how these voices are used:
- voice_clone is hardcoded to False everywhere
- only IDs in this catalog are valid for assignment
- accents are the LISTED labels (descriptive metadata), not enforced
  by ElevenLabs; the seed assumes the user-provided labels are accurate
"""

from __future__ import annotations

from typing import Literal

Gender = Literal["male", "female"]


# ── Voice records ──────────────────────────────────────────────────────────

# Each entry: (voice_id, gender, accent_bucket, display_name)
# accent_bucket values must match keys in ACCENT_TO_VOICES below.
VOICE_CATALOG: list[dict] = [
    {"voice_id": "zfpxqh60b0TrMkJHDLsR", "gender": "male",   "accent": "american",         "name": "NYC M"},
    {"voice_id": "Gvx1qZk9R4BUiBfsNPBU", "gender": "female", "accent": "american",         "name": "NYC F"},
    {"voice_id": "Yg7C1g7suzNt5TisIqkZ", "gender": "male",   "accent": "british",          "name": "British M"},
    {"voice_id": "k5o05luU9jyX4sn92sFW", "gender": "female", "accent": "british",          "name": "British F"},
    {"voice_id": "QZRlT5NqTgs34Uz6r1me", "gender": "male",   "accent": "latin_spanish",    "name": "Latin Spanish M"},
    {"voice_id": "pTX8uGyVgHCWLj6IkcbC", "gender": "female", "accent": "latin_spanish",    "name": "Latin Spanish F"},
    {"voice_id": "nwj0s2LU9bDWRKND5yzA", "gender": "male",   "accent": "indian",           "name": "Indian M"},
    {"voice_id": "vYENaCJHl4vFKNDYPr8y", "gender": "female", "accent": "indian",           "name": "Indian F"},
    {"voice_id": "IAkWen5Y9zgtcrKepkq8", "gender": "male",   "accent": "african_english",  "name": "African English M"},
    {"voice_id": "v411uyEKbaj63pTJHHbK", "gender": "female", "accent": "african_english",  "name": "African English F"},
    {"voice_id": "BHyvQU4czkhWdOZH4Rdq", "gender": "male",   "accent": "southeast_asian",  "name": "Singaporean M"},
    {"voice_id": "brM9iIbwDREZaWL8luun", "gender": "female", "accent": "southeast_asian",  "name": "Thai F"},
    {"voice_id": "dDpKZ6xv1gpboV4okVbc", "gender": "male",   "accent": "continental_eu",   "name": "French M"},
    {"voice_id": "BIvP0GN1cAtSRTxNHnWS", "gender": "female", "accent": "continental_eu",   "name": "German F"},
    {"voice_id": "VcFtBE4KloayRzveM90j", "gender": "male",   "accent": "middle_eastern",   "name": "Turkish M"},
    {"voice_id": "aCChyB4P5WEomwRsOKRh", "gender": "female", "accent": "middle_eastern",   "name": "Arabic F"},
]


# Reverse index: accent → {gender → voice_id}. Built once at import.
ACCENT_TO_VOICES: dict[str, dict[Gender, str]] = {}
for _entry in VOICE_CATALOG:
    ACCENT_TO_VOICES.setdefault(_entry["accent"], {})[_entry["gender"]] = _entry["voice_id"]


# ── appearance_descriptor → accent bucket ─────────────────────────────────


# Keyword fragments that route an LLM-A-written appearance_descriptor onto
# one of our 8 accent buckets. Lowercased substring match. Longer / more
# specific keywords come first so "south asian" beats "asian".
# Order matters: first match wins.
APPEARANCE_TO_ACCENT: list[tuple[str, str]] = [
    # Indian / South Asian
    ("indian",              "indian"),
    ("south asian",         "indian"),
    ("pakistani",           "indian"),
    ("bangladeshi",         "indian"),
    ("sri lankan",          "indian"),
    ("nepali",              "indian"),

    # African English (Nigerian, South African, etc — Sub-Saharan)
    ("nigerian",            "african_english"),
    ("ghanaian",            "african_english"),
    ("kenyan",              "african_english"),
    ("south african",       "african_english"),
    ("ethiopian",           "african_english"),
    ("african",             "african_english"),  # broad fallback

    # Middle Eastern (Arabic, Turkish, Iranian, etc)
    ("arab",                "middle_eastern"),
    ("turkish",             "middle_eastern"),
    ("iranian",             "middle_eastern"),
    ("persian",             "middle_eastern"),
    ("egyptian",            "middle_eastern"),
    ("lebanese",            "middle_eastern"),
    ("israeli",             "middle_eastern"),
    ("middle eastern",      "middle_eastern"),

    # Latin Spanish (Latin American + Iberian)
    ("mexican",             "latin_spanish"),
    ("argentin",            "latin_spanish"),
    ("colombian",           "latin_spanish"),
    ("brazilian",           "latin_spanish"),
    ("peruvian",            "latin_spanish"),
    ("chilean",             "latin_spanish"),
    ("portuguese",          "latin_spanish"),
    ("spanish",             "latin_spanish"),
    ("latin",               "latin_spanish"),
    ("hispanic",            "latin_spanish"),
    ("latina",              "latin_spanish"),
    ("latino",              "latin_spanish"),

    # Southeast Asian (Singaporean, Thai, Malaysian, Vietnamese, Indonesian, Filipino — plus East Asian fallback)
    ("singaporean",         "southeast_asian"),
    ("thai",                "southeast_asian"),
    ("malaysian",           "southeast_asian"),
    ("vietnamese",          "southeast_asian"),
    ("indonesian",          "southeast_asian"),
    ("filipino",            "southeast_asian"),
    ("japanese",            "southeast_asian"),  # gap — no JP voice; nearest substitute
    ("korean",              "southeast_asian"),  # gap — no KR voice; nearest substitute
    ("chinese",             "southeast_asian"),
    ("east asian",          "southeast_asian"),
    ("southeast asian",     "southeast_asian"),
    ("asian",               "southeast_asian"),  # broad fallback

    # Continental European (French, German, Dutch, Scandinavian, Italian, etc)
    ("french",              "continental_eu"),
    ("german",              "continental_eu"),
    ("dutch",               "continental_eu"),
    ("italian",             "continental_eu"),
    ("swedish",             "continental_eu"),
    ("norwegian",           "continental_eu"),
    ("danish",              "continental_eu"),
    ("polish",              "continental_eu"),
    ("european",            "continental_eu"),

    # British (UK + Ireland)
    ("british",             "british"),
    ("english",             "british"),
    ("scottish",            "british"),
    ("welsh",               "british"),
    ("irish",               "british"),
    ("uk",                  "british"),

    # American (default for US-based or unspecified)
    ("american",            "american"),
    ("canadian",            "american"),
    ("us-",                 "american"),
]


# ── Public API ────────────────────────────────────────────────────────────


def accent_for_appearance(descriptor: str | None) -> str:
    """Map an `appearance_descriptor` to an accent bucket.

    Falls back to `american` for empty/unmatched descriptors — least
    awkward default and matches the NYC personas in the matrix.
    """
    if not descriptor:
        return "american"
    lowered = descriptor.lower()
    for fragment, accent in APPEARANCE_TO_ACCENT:
        if fragment in lowered:
            return accent
    return "american"


def voice_for(appearance_descriptor: str | None, gender: Gender) -> dict:
    """Return the voice_profile block for a synthetic persona.

    Shape matches what the seed script writes into the Pinecone metadata:
        {
          "enabled":          True,
          "provider":         "elevenlabs",
          "voice_id":         "...",
          "accent_bucket":    "indian",
          "assignment_basis": "appearance_descriptor + gender",
          "voice_clone":      False,
        }
    """
    accent = accent_for_appearance(appearance_descriptor)
    bucket = ACCENT_TO_VOICES.get(accent, {})
    voice_id = bucket.get(gender)
    if voice_id is None:
        # No voice for this (accent, gender) pair — fall back to American
        # of the requested gender. Catalog has both M+F for American so
        # this branch should never fully empty.
        voice_id = ACCENT_TO_VOICES["american"][gender]
        accent = "american"

    return {
        "enabled":          True,
        "provider":         "elevenlabs",
        "voice_id":         voice_id,
        "accent_bucket":    accent,
        "assignment_basis": "appearance_descriptor + gender",
        "voice_clone":      False,
    }
