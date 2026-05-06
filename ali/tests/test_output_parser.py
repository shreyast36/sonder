import pytest
from ali.generation.output_parser import parse_itinerary, validate_structure
from shared.schemas import Itinerary


# ── parse_itinerary — stub ────────────────────────────────────────────────────

def test_parse_itinerary_stub(user_profile):
    with pytest.raises(NotImplementedError):
        parse_itinerary('{"itinerary_id": "itin_001", "days": []}', user_profile)
    # TODO: clean JSON → Itinerary object


def test_parse_itinerary_strips_markdown_fences_stub(user_profile):
    raw = '```json\n{"itinerary_id": "itin_001", "days": []}\n```'
    with pytest.raises(NotImplementedError):
        parse_itinerary(raw, user_profile)
    # TODO: strips ``` fences before parsing; retries once on malformed JSON


def test_parse_itinerary_raises_on_missing_fields_stub(user_profile):
    with pytest.raises(NotImplementedError):
        parse_itinerary('{"days": []}', user_profile)  # missing itinerary_id
    # TODO: raises ValueError with a clear message when required fields are absent


# ── validate_structure — stub ─────────────────────────────────────────────────

def test_validate_structure_stub(itinerary):
    with pytest.raises(NotImplementedError):
        validate_structure(itinerary)
    # TODO: True when days non-empty, each day has ≥1 activity, total_budget_usd > 0


def test_validate_structure_empty_days_fails_stub(destination):
    from shared.schemas import Itinerary
    empty_itinerary = Itinerary(
        itinerary_id="itin_empty",
        user_id="test_user_001",
        destination=destination,
        days=[],
        total_budget_usd=0.0,
    )
    with pytest.raises(NotImplementedError):
        validate_structure(empty_itinerary)
    # TODO: returns False — no days generated
