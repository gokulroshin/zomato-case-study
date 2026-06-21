"""Response parser — parse, validate, and merge Groq LLM output.

Responsibilities:
    1. Extract JSON from the Groq response (handles markdown code fences).
    2. Validate that every ``restaurant_name`` exists in the candidate set.
    3. Enforce the ``top_n`` limit.
    4. Merge Groq output with structured restaurant data (cuisine, rating,
       cost, location) from the candidate DataFrame.
    5. **Fallback**: if Groq fails or returns invalid JSON, produce a
       rule-based ranking using ``rating * log(votes + 1)`` with template
       explanations.
"""

from __future__ import annotations

import json
import logging
import math
import re
from typing import Any, Dict, List, Optional, Set

import pandas as pd

from app.models.recommendation import Recommendation

logger = logging.getLogger(__name__)


# ── JSON extraction ────────────────────────────────────────────


def _extract_json(text: str) -> Dict[str, Any]:
    """Extract a JSON object from LLM output.

    Handles cases where the model wraps JSON in markdown code fences.

    Raises
    ------
    ValueError
        If no valid JSON object can be found.
    """
    # Strip markdown code fences if present.
    cleaned = re.sub(r"```(?:json)?\s*", "", text)
    cleaned = cleaned.strip()

    # Try parsing directly first.
    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass

    # Try to find a JSON object in the text.
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            result = json.loads(match.group())
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract valid JSON from LLM response: {text[:200]}...")


# ── Validation ─────────────────────────────────────────────────


def _validate_recommendations(
    raw_recs: List[Dict[str, Any]],
    candidate_names: Set[str],
    top_n: int,
) -> List[Dict[str, Any]]:
    """Validate and filter LLM recommendations.

    - Rejects hallucinated restaurant names (not in candidate set).
    - Enforces ``top_n`` limit.
    - Logs any rejected entries.
    """
    valid = []
    for rec in raw_recs:
        name = rec.get("restaurant_name", "").strip()
        if not name:
            logger.warning("Skipping recommendation with empty name.")
            continue
        if name not in candidate_names:
            logger.warning(
                "Rejecting hallucinated restaurant: '%s' (not in candidate set).",
                name,
            )
            continue
        valid.append(rec)
        if len(valid) >= top_n:
            break

    return valid


# ── Merge with structured data ─────────────────────────────────


def _merge_with_candidates(
    validated_recs: List[Dict[str, Any]],
    candidates_df: pd.DataFrame,
) -> List[Recommendation]:
    """Merge LLM output with structured restaurant fields.

    For each validated recommendation, look up the restaurant in the
    candidate DataFrame and attach cuisine, rating, cost, and location.
    """
    recommendations = []
    # Build a lookup by name for O(1) access.
    # Use first occurrence if duplicates exist.
    lookup: Dict[str, pd.Series] = {}
    for _, row in candidates_df.iterrows():
        name = row.get("name", "")
        if name and name not in lookup:
            lookup[name] = row

    for rank_idx, rec in enumerate(validated_recs, start=1):
        name = rec["restaurant_name"]
        row = lookup.get(name)

        recommendation = Recommendation(
            rank=rank_idx,
            restaurant_name=name,
            cuisine=(
                row.get("cuisines_normalized") or row.get("cuisines")
                if row is not None
                else None
            ),
            rating=row.get("rate_normalized") if row is not None else None,
            estimated_cost=(
                row.get("approx_cost_numeric") if row is not None else None
            ),
            location=row.get("location") if row is not None else None,
            explanation=rec.get("explanation", "Recommended based on your preferences."),
        )
        recommendations.append(recommendation)

    return recommendations


# ── Fallback (rule-based ranking) ──────────────────────────────


def fallback_ranking(
    candidates_df: pd.DataFrame,
    top_n: int,
) -> tuple[Optional[str], List[Recommendation]]:
    """Produce a rule-based ranking when Groq is unavailable.

    Score formula: ``rating * log(votes + 1)``

    This gives a balance between rating quality and popularity.

    Returns
    -------
    tuple[str | None, list[Recommendation]]
        A summary string and list of recommendations.
    """
    df = candidates_df.copy()

    # Compute score. Fill NaN ratings with 0 to push them down.
    df["_score"] = df["rate_normalized"].fillna(0) * df["votes"].apply(
        lambda v: math.log(max(v, 0) + 1)
    )
    df = df.sort_values("_score", ascending=False).head(top_n)

    recommendations = []
    for rank_idx, (_, row) in enumerate(df.iterrows(), start=1):
        rating = row.get("rate_normalized")
        votes = row.get("votes", 0)
        cuisines = row.get("cuisines_normalized") or row.get("cuisines", "")
        cost = row.get("approx_cost_numeric")

        # Template explanation.
        explanation_parts = []
        if rating and not (isinstance(rating, float) and math.isnan(rating)):
            explanation_parts.append(f"Rated {rating:.1f}/5")
        if votes:
            explanation_parts.append(f"with {votes} votes")
        if cuisines:
            explanation_parts.append(f"serving {cuisines}")
        if cost and not (isinstance(cost, float) and math.isnan(cost)):
            explanation_parts.append(f"at approx. Rs.{cost:.0f} for two")

        explanation = (
            ". ".join(explanation_parts) + "."
            if explanation_parts
            else "Recommended based on your preferences."
        )

        recommendations.append(
            Recommendation(
                rank=rank_idx,
                restaurant_name=row.get("name", "Unknown"),
                cuisine=cuisines if cuisines else None,
                rating=rating if rating and not (isinstance(rating, float) and math.isnan(rating)) else None,
                estimated_cost=cost if cost and not (isinstance(cost, float) and math.isnan(cost)) else None,
                location=row.get("location"),
                explanation=explanation,
            )
        )

    summary = (
        f"Here are the top {len(recommendations)} restaurants based on "
        f"ratings and popularity. (AI ranking was unavailable; "
        f"results are sorted by a rating-popularity score.)"
    )

    return summary, recommendations


# ── Public API ────────────────────────────────────────────────


def parse_groq_response(
    response_text: str,
    candidates_df: pd.DataFrame,
    top_n: int,
) -> tuple[Optional[str], List[Recommendation]]:
    """Parse and validate a Groq LLM response.

    Parameters
    ----------
    response_text :
        Raw text content from the Groq chat completion.
    candidates_df :
        The filtered candidate DataFrame (used for validation and merging).
    top_n :
        Maximum recommendations to return.

    Returns
    -------
    tuple[str | None, list[Recommendation]]
        A (summary, recommendations) tuple. Falls back to rule-based
        ranking if parsing or validation fails.
    """
    # Build the set of valid candidate names.
    candidate_names: Set[str] = set(candidates_df["name"].dropna().unique())

    try:
        parsed = _extract_json(response_text)
    except ValueError as exc:
        logger.warning("Failed to parse Groq JSON: %s. Using fallback.", exc)
        return fallback_ranking(candidates_df, top_n)

    # Extract summary.
    summary = parsed.get("summary")

    # Extract and validate recommendations.
    raw_recs = parsed.get("recommendations", [])
    if not isinstance(raw_recs, list):
        logger.warning("'recommendations' is not a list. Using fallback.")
        return fallback_ranking(candidates_df, top_n)

    validated = _validate_recommendations(raw_recs, candidate_names, top_n)

    if not validated:
        logger.warning(
            "All Groq recommendations were rejected (hallucinated names). "
            "Using fallback."
        )
        return fallback_ranking(candidates_df, top_n)

    # Merge with structured candidate data.
    recommendations = _merge_with_candidates(validated, candidates_df)

    return summary, recommendations
