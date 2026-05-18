import logging
from datetime import date

from jahnvi.schemas.user import TripConstraints
from jahnvi.schemas.enums import TravelStyle
from shared.currency import convert_to_usd

logger = logging.getLogger(__name__)


async def capture_constraints(raw_input: dict) -> TripConstraints:
    """
    Parse and validate raw form data from Screen 2 into a TripConstraints object.
    If budget_currency is not USD, converts the amount to USD via shared/currency.py.
    USD budgets pass through unchanged.

    Expected input:
        {
            "destination_query":       "Bali",
            "destination_type":        "beach",
            "origin_query":            "London",
            "nationality":             "British",
            "start_date":              "2025-06-01",
            "end_date":                "2025-06-07",
            "flexible_dates":          false,
            "budget_amount":           2000.0,
            "budget_currency":         "GBP",
            "budget_includes_flights": true,
            "group_size":              2,
            "who_travelling_with":     "couple",
            "accommodation_types":     ["Boutique", "Hotel"],
            "hire_car":                true,
            "has_driving_licence":     true,
            "mobility_notes":          "",
            "dietary_notes":           "vegetarian",
            "must_haves":              ["snorkeling", "local food"],
            "avoid_list":              ["nightclubs"]
        }

    Expected output:
        TripConstraints(
            destination_query        = "Bali",
            nationality              = "British",
            start_date               = date(2025, 6, 1),
            end_date                 = date(2025, 6, 7),
            budget_usd               = 2531.65,
            budget_currency          = "GBP",
            ...
        )
    """
    start_date = _parse_date(raw_input.get("start_date"))
    end_date   = _parse_date(raw_input.get("end_date"))
    if start_date and end_date and end_date <= start_date:
        raise ValueError("end_date must be after start_date")

    currency      = str(raw_input.get("budget_currency") or "USD").upper()
    budget_amount = float(raw_input.get("budget_amount") or raw_input.get("budget_usd") or 0)
    if budget_amount < 0:
        raise ValueError("budget must be non-negative")
    budget_usd = await convert_to_usd(budget_amount, currency) if budget_amount > 0 else 0.0

    group_size = int(raw_input.get("group_size") or 1)
    if group_size < 1:
        raise ValueError("group_size must be at least 1")

    who_raw             = raw_input.get("who_travelling_with")
    who_travelling_with = None
    if who_raw:
        try:
            who_travelling_with = TravelStyle(who_raw)
        except ValueError:
            logger.warning("Unknown TravelStyle value '%s' — ignoring", who_raw)

    hire_car            = bool(raw_input.get("hire_car", False))
    has_driving_licence = raw_input.get("has_driving_licence")
    if has_driving_licence is not None:
        has_driving_licence = bool(has_driving_licence)

    return TripConstraints(
        destination_query       = str(raw_input.get("destination_query") or ""),
        destination_type        = str(raw_input.get("destination_type") or ""),
        origin_query            = str(raw_input.get("origin_query") or ""),
        nationality             = str(raw_input.get("nationality") or ""),
        start_date              = start_date,
        end_date                = end_date,
        flexible_dates          = bool(raw_input.get("flexible_dates", False)),
        budget_usd              = round(budget_usd, 2),
        budget_currency         = currency,
        budget_includes_flights = bool(raw_input.get("budget_includes_flights", True)),
        group_size              = group_size,
        who_travelling_with     = who_travelling_with,
        accommodation_types     = list(raw_input.get("accommodation_types") or []),
        hire_car                = hire_car,
        has_driving_licence     = has_driving_licence,
        mobility_notes          = str(raw_input.get("mobility_notes") or ""),
        dietary_notes           = str(raw_input.get("dietary_notes") or ""),
        must_haves              = list(raw_input.get("must_haves") or []),
        avoid_list              = list(raw_input.get("avoid_list") or []),
    )


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ValueError(f"Invalid date format: '{value}' — expected YYYY-MM-DD")
