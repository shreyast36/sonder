"""
Destination ranking policy — V1.

Budget feasibility is handled by filters.apply_destination_filters BEFORE
ranking, not by a feature here — so this policy carries no `budget_*`
feature. Two features, uniform 1/2 prior weights.

V2 will gain structured destination feature metadata (atmosphere,
stimulation_level, signature_affinity) once we backfill that into the
Pinecone destinations namespace. Until then, destination ranking is:
vector similarity + tag overlap.
"""

from __future__ import annotations

from shreyas.ranking.stages import (
    FeatureScoringStage,
    InteractionStage,
    WeightedCombinerStage,
    RerankerStage,
)


surface = "destination"


features: list[str] = [
    "pinecone_passthrough",
    "tag_interest_overlap",
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
