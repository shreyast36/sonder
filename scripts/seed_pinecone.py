"""
Pinecone seeding script — Shreyas owns this.

Run once before launch to populate the three index namespaces:
    destinations   — one vector per destination
    activities     — one vector per activity (metadata includes destination_id)
    cotravellers   — one vector per user profile (upserted on signup)

Usage:
    python -m scripts.seed_pinecone [--namespace destinations|activities|cotravellers|all]

Prerequisites:
    PINECONE_API_KEY, PINECONE_INDEX_NAME, EMBED_MODEL_PROVIDER, EMBED_MODEL set in .env
    pip install -r requirements.txt

Data sources (Shreyas decides):
    - Destinations + activities: replace SAMPLE_DESTINATIONS and SAMPLE_ACTIVITIES below
      with data from a travel API (e.g. Amadeus, Foursquare Places, Tripadvisor Content API)
      or a curated CSV. The structure must match the shapes below exactly.
    - Co-traveller profiles: seeded automatically on user signup via upsert_cotraveller_profile().
      The SAMPLE_COTRAVELLERS below are synthetic warm-start profiles for launch — remove once
      real users exist.
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from shreyas.retrieval.client import get_pinecone_index
from shreyas.retrieval.embeddings import embed_text, embed_batch
from jahnvi.data.persona_templates import build_embed_text, TEMPLATES_BY_ARCHETYPE


# ── Sample data — replace with real data before launch ──────────────────────────

SAMPLE_DESTINATIONS = [
    {
        "id":               "dest_001",
        "city":             "Bali",
        "country":          "Indonesia",
        "destination_type": "beach",
        "avg_daily_cost_usd": 120,
        "tags":             ["beach", "culture", "food", "temples", "surfing"],
        "embed_text":       "Bali Indonesia beach culture food temples surfing relaxed tropical",
    },
    {
        "id":               "dest_002",
        "city":             "Kyoto",
        "country":          "Japan",
        "destination_type": "city",
        "avg_daily_cost_usd": 180,
        "tags":             ["culture", "history", "temples", "food", "nature"],
        "embed_text":       "Kyoto Japan culture history temples food nature zen peaceful",
    },
    {
        "id":               "dest_003",
        "city":             "Lisbon",
        "country":          "Portugal",
        "destination_type": "city",
        "avg_daily_cost_usd": 140,
        "tags":             ["culture", "food", "history", "nightlife", "ocean"],
        "embed_text":       "Lisbon Portugal culture food history nightlife ocean fado trams",
    },
    {
        "id":               "dest_004",
        "city":             "Queenstown",
        "country":          "New Zealand",
        "destination_type": "adventure",
        "avg_daily_cost_usd": 200,
        "tags":             ["adventure", "nature", "skiing", "bungee", "hiking"],
        "embed_text":       "Queenstown New Zealand adventure nature skiing bungee hiking adrenaline",
    },
    {
        "id":               "dest_005",
        "city":             "Marrakech",
        "country":          "Morocco",
        "destination_type": "cultural",
        "avg_daily_cost_usd": 90,
        "tags":             ["culture", "food", "markets", "history", "desert"],
        "embed_text":       "Marrakech Morocco culture food souks history desert medina spices",
    },
]

SAMPLE_ACTIVITIES = [
    # Bali
    {"id": "act_001", "destination_id": "dest_001", "name": "Uluwatu Temple Sunset",   "category": "culture",    "duration_hours": 2.0, "cost_usd": 10,  "tags": ["culture", "sunset", "temple"],    "embed_text": "Uluwatu Temple Bali cliff sunset Kecak dance culture"},
    {"id": "act_002", "destination_id": "dest_001", "name": "Seminyak Beach Morning",  "category": "beach",      "duration_hours": 3.0, "cost_usd": 0,   "tags": ["beach", "relaxed", "swimming"],   "embed_text": "Seminyak beach Bali morning swim relax"},
    {"id": "act_003", "destination_id": "dest_001", "name": "Ubud Cooking Class",      "category": "food",       "duration_hours": 4.0, "cost_usd": 45,  "tags": ["food", "cooking", "culture"],     "embed_text": "Ubud Bali cooking class local food culture"},
    # Kyoto
    {"id": "act_004", "destination_id": "dest_002", "name": "Fushimi Inari Hike",      "category": "nature",     "duration_hours": 3.0, "cost_usd": 0,   "tags": ["nature", "hiking", "culture"],    "embed_text": "Fushimi Inari shrine torii gates hike Kyoto Japan"},
    {"id": "act_005", "destination_id": "dest_002", "name": "Arashiyama Bamboo Grove", "category": "nature",     "duration_hours": 1.5, "cost_usd": 0,   "tags": ["nature", "photography", "walk"],  "embed_text": "Arashiyama bamboo grove Kyoto peaceful walk photography"},
    # Lisbon
    {"id": "act_006", "destination_id": "dest_003", "name": "Alfama Fado Night",       "category": "nightlife",  "duration_hours": 3.0, "cost_usd": 35,  "tags": ["nightlife", "music", "culture"],  "embed_text": "Alfama Lisbon fado music night culture local"},
    {"id": "act_007", "destination_id": "dest_003", "name": "Pastéis de Belém Tour",   "category": "food",       "duration_hours": 2.0, "cost_usd": 15,  "tags": ["food", "culture", "history"],     "embed_text": "Belem Lisbon pastel de nata food history culture"},
    # Queenstown
    {"id": "act_008", "destination_id": "dest_004", "name": "Shotover Jet Boat",       "category": "adventure",  "duration_hours": 1.0, "cost_usd": 120, "tags": ["adventure", "adrenaline", "water"], "embed_text": "Shotover jet boat Queenstown adventure adrenaline"},
    {"id": "act_009", "destination_id": "dest_004", "name": "Nevis Bungee Jump",       "category": "adventure",  "duration_hours": 2.0, "cost_usd": 250, "tags": ["adventure", "extreme", "adrenaline"], "embed_text": "Nevis bungee jump Queenstown extreme adventure"},
    # Marrakech
    {"id": "act_010", "destination_id": "dest_005", "name": "Djemaa el-Fna Evening",   "category": "culture",    "duration_hours": 3.0, "cost_usd": 5,   "tags": ["culture", "food", "markets"],     "embed_text": "Djemaa el-Fna square Marrakech evening food culture market"},
]

# Synthetic co-traveller profiles for warm-start matching at launch.
# Replace / supplement with real user profiles as they sign up.
#
# embed_text is generated via build_embed_text() from jahnvi/data/persona_templates.py
# so it stays consistent with what infer_persona() produces for real users.
# To add more synthetic profiles: pick an archetype from TEMPLATES_BY_ARCHETYPE and
# call build_embed_text(template, pace, budget_style, travel_style).
_ct = [
    ("ct_001", "synthetic_maya_001",  "Maya Sharma",   "Delhi, India",    "Cultural Explorer", ["food", "culture", "photography"],  "relaxed",  "mid_range", "couple"),
    ("ct_002", "synthetic_raj_002",   "Raj Patel",     "Mumbai, India",   "Adventure Seeker",  ["adventure", "nature", "hiking"],   "packed",   "mid_range", "solo"),
    ("ct_003", "synthetic_sarah_003", "Sarah Chen",    "Singapore",       "Foodie",            ["food", "nightlife", "cooking"],    "moderate", "luxury",    "group"),
    ("ct_004", "synthetic_james_004", "James O'Brien", "London, UK",      "Cultural Explorer", ["history", "culture", "art"],       "relaxed",  "budget",    "solo"),
    ("ct_005", "synthetic_priya_005", "Priya Nair",    "Bangalore, India","Relaxed Wanderer",  ["yoga", "nature", "wellness"],      "relaxed",  "mid_range", "couple"),
]

SAMPLE_COTRAVELLERS = [
    {
        "id":           cid,
        "profile_id":   pid,
        "display_name": name,
        "location":     loc,
        "interests":    interests,
        "pace":         pace,
        "budget_style": budget,
        "embed_text":   build_embed_text(TEMPLATES_BY_ARCHETYPE[archetype], pace, budget, style),
    }
    for cid, pid, name, loc, archetype, interests, pace, budget, style in _ct
]


# ── Seeding functions ────────────────────────────────────────────────────────────

def seed_destinations():
    print("Seeding destinations...")
    index = get_pinecone_index()
    texts = [d["embed_text"] for d in SAMPLE_DESTINATIONS]
    vectors = embed_batch(texts)
    records = [
        {
            "id":       d["id"],
            "values":   v,
            "metadata": {k: val for k, val in d.items() if k not in ("id", "embed_text")},
        }
        for d, v in zip(SAMPLE_DESTINATIONS, vectors)
    ]
    index.upsert(vectors=records, namespace="destinations")
    print(f"  Upserted {len(records)} destinations.")


def seed_activities():
    print("Seeding activities...")
    index = get_pinecone_index()
    texts = [a["embed_text"] for a in SAMPLE_ACTIVITIES]
    vectors = embed_batch(texts)
    records = [
        {
            "id":       a["id"],
            "values":   v,
            "metadata": {k: val for k, val in a.items() if k not in ("id", "embed_text")},
        }
        for a, v in zip(SAMPLE_ACTIVITIES, vectors)
    ]
    index.upsert(vectors=records, namespace="activities")
    print(f"  Upserted {len(records)} activities.")


def seed_cotravellers():
    print("Seeding synthetic co-traveller profiles...")
    index = get_pinecone_index()
    texts = [c["embed_text"] for c in SAMPLE_COTRAVELLERS]
    vectors = embed_batch(texts)
    records = [
        {
            "id":       c["id"],
            "values":   v,
            "metadata": {k: val for k, val in c.items() if k not in ("id", "embed_text")},
        }
        for c, v in zip(SAMPLE_COTRAVELLERS, vectors)
    ]
    index.upsert(vectors=records, namespace="cotravellers")
    print(f"  Upserted {len(records)} co-traveller profiles.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Pinecone index for Sonder")
    parser.add_argument(
        "--namespace",
        choices=["destinations", "activities", "cotravellers", "all"],
        default="all",
    )
    args = parser.parse_args()

    if args.namespace in ("destinations", "all"):
        seed_destinations()
    if args.namespace in ("activities", "all"):
        seed_activities()
    if args.namespace in ("cotravellers", "all"):
        seed_cotravellers()

    print("Done.")
