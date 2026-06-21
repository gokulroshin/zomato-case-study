"""Unit tests for app.data.filter — candidate filter engine."""

import numpy as np
import pandas as pd
import pytest

from app.data.filter import FilterResult, filter_candidates
from app.models.preferences import BudgetTier, UserPreferences


# ── Fixtures ───────────────────────────────────────────────────


@pytest.fixture
def sample_df():
    """A small preprocessed DataFrame mimicking Phase 1 output.

    Includes sub-area locations for testing substring matching (FILT-002).
    """
    return pd.DataFrame(
        {
            "name": [
                "Dragon Palace",
                "Pasta House",
                "Biryani King",
                "Quick Bites Cafe",
                "Family Diner",
                "Spicy Bowl",
                "Block 5 Pizza",
                "Whitefield Wok",
            ],
            "location": [
                "Banashankari",
                "Indiranagar",
                "Banashankari",
                "Banashankari",
                "Banashankari",
                "Koramangala",
                "Koramangala 5th Block",
                "ITPL Main Road, Whitefield",
            ],
            "listed_in(city)": [
                "Banashankari",
                "Indiranagar",
                "Banashankari",
                "Banashankari",
                "Banashankari",
                "Koramangala 4th Block",
                "Koramangala 5th Block",
                "Whitefield",
            ],
            "cuisines": [
                "Chinese, Thai",
                "Italian, Continental",
                "Biryani, North Indian",
                "Chinese, Fast Food",
                "North Indian, Chinese",
                "Chinese, Korean",
                "Pizza, Italian",
                "Chinese, Thai",
            ],
            "cuisines_normalized": [
                "chinese, thai",
                "italian, continental",
                "biryani, north indian",
                "chinese, fast food",
                "north indian, chinese",
                "chinese, korean",
                "pizza, italian",
                "chinese, thai",
            ],
            "rate": ["4.2/5", "4.5/5", "3.8/5", "3.5/5", "4.0/5", "4.3/5", "4.1/5", "3.9/5"],
            "rate_normalized": [4.2, 4.5, 3.8, 3.5, 4.0, 4.3, 4.1, 3.9],
            "votes": [500, 300, 200, 50, 150, 400, 250, 180],
            "approx_cost(for two people)": ["400", "800", "250", "200", "500", "350", "500", "450"],
            "approx_cost_numeric": [400.0, 800.0, 250.0, 200.0, 500.0, 350.0, 500.0, 450.0],
            "budget_tier": ["medium", "high", "low", "low", "medium", "medium", "medium", "medium"],
            "online_order": ["Yes", "No", "Yes", "Yes", "No", "Yes", "Yes", "Yes"],
            "book_table": ["Yes", "No", "No", "No", "Yes", "No", "No", "No"],
            "rest_type": [
                "Casual Dining",
                "Fine Dining",
                "Quick Bites",
                "Quick Bites",
                "Casual Dining",
                "Cafe",
                "Casual Dining",
                "Quick Bites",
            ],
            "dish_liked": [
                "Momos",
                "Pasta",
                "Biryani",
                "Noodles",
                "Paneer",
                "Kimchi",
                "Margherita",
                "Pad Thai",
            ],
            # Columns that exist in the real data but aren't used by filters:
            "url": [None] * 8,
            "address": [None] * 8,
            "phone": [None] * 8,
            "reviews_list": [None] * 8,
            "menu_item": [None] * 8,
            "listed_in(type)": ["Delivery"] * 8,
        }
    )


# ── Location filter ────────────────────────────────────────────


class TestLocationFilter:
    def test_filters_by_location(self, sample_df):
        prefs = UserPreferences(location="Banashankari")
        result = filter_candidates(sample_df, prefs)
        assert result.total_matches == 4
        names = result.candidates["name"].tolist()
        assert "Pasta House" not in names
        assert "Spicy Bowl" not in names
        assert "Block 5 Pizza" not in names

    def test_location_case_insensitive(self, sample_df):
        prefs = UserPreferences(location="banashankari")
        result = filter_candidates(sample_df, prefs)
        assert result.total_matches == 4

    def test_location_no_match(self, sample_df):
        prefs = UserPreferences(location="JP Nagar")
        result = filter_candidates(sample_df, prefs)
        assert result.is_empty
        assert result.reason is not None
        assert "JP Nagar" in result.reason

    def test_substring_match_koramangala(self, sample_df):
        """Searching 'Koramangala' should match both 'Koramangala' and
        'Koramangala 5th Block' etc. (FILT-002)."""
        prefs = UserPreferences(location="Koramangala")
        result = filter_candidates(sample_df, prefs)
        names = result.candidates["name"].tolist()
        # Spicy Bowl (location=Koramangala, listed_in=Koramangala 4th Block)
        # Block 5 Pizza (location=Koramangala 5th Block)
        assert "Spicy Bowl" in names
        assert "Block 5 Pizza" in names
        assert result.total_matches == 2

    def test_substring_match_whitefield(self, sample_df):
        """Searching 'Whitefield' should match 'ITPL Main Road, Whitefield'
        and listed_in(city)='Whitefield'. (FILT-002)."""
        prefs = UserPreferences(location="Whitefield")
        result = filter_candidates(sample_df, prefs)
        names = result.candidates["name"].tolist()
        assert "Whitefield Wok" in names
        assert result.total_matches == 1

    def test_exact_subarea_still_works(self, sample_df):
        """Searching an exact sub-area should still work."""
        prefs = UserPreferences(location="Koramangala 5th Block")
        result = filter_candidates(sample_df, prefs)
        names = result.candidates["name"].tolist()
        assert "Block 5 Pizza" in names


# ── Budget filter ──────────────────────────────────────────────


class TestBudgetFilter:
    def test_filters_by_budget_low(self, sample_df):
        prefs = UserPreferences(budget=BudgetTier.low)
        result = filter_candidates(sample_df, prefs)
        assert all(
            r["budget_tier"] == "low"
            for _, r in result.candidates.iterrows()
        )

    def test_filters_by_budget_medium(self, sample_df):
        prefs = UserPreferences(budget=BudgetTier.medium)
        result = filter_candidates(sample_df, prefs)
        # Dragon Palace, Family Diner, Spicy Bowl, Block 5 Pizza, Whitefield Wok
        assert result.total_matches == 5


# ── Cuisine filter ─────────────────────────────────────────────


class TestCuisineFilter:
    def test_filters_by_cuisine(self, sample_df):
        prefs = UserPreferences(cuisine="Chinese")
        result = filter_candidates(sample_df, prefs)
        # Dragon Palace, Quick Bites Cafe, Family Diner, Spicy Bowl, Whitefield Wok
        assert result.total_matches == 5

    def test_cuisine_case_insensitive(self, sample_df):
        prefs = UserPreferences(cuisine="chinese")
        result = filter_candidates(sample_df, prefs)
        assert result.total_matches == 5

    def test_cuisine_partial_match(self, sample_df):
        prefs = UserPreferences(cuisine="Italian")
        result = filter_candidates(sample_df, prefs)
        # Pasta House (italian, continental) + Block 5 Pizza (pizza, italian)
        assert result.total_matches == 2
        names = result.candidates["name"].tolist()
        assert "Pasta House" in names
        assert "Block 5 Pizza" in names


# ── Rating filter ──────────────────────────────────────────────


class TestRatingFilter:
    def test_filters_by_min_rating(self, sample_df):
        prefs = UserPreferences(min_rating=4.0)
        result = filter_candidates(sample_df, prefs)
        assert all(
            r["rate_normalized"] >= 4.0
            for _, r in result.candidates.iterrows()
        )

    def test_high_min_rating_reduces_results(self, sample_df):
        prefs = UserPreferences(min_rating=4.5)
        result = filter_candidates(sample_df, prefs)
        assert result.total_matches == 1
        assert result.candidates.iloc[0]["name"] == "Pasta House"

    def test_null_ratings_handled(self):
        """Rows with NaN rating and min_rating set should be excluded
        (since NaN filled to 0 < min_rating)."""
        df = pd.DataFrame(
            {
                "name": ["Rated", "Unrated"],
                "rate_normalized": [4.0, np.nan],
                "votes": [100, 50],
                "location": ["A", "A"],
                "listed_in(city)": ["A", "A"],
                "cuisines_normalized": ["cafe", "cafe"],
                "budget_tier": ["low", "low"],
                "online_order": ["Yes", "Yes"],
                "rest_type": ["Cafe", "Cafe"],
                "approx_cost_numeric": [200, 200],
            }
        )
        prefs = UserPreferences(min_rating=3.5)
        result = filter_candidates(df, prefs)
        assert result.total_matches == 1
        assert result.candidates.iloc[0]["name"] == "Rated"


# ── Additional preferences ─────────────────────────────────────


class TestAdditionalPreferences:
    def test_family_friendly(self, sample_df):
        prefs = UserPreferences(additional_preferences="family-friendly")
        result = filter_candidates(sample_df, prefs)
        # Casual Dining and Fine Dining match "family-friendly"
        for _, r in result.candidates.iterrows():
            assert any(
                kw in r["rest_type"].lower()
                for kw in ("casual dining", "dining", "family")
            )

    def test_quick_service(self, sample_df):
        prefs = UserPreferences(additional_preferences="quick service")
        result = filter_candidates(sample_df, prefs)
        for _, r in result.candidates.iterrows():
            rest_type_lower = r["rest_type"].lower()
            online = str(r.get("online_order", "")).lower()
            assert (
                "quick" in rest_type_lower
                or "delivery" in rest_type_lower
                or online == "yes"
            )


# ── Combined filters ──────────────────────────────────────────


class TestCombinedFilters:
    def test_location_budget_cuisine(self, sample_df):
        """The acceptance criteria query from the implementation plan."""
        prefs = UserPreferences(
            location="Banashankari",
            budget=BudgetTier.medium,
            cuisine="Chinese",
            min_rating=4.0,
        )
        result = filter_candidates(sample_df, prefs)
        assert not result.is_empty
        # Should match Dragon Palace (Banashankari, medium, Chinese, 4.2)
        assert result.candidates.iloc[0]["name"] == "Dragon Palace"

    def test_all_filters_no_match(self, sample_df):
        prefs = UserPreferences(
            location="Banashankari",
            budget=BudgetTier.high,
            cuisine="Japanese",
            min_rating=4.5,
        )
        result = filter_candidates(sample_df, prefs)
        assert result.is_empty
        assert "No restaurants matched" in result.reason


# ── Sorting ────────────────────────────────────────────────────


class TestSorting:
    def test_sorted_by_rating_then_votes(self, sample_df):
        prefs = UserPreferences()  # no filters → all restaurants
        result = filter_candidates(sample_df, prefs)
        ratings = result.candidates["rate_normalized"].tolist()
        # Ratings should be descending.
        for i in range(len(ratings) - 1):
            assert ratings[i] >= ratings[i + 1] or (
                np.isnan(ratings[i + 1])
            ), f"Not sorted at index {i}: {ratings[i]} vs {ratings[i + 1]}"


# ── Top-K cap ──────────────────────────────────────────────────


class TestTopKCap:
    def test_max_candidates_respected(self, sample_df):
        prefs = UserPreferences()
        result = filter_candidates(sample_df, prefs, max_candidates=2)
        assert len(result.candidates) == 2
        assert result.total_matches == 8  # all 8 matched, but capped at 2


# ── FilterResult ───────────────────────────────────────────────


class TestFilterResult:
    def test_is_empty_true(self):
        fr = FilterResult(candidates=pd.DataFrame(), total_matches=0)
        assert fr.is_empty

    def test_is_empty_false(self):
        fr = FilterResult(
            candidates=pd.DataFrame({"a": [1]}), total_matches=1
        )
        assert not fr.is_empty

    def test_reason_set_on_zero_match(self, sample_df):
        prefs = UserPreferences(location="Nonexistent Place")
        result = filter_candidates(sample_df, prefs)
        assert result.reason is not None
        assert "Nonexistent Place" in result.reason
