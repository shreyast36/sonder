from jahnvi.schemas.user import TripConstraints
from jahnvi.schemas.enums import PacePreference
from shared.currency import convert_to_usd


async def capture_constraints(raw_input: dict) -> TripConstraints:
    """
    Parse and validate raw form data from Screen 2 into a TripConstraints object.
    Converts the user's budget to USD regardless of input currency.

    Expected input (from frontend form submission):
        {
            "destination_type":  "beach",
            "start_date":        "2025-06-01",
            "end_date":          "2025-06-07",
            "budget_amount":     150000.0,
            "budget_currency":   "INR",        # ISO 4217 — defaults to "USD" if omitted
            "group_size":        2,
            "pace_preference":   "relaxed",
            "must_haves":        ["snorkeling", "local food"],
            "avoid_list":        ["nightclubs"]
        }

    Expected output:
        TripConstraints(
            destination_type = "beach",
            start_date       = date(2025, 6, 1),
            end_date         = date(2025, 6, 7),
            budget_usd       = 1796.41,   # converted from 150000 INR
            budget_currency  = "INR",     # kept for display
            group_size       = 2,
            pace_preference  = PacePreference.relaxed,
            must_haves       = ["snorkeling", "local food"],
            avoid_list       = ["nightclubs"]
        )

    Validation rules:
        - end_date must be after start_date
        - budget_amount must be > 0
        - group_size must be >= 1
        - budget_currency must be a recognised ISO 4217 code (see shared/currency.py FALLBACK_RATES)
    """
    # TODO: parse start_date / end_date strings → date objects, validate order
    # TODO: validate budget_amount > 0, group_size >= 1
    # TODO: currency = raw_input.get("budget_currency", "USD").upper()
    # TODO: budget_usd = await convert_to_usd(raw_input["budget_amount"], currency)
    # TODO: return TripConstraints(**{...raw_input, "budget_usd": budget_usd, "budget_currency": currency})
    raise NotImplementedError
