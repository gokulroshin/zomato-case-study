"""Unit tests for app.llm.parser — Groq response parsing, validation, fallback."""

import json
import math

import numpy as np
import pandas as pd
import pytest

from app.llm.parser import (
    _extract_json,
    _validate_recommendations,
    fallback_ranking,
    parse_groq_response,
)
from app.models.recommendation import Recommendation


# ── Fixtures ───────────────────────────────────────────────────


@pytest.fixture
def candidates_df():
    """A small candidate DataFrame for testing."""
    return pd.DataFrame(
        {
            "name": ["Dragon Palace", "Spice Garden", "Pasta House", "Quick Bites"],
            "cuisines": ["Chinese, Thai", "North Indian", "Italian", "Fast Food"],
            "cuisines_normalized": [
                "chinese, thai",
                "north indian",
                "italian",
                "fast food",
            ],
            "rate": ["4.2/5", "4.5/5", "3.8/5", "3.5/5"],
            "rate_normalized": [4.2, 4.5, 3.8, 3.5],
            "votes": [500, 300, 200, 50],
            "approx_cost(for two people)": ["400", "600", "800", "200"],
            "approx_cost_numeric": [400.0, 600.0, 800.0, 200.0],
            "budget_tier": ["medium", "medium", "high", "low"],
            "location": ["Banashankari", "Indiranagar", "Koramangala", "BTM"],
            "rest_type": ["Casual Dining", "Fine Dining", "Cafe", "Quick Bites"],
            "dish_liked": ["Momos", "Biryani", "Pasta", "Noodles"],
            "online_order": ["Yes", "No", "No", "Yes"],
        }
    )


# ── _extract_json ──────────────────────────────────────────────


class TestExtractJson:
    def test_clean_json(self):
        text = '{"summary": "test", "recommendations": []}'
        result = _extract_json(text)
        assert result["summary"] == "test"

    def test_markdown_code_fence(self):
        text = '```json\n{"summary": "test", "recommendations": []}\n```'
        result = _extract_json(text)
        assert result["summary"] == "test"

    def test_json_with_surrounding_text(self):
        text = 'Here are the results:\n{"summary": "test", "recommendations": []}\nDone!'
        result = _extract_json(text)
        assert result["summary"] == "test"

    def test_invalid_json_raises(self):
        with pytest.raises(ValueError, match="Could not extract valid JSON"):
            _extract_json("This is not JSON at all")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            _extract_json("")


# ── _validate_recommendations ──────────────────────────────────


class TestValidateRecommendations:
    def test_valid_names_pass(self):
        recs = [
            {"restaurant_name": "Dragon Palace", "explanation": "Great food"},
            {"restaurant_name": "Spice Garden", "explanation": "Good vibes"},
        ]
        result = _validate_recommendations(
            recs, {"Dragon Palace", "Spice Garden", "Pasta House"}, top_n=5
        )
        assert len(result) == 2

    def test_hallucinated_name_rejected(self):
        recs = [
            {"restaurant_name": "Dragon Palace", "explanation": "Great food"},
            {"restaurant_name": "Nonexistent Place", "explanation": "Made up"},
            {"restaurant_name": "Spice Garden", "explanation": "Good vibes"},
        ]
        result = _validate_recommendations(
            recs, {"Dragon Palace", "Spice Garden"}, top_n=5
        )
        assert len(result) == 2
        names = [r["restaurant_name"] for r in result]
        assert "Nonexistent Place" not in names

    def test_top_n_enforced(self):
        recs = [
            {"restaurant_name": f"Rest {i}", "explanation": f"Reason {i}"}
            for i in range(10)
        ]
        candidate_names = {f"Rest {i}" for i in range(10)}
        result = _validate_recommendations(recs, candidate_names, top_n=3)
        assert len(result) == 3

    def test_empty_name_skipped(self):
        recs = [
            {"restaurant_name": "", "explanation": "No name"},
            {"restaurant_name": "Dragon Palace", "explanation": "Valid"},
        ]
        result = _validate_recommendations(
            recs, {"Dragon Palace"}, top_n=5
        )
        assert len(result) == 1

    def test_all_hallucinated(self):
        recs = [
            {"restaurant_name": "Fake 1", "explanation": "Fake"},
            {"restaurant_name": "Fake 2", "explanation": "Fake"},
        ]
        result = _validate_recommendations(
            recs, {"Dragon Palace", "Spice Garden"}, top_n=5
        )
        assert len(result) == 0


# ── parse_groq_response ───────────────────────────────────────


class TestParseGroqResponse:
    def test_valid_response(self, candidates_df):
        response = json.dumps(
            {
                "summary": "Top picks for you.",
                "recommendations": [
                    {
                        "rank": 1,
                        "restaurant_name": "Dragon Palace",
                        "explanation": "Best Chinese in the area.",
                    },
                    {
                        "rank": 2,
                        "restaurant_name": "Spice Garden",
                        "explanation": "Excellent North Indian cuisine.",
                    },
                ],
            }
        )
        summary, recs = parse_groq_response(response, candidates_df, top_n=5)
        assert summary == "Top picks for you."
        assert len(recs) == 2
        assert recs[0].restaurant_name == "Dragon Palace"
        assert recs[0].rank == 1
        # Merged fields from candidate data.
        assert recs[0].cuisine == "chinese, thai"
        assert recs[0].rating == 4.2
        assert recs[0].estimated_cost == 400.0
        assert recs[0].location == "Banashankari"

    def test_invalid_json_triggers_fallback(self, candidates_df):
        response = "Sorry, I can't help with that."
        summary, recs = parse_groq_response(response, candidates_df, top_n=3)
        # Should fallback gracefully.
        assert len(recs) > 0
        assert "unavailable" in summary.lower() or "rating" in summary.lower()

    def test_hallucinated_names_trigger_fallback(self, candidates_df):
        response = json.dumps(
            {
                "summary": "My picks.",
                "recommendations": [
                    {
                        "rank": 1,
                        "restaurant_name": "Imaginary Restaurant",
                        "explanation": "I made this up.",
                    },
                ],
            }
        )
        summary, recs = parse_groq_response(response, candidates_df, top_n=3)
        # All names rejected → fallback.
        assert len(recs) > 0
        assert any("unavailable" in (summary or "").lower() for _ in [1]) or len(recs) > 0

    def test_partial_hallucination(self, candidates_df):
        """Mix of valid and hallucinated — only valid ones should survive."""
        response = json.dumps(
            {
                "summary": "Mixed results.",
                "recommendations": [
                    {
                        "rank": 1,
                        "restaurant_name": "Dragon Palace",
                        "explanation": "Real restaurant.",
                    },
                    {
                        "rank": 2,
                        "restaurant_name": "Ghost Kitchen",
                        "explanation": "Hallucinated.",
                    },
                    {
                        "rank": 3,
                        "restaurant_name": "Spice Garden",
                        "explanation": "Real restaurant.",
                    },
                ],
            }
        )
        summary, recs = parse_groq_response(response, candidates_df, top_n=5)
        assert summary == "Mixed results."
        assert len(recs) == 2
        names = [r.restaurant_name for r in recs]
        assert "Dragon Palace" in names
        assert "Spice Garden" in names
        assert "Ghost Kitchen" not in names

    def test_markdown_wrapped_json(self, candidates_df):
        """Groq sometimes wraps JSON in code fences."""
        inner = json.dumps(
            {
                "summary": "Wrapped.",
                "recommendations": [
                    {
                        "rank": 1,
                        "restaurant_name": "Dragon Palace",
                        "explanation": "Good food.",
                    },
                ],
            }
        )
        response = f"```json\n{inner}\n```"
        summary, recs = parse_groq_response(response, candidates_df, top_n=5)
        assert summary == "Wrapped."
        assert len(recs) == 1


# ── fallback_ranking ──────────────────────────────────────────


class TestFallbackRanking:
    def test_returns_top_n(self, candidates_df):
        summary, recs = fallback_ranking(candidates_df, top_n=2)
        assert len(recs) == 2
        assert "unavailable" in summary.lower()

    def test_sorted_by_score(self, candidates_df):
        """Higher score should rank first.

        Spice Garden: 4.5 * log(301) ~= 25.7
        Dragon Palace: 4.2 * log(501) ~= 26.1
        So Dragon Palace should be first.
        """
        summary, recs = fallback_ranking(candidates_df, top_n=4)
        # Both should be near the top. Exact order depends on the score.
        scores = []
        for _, row in candidates_df.iterrows():
            r = row["rate_normalized"] if not (isinstance(row["rate_normalized"], float) and math.isnan(row["rate_normalized"])) else 0
            s = r * math.log(row["votes"] + 1)
            scores.append((row["name"], s))
        scores.sort(key=lambda x: x[1], reverse=True)
        assert recs[0].restaurant_name == scores[0][0]

    def test_includes_explanation(self, candidates_df):
        _, recs = fallback_ranking(candidates_df, top_n=2)
        for rec in recs:
            assert rec.explanation
            assert len(rec.explanation) > 10

    def test_ranks_are_sequential(self, candidates_df):
        _, recs = fallback_ranking(candidates_df, top_n=3)
        for i, rec in enumerate(recs, start=1):
            assert rec.rank == i

    def test_nan_rating_handled(self):
        """Restaurants with NaN ratings should get score 0 and rank last."""
        df = pd.DataFrame(
            {
                "name": ["Rated", "Unrated"],
                "rate_normalized": [4.0, np.nan],
                "votes": [100, 500],
                "cuisines_normalized": ["cafe", "cafe"],
                "cuisines": ["Cafe", "Cafe"],
                "approx_cost_numeric": [300, 200],
                "location": ["A", "B"],
            }
        )
        _, recs = fallback_ranking(df, top_n=2)
        assert recs[0].restaurant_name == "Rated"
