"""Tests for API routes with caching."""

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to sys.path to import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from services.cache import cache

client = TestClient(app)


def test_positions_endpoint_with_caching():
    """Test that the positions endpoint uses caching."""
    # Clear cache before test
    cache.clear()
    
    # Mock the database function to return sample data
    mock_positions = [
        {
            "id": "pos_1",
            "symbol": "AAPL",
            "type": "Call",  # Changed from "CALL" to "Call"
            "strike": 150.0,
            "expiration": "2023-12-31",
            "quantity": 10,
            "avgPrice": 145.0,
            "marketPrice": 150.0,
            "pnl": 50.0,
            "iv": 0.3,
            "delta": 0.5,
            "gamma": 0.01,
            "theta": -0.05,
            "vega": 0.1
        }
    ]
    
    with patch('api.routes.fetch_positions_from_db', return_value=mock_positions):
        # First request should populate cache
        response1 = client.get("/positions")
        assert response1.status_code == 200
        
        # Second request should use cache
        response2 = client.get("/positions")
        assert response2.status_code == 200
        
        # Both responses should be identical
        assert response1.json() == response2.json()


def test_positions_endpoint_nocache_override():
    """Test that the positions endpoint bypasses cache when nocache=1 is provided."""
    # Clear cache before test
    cache.clear()
    
    # Mock the database function to return different data each time
    mock_positions_first = [
        {
            "id": "pos_1",
            "symbol": "AAPL",
            "type": "Call",  # Changed from "CALL" to "Call"
            "strike": 150.0,
            "expiration": "2023-12-31",
            "quantity": 10,
            "avgPrice": 145.0,
            "marketPrice": 150.0,
            "pnl": 50.0,
            "iv": 0.3,
            "delta": 0.5,
            "gamma": 0.01,
            "theta": -0.05,
            "vega": 0.1
        }
    ]
    
    mock_positions_second = [
        {
            "id": "pos_2",
            "symbol": "GOOGL",
            "type": "Put",  # Changed from "PUT" to "Put"
            "strike": 2500.0,
            "expiration": "2023-12-31",
            "quantity": 5,
            "avgPrice": 2450.0,
            "marketPrice": 2500.0,
            "pnl": 250.0,
            "iv": 0.25,
            "delta": -0.4,
            "gamma": 0.02,
            "theta": -0.03,
            "vega": 0.15
        }
    ]
    
    # Patch the function to return different values on consecutive calls
    def side_effect():
        if not hasattr(side_effect, "call_count"):
            side_effect.call_count = 0
        side_effect.call_count += 1
        return mock_positions_first if side_effect.call_count == 1 else mock_positions_second
    
    with patch('api.routes.fetch_positions_from_db', side_effect=side_effect):
        # First request with cache enabled
        response1 = client.get("/positions")
        assert response1.status_code == 200
        
        # Second request with nocache=1 should get fresh data
        response2 = client.get("/positions?nocache=1")
        assert response2.status_code == 200
        
        # Responses should be different
        assert response1.json() != response2.json()
        assert response2.json()[0]["symbol"] == "GOOGL"