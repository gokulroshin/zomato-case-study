"""Restaurant data model.

Represents a single restaurant after preprocessing, carrying both the
original fields and the normalized/derived columns added in Phase 1.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class Restaurant(BaseModel):
    """A normalized restaurant record from the Zomato dataset.

    This model is used to serialize candidates sent to the LLM prompt
    and to build the final recommendation output.
    """

    name: str
    url: Optional[str] = None
    address: Optional[str] = None
    location: Optional[str] = None
    listed_in_city: Optional[str] = Field(
        default=None,
        description="Neighborhood grouping from the dataset's 'listed_in(city)' column.",
    )
    listed_in_type: Optional[str] = Field(
        default=None,
        description="Listing category (e.g. 'Buffet', 'Delivery').",
    )
    online_order: Optional[str] = None
    book_table: Optional[str] = None
    rest_type: Optional[str] = Field(
        default=None,
        description="Restaurant type (e.g. 'Casual Dining', 'Quick Bites').",
    )
    cuisines: Optional[str] = Field(
        default=None,
        description="Original cuisines string from the dataset.",
    )
    cuisines_normalized: Optional[str] = Field(
        default=None,
        description="Lowercase, trimmed, comma-separated cuisine tags.",
    )
    dish_liked: Optional[str] = None

    # ── Numeric / derived fields ────────────────────────────────
    rate: Optional[str] = Field(
        default=None,
        description="Original rate string (e.g. '4.1/5').",
    )
    rate_normalized: Optional[float] = Field(
        default=None,
        description="Parsed numeric rating (0–5 scale).",
    )
    votes: int = 0
    approx_cost_raw: Optional[str] = Field(
        default=None,
        description="Original cost string from 'approx_cost(for two people)'.",
    )
    approx_cost_numeric: Optional[float] = Field(
        default=None,
        description="Parsed numeric cost for two (₹).",
    )
    budget_tier: Optional[str] = Field(
        default=None,
        description="Derived budget tier: 'low', 'medium', or 'high'.",
    )

    @classmethod
    def from_dataframe_row(cls, row) -> "Restaurant":
        """Construct a Restaurant from a pandas Series (DataFrame row).

        Handles the column-name mapping between the DataFrame and the
        model fields (e.g. ``listed_in(city)`` → ``listed_in_city``).
        """
        return cls(
            name=row.get("name", ""),
            url=row.get("url"),
            address=row.get("address"),
            location=row.get("location"),
            listed_in_city=row.get("listed_in(city)"),
            listed_in_type=row.get("listed_in(type)"),
            online_order=row.get("online_order"),
            book_table=row.get("book_table"),
            rest_type=row.get("rest_type"),
            cuisines=row.get("cuisines"),
            cuisines_normalized=row.get("cuisines_normalized"),
            dish_liked=row.get("dish_liked"),
            rate=row.get("rate"),
            rate_normalized=row.get("rate_normalized"),
            votes=int(row.get("votes", 0)),
            approx_cost_raw=row.get("approx_cost(for two people)"),
            approx_cost_numeric=row.get("approx_cost_numeric"),
            budget_tier=row.get("budget_tier"),
        )
