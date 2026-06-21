"""Data ingestion, preprocessing, and filtering.

Public API:
    load_dataset       — download from HF or read Parquet cache.
    preprocess         — clean and normalize the raw DataFrame.
    filter_candidates  — apply user preference filters.
"""

from app.data.filter import FilterResult, filter_candidates
from app.data.loader import load_dataset
from app.data.preprocessor import preprocess

__all__ = ["load_dataset", "preprocess", "filter_candidates", "FilterResult"]
