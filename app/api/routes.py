"""REST API routes for the recommendation system."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any

from app.models.preferences import UserPreferences
from app.models.recommendation import RecommendationResponse
from app.services.recommender import RecommenderService

router = APIRouter(prefix="/api/v1", tags=["recommendations"])

class MetadataResponse(BaseModel):
    """Metadata response for frontend dropdowns."""
    locations: List[str]
    cuisines: List[str]
    budget_tiers: List[str]

@router.post(
    "/recommend",
    response_model=RecommendationResponse,
    summary="Get restaurant recommendations",
)
def recommend(prefs: UserPreferences) -> RecommendationResponse:
    """Get restaurant recommendations based on user preferences.
    
    If no restaurants match the given filters, a 422 Unprocessable Entity
    error is returned with suggestions to broaden the search.
    """
    return RecommenderService.get_recommendations(prefs)

@router.get(
    "/metadata",
    response_model=MetadataResponse,
    summary="Get available filter options",
)
def get_metadata() -> MetadataResponse:
    """Return distinct locations, cuisines, and budgets to populate frontend UI."""
    from app.main import app_state
    
    df = app_state.get("df")
    if df is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dataset is not loaded. Please try again later.",
        )
        
    # Extract unique locations using 'listed_in(city)' for clean neighborhood names
    locations = set(df["listed_in(city)"].dropna().unique())
    locations_list = sorted([loc.strip() for loc in locations if loc.strip()])
    
    # Extract unique cuisines
    # Cuisines are comma separated in 'cuisines_normalized' or 'cuisines'
    cuisines_series = df["cuisines_normalized"].dropna().str.split(", ")
    cuisines = set()
    for row in cuisines_series:
        if isinstance(row, list):
            cuisines.update([c.strip() for c in row if c.strip()])
    cuisines_list = sorted(list(cuisines))
    
    # Budget tiers are hardcoded in the model but we can return them
    from app.models.preferences import BudgetTier
    budget_tiers = [tier.value for tier in BudgetTier]
    
    return MetadataResponse(
        locations=locations_list,
        cuisines=cuisines_list,
        budget_tiers=budget_tiers,
    )
