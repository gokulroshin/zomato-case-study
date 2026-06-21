"""FastAPI application entry point.

Provides the application factory, lifespan management, and the health
check endpoint.  Phase 1 wires dataset loading + preprocessing into the
startup lifecycle.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.data.loader import load_dataset
from app.data.preprocessor import preprocess
from app.api.routes import router as api_router

logger = logging.getLogger(__name__)

# ── Application state shared across requests ────────────────────
app_state: dict = {
    "dataset_loaded": False,
    "dataset_rows": 0,
    "cache_hit": False,
    "started_at": None,
    "df": None,  # preprocessed DataFrame, used by downstream services
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook.

    On startup:
        1. Load the Zomato dataset (from Parquet cache or Hugging Face).
        2. Run preprocessing (normalize rate, cost, cuisines, budget tier).
        3. Store the cleaned DataFrame in ``app_state`` for downstream use.
    """
    app_state["started_at"] = datetime.now(timezone.utc).isoformat()

    # Detect whether we'll hit the cache.
    cache_exists = settings.cache_path.exists()
    app_state["cache_hit"] = cache_exists

    try:
        raw_df: pd.DataFrame = load_dataset()
        df: pd.DataFrame = preprocess(raw_df)
        app_state["df"] = df
        app_state["dataset_loaded"] = True
        app_state["dataset_rows"] = len(df)
        logger.info(
            "Dataset ready: %d rows (cache %s).",
            len(df),
            "hit" if cache_exists else "miss — downloaded from HF",
        )
    except Exception:
        logger.exception("Failed to load or preprocess dataset.")
        # The app still starts so the health endpoint can report the failure.

    yield
    # Shutdown cleanup (if any) goes here.


app = FastAPI(
    title="Zomato AI Restaurant Recommendation System",
    description=(
        "AI-powered restaurant recommendations combining structured "
        "Zomato data filtering with Groq ranking and explanation."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


# ── Health check ────────────────────────────────────────────────
@app.get("/api/v1/health", tags=["system"])
async def health_check():
    """Return service health, dataset status, and Groq configuration state."""
    return {
        "status": "ok" if app_state["dataset_loaded"] else "degraded",
        "started_at": app_state["started_at"],
        "dataset": {
            "loaded": app_state["dataset_loaded"],
            "rows": app_state["dataset_rows"],
            "cache_hit": app_state["cache_hit"],
            "cache_path": str(settings.cache_path),
        },
        "groq": {
            "configured": settings.is_groq_configured,
            "model": settings.groq_model,
        },
    }

# ── Static Frontend ─────────────────────────────────────────────
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
