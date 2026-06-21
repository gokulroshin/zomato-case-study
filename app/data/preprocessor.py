"""Data preprocessing — clean and normalize the raw Zomato DataFrame.

Transformations (per the implementation plan + edge case mitigations):
    - ``rate``:  ``"4.1/5"`` → ``4.1``; ``"NEW"``, ``"-"``, empty → NaN
    - ``approx_cost(for two people)``: ``"300"`` → 300; ``"300-400"`` → 350
    - ``cuisines``: lowercase, trimmed, comma-separated preserved
    - Budget tier mapping: low ≤ ₹300, medium ₹301–600, high ₹601+
    - Rows missing ``name`` are dropped
    - ``votes`` cast to integer
    - Null cuisines default to ``"other"``  (DATA-003)
    - Null locations filled from ``listed_in(city)`` (FILT-002)
    - Null costs filled with neighborhood median (DATA-002)
"""

from __future__ import annotations

import logging
import re

import numpy as np
import pandas as pd

from app.config import settings

logger = logging.getLogger(__name__)

# ── Helpers ────────────────────────────────────────────────────


def _parse_rate(value) -> float | None:
    """Convert rate strings like ``"4.1/5"`` to a float.

    Returns *NaN* for non-numeric values (``"NEW"``, ``"-"``, empty, etc.).
    """
    if pd.isna(value):
        return np.nan
    s = str(value).strip()
    if not s or s in ("-", "NEW", "new", "--"):
        return np.nan
    # Strip a trailing "/5" if present.
    s = re.sub(r"\s*/\s*5\s*$", "", s)
    try:
        return float(s)
    except ValueError:
        return np.nan


def _parse_cost(value) -> float | None:
    """Convert cost strings to a numeric value.

    Single values (``"300"``) are returned as-is.
    Ranges (``"300-400"``, ``"300 - 400"``) are converted to the midpoint.
    Commas (e.g. ``"1,200"``) are stripped before parsing.
    """
    if pd.isna(value):
        return np.nan
    s = str(value).strip().replace(",", "")
    if not s or s in ("-", "--"):
        return np.nan
    # Detect range like "300-400" or "300 - 400".
    parts = re.split(r"\s*[-–]\s*", s)
    try:
        nums = [float(p) for p in parts if p]
        if not nums:
            return np.nan
        return sum(nums) / len(nums)
    except ValueError:
        return np.nan


def _normalize_cuisines(value) -> str | None:
    """Lowercase, trim whitespace around each comma-separated cuisine tag."""
    if pd.isna(value):
        return None
    s = str(value).strip()
    if not s:
        return None
    return ", ".join(tag.strip().lower() for tag in s.split(",") if tag.strip())


def _assign_budget_tier(cost: float) -> str | None:
    """Map a numeric cost to a budget tier label.

    Uses thresholds from ``settings``:
        - ``low``   ≤ budget_low_max  (default ₹300)
        - ``medium`` ≤ budget_medium_max (default ₹600)
        - ``high``  > budget_medium_max
    """
    if pd.isna(cost):
        return None
    if cost <= settings.budget_low_max:
        return "low"
    if cost <= settings.budget_medium_max:
        return "medium"
    return "high"


# ── Main entry point ──────────────────────────────────────────


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all cleaning and normalization steps to a raw Zomato DataFrame.

    Returns a **copy** — the original DataFrame is not mutated.

    New columns added:
        - ``rate_normalized``       (float, nullable)
        - ``approx_cost_numeric``   (float, nullable)
        - ``cuisines_normalized``   (str, nullable)
        - ``budget_tier``           (str: ``low`` | ``medium`` | ``high`` | None)
    """
    logger.info("Preprocessing %d rows …", len(df))
    out = df.copy()

    # 1. Drop rows with missing restaurant name.
    name_col = "name"
    before = len(out)
    out = out.dropna(subset=[name_col])
    out = out[out[name_col].astype(str).str.strip() != ""]
    dropped = before - len(out)
    if dropped:
        logger.info("Dropped %d rows missing '%s'.", dropped, name_col)

    # 2. Normalize rating.
    out["rate_normalized"] = out["rate"].apply(_parse_rate)

    # 3. Parse cost.
    cost_col = "approx_cost(for two people)"
    out["approx_cost_numeric"] = out[cost_col].apply(_parse_cost)

    # 4. Normalize cuisines.
    out["cuisines_normalized"] = out["cuisines"].apply(_normalize_cuisines)

    # 4a. Default null cuisines to "other" (DATA-003).
    null_cuisine_count = out["cuisines_normalized"].isnull().sum()
    if null_cuisine_count:
        out["cuisines_normalized"] = out["cuisines_normalized"].fillna("other")
        logger.info(
            "Filled %d null cuisines with 'other'.", null_cuisine_count
        )

    # 5. Assign budget tier.
    out["budget_tier"] = out["approx_cost_numeric"].apply(_assign_budget_tier)

    # 6. Cast votes to integer (coerce bad values to 0).
    out["votes"] = pd.to_numeric(out["votes"], errors="coerce").fillna(0).astype(int)

    # 7. Fill null locations from listed_in(city) (FILT-002).
    null_loc_mask = out["location"].isnull() | (out["location"].str.strip() == "")
    null_loc_count = null_loc_mask.sum()
    if null_loc_count:
        out.loc[null_loc_mask, "location"] = out.loc[
            null_loc_mask, "listed_in(city)"
        ]
        logger.info(
            "Filled %d null locations from 'listed_in(city)'.",
            null_loc_count,
        )

    # 8. Fill null cost with neighborhood median (DATA-002).
    #    Uses `location` to compute the median cost per neighborhood.
    #    Remaining nulls (if an entire neighborhood has no costs) stay NaN.
    null_cost_mask = out["approx_cost_numeric"].isnull()
    null_cost_count = null_cost_mask.sum()
    if null_cost_count:
        median_by_loc = out.groupby("location")["approx_cost_numeric"].transform(
            "median"
        )
        out.loc[null_cost_mask, "approx_cost_numeric"] = median_by_loc[
            null_cost_mask
        ]
        # Recompute budget tier for filled rows.
        filled_mask = null_cost_mask & out["approx_cost_numeric"].notna()
        out.loc[filled_mask, "budget_tier"] = out.loc[
            filled_mask, "approx_cost_numeric"
        ].apply(_assign_budget_tier)
        actually_filled = null_cost_count - out["approx_cost_numeric"].isnull().sum()
        logger.info(
            "Filled %d/%d null costs with neighborhood median.",
            actually_filled,
            null_cost_count,
        )

    # 9. Deduplicate: Drop rows with the same name and location
    before_dedup = len(out)
    out = out.drop_duplicates(subset=["name", "location"], keep="first")
    dedup_dropped = before_dedup - len(out)
    if dedup_dropped:
        logger.info("Dropped %d duplicate rows (same name and location).", dedup_dropped)

    # Reset index after potential row drops.
    out = out.reset_index(drop=True)

    logger.info(
        "Preprocessing complete: %d rows, %d columns.",
        len(out),
        len(out.columns),
    )
    return out
