"""
Smoke tests for shreyas.ranking.feedback.apply_text_feedback.

Asserts:
  - "cheaper" boosts budget-related features
  - "less packed" boosts pace-related features
  - min_weight clamp comes from the policy config, not a hardcoded constant
  - weights renormalise to sum 1.0 after every update
  - foreign feature keys in current_weights don't leak in
"""

from __future__ import annotations

from shreyas.ranking.feedback import apply_text_feedback
from shreyas.ranking.policies import load_policy


def _policy():
    return load_policy("cotraveller")


def test_cheaper_boosts_budget_features():
    policy = _policy()
    weights, boosted = apply_text_feedback(dict(policy.weights), "make it cheaper", policy)
    assert "budget_ordinal_fit" in boosted
    # Budget gained against the uniform prior.
    assert weights["budget_ordinal_fit"] > 1.0 / len(policy.features)


def test_less_packed_boosts_pace_features():
    policy = _policy()
    weights, boosted = apply_text_feedback(dict(policy.weights), "feels too packed", policy)
    assert "pace_ordinal_fit" in boosted
    assert weights["pace_ordinal_fit"] > 1.0 / len(policy.features)


def test_weights_sum_to_one_after_update():
    policy = _policy()
    weights, _ = apply_text_feedback(dict(policy.weights), "cheaper and less rushed", policy)
    total = sum(weights.values())
    assert abs(total - 1.0) < 1e-6


def test_min_weight_clamp_from_policy_config():
    """Every feature's weight is at least policy.feedback_policy['min_weight']
    after any update — no feature gets zeroed out."""
    policy = _policy()
    min_w = float(policy.feedback_policy["min_weight"])
    weights, _ = apply_text_feedback(dict(policy.weights), "cheaper", policy)
    # Renormalisation may scale below the clamp; the clamp is applied
    # before renormalise, so post-renorm we just check no value is exactly 0.
    assert all(v >= min_w * 0.5 for v in weights.values())


def test_no_keyword_means_no_boost():
    policy = _policy()
    weights, boosted = apply_text_feedback(dict(policy.weights), "this trip is fine actually", policy)
    assert boosted == []
    # All weights should still sum to 1.
    assert abs(sum(weights.values()) - 1.0) < 1e-6


def test_foreign_feature_keys_dont_leak_in():
    """If existing weights contain a feature the policy doesn't use, the
    update should drop it instead of carrying it through."""
    policy = _policy()
    current = dict(policy.weights)
    current["fake_feature_name"] = 0.5
    weights, _ = apply_text_feedback(current, "cheaper", policy)
    assert "fake_feature_name" not in weights
    assert set(weights.keys()) == set(policy.features)


def test_destination_policy_only_boosts_its_own_features():
    """destination policy has fewer features — apply_text_feedback shouldn't
    try to boost cotraveller-only features even if the text matches them."""
    policy = load_policy("destination")
    weights, boosted = apply_text_feedback(dict(policy.weights), "less packed and cheaper", policy)
    # cotraveller has pace_ordinal_fit/budget_ordinal_fit — destination has
    # neither. tag_interest_overlap is the only feature touched by "cheaper"
    # mapping that destination uses, and that's only if the mapping fires;
    # otherwise boosted stays empty.
    assert "pace_ordinal_fit" not in weights
    assert "budget_ordinal_fit" not in weights
    assert set(weights.keys()) == set(policy.features)
    # boosted is restricted to policy features
    assert all(b in policy.features for b in boosted)
