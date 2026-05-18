"""
Demo script for Ali's AI module.

    python -m ali.demo
"""
import asyncio
import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv()

from shared.schemas import (
    UserProfile, TripConstraints, PersonaQuestionAnswers,
    Destination, Activity, CoTravellerProfile, CoTravellerMatch,
    PacePreference, BudgetStyle, TravelStyle, EmotionIntent,
)
from ali.routing.engine import route_request, stream_request
from ali.generation.itinerary_generator import generate_itinerary
from ali.generation.output_parser import parse_itinerary, validate_structure
from ali.generation.topics import generate_topics, generate_icebreaker

# ── Demo data ─────────────────────────────────────────────────────────────────

USER = UserProfile(
    user_id="demo_user_001",
    display_name="Ali",
    constraints=TripConstraints(
        destination_type="beach",
        start_date=date(2025, 6, 1),
        end_date=date(2025, 6, 4),
        budget_usd=1200.0,
        group_size=2,
        pace_preference=PacePreference.relaxed,
        must_haves=["snorkeling"],
        avoid_list=["nightclubs"],
    ),
    persona_answers=PersonaQuestionAnswers(
        food_interest=5, adventure_interest=2, culture_interest=4,
        nature_interest=3, nightlife_interest=1,
        budget_style=BudgetStyle.mid_range, travel_style=TravelStyle.couple,
        pace_preference=PacePreference.relaxed, energy_level=3,
    ),
    emotion_intent=EmotionIntent.excited,
    compatibility_signals={"top_interests": ["food", "culture"]},
)

DESTINATION = Destination(
    destination_id="bali_001", city="Bali", country="Indonesia",
    avg_daily_cost_usd=120.0, tags=["beach", "culture", "food", "nature"],
    description="Tropical island known for temples, rice terraces, and surf.",
)

ACTIVITIES = [
    Activity(activity_id="act_001", name="Uluwatu Temple Sunset", category="culture",
             cost_usd=10.0, duration_hours=2.0, tags=["culture", "sunset", "temple"],
             description="Clifftop sea temple with sweeping Indian Ocean views and Kecak dance."),
    Activity(activity_id="act_002", name="Seminyak Beach Morning", category="beach",
             cost_usd=0.0, duration_hours=3.0, tags=["beach", "relaxed", "swimming"],
             description="Relaxed morning swim on one of Bali's most popular beaches."),
    Activity(activity_id="act_003", name="Ubud Cooking Class", category="food",
             cost_usd=45.0, duration_hours=4.0, tags=["food", "cooking", "culture"],
             description="Learn to cook traditional Balinese dishes with a local chef."),
    Activity(activity_id="act_004", name="Snorkeling at Amed", category="adventure",
             cost_usd=35.0, duration_hours=3.0, tags=["snorkeling", "ocean", "adventure"],
             description="Crystal-clear waters with vibrant coral reefs and tropical fish."),
    Activity(activity_id="act_005", name="Tirta Empul Temple", category="culture",
             cost_usd=5.0, duration_hours=1.5, tags=["culture", "spiritual", "history"],
             description="Sacred Hindu temple with holy spring water purification pools."),
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
    match_reasons=["Similar interest in food and culture", "Same relaxed travel pace"],
    compatibility_breakdown={"interests": 0.95, "pace": 1.0, "budget": 0.88},
)


def divider(title=""):
    line = "=" * 60
    if title:
        print("\n" + line)
        print("  " + title)
        print(line)
    else:
        print(line)


async def demo_routing():
    divider("1. LLM ROUTING ENGINE")
    print("Task: 'short_explanation' -> SMALL tier")
    print("Prompt: 'Name one famous dish from Bali in 5 words.'")
    print()
    response = await route_request(
        "short_explanation",
        "Name one famous dish from Bali in 5 words or less.",
        "You are a travel expert. Be concise."
    )
    print("Response:", response.strip())


async def demo_generation():
    divider("2. ITINERARY GENERATION  (streaming live)")
    print(f"User: {USER.display_name} | {DESTINATION.city} | "
          f"{USER.constraints.pace_preference.value} pace | "
          f"${USER.constraints.budget_usd:.0f} budget | "
          f"{(USER.constraints.end_date - USER.constraints.start_date).days} days")
    print("Must-have: snorkeling | Avoid: nightclubs")
    print("\nStreaming itinerary...\n")

    chunks = []
    async for chunk in generate_itinerary(USER, DESTINATION, ACTIVITIES):
        print(chunk, end="", flush=True)
        chunks.append(chunk)

    raw = "".join(chunks)
    print("\n\nParsing itinerary...")
    itinerary = parse_itinerary(raw, USER, destination=DESTINATION, activities=ACTIVITIES)

    print()
    divider("Parsed Result")
    print(f"Destination : {itinerary.destination.city}, {itinerary.destination.country}")
    print(f"Days        : {len(itinerary.days)}")
    print(f"Total budget: ${itinerary.total_budget_usd:.0f}")
    print(f"Valid struct : {validate_structure(itinerary)}")
    print()
    for day in itinerary.days:
        print(f"  Day {day.day_number} - {day.theme or 'No theme'} (${day.daily_cost_usd:.0f})")
        for ia in day.activities:
            print(f"    {ia.time:10s}  {ia.activity.name}")

    return itinerary


async def demo_topics(itinerary):
    divider("3. CHAT TOPICS + ICEBREAKER")
    print(f"Match: {MATCH.profile.display_name} ({MATCH.profile.archetype})")
    print(f"Score: {MATCH.match_score * 100:.0f}%  |  {', '.join(MATCH.match_reasons)}")
    print()

    print("Generating conversation starters...")
    topics = await generate_topics(USER, MATCH, itinerary)
    print("\nTopics:")
    for i, t in enumerate(topics, 1):
        print(f"  {i}. {t}")

    print("\nGenerating icebreaker message...")
    icebreaker = await generate_icebreaker(USER, MATCH)
    print(f"\nIcebreaker:\n  \"{icebreaker}\"")


async def main():
    print()
    divider("SONDER - Ali's AI Module Demo")
    print("  Multi-model routing | Itinerary generation | Chat AI")
    divider()

    await demo_routing()
    itinerary = await demo_generation()
    await demo_topics(itinerary)

    print()
    divider("DEMO COMPLETE")
    print("  Routing engine    - small/large tier")
    print("  Itinerary stream  - token-by-token SSE-ready output")
    print("  Output parser     - JSON extraction + schema validation")
    print("  Chat AI           - personalised topics + icebreaker")
    print("=" * 60)
    print()


if __name__ == "__main__":
    asyncio.run(main())
