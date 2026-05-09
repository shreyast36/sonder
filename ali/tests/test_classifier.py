import pytest
from ali.routing.classifier import classify, estimate_tokens, TASK_TIER_MAP
from shared.schemas import ModelTier


# ── classify() — implemented, test fully ─────────────────────────────────────

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
        result = classify(task_type)
        assert isinstance(result, ModelTier)


# ── estimate_tokens() — stub ──────────────────────────────────────────────────

def test_estimate_tokens_stub():
    with pytest.raises(NotImplementedError):
        estimate_tokens("Generate a 7-day beach trip for Bali")
    # TODO: returns int; roughly len(prompt.split()) * 1.3 or tiktoken count
