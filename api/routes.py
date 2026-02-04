"""API routes for the derivatives trading dashboard."""

from fastapi import APIRouter, WebSocket
from typing import List
import json
import asyncio
import os
from datetime import datetime, timedelta

from models import PortfolioItem, Alert, DMADataPoint, IVDataPoint, OptionType, Priority
from services.data_generator import (
    generate_mock_positions, generate_mock_alerts, generate_dma_curve, generate_iv_curve
)
from services.database import get_db_connection, TursoClient
from services.market_data import get_stock_price

# Create router
router = APIRouter()

# In-memory storage for websocket connections
active_connections: List[WebSocket] = []


@router.get("/positions", response_model=List[PortfolioItem])
async def get_positions():
    """Get portfolio positions from database or fallback to mock."""
    positions = fetch_positions_from_db()
    if positions:
        return positions
    # Fallback to mock with real prices
    return generate_mock_positions()


def fetch_positions_from_db() -> List[PortfolioItem]:
    """Fetch positions from Turso database."""
    try:
        conn = get_db_connection()
        
        # Get distinct tickers from daily_prices
        if isinstance(conn, TursoClient):
            rows = conn.execute("SELECT DISTINCT ticker FROM daily_prices ORDER BY ticker")
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT ticker FROM daily_prices ORDER BY ticker")
            rows = cursor.fetchall()
        
        if not rows:
            conn.close()
            return []
        
        tickers = [row['ticker'] if isinstance(row, dict) else row[0] for row in rows]
        positions = []
        
        for i, ticker in enumerate(tickers[:10]):  # Limit to 10 positions
            # Get latest price
            latest_price = get_stock_price(ticker)
            if not latest_price:
                latest_price = 100.0
            
            # Create synthetic positions for each ticker
            for j, opt_type in enumerate([OptionType.CALL, OptionType.PUT]):
                strike_offset = 0.05 if j == 0 else -0.05
                strike = round(latest_price * (1 + strike_offset), 2)
                expiration = (datetime.now() + timedelta(days=45)).strftime("%Y-%m-%d")
                
                # Greeks estimation
                delta = 0.6 if opt_type == OptionType.CALL else -0.4
                
                position = PortfolioItem(
                    id=f"pos_{i}_{j}",
                    symbol=ticker,
                    type=opt_type,
                    strike=strike,
                    expiration=expiration,
                    quantity=10,
                    avgPrice=round(latest_price * 0.1, 2),
                    marketPrice=round(latest_price * 0.12, 2),
                    pnl=round(latest_price * 0.5, 2),
                    iv=0.35,
                    delta=round(delta, 2),
                    gamma=0.05,
                    theta=-0.02,
                    vega=0.15
                )
                positions.append(position)
        
        conn.close()
        return positions
    except Exception as e:
        print(f"Error fetching positions from DB: {e}")
        return []


@router.get("/alerts", response_model=List[Alert])
async def get_alerts():
    """Get alerts from database analysis or fallback to mock."""
    alerts = fetch_alerts_from_db()
    if alerts:
        return alerts
    return generate_mock_alerts()


def fetch_alerts_from_db() -> List[Alert]:
    """Generate alerts based on database analysis."""
    try:
        conn = get_db_connection()
        alerts = []
        
        # Check for recent IV spikes
        if isinstance(conn, TursoClient):
            iv_rows = conn.execute("""
                SELECT ticker, iv_30day, iv_52wk_high, iv_52wk_low 
                FROM iv_history 
                ORDER BY date DESC 
                LIMIT 20
            """)
        else:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ticker, iv_30day, iv_52wk_high, iv_52wk_low 
                FROM iv_history 
                ORDER BY date DESC 
                LIMIT 20
            """)
            iv_rows = cursor.fetchall()
        
        for i, row in enumerate(iv_rows):
            ticker = row['ticker'] if isinstance(row, dict) else row[0]
            iv_30 = row.get('iv_30day') if isinstance(row, dict) else row[1]
            iv_high = row.get('iv_52wk_high') if isinstance(row, dict) else row[2]
            iv_low = row.get('iv_52wk_low') if isinstance(row, dict) else row[3]
            
            if iv_30 and iv_high and iv_30 > iv_high * 0.8:
                alert = Alert(
                    id=f"alert_iv_{i}",
                    title=f"High IV Alert: {ticker}",
                    description=f"{ticker} IV at {iv_30:.1%}, near 52wk high of {iv_high:.1%}",
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    priority=Priority.HIGH,
                    read=False
                )
                alerts.append(alert)
        
        conn.close()
        return alerts[:5]  # Limit to 5 alerts
    except Exception as e:
        print(f"Error fetching alerts from DB: {e}")
        return []


@router.get("/dma-data", response_model=List[DMADataPoint])
async def get_dma_data():
    """Get DMA curve data from database or fallback to mock."""
    dma_data = fetch_dma_from_db()
    if dma_data:
        return dma_data
    return generate_dma_curve()


def fetch_dma_from_db() -> List[DMADataPoint]:
    """Fetch DMA (20-day moving average) from daily_prices."""
    try:
        conn = get_db_connection()
        
        # Get a popular ticker with data
        if isinstance(conn, TursoClient):
            ticker_rows = conn.execute("SELECT DISTINCT ticker FROM daily_prices LIMIT 1")
            if not ticker_rows:
                conn.close()
                return []
            ticker = ticker_rows[0].get('ticker') if isinstance(ticker_rows[0], dict) else ticker_rows[0][0]
            
            # Get last 50 days of closing prices
            rows = conn.execute("""
                SELECT date, close 
                FROM daily_prices 
                WHERE ticker = ? 
                ORDER BY date DESC 
                LIMIT 50
            """, [ticker])
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT ticker FROM daily_prices LIMIT 1")
            ticker_row = cursor.fetchone()
            if not ticker_row:
                conn.close()
                return []
            ticker = ticker_row[0]
            
            cursor.execute("""
                SELECT date, close 
                FROM daily_prices 
                WHERE ticker = ? 
                ORDER BY date DESC 
                LIMIT 50
            """, (ticker,))
            rows = cursor.fetchall()
        
        if not rows:
            conn.close()
            return []
        
        # Reverse to chronological order
        rows = list(reversed(rows))
        
        # Calculate 20-day moving average
        dma_data = []
        closes = [row['close'] if isinstance(row, dict) else row[1] for row in rows]
        
        for i, row in enumerate(rows):
            if i < 19:  # Need 20 days for DMA
                continue
            
            date = row['date'] if isinstance(row, dict) else row[0]
            dma_20 = sum(closes[i-19:i+1]) / 20
            
            dma_data.append(DMADataPoint(
                time=date,
                value=round(dma_20, 2)
            ))
        
        conn.close()
        return dma_data
    except Exception as e:
        print(f"Error fetching DMA from DB: {e}")
        return []


@router.get("/iv-data", response_model=List[IVDataPoint])
async def get_iv_data():
    """Get implied volatility curve data from database or fallback to mock."""
    iv_data = fetch_iv_from_db()
    if iv_data:
        return iv_data
    return generate_iv_curve()


def fetch_iv_from_db() -> List[IVDataPoint]:
    """Fetch IV data from iv_history table."""
    try:
        conn = get_db_connection()
        
        # Get latest IV data for available tickers
        if isinstance(conn, TursoClient):
            # Get the most recent date
            date_rows = conn.execute("SELECT MAX(date) as max_date FROM iv_history")
            if not date_rows:
                conn.close()
                return []
            latest_date = date_rows[0].get('max_date') if isinstance(date_rows[0], dict) else date_rows[0][0]
            
            rows = conn.execute("""
                SELECT ticker, iv_30day 
                FROM iv_history 
                WHERE date = ? AND iv_30day IS NOT NULL
                ORDER BY ticker
            """, [latest_date])
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(date) FROM iv_history")
            latest_date = cursor.fetchone()[0]
            if not latest_date:
                conn.close()
                return []
            
            cursor.execute("""
                SELECT ticker, iv_30day 
                FROM iv_history 
                WHERE date = ? AND iv_30day IS NOT NULL
                ORDER BY ticker
            """, (latest_date,))
            rows = cursor.fetchall()
        
        if not rows:
            conn.close()
            return []
        
        # Create IV curve points from ticker data
        iv_data = []
        base_strike = 50  # Synthetic strike scale
        
        for i, row in enumerate(rows):
            ticker = row['ticker'] if isinstance(row, dict) else row[0]
            iv_30 = row['iv_30day'] if isinstance(row, dict) else row[1]
            if iv_30 is None:
                continue
            
            # Create synthetic strike based on position
            strike = base_strike + (i * 10)
            
            iv_data.append(IVDataPoint(
                strike=strike,
                iv=round(iv_30, 3)
            ))
        
        conn.close()
        return iv_data if iv_data else []
    except Exception as e:
        print(f"Error fetching IV from DB: {e}")
        return []


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
