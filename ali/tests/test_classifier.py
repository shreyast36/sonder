from ali.routing.classifier import classify, estimate_tokens, TASK_TIER_MAP
from shared.schemas import ModelTier


def test_small_tasks_route_to_small_tier():
    for task in ["chat_topics", "icebreaker", "persona_label", "preference_parse",
                 "quick_edit", "notification_message", "short_explanation"]:
        assert classify(task) == ModelTier.small, f"{task} should be small tier"


def test_large_tasks_route_to_large_tier():
    for task in ["itinerary_generation", "complex_refinement", "conflict_resolution",
                 "rag_explanation", "what_if"]:
        assert classify(task) == ModelTier.large, f"{task} should be large tier"


def test_unknown_task_falls_back_to_large():
    assert classify("some_unknown_task_type") == ModelTier.large


def test_every_mapped_task_resolves_to_a_valid_tier():
    for task_type in TASK_TIER_MAP:
        assert isinstance(classify(task_type), ModelTier)


def test_estimate_tokens_returns_int():
    result = estimate_tokens("Generate a 7-day beach trip for Bali")
    assert isinstance(result, int)
    assert result > 0


def test_estimate_tokens_scales_with_length():
    assert estimate_tokens("hello " * 100) > estimate_tokens("hello")
