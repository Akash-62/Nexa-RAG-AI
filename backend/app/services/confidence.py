"""
Derives a confidence score from retrieval relevance scores.
Scores below FALLBACK_THRESHOLD trigger a "not enough context" response.
"""

FALLBACK_THRESHOLD = 0.35


def compute_confidence(chunks: list[dict]) -> float:
    """
    Returns a 0–1 score.
    Strategy: mean of top-3 chunk scores (more robust than max alone).
    """
    if not chunks:
        return 0.0
    top_scores = sorted(
        [c.get("score", 0.0) for c in chunks], reverse=True
    )[:3]
    return round(sum(top_scores) / len(top_scores), 4)


def is_low_confidence(score: float) -> bool:
    return score < FALLBACK_THRESHOLD
