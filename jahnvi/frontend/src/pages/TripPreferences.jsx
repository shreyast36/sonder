// TODO: Jahnvi — Screen 2: Trip Preferences form.
// Design ref: Figma screen 2 (destination input, date picker, budget slider, travel style grid, pace slider).
// On submit → POST to /api/plan-trip, stream SSE response, navigate to /itinerary.
//
// Budget input — multi-currency:
//   Render a currency selector (dropdown or auto-detected from browser locale) next to the budget field.
//   Send { budget_amount: number, budget_currency: "INR" } — NOT budget_usd.
//   The backend converts to USD in capture_constraints() via shared/currency.py.
//   After receiving the PlanTripResponse, display the total_budget_usd back in the user's
//   currency using format_budget_display() equivalent on the frontend:
//     const displayBudget = (usd) => (usd * APPROX_RATES[currency]).toLocaleString(locale, { style: "currency", currency })
//   Supported currencies: see FALLBACK_RATES in shared/currency.py for the full list.
