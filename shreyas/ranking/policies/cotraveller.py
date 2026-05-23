"""
Cotraveller ranking policy — V1.

Six features, uniform 1/6 prior weights. Pipeline declares the full V1
shape even though InteractionStage and RerankerStage are no-ops — future
diversity / fatigue / "you've already seen this profile" stages will
slot in without engine surgery.

`feedback_policy` holds the learning hyperparameters so feedback.py can
read them without hardcoding. These are starting guesses, not predictions
about the world — they live in policy config explicitly so they're
reviewable and tunable from feature_stats logs.
"""

from __future__ import annotations

from shreyas.ranking.stages import (
    FeatureScoringStage,
    InteractionStage,
    WeightedCombinerStage,
    RerankerStage,
)


surface = "cotraveller"


features: list[str] = [
    "pinecone_passthrough",
    "salience_weighted_question_overlap",
    "signature_proximity",
    "pace_ordinal_fit",
    "budget_ordinal_fit",
    "style_match",
]


# Equal-weight prior — we haven't earned any confidence in feature
# importance yet. Per-user weights from compatibility_signals.ranker_weights
# override these once feedback has shaped them.
weights: dict[str, float] = {name: 1.0 / len(features) for name in features}


# Hyperparameters consumed by feedback.apply_text_feedback. NOT predictions
# about feature importance; these tune the learning step itself. Reviewable
# here because they're policy, not engine.
feedback_policy: dict = {
    "min_weight":      0.05,
    "boost_amount":    0.10,
    "reduce_amount":   0.05,
    "renormalization": "sum_to_one",
}


# V1 pipeline. NO-OP stages exist so adding cross-candidate features /
# diversity / fatigue later doesn't require an engine rewrite.
pipeline: list = [
    FeatureScoringStage(),
    InteractionStage(),
    WeightedCombinerStage(),
    RerankerStage(),
]


# pinecone_passthrough is in `features`, so the combiner does NOT add
# retrieval_score directly (avoids double-counting). Flip to True in V2
# when pinecone_passthrough is removed from the feature list and retrieval
# gets its own weight slot.
include_retrieval_in_sum: bool = False
