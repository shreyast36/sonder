"""
Smoke test -run manually to verify Ali's live API integrations.

    python -m ali.tests.smoke_test

Requires .env with at minimum:
    ANTHROPIC_API_KEY, OPENAI_API_KEY
    SMALL_MODEL_PROVIDER=anthropic SMALL_MODEL_NAME=claude-haiku-4-5
    LARGE_MODEL_PROVIDER=anthropic LARGE_MODEL_NAME=claude-sonnet-4-6
    EMBED_MODEL_PROVIDER=openai    EMBED_MODEL=text-embedding-3-small

For Pinecone tests (optional -skip if index not seeded):
    PINECONE_API_KEY, PINECONE_INDEX_NAME, EMBED_DIMENSIONS=1536
"""

import asyncio
import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from dotenv import load_dotenv
load_dotenv()

from shared.schemas import (
    UserProfile, TripConstraints, PersonaQuestionAnswers,
    Destination, Activity, CoTravellerProfile, CoTravellerMatch,
    PacePreference, BudgetStyle, TravelStyle, EmotionIntent,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

USER = UserProfile(
    user_id="smoke_test_user",
    display_name="Ali",
    constraints=TripConstraints(
        destination_query="Bali, Indonesia",
        destination_type="beach",
        start_date=date(2025, 6, 1),
        end_date=date(2025, 6, 4),
        budget_usd=1200.0,
        group_size=2,
        who_travelling_with=TravelStyle.couple,
        pace=PacePreference.relaxed,
        must_haves=["snorkeling"],
        avoid_list=["nightclubs"],
        social_role="place_finder",
        trip_feeling="story_collector",
        friction_response="pivot",
        ideal_atmosphere="slow_sunlit",
    ),
    persona_answers=PersonaQuestionAnswers(
        small_thing="cold sheets at the end of a long day",
    ),
    emotion_intent=EmotionIntent.excited,
    compatibility_signals={"top_interests": ["food", "culture"]},
)

DESTINATION = Destination(
    destination_id="bali_001", city="Bali", country="Indonesia",
    avg_daily_cost_usd=120.0, tags=["beach", "culture", "food"],
    description="Tropical island known for temples, rice terraces, and surf.",
)

ACTIVITIES = [
    Activity(activity_id="act_001", name="Uluwatu Temple Sunset", category="culture",
             cost_usd=10.0, duration_hours=2.0, tags=["culture", "sunset"],
             description="Clifftop sea temple with sweeping Indian Ocean views."),
    Activity(activity_id="act_002", name="Seminyak Beach Morning", category="beach",
             cost_usd=0.0, duration_hours=3.0, tags=["beach", "relaxed"],
             description="Relaxed morning swim on a popular beach."),
    Activity(activity_id="act_003", name="Ubud Cooking Class", category="food",
             cost_usd=45.0, duration_hours=4.0, tags=["food", "cooking"],
             description="Learn to cook traditional Balinese dishes."),
]

MATCH = CoTravellerMatch(
    profile=CoTravellerProfile(
        profile_id="maya_001", display_name="Maya Sharma", age=24,
        location="Delhi, India", archetype="Cultural Explorer",
        interests=["food", "culture", "photography"],
        pace=PacePreference.relaxed, budget_style=BudgetStyle.mid_range,
        travel_style=TravelStyle.couple,
    ),
    match_score=0.92,
    match_reasons=["Similar interest in food and culture", "Same travel pace"],
    compatibility_breakdown={"interests": 0.95, "pace": 1.0},
)


# ── Test helpers ──────────────────────────────────────────────────────────────

def ok(label):   print("  [PASS] " + str(label))
def fail(label, err): print(f"  [FAIL] {label}: {err}")


async def test_embeddings():
    print("\n[1] Embeddings (OpenAI text-embedding-3-small)")
    if not os.getenv("OPENAI_API_KEY"):
        print("  [SKIP] OPENAI_API_KEY not set -skipping.")
        print("     Embeddings are only needed for RAG ('Why this?' explanations).")
        print("     Core generation + routing works without it.")
        return
    try:
        from ali.vector.embeddings import embed_text, embed_batch, build_user_query
        vec = embed_text("Bali beach culture food")
        assert len(vec) == 1536
        ok(f"embed_text() -> {len(vec)}-dim vector")

        vecs = embed_batch(["Bali", "Kyoto", "Lisbon"])
        assert len(vecs) == 3
        ok(f"embed_batch() -> {len(vecs)} vectors")

        query = build_user_query(USER)
        assert "beach" in query and "relaxed" in query
        ok(f"build_user_query() -> '{query[:60]}...'")
    except Exception as e:
        fail("embeddings", e)


async def test_routing():
    print("\n[2] Routing engine")
    try:
        from ali.routing.engine import route_request
        response = await route_request(
            "short_explanation",
            "Say 'routing works' and nothing else.",
            "You are a test assistant. Follow instructions exactly."
        )
        assert response and len(response) > 0
        ok(f"route_request(small) -> '{response.strip()[:60]}'")
    except Exception as e:
        fail("routing", e)


async def test_itinerary_generation():
    print("\n[3] Itinerary generation (streaming)")
    try:
        from ali.generation.itinerary_generator import generate_itinerary
        from ali.generation.output_parser import parse_itinerary, validate_structure

        chunks = []
        async for chunk in generate_itinerary(USER, DESTINATION, ACTIVITIES):
            chunks.append(chunk)
        raw = "".join(chunks)
        ok(f"generate_itinerary() streamed {len(chunks)} chunks ({len(raw)} chars)")

        itinerary = parse_itinerary(raw, USER, destination=DESTINATION, activities=ACTIVITIES)
        ok("parse_itinerary() -> " + str(len(itinerary.days)) + " days, $" + str(int(itinerary.total_budget_usd)) + " total")

        assert validate_structure(itinerary)
        ok("validate_structure() passed")
    except Exception as e:
        fail("itinerary generation", e)


async def test_chat_topics():
    print("\n[4] Chat topics + icebreaker")
    try:
        from ali.generation.topics import generate_topics, generate_icebreaker

        topics = await generate_topics(USER, MATCH, __import__(
            "shared.schemas", fromlist=["Itinerary"]
        ).Itinerary(
            itinerary_id="itin_smoke", user_id="smoke_test_user",
            destination=DESTINATION, days=[], total_budget_usd=1200.0,
        ))
        assert len(topics) > 0
        ok(f"generate_topics() -> {topics}")

        icebreaker = await generate_icebreaker(USER, MATCH)
        assert len(icebreaker) > 0
        ok(f"generate_icebreaker() -> '{icebreaker}'")
    except Exception as e:
        fail("chat topics", e)


async def test_pinecone(skip=False):
    print("\n[5] Pinecone connection + retriever")
    if skip or not os.getenv("PINECONE_API_KEY"):
        print("  [SKIP] PINECONE_API_KEY not set -skipping. Seed first with:")
        print("     python -m scripts.seed_pinecone --namespace all")
        return
    try:
        from ali.vector.client import get_pinecone_index
        index = get_pinecone_index()
        stats = index.describe_index_stats()
        total = stats.get("total_vector_count", 0)
        ok(f"Pinecone connected -{total} vectors in index")

        if total == 0:
            print("  [SKIP] Index is empty -run: python -m scripts.seed_pinecone --namespace all")
            return

        from ali.rag.retriever import retrieve_activity_context
        context = await retrieve_activity_context(ACTIVITIES[0])
        ok(f"retrieve_activity_context() -> {len(context)} snippets")
    except Exception as e:
        fail("pinecone", e)


async def main():
    print("=" * 55)
    print("  Sonder - Ali module smoke test")
    print("=" * 55)
    await test_embeddings()
    await test_routing()
    await test_itinerary_generation()
    await test_chat_topics()
    await test_pinecone()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
