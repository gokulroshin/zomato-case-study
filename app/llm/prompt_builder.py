"""Prompt builder — constructs the system and user messages for Groq.

Design decisions (per implementation plan):
    - System prompt: grounding rules, JSON-only output, no hallucination.
    - User prompt: serializes user preferences + compact candidate JSON.
    - ``reviews_list`` is excluded to control token usage.
    - ``dish_liked`` is included for richer explanations.
    - Candidates are capped at 30–50 per request.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

import pandas as pd

from app.models.preferences import UserPreferences

logger = logging.getLogger(__name__)

# ── System prompt ──────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a restaurant recommendation assistant for Bangalore, India.

## Rules
1. You MUST recommend ONLY from the CANDIDATES list provided below.
2. Do NOT invent or hallucinate any restaurant names.
3. Rank restaurants by how well they match the user's preferences.
4. Provide a short, specific explanation for each recommendation \
   (why it fits the user's criteria).
5. Provide a brief overall summary of your recommendations.
6. Respond with valid JSON ONLY — no markdown, no extra text.

## Output Schema
Return a JSON object with this exact structure:
{
  "summary": "A brief 1-2 sentence summary of the recommendations.",
  "recommendations": [
    {
      "rank": 1,
      "restaurant_name": "Exact name from CANDIDATES",
      "explanation": "Why this restaurant matches the user's preferences."
    }
  ]
}

## Important
- Use the EXACT restaurant name from the CANDIDATES list.
- Return the number of recommendations the user requests (top_n).
- Keep explanations concise (1-2 sentences each).
- Consider rating, cost, cuisine match, and any additional preferences.
"""


# ── Candidate serialization ───────────────────────────────────


def _serialize_candidates(df: pd.DataFrame, max_candidates: int = 30) -> List[Dict[str, Any]]:
    """Convert candidate DataFrame rows to compact dicts for the prompt.

    Fields included: name, cuisines, rating, cost, rest_type, dish_liked,
    location, online_order, votes.
    Fields excluded: reviews_list (token control), url, address, phone.
    """
    rows = df.head(max_candidates)
    candidates = []
    for _, row in rows.iterrows():
        candidate: Dict[str, Any] = {
            "name": row.get("name", ""),
            "cuisines": row.get("cuisines_normalized") or row.get("cuisines", ""),
            "rating": row.get("rate_normalized"),
            "cost_for_two": row.get("approx_cost_numeric"),
            "type": row.get("rest_type", ""),
            "location": row.get("location", ""),
            "online_order": row.get("online_order", ""),
            "votes": int(row.get("votes", 0)),
        }
        # Include dish_liked for richer explanations (if available).
        dish = row.get("dish_liked")
        if pd.notna(dish) and str(dish).strip():
            candidate["popular_dishes"] = str(dish).strip()

        candidates.append(candidate)

    return candidates


# ── User prompt ───────────────────────────────────────────────


def _format_preferences(prefs: UserPreferences) -> str:
    """Build a human-readable preferences block for the user message."""
    lines = []
    if prefs.location:
        lines.append(f"- Location: {prefs.location}")
    if prefs.budget is not None:
        lines.append(f"- Budget upper limit: ₹{prefs.budget} for two")
    if prefs.diet and prefs.diet.lower() != 'any':
        lines.append(f"- Dietary preference: {prefs.diet}")
    if prefs.cuisine:
        lines.append(f"- Cuisine preference: {prefs.cuisine}")
    if prefs.min_rating is not None:
        lines.append(f"- Minimum rating: {prefs.min_rating}")
    if prefs.additional_preferences:
        lines.append(f"- Additional preferences: {prefs.additional_preferences}")
    lines.append(f"- Number of recommendations requested: {prefs.top_n}")
    return "\n".join(lines) if lines else "No specific preferences provided."


# ── Public API ────────────────────────────────────────────────


def build_messages(
    prefs: UserPreferences,
    candidates_df: pd.DataFrame,
    *,
    max_candidates: int = 30,
) -> List[Dict[str, str]]:
    """Build the chat messages list for the Groq API call.

    Parameters
    ----------
    prefs :
        The user's preferences.
    candidates_df :
        The filtered candidate DataFrame from the filter engine.
    max_candidates :
        Maximum candidates to include in the prompt.

    Returns
    -------
    list[dict]
        A list of message dicts with ``role`` and ``content`` keys,
        ready to pass to ``GroqClient.chat()``.
    """
    candidates_json = _serialize_candidates(candidates_df, max_candidates)

    user_content = (
        f"## User Preferences\n"
        f"{_format_preferences(prefs)}\n\n"
        f"## CANDIDATES ({len(candidates_json)} restaurants)\n"
        f"{json.dumps(candidates_json, indent=None, default=str)}"
    )

    logger.debug(
        "Prompt built: %d candidates, ~%d chars.",
        len(candidates_json),
        len(user_content),
    )

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
