import json
import pytest
from ali.generation.output_parser import parse_itinerary, validate_structure
from shared.schemas import Itinerary

VALID_JSON = """{
  "itinerary_id": "itin_001",
  "user_id": "test_user_001",
  "destination": {
    "destination_id": "bali_001", "city": "Bali", "country": "Indonesia",
    "avg_daily_cost_usd": 120.0, "tags": ["beach"], "description": "Tropical island."
  },
  "days": [{
    "day_number": 1, "theme": "Culture Day", "daily_cost_usd": 140.0,
    "activities": [{
      "time": "9:00 AM", "why_this": null,
      "activity": {
        "activity_id": "uluwatu_001", "name": "Uluwatu Temple", "category": "culture",
        "cost_usd": 15.0, "duration_hours": 2.0, "tags": ["culture"],
        "description": "Clifftop temple."
      }
    }]
  }],
  "total_budget_usd": 840.0, "notes": [], "co_traveller_ids": []
}"""


def test_parse_clean_json(user_profile):
    itinerary = parse_itinerary(VALID_JSON, user_profile)
    assert isinstance(itinerary, Itinerary)
    assert itinerary.destination.city == "Bali"
    assert len(itinerary.days) == 1


def test_parse_strips_markdown_fences(user_profile):
    itinerary = parse_itinerary(f"```json\n{VALID_JSON}\n```", user_profile)
    assert itinerary.destination.city == "Bali"


def test_parse_strips_preamble_text(user_profile):
    itinerary = parse_itinerary(f"Here is your itinerary:\n{VALID_JSON}", user_profile)
    assert itinerary.destination.city == "Bali"


def test_parse_always_injects_user_id(user_profile):
    data = json.loads(VALID_JSON)
    data["user_id"] = "some_other_id"
    itinerary = parse_itinerary(json.dumps(data), user_profile)
    assert itinerary.user_id == user_profile.user_id


def test_parse_generates_itinerary_id_if_missing(user_profile):
    data = json.loads(VALID_JSON)
    del data["itinerary_id"]
    itinerary = parse_itinerary(json.dumps(data), user_profile)
    assert itinerary.itinerary_id.startswith("itin_")


def test_parse_raises_on_malformed_json(user_profile):
    with pytest.raises(ValueError, match="malformed JSON"):
        parse_itinerary("this is definitely not json", user_profile)


def test_validate_structure_passes(itinerary):
    assert validate_structure(itinerary) is True


def test_validate_structure_fails_empty_days(itinerary):
    itinerary.days = []
    assert validate_structure(itinerary) is False


def test_validate_structure_fails_empty_activities(itinerary):
    itinerary.days[0].activities = []
    assert validate_structure(itinerary) is False


def test_validate_structure_fails_zero_budget(itinerary):
    itinerary.total_budget_usd = 0
    assert validate_structure(itinerary) is False
