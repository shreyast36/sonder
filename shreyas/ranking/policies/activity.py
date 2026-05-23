"""
Activity ranking policy — V1.

Budget feasibility is handled by filters.apply_activity_filters BEFORE
ranking, not by a feature here. Three features, uniform 1/3 prior weights.

pace_duration_fit is a soft feature (rewards activities whose duration
matches the user's pace preference); cost_fit isn't here because the
filter already drops the truly infeasible ones, and cost within the
feasible range is mostly noise — that decision moves into the policy once
feedback shows it matters.
"""

from __future__ import annotations

from shreyas.ranking.stages import (
    FeatureScoringStage,
    InteractionStage,
    WeightedCombinerStage,
    RerankerStage,
)


surface = "activity"


features: list[str] = [
    "pinecone_passthrough",
    "tag_interest_overlap",
    "pace_duration_fit",
]


weights: dict[str, float] = {name: 1.0 / len(features) for name in features}


feedback_policy: dict = {
    "min_weight":      0.05,
    "boost_amount":    0.10,
    "reduce_amount":   0.05,
    "renormalization": "sum_to_one",
}


pipeline: list = [
    FeatureScoringStage(),
    InteractionStage(),
    WeightedCombinerStage(),
    RerankerStage(),
]


include_retrieval_in_sum: bool = False
