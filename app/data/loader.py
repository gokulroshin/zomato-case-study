"""Dataset loader — fetch from Hugging Face or local Parquet cache.

First run:
    1. Downloads from HF via the ``datasets`` library.
    2. Converts to a pandas DataFrame.
    3. Saves to ``data/restaurants.parquet`` for fast reuse.

Subsequent runs:
    Reads directly from the Parquet cache (< 2 s warm start).
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from app.config import settings

logger = logging.getLogger(__name__)


def load_dataset(
    *,
    cache_path: Path | None = None,
    hf_dataset: str | None = None,
    force_reload: bool = False,
) -> pd.DataFrame:
    """Return the Zomato restaurant DataFrame.

    Parameters
    ----------
    cache_path:
        Override the default Parquet cache location.
    hf_dataset:
        Override the Hugging Face dataset identifier.
    force_reload:
        If *True*, re-download even when a cache exists.

    Returns
    -------
    pd.DataFrame
        Raw (unprocessed) restaurant data.
    """
    cache = cache_path or settings.cache_path
    hf_id = hf_dataset or settings.hf_dataset

    if cache.exists() and not force_reload:
        logger.info("Loading dataset from Parquet cache: %s", cache)
        df = pd.read_parquet(cache)
        logger.info("Loaded %d rows from cache.", len(df))
        return df

    # ── Cold path: download from Hugging Face ──────────────────
    logger.info("Downloading dataset '%s' from Hugging Face …", hf_id)
    from datasets import load_dataset as hf_load  # heavy import, deferred

    hf_ds = hf_load(hf_id)

    # The dataset may have a single split (e.g. "train") or multiple.
    # Use the first available split.
    split_name = list(hf_ds.keys())[0]
    logger.info("Using split '%s' (%d rows).", split_name, len(hf_ds[split_name]))

    df = hf_ds[split_name].to_pandas()

    # Ensure the cache directory exists and persist.
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(cache, index=False)
    logger.info("Dataset cached to %s.", cache)

    return df
