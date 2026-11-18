"""
Matching a probe face against enrolled templates.

A person can have several templates (photos from different angles or lighting). Their score is
their BEST template's cosine similarity. A match is accepted only if:
  1. the best person's score is at least `threshold`, and
  2. it beats the runner-up PERSON by at least `margin`,
so two similar-looking people can't be confused for each other.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MatchResult:
    person_id: int | None
    score: float  # best similarity found (even when rejected)
    reason: str  # "match" | "no-enrolled-faces" | "below-threshold" | "ambiguous"


def best_scores(probe: list[float], templates: list[tuple[int, list[float]]]) -> dict[int, float]:
    """Best cosine similarity per person. Vectors are L2-normalised, so similarity is a dot product."""
    if not templates:
        return {}
    ids = np.array([pid for pid, _ in templates])
    sims = np.array([v for _, v in templates], dtype=np.float64) @ np.asarray(probe, dtype=np.float64)
    scores: dict[int, float] = {}
    for pid, sim in zip(ids.tolist(), sims.tolist(), strict=True):
        scores[pid] = max(scores.get(pid, -1.0), sim)
    return scores


def match(probe: list[float], templates: list[tuple[int, list[float]]], threshold: float, margin: float) -> MatchResult:
    scores = best_scores(probe, templates)
    if not scores:
        return MatchResult(None, 0.0, "no-enrolled-faces")

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best_id, best = ranked[0]
    runner_up = ranked[1][1] if len(ranked) > 1 else -1.0

    if best < threshold:
        return MatchResult(None, best, "below-threshold")
    if best - runner_up < margin:
        return MatchResult(None, best, "ambiguous")
    return MatchResult(best_id, best, "match")


def is_duplicate_enrolment(new: list[float], existing: list[list[float]], limit: float = 0.995) -> bool:
    """Blocks enrolling (almost) the same photo twice, which adds nothing to accuracy."""
    return any(float(np.dot(new, e)) >= limit for e in existing)
