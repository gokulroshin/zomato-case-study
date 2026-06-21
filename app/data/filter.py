"""Deterministic candidate filter engine.

Applies user preference filters to the preprocessed Zomato DataFrame
and returns a ranked list of candidate restaurants for LLM ranking.

Filter pipeline (applied in order):
    1. Location — match on ``listed_in(city)`` or ``location`` (case-insensitive)
    2. Budget — match on ``budget_tier``
    3. Cuisine — substring match on ``cuisines_normalized``
    4. Minimum rating — filter on ``rate_normalized`` (null ratings pass through)
    5. Additional preferences — keyword-mapped structural filters
    6. Sort by rating desc → votes desc
    7. Return top K candidates
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import pandas as pd

from app.config import settings
from app.models.preferences import UserPreferences

logger = logging.getLogger(__name__)

# ── Keyword mappings for additional_preferences ────────────────

# Restaurant types associated with family-friendly dining.
_FAMILY_FRIENDLY_TYPES = {
    "casual dining",
    "family style",
    "buffet",
    "dining",
}

# Restaurant types associated with quick service.
_QUICK_SERVICE_TYPES = {
    "quick bites",
    "takeaway",
    "delivery",
    "food court",
    "kiosk",
}


@dataclass
class FilterResult:
    """Container for filter engine output.

    Attributes
    ----------
    candidates : pd.DataFrame
        Filtered and sorted candidate rows.
    total_matches : int
        Number of rows that passed all filters (before top-K truncation).
    applied_filters : list[str]
        Human-readable descriptions of filters that were applied.
    reason : str | None
        If ``total_matches == 0``, a user-friendly explanation of why no
        restaurants matched, with suggestions to broaden the search.
    """

    candidates: pd.DataFrame
    total_matches: int = 0
    applied_filters: list = field(default_factory=list)
    reason: Optional[str] = None

    @property
    def is_empty(self) -> bool:
        return self.total_matches == 0


# ── Internal filter steps ─────────────────────────────────────


def _filter_location(df: pd.DataFrame, location: str) -> pd.DataFrame:
    """Match on ``listed_in(city)`` OR ``location`` (case-insensitive, substring).

    Uses substring/contains matching so that:
        - ``"Koramangala"`` matches ``"Koramangala 5th Block"`` etc.
        - ``"Whitefield"`` matches ``"ITPL Main Road, Whitefield"`` etc.
        - ``"Bangalore"`` matches ``"South Bangalore"`` etc.
    This addresses edge case FILT-002 (location hierarchy matching).
    """
    loc_lower = location.strip().lower()
    mask_city = (
        df["listed_in(city)"]
        .fillna("")
        .str.strip()
        .str.lower()
        .str.contains(loc_lower, case=False, na=False)
    )
    mask_loc = (
        df["location"]
        .fillna("")
        .str.strip()
        .str.lower()
        .str.contains(loc_lower, case=False, na=False)
    )
    return df[mask_city | mask_loc]


def _filter_budget(df: pd.DataFrame, budget: float) -> pd.DataFrame:
    """Match on the derived ``approx_cost_numeric`` column."""
    return df[df["approx_cost_numeric"].fillna(0) <= budget]

def _filter_diet(df: pd.DataFrame, diet: str) -> pd.DataFrame:
    """Filter by dietary preference."""
    diet = diet.strip().lower()
    if diet == "veg":
        mask_rt = df["rest_type"].fillna("").str.lower().str.contains("veg")
        mask_c = df["cuisines_normalized"].fillna("").str.lower().str.contains("veg")
        return df[mask_rt | mask_c]
    elif diet == "non-veg":
        mask_rt = ~df["rest_type"].fillna("").str.lower().str.contains("pure veg")
        return df[mask_rt]
    return df


def _filter_cuisine(df: pd.DataFrame, cuisine: str) -> pd.DataFrame:
    """Substring match on ``cuisines_normalized`` (case-insensitive)."""
    cuisine_lower = cuisine.strip().lower()
    return df[
        df["cuisines_normalized"]
        .fillna("")
        .str.contains(cuisine_lower, case=False, na=False)
    ]


def _filter_min_rating(df: pd.DataFrame, min_rating: float) -> pd.DataFrame:
    """Keep rows where ``rate_normalized >= min_rating`` or rating is null.

    Null ratings are treated as pass-through (lower priority) rather than
    excluded, so we don't over-filter areas with many unrated restaurants.
    They will naturally sort to the bottom due to the NaN-last sort order.
    """
    return df[df["rate_normalized"].fillna(0) >= min_rating]


def _apply_additional_preferences(df: pd.DataFrame, prefs: str) -> pd.DataFrame:
    """Map free-text preferences to structured filters where possible.

    Currently recognised keywords:
        - ``family-friendly`` / ``family`` → rest_type contains relevant terms
        - ``quick service`` / ``quick`` → online_order == "Yes" or Quick Bites type
    """
    prefs_lower = prefs.strip().lower()
    mask = pd.Series(True, index=df.index)

    if "family" in prefs_lower:
        rest_type_lower = df["rest_type"].fillna("").str.lower()
        family_mask = rest_type_lower.apply(
            lambda rt: any(kw in rt for kw in _FAMILY_FRIENDLY_TYPES)
        )
        mask = mask & family_mask

    if "quick" in prefs_lower:
        rest_type_lower = df["rest_type"].fillna("").str.lower()
        quick_type_mask = rest_type_lower.apply(
            lambda rt: any(kw in rt for kw in _QUICK_SERVICE_TYPES)
        )
        online_mask = df["online_order"].fillna("").str.strip().str.lower() == "yes"
        mask = mask & (quick_type_mask | online_mask)

    return df[mask]


def _sort_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """Sort by rating (desc) then votes (desc), NaN ratings last."""
    return df.sort_values(
        by=["rate_normalized", "votes"],
        ascending=[False, False],
        na_position="last",
    )


# ── Zero-match reason builder ─────────────────────────────────


def _build_zero_match_reason(prefs: UserPreferences) -> str:
    """Build a helpful message when no restaurants match the filters."""
    parts = ["We couldn't find any restaurants matching all your filters. Here are a few things you can try:"]
    suggestions: List[str] = []

    if prefs.location:
        suggestions.append(f"Try a different neighborhood (you searched for <strong>'{prefs.location}'</strong>)")
    if prefs.budget is not None:
        suggestions.append(f"Relax the budget limit (currently <strong>₹{prefs.budget}</strong>)")
    if prefs.diet and prefs.diet.lower() != "any":
        suggestions.append(f"Remove dietary constraints (currently <strong>'{prefs.diet}'</strong>)")
    if prefs.cuisine:
        suggestions.append(f"Broaden the cuisine (you searched for <strong>'{prefs.cuisine}'</strong>)")
    if prefs.min_rating is not None:
        suggestions.append(f"Lower the minimum rating (currently <strong>{prefs.min_rating}</strong>)")
    if prefs.additional_preferences:
        suggestions.append("Remove additional preference filters")

    if suggestions:
        parts.append("<ul class='error-suggestions'>")
        for s in suggestions:
            parts.append(f"<li>{s}</li>")
        parts.append("</ul>")

    return "".join(parts)


# ── Public API ─────────────────────────────────────────────────


def filter_candidates(
    df: pd.DataFrame,
    prefs: UserPreferences,
    *,
    max_candidates: int | None = None,
) -> FilterResult:
    """Apply all user preference filters and return ranked candidates.

    Parameters
    ----------
    df :
        The preprocessed Zomato DataFrame (from Phase 1).
    prefs :
        User preferences to filter on.
    max_candidates :
        Maximum number of candidates to return.  Defaults to
        ``settings.max_candidates`` (30).

    Returns
    -------
    FilterResult
        Contains the filtered DataFrame, match count, applied filters,
        and an explanatory reason if no matches were found.
    """
    cap = max_candidates or settings.max_candidates
    applied: List[str] = []
    result = df.copy()

    # 1. Location
    if prefs.location:
        result = _filter_location(result, prefs.location)
        applied.append(f"location = '{prefs.location}'")

    # 2. Budget
    if prefs.budget is not None:
        result = _filter_budget(result, prefs.budget)
        applied.append(f"budget ≤ {prefs.budget}")

    # Diet
    if prefs.diet and prefs.diet.lower() != "any":
        result = _filter_diet(result, prefs.diet)
        applied.append(f"diet = '{prefs.diet}'")

    # 3. Cuisine
    if prefs.cuisine:
        result = _filter_cuisine(result, prefs.cuisine)
        applied.append(f"cuisine contains '{prefs.cuisine}'")

    # 4. Minimum rating
    if prefs.min_rating is not None:
        result = _filter_min_rating(result, prefs.min_rating)
        applied.append(f"min_rating ≥ {prefs.min_rating}")

    # 5. Additional preferences
    if prefs.additional_preferences:
        result = _apply_additional_preferences(result, prefs.additional_preferences)
        applied.append(f"additional = '{prefs.additional_preferences}'")

    # 6. Sort
    result = _sort_candidates(result)

    total = len(result)
    logger.info(
        "Filter pipeline: %d → %d candidates (filters: %s).",
        len(df),
        total,
        ", ".join(applied) or "none",
    )

    # 7. Handle zero-match case
    if total == 0:
        return FilterResult(
            candidates=result,
            total_matches=0,
            applied_filters=applied,
            reason=_build_zero_match_reason(prefs),
        )

    # 8. Truncate to top K
    truncated = result.head(cap)

    return FilterResult(
        candidates=truncated,
        total_matches=total,
        applied_filters=applied,
    )
