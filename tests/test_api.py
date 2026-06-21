"""Integration tests for API routes."""

import json
from unittest.mock import patch, MagicMock
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app, app_state

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_dataset():
    """Mock the dataset so tests run quickly without real data."""
    # Create a small mock dataset
    data = [
        {
            "name": "Restaurant A",
            "listed_in(city)": "Banashankari",
            "location": "Banashankari",
            "cuisines_normalized": "chinese, thai",
            "rate_normalized": 4.5,
            "approx_cost_numeric": 500,
            "budget_tier": "medium",
            "rest_type": "casual dining",
            "online_order": "Yes",
            "votes": 100,
        },
        {
            "name": "Restaurant B",
            "listed_in(city)": "Indiranagar",
            "location": "Indiranagar",
            "cuisines_normalized": "italian",
            "rate_normalized": 3.0,
            "approx_cost_numeric": 1200,
            "budget_tier": "high",
            "rest_type": "fine dining",
            "online_order": "No",
            "votes": 50,
        },
    ]
    app_state["df"] = pd.DataFrame(data)
    app_state["dataset_loaded"] = True
    yield
    # Cleanup not strictly necessary since autouse overrides it each test
    
def test_metadata_endpoint():
    """Test that /api/v1/metadata returns expected structure based on mock dataset."""
    response = client.get("/api/v1/metadata")
    assert response.status_code == 200
    data = response.json()
    assert "locations" in data
    assert "cuisines" in data
    assert "budget_tiers" in data
    
    assert "Banashankari" in data["locations"]
    assert "Indiranagar" in data["locations"]
    assert "chinese" in data["cuisines"]
    assert "thai" in data["cuisines"]
    assert "italian" in data["cuisines"]

@patch("app.services.recommender.GroqClient")
def test_recommend_endpoint_success(mock_groq_class):
    """Test the end-to-end recommend endpoint with a mock LLM."""
    mock_client_instance = MagicMock()
    mock_groq_class.return_value = mock_client_instance
    mock_client_instance.model = "mock-llama"
    # Mock the LLM returning a valid JSON string
    mock_client_instance.chat.return_value = json.dumps({
        "summary": "Here are some Chinese places in Banashankari.",
        "recommendations": [
            {
                "rank": 1,
                "restaurant_name": "Restaurant A",
                "explanation": "Great Chinese food in your budget."
            }
        ]
    })
    
    payload = {
        "location": "Banashankari",
        "budget": "medium",
        "cuisine": "chinese",
        "top_n": 5
    }
    
    response = client.post("/api/v1/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == "Here are some Chinese places in Banashankari."
    assert len(data["recommendations"]) == 1
    assert data["recommendations"][0]["restaurant_name"] == "Restaurant A"
    assert data["candidates_considered"] == 1
    assert data["model"] == "mock-llama"

def test_recommend_endpoint_empty_results():
    """Test recommend endpoint when filters match nothing."""
    payload = {
        "location": "Nowhere",
        "budget": "low",
        "cuisine": "alien",
        "top_n": 5
    }
    
    response = client.post("/api/v1/recommend", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert "No restaurants matched" in data["detail"]
