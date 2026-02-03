"""API routes for the derivatives trading dashboard."""

from fastapi import APIRouter, WebSocket, Depends
from typing import List
import json
import asyncio

from models import PortfolioItem, Alert, DMADataPoint, IVDataPoint
from services.data_generator import generate_mock_positions, generate_mock_alerts, generate_dma_curve, generate_iv_curve
from services.calculations import calculate_greeks, calculate_iv

# Create router
router = APIRouter()

# In-memory storage for websocket connections
active_connections: List[WebSocket] = []

@router.get("/positions", response_model=List[PortfolioItem])
async def get_positions():
    """Get portfolio positions."""
    return generate_mock_positions()

@router.get("/alerts", response_model=List[Alert])
async def get_alerts():
    """Get alerts."""
    return generate_mock_alerts()

@router.get("/dma-data", response_model=List[DMADataPoint])
async def get_dma_data():
    """Get DMA curve data."""
    return generate_dma_curve()

@router.get("/iv-data", response_model=List[IVDataPoint])
async def get_iv_data():
    """Get implied volatility curve data."""
    return generate_iv_curve()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            # Keep the connection alive
            await asyncio.sleep(30)
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        active_connections.remove(websocket)

async def broadcast_update(update_data: dict):
    """Broadcast update to all active WebSocket connections."""
    for connection in active_connections.copy():
        try:
            await connection.send_text(json.dumps(update_data))
        except Exception as e:
            print(f"Error sending WebSocket message: {e}")
            active_connections.remove(connection)