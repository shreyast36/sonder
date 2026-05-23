from shared.schemas import ModelTier

# Task type → tier mapping. Ali decides the final assignments.
# These are suggestions — override as you benchmark latency and cost.
# Validator tasks (validate_itinerary, critic_check) are Mushahid's — not routed here.

TASK_TIER_MAP: dict[str, ModelTier] = {
    # Small tier — fast, cheap
    "chat_topics":          ModelTier.small,
    "icebreaker":           ModelTier.small,
    "persona_label":        ModelTier.small,
    "persona_emotional_signature": ModelTier.small,
    "preference_parse":     ModelTier.small,
    "quick_edit":           ModelTier.small,
    "notification_message": ModelTier.small,
    "short_explanation":    ModelTier.small,
    # Synthetic co-traveller's chat replies. 1-3 sentence text-message
    # register doesn't need Sonnet/GPT-4o — Haiku/GPT-4o-mini gives the
    # same persona voice ~3x faster, which the user actively feels in
    # the UI (typing indicator visible the whole call).
    "chat_reply":           ModelTier.small,
    "chat_opener":          ModelTier.small,
    # Persona evaluating a user's itinerary proposal (accept/counter).
    # Same shape as chat_reply — short JSON, conversational message field.
    "proposal_evaluation":  ModelTier.small,
    # rag_explanation produces one short sentence per activity — Haiku is plenty
    # and 4x faster than Sonnet. With 20+ concurrent per-activity calls in
    # explain_itinerary, the speedup compounds.
    "rag_explanation":      ModelTier.small,

    # Large tier — complex, high-context
    "itinerary_generation": ModelTier.large,
    "complex_refinement":   ModelTier.large,
    "conflict_resolution":  ModelTier.large,
    "what_if":              ModelTier.large,
}


def classify(task_type: str, context: dict | None = None) -> ModelTier:
    """
    Determine which model tier to use for a given task.

    Expected input:
        task_type = "itinerary_generation"
        context   = {"token_estimate": 3200, "latency_budget_ms": 5000}

    Expected output:
        ModelTier.large

    Ali: you can extend this to be context-aware — e.g. if token_estimate is very
    high, prefer a model with a larger context window regardless of tier.
    """
    if task_type in TASK_TIER_MAP:
        return TASK_TIER_MAP[task_type]
    # TODO: fallback logic for unknown task types
    return ModelTier.large


def estimate_tokens(prompt: str) -> int:
    """
    Rough token count estimate for budget-aware routing.

    Expected input:  "Generate a 5-day itinerary for Bali..."
    Expected output: 312  (approximate token count)
    """
    return int(len(prompt.split()) * 1.3)
