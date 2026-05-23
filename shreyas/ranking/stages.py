"""
Ranking pipeline stages.

A policy declares its pipeline as a list of stages. The engine runs them in
order, threading a per-candidate `ScoreSheet` through each. V1 ships:

  1. FeatureScoringStage — runs every feature in the policy, stores
     (raw, weighted) tuples on the ScoreSheet.
  2. InteractionStage — NO-OP. Reserved for cross-candidate features
     (e.g. "you've already seen this profile this session", recency
     penalties). Defined now so adding it later doesn't require an
     engine rewrite.
  3. WeightedCombinerStage — sums retrieval_score + Σ(weighted features) +
     Σ(rerank adjustments) into final_score, clips to [0,1].
  4. RerankerStage — NO-OP. Reserved for MMR diversity, fatigue penalty,
     sequencing.

Each stage runs over the full candidate list, mutating its ScoreSheet
in place. No stage knows about specific feature names or weights — those
live in the policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from shreyas.ranking.features import get_feature


@dataclass
class ScoreSheet:
    """Mutable per-candidate accumulator threaded through pipeline stages.

    `candidate` is the underlying object (CoTravellerProfile, Destination,
    Activity, ...). `retrieval_score` is set once at engine entry from the
    pinecone cosine and never modified by stages — its own slot, separate
    from feature_scores, so V2 can split retrieval confidence from
    semantic compatibility without restructuring data.
    """
    candidate:          Any
    retrieval_score:    float                              = 0.0
    feature_scores:     dict[str, tuple[float, float]]     = field(default_factory=dict)
    feature_snippets:   dict[str, str]                     = field(default_factory=dict)
    rerank_adjustments: dict[str, float]                   = field(default_factory=dict)
    final_score:        float                              = 0.0


class Stage(Protocol):
    """Every stage exposes a single `run` method that mutates the list of
    ScoreSheets in place. Stages MUST be deterministic — no I/O, no LLM
    calls. Side effects (logging) happen inside specific stages or after
    the pipeline, not inside generic ones."""

    def run(self, viewer: Any, sheets: list[ScoreSheet], policy: Any, ctx: dict) -> None: ...


@dataclass(frozen=True)
class FeatureScoringStage:
    """Runs each feature in `policy.features` against every candidate.
    Stores (raw, weighted) tuples + the feature's explanation snippet on
    the candidate's ScoreSheet. Weights come from the viewer's per-user
    overrides (if present in ctx['weights']) else the policy defaults."""

    def run(self, viewer: Any, sheets: list[ScoreSheet], policy: Any, ctx: dict) -> None:
        feature_names: list[str] = list(getattr(policy, "features", []) or [])
        weights:       dict[str, float] = ctx.get("weights") or {}

        for sheet in sheets:
            local_ctx = {**ctx, "retrieval_score": sheet.retrieval_score}
            for name in feature_names:
                fn = get_feature(name)
                try:
                    raw, snippet = fn(viewer, sheet.candidate, local_ctx)
                except Exception:
                    # Feature failed for this candidate — record 0 + a flag
                    # so downstream observability sees it instead of crashing.
                    raw, snippet = 0.0, "feature error"
                weight = float(weights.get(name, 0.0))
                sheet.feature_scores[name]   = (float(raw), float(raw) * weight)
                sheet.feature_snippets[name] = snippet


@dataclass(frozen=True)
class InteractionStage:
    """V1 NO-OP. Reserved for cross-candidate features (recency penalty,
    diversity-aware feature blending, repeat-exposure damping). Lives in
    the pipeline now so it can be filled in later without an engine
    refactor."""

    def run(self, viewer: Any, sheets: list[ScoreSheet], policy: Any, ctx: dict) -> None:
        return


@dataclass(frozen=True)
class WeightedCombinerStage:
    """Sums retrieval_score + Σ(weighted feature scores) + Σ(rerank
    adjustments) into final_score, clips to [0,1].

    Includes retrieval_score directly even though pinecone_passthrough may
    also appear as a feature — to avoid double-counting, this stage uses
    feature contributions only when retrieval_score isn't also wired as a
    feature. In V1 (where pinecone_passthrough IS a feature) the retrieval
    contribution is captured through the feature's weighted score, so the
    direct retrieval_score term is gated off via policy.include_retrieval.
    Default off for V1; flip to True in V2 once pinecone_passthrough is
    removed from feature lists.
    """

    def run(self, viewer: Any, sheets: list[ScoreSheet], policy: Any, ctx: dict) -> None:
        include_retrieval = bool(getattr(policy, "include_retrieval_in_sum", False))
        for sheet in sheets:
            features_total = sum(weighted for (_raw, weighted) in sheet.feature_scores.values())
            rerank_total   = sum(sheet.rerank_adjustments.values())
            retrieval_term = sheet.retrieval_score if include_retrieval else 0.0
            sheet.final_score = max(0.0, min(1.0, retrieval_term + features_total + rerank_total))


@dataclass(frozen=True)
class RerankerStage:
    """V1 NO-OP. Reserved for MMR diversity, fatigue penalties, sequence-
    aware reranking (e.g. don't stack five high-intensity activities for a
    reset_seeker). Implementations write into sheet.rerank_adjustments so
    WeightedCombinerStage can include them in the final sum — except this
    stage runs AFTER the combiner today, so for now any future impl will
    need to either rerun the combiner or write directly to final_score.

    Kept here as a no-op so policies declare the full pipeline shape now.
    """

    def run(self, viewer: Any, sheets: list[ScoreSheet], policy: Any, ctx: dict) -> None:
        return
