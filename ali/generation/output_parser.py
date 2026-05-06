import json
from shared.schemas import Itinerary, UserProfile


def parse_itinerary(raw: str, user_profile: UserProfile) -> Itinerary:
    """
    Parse raw LLM output into a structured Itinerary object.

    Expected input:
        raw = '{"itinerary_id": "itin_001", "days": [{"day_number": 1, "activities": [...]}], ...}'

    Expected output:
        Itinerary(itinerary_id="itin_001", days=[ItineraryDay(...)], ...)

    Error handling:
        - If JSON is malformed: extract the JSON block from the response and retry once
        - If required fields are missing: raise ValueError with a clear message
    """
    # TODO: json.loads(raw), map to Itinerary model, handle malformed JSON
    raise NotImplementedError


def validate_structure(itinerary: Itinerary) -> bool:
    """
    Quick structural check before passing to Mushahid's validator.
    Catches obvious generation failures (empty days, missing activities).

    Expected input:  Itinerary(days=[ItineraryDay(activities=[])], ...)
    Expected output: False  ← days exist but activities list is empty

    Checks:
        - itinerary.days is not empty
        - each day has at least one activity
        - total_budget_usd > 0
    """
    # TODO: implement checks, return True only if all pass
    raise NotImplementedError
