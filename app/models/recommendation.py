"""Recommendation output model.

Defines the shape of individual recommendations and the overall response
returned by the recommendation pipeline (Phase 4).
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Recommendation(BaseModel):
    """A single restaurant recommendation with AI-generated explanation."""

    rank: int = Field(description="1-indexed rank in the recommendation list.")
    restaurant_name: str
    cuisine: Optional[str] = None
    rating: Optional[float] = None
    estimated_cost: Optional[float] = Field(
        default=None,
        description="Approximate cost for two people (₹).",
    )
    location: Optional[str] = None
    explanation: str = Field(
        description="AI-generated explanation of why this restaurant was recommended.",
    )


class RecommendationResponse(BaseModel):
    """Full response from the recommendation pipeline."""

    summary: Optional[str] = Field(
        default=None,
        description="AI-generated summary of the recommendation set.",
    )
    recommendations: List[Recommendation] = Field(default_factory=list)
    candidates_considered: int = Field(
        default=0,
        description="Number of candidates that passed deterministic filters.",
    )
    model: Optional[str] = Field(
        default=None,
        description="LLM model used for ranking (null if fallback was used).",
    )
    latency_ms: Optional[float] = Field(
        default=None,
        description="End-to-end pipeline latency in milliseconds.",
    )
