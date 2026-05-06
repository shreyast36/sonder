"""
Root conftest — fixtures available to all test modules.

Shared fixtures: constraints, persona_answers, user_profile, activity, destination, itinerary
HTTP client fixtures: client (async), override_auth (dependency override for verify_token)
"""
import pytest
from datetime import date
from shared.schemas import (
    TripConstraints, PersonaQuestionAnswers, UserProfile,
    Destination, Activity, ItineraryActivity, ItineraryDay, Itinerary,
    PacePreference, BudgetStyle, TravelStyle, EmotionIntent,
)


@pytest.fixture
def constraints():
    return TripConstraints(
        destination_type="beach",
        start_date=date(2025, 6, 1),
        end_date=date(2025, 6, 7),
        budget_usd=2000.0,
        group_size=2,
        pace_preference=PacePreference.relaxed,
        must_haves=["snorkeling"],
        avoid_list=["nightclubs"],
    )


@pytest.fixture
def persona_answers():
    return PersonaQuestionAnswers(
        food_interest=5,
        adventure_interest=2,
        culture_interest=4,
        nature_interest=3,
        nightlife_interest=1,
        budget_style=BudgetStyle.mid_range,
        travel_style=TravelStyle.couple,
        pace_preference=PacePreference.relaxed,
        energy_level=3,
    )


@pytest.fixture
def user_profile(constraints, persona_answers):
    return UserProfile(
        user_id="test_user_001",
        display_name="Test User",
        constraints=constraints,
        persona_answers=persona_answers,
        emotion_intent=EmotionIntent.excited,
        compatibility_signals={"pace": "relaxed", "top_interests": ["food", "culture"]},
    )


@pytest.fixture
def activity():
    return Activity(
        activity_id="uluwatu_001",
        name="Uluwatu Temple",
        category="culture",
        cost_usd=15.0,
        duration_hours=2.0,
        tags=["culture", "scenic", "spiritual"],
        description="Clifftop sea temple with sweeping Indian Ocean views.",
    )


@pytest.fixture
def destination():
    return Destination(
        destination_id="bali_001",
        city="Bali",
        country="Indonesia",
        avg_daily_cost_usd=120.0,
        tags=["beach", "culture", "food", "nature"],
        description="Tropical island known for temples, rice terraces, and surf.",
    )


@pytest.fixture
def itinerary(destination, activity):
    day = ItineraryDay(
        day_number=1,
        activities=[ItineraryActivity(activity=activity, time="9:00 AM")],
        daily_cost_usd=140.0,
        theme="Culture & Coastal Views",
    )
    return Itinerary(
        itinerary_id="itin_test_001",
        user_id="test_user_001",
        destination=destination,
        days=[day],
        total_budget_usd=840.0,
    )


# ── HTTP test client ──────────────────────────────────────────────────────────
# Requires: routers registered in mushahid/main.py (uncomment include_router calls).

@pytest.fixture
def override_auth():
    """Override verify_token so tests don't need a real Firebase token."""
    from mushahid.main import app
    from mushahid.auth import verify_token
    app.dependency_overrides[verify_token] = lambda: "test_user_001"
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def client():
    from httpx import AsyncClient, ASGITransport
    from mushahid.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
