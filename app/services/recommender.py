"""Orchestrator service for the recommendation pipeline.

Wires together the deterministic filter engine and the Groq LLM to
produce the final RecommendationResponse.
"""

from __future__ import annotations

import logging
import time

from fastapi import HTTPException, status
from app.config import settings
from app.models.preferences import UserPreferences
from app.models.recommendation import RecommendationResponse
from app.data.filter import filter_candidates
from app.llm.prompt_builder import build_messages
from app.llm.groq_client import GroqClient, GroqError
from app.llm.parser import parse_groq_response

logger = logging.getLogger(__name__)

class RecommenderService:
    """Service to orchestrate the restaurant recommendation flow."""
    
    @staticmethod
    def get_recommendations(prefs: UserPreferences) -> RecommendationResponse:
        """Run the end-to-end recommendation pipeline.
        
        Steps:
        1. Get the preprocessed DataFrame from app_state.
        2. Filter candidates based on user preferences.
        3. If no candidates, raise 422 with the reason.
        4. Build LLM prompt with candidates.
        5. Call Groq API.
        6. Parse response and assemble final RecommendationResponse.
        """
        # Delaying import to avoid circular dependency with main.py
        from app.main import app_state
        
        t0 = time.time()
        
        df = app_state.get("df")
        if df is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Dataset is not loaded. Please try again later.",
            )

        # 1. Filter candidates
        filter_result = filter_candidates(df, prefs)
        
        if filter_result.is_empty:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=filter_result.reason,
            )

        candidates_df = filter_result.candidates
        candidates_considered = filter_result.total_matches

        # 2. Build Prompt
        messages = build_messages(prefs, candidates_df)

        # 3. Call Groq
        groq_client = GroqClient()
        response_text = ""
        model_used = groq_client.model
        
        if settings.is_groq_configured:
            try:
                response_text = groq_client.chat(messages)
            except GroqError as e:
                logger.error("Groq API failed: %s", e)
                # Parse will handle empty response_text with fallback
                response_text = ""
                model_used = None
        else:
            logger.info("Groq is not configured. Falling back to rule-based ranking.")
            model_used = None

        # 4. Parse Response (will use fallback if response_text is empty or invalid)
        summary, recommendations = parse_groq_response(response_text, candidates_df, prefs.top_n)
        
        latency_ms = (time.time() - t0) * 1000
        
        return RecommendationResponse(
            summary=summary,
            recommendations=recommendations,
            candidates_considered=candidates_considered,
            model=model_used,
            latency_ms=latency_ms,
        )
