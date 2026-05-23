"""
Generic ranking engine.

`rank()` is the single entry point. It does not know about specific features,
weights, or taxonomies — it iterates the policy's pipeline of stages and
returns a sorted list of `RankedCandidate`s with full feature breakdowns so
the LLM consumer can turn them into natural-language explanations.

Inputs:
  - viewer:     the user we're ranking for (UserProfile or anything with the
                same compatibility_signals / constraints shape).
  - candidates: list of (candidate_obj, retrieval_score) tuples. Pinecone
                cosine is captured here so the engine can attach it to each
                RankedCandidate without rerunning retrieval.
  - policy:     a module from shreyas/ranking/policies/* with `pipeline`,
                `features`, `weights`, `feedback_policy` attributes.
  - ctx:        per-call context (surface, salience, trip_days, ...).
                Augmented internally with the viewer's per-user weight
                overrides if they exist on compatibility_signals.

Output:
  - sorted list of RankedCandidate (descending final_score), capped to
    `top_n` if specified.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from shreyas.ranking.stages import ScoreSheet


@dataclass
class RankedCandidate:
    """Engine result shape. Carries:
      - candidate:          original object
      - retrieval_score:    Pinecone cosine, in its own slot
      - feature_scores:     per-feature (raw, weighted) tuples
      - feature_snippets:   per-feature one-line explanations
      - rerank_adjustments: per-stage delta from reranking (empty V1)
      - final_score:        the combined number, clipped [0,1]
    """
    candidate:          Any
    retrieval_score:    float
    feature_scores:     dict[str, tuple[float, float]]
    feature_snippets:   dict[str, str]
    rerank_adjustments: dict[str, float] = field(default_factory=dict)
    final_score:        float            = 0.0

    def explanation_summary(self, top_k: int = 3) -> list[str]:
        """Top-K contributing feature snippets, ordered by their weighted
        contribution. Used by the LLM consumer to write match_reasons."""
        contributions = sorted(
            self.feature_scores.items(),
            key=lambda kv: kv[1][1],
            reverse=True,
        )
        return [self.feature_snippets[name] for name, _ in contributions[:top_k] if name in self.feature_snippets]


def _resolve_weights(viewer: Any, policy: Any) -> dict[str, float]:
    """Read per-user weight overrides from
    viewer.compatibility_signals.ranker_weights[surface]; fall back to the
    policy's default weights when absent or malformed."""
    surface = getattr(policy, "surface", None) or ""
    defaults = dict(getattr(policy, "weights", {}) or {})

    cs = getattr(viewer, "compatibility_signals", None) or {}
    if isinstance(cs, dict):
        per_user_all = cs.get("ranker_weights") or {}
    else:
        per_user_all = getattr(cs, "ranker_weights", {}) or {}

    if not isinstance(per_user_all, dict):
        return defaults

    user_weights = per_user_all.get(surface)
    if not isinstance(user_weights, dict) or not user_weights:
        return defaults

    # Only honor user overrides for keys the policy actually declares —
    # prevents stale/foreign feature names from leaking in.
    feature_names = set(getattr(policy, "features", []) or [])
    cleaned: dict[str, float] = {}
    for k, v in user_weights.items():
        if k in feature_names:
            try:
                cleaned[k] = float(v)
            except (TypeError, ValueError):
                continue
    # Backfill any feature the user weights don't cover with the policy default.
    for name in feature_names:
        cleaned.setdefault(name, float(defaults.get(name, 0.0)))
    return cleaned


def rank(
    viewer:     Any,
    candidates: Iterable[tuple[Any, float]],
    policy:     Any,
    ctx:        dict | None = None,
    top_n:      int | None  = None,
) -> list[RankedCandidate]:
    """Run the policy's pipeline against the candidates, return sorted
    list of RankedCandidates. See module docstring for argument shapes.
    """
    ctx = dict(ctx or {})
    ctx.setdefault("surface", getattr(policy, "surface", "unknown"))
    ctx["weights"] = _resolve_weights(viewer, policy)

    # Build sheets — retrieval_score lives on the sheet from the start, in
    # its own slot, independent of any feature reading it.
    sheets: list[ScoreSheet] = [
        ScoreSheet(candidate=obj, retrieval_score=float(score or 0.0))
        for obj, score in candidates
    ]

    # Run every stage in the declared pipeline order. Stages mutate sheets.
    pipeline = list(getattr(policy, "pipeline", []) or [])
    for stage in pipeline:
        try:
            stage.run(viewer, sheets, policy, ctx)
        except Exception as e:
            # Stage failure is non-fatal — log via feature_stats if wired,
            # but the engine continues with whatever the previous stages
            # produced. We don't want a single bad stage to nuke the page.
            import logging
            logging.getLogger(__name__).warning(
                "ranking stage %s failed: %s", type(stage).__name__, e,
            )

    # Materialize RankedCandidate, sort descending.
    results = [
        RankedCandidate(
            candidate=         s.candidate,
            retrieval_score=   s.retrieval_score,
            feature_scores=    s.feature_scores,
            feature_snippets=  s.feature_snippets,
            rerank_adjustments=s.rerank_adjustments,
            final_score=       s.final_score,
        )
        for s in sheets
    ]
    results.sort(key=lambda rc: rc.final_score, reverse=True)

    if top_n is not None:
        results = results[:max(0, top_n)]

    # Best-effort fire-and-forget observability. Wrapped in try blocks so
    # observability failures never affect the user-facing rank result.
    # feature_stats: per-feature distribution → spot silent domination.
    # feature_logging: per-candidate breakdown → V2 gradient learning.
    surface = ctx.get("surface", "unknown")
    try:
        from shreyas.ranking.feature_stats import record_rank_call as record_stats
        record_stats(surface, results)
    except Exception:
        pass
    try:
        from shreyas.ranking.feature_logging import record_rank_call as record_log
        record_log(surface, results)
    except Exception:
        pass

    return results
