from jahnvi.schemas.user import TripConstraints
from jahnvi.schemas.enums import PacePreference


def capture_constraints(raw_input: dict) -> TripConstraints:
    """
    Parse and validate raw form data from Screen 2 into a TripConstraints object.

    Expected input (from frontend form submission):
        {
            "destination_type": "beach",
            "start_date": "2025-06-01",
            "end_date": "2025-06-07",
            "budget_usd": 2000.0,
            "group_size": 2,
            "pace_preference": "relaxed",
            "must_haves": ["snorkeling", "local food"],
            "avoid_list": ["nightclubs"]
        }

    Expected output:
        TripConstraints(
            destination_type = "beach",
            start_date       = date(2025, 6, 1),
            end_date         = date(2025, 6, 7),
            budget_usd       = 2000.0,
            group_size       = 2,
            pace_preference  = PacePreference.relaxed,
            must_haves       = ["snorkeling", "local food"],
            avoid_list       = ["nightclubs"]
        )

    Validation rules:
        - end_date must be after start_date
        - budget_usd must be > 0
        - group_size must be >= 1
    """
    # TODO: parse dates, validate fields, return TripConstraints(**raw_input)
    raise NotImplementedError
