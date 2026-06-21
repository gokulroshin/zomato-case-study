"""User preference input model.

Captures the filters and preferences a user submits when requesting
restaurant recommendations.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class BudgetTier(str, Enum):
    """Budget categories mapped to cost ranges in app.config."""

    low = "low"
    medium = "medium"
    high = "high"


class UserPreferences(BaseModel):
    """Validated user input for the recommendation pipeline.

    All filter fields are optional — omitting a field means "no preference"
    for that dimension, broadening the candidate set.
    """

    location: Optional[str] = Field(
        default=None,
        description="Neighborhood or area name (e.g. 'Banashankari', 'Indiranagar').",
        max_length=100,
    )
    budget: Optional[float] = Field(
        default=None,
        description="Upper limit for the budget for two people in ₹.",
        ge=0.0,
    )
    diet: Optional[str] = Field(
        default="any",
        description="Dietary preference: 'any', 'veg', or 'non-veg'.",
    )
    cuisine: Optional[str] = Field(
        default=None,
        description="Cuisine type to search for (e.g. 'Chinese', 'Italian'). "
        "Substring-matched against the restaurant's cuisine list.",
        max_length=100,
    )
    min_rating: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=5.0,
        description="Minimum rating threshold (0–5). Restaurants with null "
        "ratings are treated as lower priority but not excluded.",
    )
    additional_preferences: Optional[str] = Field(
        default=None,
        description="Free-text preferences like 'family-friendly', 'quick service'. "
        "Mapped to structured filters where possible.",
        max_length=300,
    )
    top_n: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of final recommendations to return.",
    )
