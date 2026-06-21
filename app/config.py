"""Centralized application settings.

Reads configuration from environment variables (or a .env file) using
pydantic-settings.  All secrets and tunables live here so they are never
hardcoded in application code.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Groq ───────────────────────────────────────────────────────
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    groq_temperature: float = 0.3
    groq_timeout_seconds: int = 15
    groq_max_retries: int = 1

    # ── Data ────────────────────────────────────────────────────
    cache_path: Path = Path("data/restaurants.parquet")
    hf_dataset: str = "ManikaSaini/zomato-restaurant-recommendation"

    # ── Filtering ───────────────────────────────────────────────
    max_candidates: int = 30
    default_top_n: int = 5

    # ── Budget tier ranges (cost for two, in ₹) ────────────────
    budget_low_max: int = 300
    budget_medium_max: int = 600

    @property
    def is_groq_configured(self) -> bool:
        """Return True if a Groq API key has been provided."""
        return bool(self.groq_api_key)


# Module-level singleton — import this wherever settings are needed.
settings = Settings()
