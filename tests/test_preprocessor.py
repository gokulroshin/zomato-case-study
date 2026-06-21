"""Unit tests for app.data.preprocessor — rate/cost parsing edge cases."""

import math

import numpy as np
import pandas as pd
import pytest

from app.data.preprocessor import (
    _assign_budget_tier,
    _normalize_cuisines,
    _parse_cost,
    _parse_rate,
    preprocess,
)


# ── _parse_rate ────────────────────────────────────────────────


class TestParseRate:
    """Covers normal values, edge cases, and malformed strings."""

    def test_normal_with_slash(self):
        assert _parse_rate("4.1/5") == 4.1

    def test_normal_without_slash(self):
        assert _parse_rate("3.9") == 3.9

    def test_integer_rate(self):
        assert _parse_rate("4/5") == 4.0

    def test_new_string(self):
        assert math.isnan(_parse_rate("NEW"))

    def test_new_lowercase(self):
        assert math.isnan(_parse_rate("new"))

    def test_dash(self):
        assert math.isnan(_parse_rate("-"))

    def test_double_dash(self):
        assert math.isnan(_parse_rate("--"))

    def test_empty_string(self):
        assert math.isnan(_parse_rate(""))

    def test_none(self):
        assert math.isnan(_parse_rate(None))

    def test_nan(self):
        assert math.isnan(_parse_rate(np.nan))

    def test_whitespace(self):
        assert _parse_rate("  4.5 / 5  ") == 4.5

    def test_garbage(self):
        assert math.isnan(_parse_rate("abc"))


# ── _parse_cost ────────────────────────────────────────────────


class TestParseCost:
    """Covers single values, ranges, commas, and malformed strings."""

    def test_single_value(self):
        assert _parse_cost("300") == 300.0

    def test_single_with_comma(self):
        assert _parse_cost("1,200") == 1200.0

    def test_range_no_spaces(self):
        assert _parse_cost("300-400") == 350.0

    def test_range_with_spaces(self):
        assert _parse_cost("300 - 400") == 350.0

    def test_range_with_en_dash(self):
        assert _parse_cost("200–300") == 250.0

    def test_dash_only(self):
        assert math.isnan(_parse_cost("-"))

    def test_double_dash(self):
        assert math.isnan(_parse_cost("--"))

    def test_empty_string(self):
        assert math.isnan(_parse_cost(""))

    def test_none(self):
        assert math.isnan(_parse_cost(None))

    def test_nan(self):
        assert math.isnan(_parse_cost(np.nan))

    def test_garbage(self):
        assert math.isnan(_parse_cost("free"))


# ── _normalize_cuisines ────────────────────────────────────────


class TestNormalizeCuisines:
    def test_normal(self):
        assert _normalize_cuisines("Chinese, Italian, Mexican") == (
            "chinese, italian, mexican"
        )

    def test_extra_whitespace(self):
        assert _normalize_cuisines("  North Indian ,  Mughlai  ") == (
            "north indian, mughlai"
        )

    def test_single(self):
        assert _normalize_cuisines("Cafe") == "cafe"

    def test_empty(self):
        assert _normalize_cuisines("") is None

    def test_none(self):
        assert _normalize_cuisines(None) is None

    def test_nan(self):
        assert _normalize_cuisines(np.nan) is None


# ── _assign_budget_tier ────────────────────────────────────────


class TestAssignBudgetTier:
    def test_low(self):
        assert _assign_budget_tier(200) == "low"

    def test_low_boundary(self):
        assert _assign_budget_tier(300) == "low"

    def test_medium(self):
        assert _assign_budget_tier(450) == "medium"

    def test_medium_boundary(self):
        assert _assign_budget_tier(600) == "medium"

    def test_high(self):
        assert _assign_budget_tier(800) == "high"

    def test_nan(self):
        assert _assign_budget_tier(np.nan) is None


# ── preprocess (integration) ──────────────────────────────────


class TestPreprocess:
    """Verify the full preprocess pipeline on a small synthetic DataFrame."""

    @pytest.fixture
    def raw_df(self):
        return pd.DataFrame(
            {
                "name": ["A", "B", "", None, "E"],
                "rate": ["4.1/5", "NEW", "-", "3.5/5", "3.0"],
                "votes": [100, "50", 0, "abc", 200],
                "cuisines": ["Chinese, Italian", "Cafe", None, "Pizza", "Biryani"],
                "approx_cost(for two people)": ["300", "1,200", "200-400", None, "600"],
                "url": [None] * 5,
                "address": [None] * 5,
                "online_order": [None] * 5,
                "book_table": [None] * 5,
                "phone": [None] * 5,
                "location": [None] * 5,
                "rest_type": [None] * 5,
                "dish_liked": [None] * 5,
                "reviews_list": [None] * 5,
                "menu_item": [None] * 5,
                "listed_in(type)": [None] * 5,
                "listed_in(city)": [None] * 5,
            }
        )

    def test_drops_empty_name(self, raw_df):
        out = preprocess(raw_df)
        # Rows with empty or None name should be dropped.
        assert len(out) == 3  # A, B, E survive

    def test_rate_normalized(self, raw_df):
        out = preprocess(raw_df)
        assert out.iloc[0]["rate_normalized"] == 4.1
        assert math.isnan(out.iloc[1]["rate_normalized"])  # "NEW"

    def test_cost_numeric(self, raw_df):
        out = preprocess(raw_df)
        assert out.iloc[0]["approx_cost_numeric"] == 300.0

    def test_cuisines_normalized(self, raw_df):
        out = preprocess(raw_df)
        assert out.iloc[0]["cuisines_normalized"] == "chinese, italian"

    def test_budget_tier(self, raw_df):
        out = preprocess(raw_df)
        assert out.iloc[0]["budget_tier"] == "low"

    def test_votes_cast(self, raw_df):
        out = preprocess(raw_df)
        assert out.iloc[0]["votes"] == 100
        # "abc" should become 0 after coerce.
