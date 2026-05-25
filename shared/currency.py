"""
Currency conversion utility. Used by jahnvi/pipeline/module1_constraints.py to
normalise user budget input to USD before it enters the rest of the system.

All internal cost fields (budget_usd, cost_usd, avg_daily_cost_usd, total_budget_usd,
daily_cost_usd) are denominated in USD. Conversion happens once at the input boundary —
nothing downstream needs to change.

We use a static FALLBACK_RATES table for 30 common currencies. A live-rate API
integration was scoped initially but never shipped; the static table is accurate
enough for budget-tier classification (where the user's intent is ranges like
"mid-range" / "luxury" rather than a precise figure). Refresh FALLBACK_RATES
periodically — quarterly is plenty.
"""

# Approximate rates to USD — refresh quarterly.
# Format: { ISO-4217 code: units-of-currency-per-1-USD }
FALLBACK_RATES: dict[str, float] = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "INR": 83.5,
    "JPY": 155.0,
    "CAD": 1.37,
    "AUD": 1.53,
    "SGD": 1.34,
    "AED": 3.67,
    "CHF": 0.90,
    "CNY": 7.24,
    "HKD": 7.82,
    "NZD": 1.63,
    "SEK": 10.6,
    "NOK": 10.7,
    "DKK": 6.88,
    "MXN": 17.2,
    "BRL": 5.05,
    "ZAR": 18.7,
    "IDR": 15900.0,
    "MYR": 4.72,
    "THB": 35.5,
    "PHP": 56.5,
    "VND": 25100.0,
    "KRW": 1340.0,
    "TRY": 32.2,
    "SAR": 3.75,
    "QAR": 3.64,
    "EGP": 30.9,
    "PKR": 278.0,
}


async def convert_to_usd(amount: float, currency_code: str) -> float:
    """
    Convert amount in the given currency to USD using FALLBACK_RATES.

    Expected input:
        amount        = 150000.0
        currency_code = "INR"

    Expected output:
        1796.41   (≈ 150000 / 83.5)

    Raises ValueError for unknown currency codes not in FALLBACK_RATES.
    Async signature is preserved for API compatibility with the orchestrator.
    """
    code = currency_code.upper()

    if code == "USD":
        return amount

    if code not in FALLBACK_RATES:
        raise ValueError(
            f"Unsupported currency '{currency_code}'. "
            f"Supported codes: {sorted(FALLBACK_RATES.keys())}"
        )
    return amount / FALLBACK_RATES[code]


def format_budget_display(budget_usd: float, currency_code: str) -> str:
    """
    Format a USD budget for display in the user's original currency.
    Used by the frontend to show "~₹1,50,000" alongside the stored USD value.

    Expected input:  budget_usd=1796.0, currency_code="INR"
    Expected output: "~₹1,49,866"
    """
    code = currency_code.upper()
    rate = FALLBACK_RATES.get(code, 1.0)
    local_amount = budget_usd * rate

    CURRENCY_SYMBOLS = {
        "USD": "$",   "EUR": "€",   "GBP": "£",   "INR": "₹",  "JPY": "¥",
        "CNY": "¥",   "KRW": "₩",   "SGD": "S$",  "AUD": "A$", "CAD": "C$",
        "CHF": "Fr.", "HKD": "HK$", "NZD": "NZ$", "MXN": "MX$",
        "SEK": "kr",  "NOK": "kr",
    }
    symbol = CURRENCY_SYMBOLS.get(code, code + " ")
    return f"~{symbol}{local_amount:,.0f}"
