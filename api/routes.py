"""API routes for the derivatives trading dashboard."""

from fastapi import APIRouter, WebSocket
from typing import List
import json
import asyncio
import logging
from datetime import datetime, timedelta

from models import PortfolioItem, Alert, DMADataPoint, IVDataPoint, OptionType, Priority
from services.data_generator import (
    generate_mock_positions, generate_mock_alerts, generate_dma_curve, generate_iv_curve
)
from services.database import get_db
from services.market_data import get_stock_price

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# In-memory storage for websocket connections
active_connections: List[WebSocket] = []


@router.get("/debug/tickers")
async def get_debug_tickers():
    """Debug endpoint to check what tickers are in the database."""
    try:
        with get_db() as db:
            is_turso = hasattr(db, 'execute')
            
            if is_turso:
                result = db.execute("SELECT DISTINCT ticker FROM daily_prices ORDER BY ticker")
                tickers = [row['ticker'] for row in result]
                count_result = db.execute("SELECT COUNT(*) as count FROM daily_prices")
                count = count_result[0]['count'] if count_result else 0
            else:
                cursor = db.cursor()
                cursor.execute("SELECT DISTINCT ticker FROM daily_prices ORDER BY ticker")
                tickers = [row[0] for row in cursor.fetchall()]
                cursor.execute("SELECT COUNT(*) FROM daily_prices")
                count = cursor.fetchone()[0]
            
            return {
                "tickers": tickers,
                "total_rows": count,
                "source": "turso" if is_turso else "sqlite"
            }
    except Exception as e:
        return {"error": str(e)}


@router.get("/positions", response_model=List[PortfolioItem])
async def get_positions():
    """Get portfolio positions from database with fallback to mock data."""
    try:
        positions = fetch_positions_from_db()
        if positions:
            logger.info(f"Returning {len(positions)} real positions from database")
            return positions
        else:
            logger.warning("No real positions found in database, falling back to mock data")
            return generate_mock_positions()
    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        return generate_mock_positions()


def fetch_positions_from_db() -> List[PortfolioItem]:
    """Fetch positions from database with proper error handling."""
    try:
        with get_db() as db:
            # Check if we're using Turso or SQLite
            is_turso = hasattr(db, 'execute')
            
            if is_turso:
                # For Turso, we need to get distinct tickers first
                ticker_result = db.execute("SELECT DISTINCT ticker FROM daily_prices ORDER BY ticker")
                tickers = [row['ticker'] for row in ticker_result]
            else:
                # For SQLite
                cursor = db.cursor()
                cursor.execute("SELECT DISTINCT ticker FROM daily_prices ORDER BY ticker")
                tickers = [row[0] for row in cursor.fetchall()]
            
            positions = []
            for i, ticker in enumerate(tickers[:10]):  # Limit to 10 positions
                if is_turso:
                    # Get recent data for this ticker (last record)
                    price_data = db.execute("""
                        SELECT * FROM daily_prices 
                        WHERE ticker = ? 
                        ORDER BY date DESC 
                        LIMIT 1
                    """, [ticker])
                    
                    iv_data = db.execute("""
                        SELECT * FROM iv_history 
                        WHERE ticker = ? 
                        ORDER BY date DESC 
                        LIMIT 1
                    """, [ticker])
                    
                    if not price_data:
                        continue
                        
                    latest_price = price_data[0]
                    latest_iv = iv_data[0] if iv_data else None
                else:
                    # For SQLite
                    cursor = db.cursor()
                    cursor.execute("""
                        SELECT * FROM daily_prices 
                        WHERE ticker = ? 
                        ORDER BY date DESC 
                        LIMIT 1
                    """, (ticker,))
                    price_row = cursor.fetchone()
                    
                    if not price_row:
                        continue
                    
                    latest_price = dict(price_row)  # Convert Row to dict
                    
                    cursor.execute("""
                        SELECT * FROM iv_history 
                        WHERE ticker = ? 
                        ORDER BY date DESC 
                        LIMIT 1
                    """, (ticker,))
                    iv_row = cursor.fetchone()
                    latest_iv = dict(iv_row) if iv_row else None
                
                # Create portfolio item based on real data
                close_price = latest_price['close']
                open_price = latest_price['open']
                
                # Determine option type based on price movement
                option_type = OptionType.CALL if close_price > open_price else OptionType.PUT
                strike = round(close_price, 2)
                expiration = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                quantity = 10
                avg_price = round(strike * 0.95, 2)  # Slightly OTM assumption
                market_price = round(strike, 2)
                pnl = round((market_price - avg_price) * quantity, 2)
                
                # Use real IV if available, otherwise generate mock
                iv = latest_iv['iv_30day'] if latest_iv and latest_iv.get('iv_30day') else 0.3
                
                # Simplified greeks
                delta = 0.5 if option_type == OptionType.CALL else -0.5
                gamma = 0.01
                theta = -0.05
                vega = 0.1

                position = PortfolioItem(
                    id=f"pos_{i+1}",
                    symbol=ticker,
                    type=option_type,
                    strike=strike,
                    expiration=expiration,
                    quantity=quantity,
                    avgPrice=avg_price,
                    marketPrice=market_price,
                    pnl=pnl,
                    iv=iv,
                    delta=delta,
                    gamma=gamma,
                    theta=theta,
                    vega=vega
                )
                positions.append(position)
            
            return positions
    
    except Exception as e:
        logger.error(f"Error fetching positions from database: {e}")
        return []


@router.get("/alerts", response_model=List[Alert])
async def get_alerts():
    """Generate alerts based on actual data from database with fallback to mock."""
    try:
        alerts = fetch_alerts_from_db()
        if alerts:
            return alerts
        else:
            logger.info("No real alerts generated, falling back to mock data")
            return generate_mock_alerts()
    except Exception as e:
        logger.error(f"Error generating alerts: {e}")
        return generate_mock_alerts()


def fetch_alerts_from_db() -> List[Alert]:
    """Generate alerts based on database analysis."""
    try:
        with get_db() as db:
            # Check if we're using Turso or SQLite
            is_turso = hasattr(db, 'execute')
            
            alerts = []
            
            # Check for IV spikes - join iv_history with iv_52wk_ranges
            if is_turso:
                iv_rows = db.execute("""
                    SELECT h.ticker, h.date, h.atm_iv, r.low_52wk
                    FROM iv_history h
                    JOIN iv_52wk_ranges r ON h.ticker = r.ticker
                    WHERE h.atm_iv IS NOT NULL AND r.low_52wk IS NOT NULL AND r.low_52wk > 0
                    ORDER BY h.date DESC 
                    LIMIT 20
                """)
            else:
                cursor = db.cursor()
                cursor.execute("""
                    SELECT h.ticker, h.date, h.atm_iv, r.low_52wk
                    FROM iv_history h
                    JOIN iv_52wk_ranges r ON h.ticker = r.ticker
                    WHERE h.atm_iv IS NOT NULL AND r.low_52wk IS NOT NULL AND r.low_52wk > 0
                    ORDER BY h.date DESC 
                    LIMIT 20
                """)
                iv_rows = [dict(row) for row in cursor.fetchall()]
            
            alert_id = 1
            seen_tickers = set()
            for row in iv_rows:
                ticker = row['ticker']
                if ticker in seen_tickers:
                    continue
                seen_tickers.add(ticker)
                
                atm_iv = row['atm_iv']
                low_52wk = row['low_52wk']
                
                # Check for IV spike (>80% of 52-week range from low)
                if atm_iv > low_52wk * 1.8:
                    alert = Alert(
                        id=f"alert_iv_{alert_id}",
                        title=f"IV Elevated: {ticker}",
                        description=f"{ticker} IV at {(atm_iv*100):.1f}%, near 52-week high",
                        timestamp=row['date'],
                        priority=Priority.HIGH if atm_iv > low_52wk * 2 else Priority.MEDIUM,
                        read=False
                    )
                    alerts.append(alert)
                    alert_id += 1
                    if alert_id > 3:  # Limit to 3 IV alerts
                        break
            
            # Check for large price movements (>5% in a day)
            if is_turso:
                price_rows = db.execute("""
                    SELECT ticker, date, open, close
                    FROM daily_prices 
                    WHERE open > 0 AND close > 0
                    ORDER BY date DESC 
                    LIMIT 50
                """)
            else:
                cursor = db.cursor()
                cursor.execute("""
                    SELECT ticker, date, open, close
                    FROM daily_prices 
                    WHERE open > 0 AND close > 0
                    ORDER BY date DESC 
                    LIMIT 50
                """)
                price_rows = [dict(row) for row in cursor.fetchall()]
            
            # Group by ticker
            ticker_prices = {}
            for row in price_rows:
                ticker = row['ticker']
                if ticker not in ticker_prices:
                    ticker_prices[ticker] = []
                ticker_prices[ticker].append(row)
            
            # Check for large movements
            for ticker, prices in ticker_prices.items():
                if len(prices) < 2:
                    continue
                
                # Check most recent day
                latest = prices[0]
                open_price = latest['open']
                close_price = latest['close']
                
                if open_price > 0:
                    pct_change = ((close_price - open_price) / open_price) * 100
                    
                    if abs(pct_change) > 5:  # 5% threshold
                        priority = Priority.HIGH if abs(pct_change) > 10 else Priority.MEDIUM
                        direction = "gained" if pct_change > 0 else "dropped"
                        
                        alert = Alert(
                            id=f"alert_price_{alert_id}",
                            title=f"Large Price Movement: {ticker}",
                            description=f"{ticker} {direction} {abs(pct_change):.1f}% today",
                            timestamp=latest['date'],
                            priority=priority,
                            read=False
                        )
                        alerts.append(alert)
                        alert_id += 1
                        if alert_id > 6:  # Limit total alerts
                            break
            
            return alerts[:5]  # Return maximum of 5 alerts
    
    except Exception as e:
        logger.error(f"Error fetching alerts from database: {e}")
        return []


@router.get("/dma-data", response_model=List[DMADataPoint])
async def get_dma_data():
    """Fetch daily_prices from database, calculate DMA (20-day simple moving average)."""
    try:
        dma_data = fetch_dma_from_db()
        if dma_data:
            logger.info(f"Returning {len(dma_data)} real DMA data points from database")
            return dma_data
        else:
            logger.info("No real DMA data found, falling back to mock data")
            return generate_dma_curve()
    except Exception as e:
        logger.error(f"Error calculating DMA: {e}")
        return generate_dma_curve()


def fetch_dma_from_db() -> List[DMADataPoint]:
    """Fetch DMA (20-day moving average) from daily_prices."""
    try:
        with get_db() as db:
            is_turso = hasattr(db, 'execute')
            prices = []
            
            # Get first available ticker from database (not hardcoded SPY)
            if is_turso:
                ticker_rows = db.execute("SELECT DISTINCT ticker FROM daily_prices LIMIT 1")
                if ticker_rows:
                    ticker = ticker_rows[0]['ticker']
                    logger.info(f"Using ticker '{ticker}' for DMA calculation")
                    prices = db.execute("""
                        SELECT date, close 
                        FROM daily_prices 
                        WHERE ticker = ?
                        ORDER BY date DESC 
                        LIMIT 50
                    """, [ticker])
                    prices = list(reversed(prices))
            else:
                # For SQLite
                cursor = db.cursor()
                cursor.execute("SELECT DISTINCT ticker FROM daily_prices LIMIT 1")
                ticker_row = cursor.fetchone()
                if ticker_row:
                    ticker = ticker_row[0]
                    logger.info(f"Using ticker '{ticker}' for DMA calculation")
                    cursor.execute("""
                        SELECT date, close 
                        FROM daily_prices 
                        WHERE ticker = ?
                        ORDER BY date DESC 
                        LIMIT 50
                    """, (ticker,))
                    prices = [dict(row) for row in reversed(cursor.fetchall())]
            
            if not prices:
                return []
            
            # Calculate 20-day SMA
            dma_data = []
            window_size = 20
            
            for i in range(window_size - 1, len(prices)):
                # Calculate SMA for the window ending at index i
                window = prices[i - window_size + 1:i + 1]
                sma = sum(p['close'] for p in window) / window_size
                
                dma_data.append(DMADataPoint(
                    time=prices[i]['date'],
                    value=round(sma, 2)
                ))
            
            return dma_data
    
    except Exception as e:
        logger.error(f"Error calculating DMA from database: {e}")
        return []


@router.get("/iv-data", response_model=List[IVDataPoint])
async def get_iv_data():
    """Fetch iv_history from database."""
    try:
        iv_data = fetch_iv_from_db()
        if iv_data:
            return iv_data
        else:
            logger.info("No real IV data found, falling back to mock data")
            return generate_iv_curve()
    except Exception as e:
        logger.error(f"Error fetching IV data: {e}")
        return generate_iv_curve()


def fetch_iv_from_db() -> List[IVDataPoint]:
    """Fetch IV data from iv_history table using atm_iv column."""
    try:
        with get_db() as db:
            is_turso = hasattr(db, 'execute')
            rows = []
            
            if is_turso:
                # Find the latest date with IV data (any data, not requiring 3+ tickers)
                date_check = db.execute("""
                    SELECT date 
                    FROM iv_history 
                    WHERE atm_iv IS NOT NULL 
                    GROUP BY date 
                    ORDER BY date DESC 
                    LIMIT 1
                """)
                
                if not date_check:
                    logger.warning("No IV data found in database")
                    return []
                
                latest_date = date_check[0]['date']
                logger.info(f"Using IV data from date: {latest_date}")
                
                rows = db.execute("""
                    SELECT h.ticker, h.atm_iv, r.high_52wk, r.low_52wk
                    FROM iv_history h
                    LEFT JOIN iv_52wk_ranges r ON h.ticker = r.ticker
                    WHERE h.date = ? AND h.atm_iv IS NOT NULL
                    ORDER BY h.ticker
                """, [latest_date])
            else:
                cursor = db.cursor()
                cursor.execute("""
                    SELECT date 
                    FROM iv_history 
                    WHERE atm_iv IS NOT NULL 
                    GROUP BY date 
                    ORDER BY date DESC 
                    LIMIT 1
                """)
                date_row = cursor.fetchone()
                
                if not date_row:
                    return []
                
                latest_date = date_row[0]
                
                cursor.execute("""
                    SELECT h.ticker, h.atm_iv, r.high_52wk, r.low_52wk
                    FROM iv_history h
                    LEFT JOIN iv_52wk_ranges r ON h.ticker = r.ticker
                    WHERE h.date = ? AND h.atm_iv IS NOT NULL
                    ORDER BY h.ticker
                """, (latest_date,))
                rows = [dict(row) for row in cursor.fetchall()]
            
            if not rows:
                logger.warning("No IV rows found for the latest date")
                return []
            
            logger.info(f"Found {len(rows)} IV records from database")
            
            # Transform to IVDataPoint objects
            iv_points = []
            for i, row in enumerate(rows[:20]):
                ticker = row['ticker']
                atm_iv = row['atm_iv']
                
                if atm_iv is not None:
                    # Use ticker position for distinct strike values
                    strike = float(100 + i * 10)
                    
                    iv_points.append(IVDataPoint(
                        strike=round(strike, 0),
                        iv=round(atm_iv, 3)
                    ))
            
            logger.info(f"Returning {len(iv_points)} real IV data points")
            return iv_points
    
    except Exception as e:
        logger.error(f"Error fetching IV data from database: {e}")
        return []


@router.get("/dma-data-by-ticker")
async def get_dma_data_by_ticker():
    """Fetch DMA data for all tickers, grouped by ticker."""
    try:
        dma_by_ticker = fetch_dma_by_ticker()
        if dma_by_ticker:
            return {"tickers": dma_by_ticker}
        return {"tickers": {}, "error": "No DMA data found"}
    except Exception as e:
        logger.error(f"Error fetching DMA by ticker: {e}")
        return {"tickers": {}, "error": str(e)}


def fetch_dma_by_ticker() -> dict:
    """Fetch 50-day and 200-day DMA for each ticker in the database."""
    try:
        with get_db() as db:
            is_turso = hasattr(db, 'execute')
            
            # Get all tickers
            if is_turso:
                ticker_rows = db.execute("SELECT DISTINCT ticker FROM daily_prices ORDER BY ticker")
                tickers = [row['ticker'] for row in ticker_rows]
            else:
                cursor = db.cursor()
                cursor.execute("SELECT DISTINCT ticker FROM daily_prices ORDER BY ticker")
                tickers = [row[0] for row in cursor.fetchall()]
            
            result = {}
            dma_50_window = 50
            dma_200_window = 200
            
            for ticker in tickers:
                if is_turso:
                    prices = db.execute("""
                        SELECT date, close 
                        FROM daily_prices 
                        WHERE ticker = ?
                        ORDER BY date ASC 
                        LIMIT 250
                    """, [ticker])
                else:
                    cursor.execute("""
                        SELECT date, close 
                        FROM daily_prices 
                        WHERE ticker = ?
                        ORDER BY date ASC 
                        LIMIT 250
                    """, (ticker,))
                    prices = [dict(row) for row in cursor.fetchall()]
                
                # Need at least 200 days for full 200-day DMA
                if len(prices) < dma_50_window:
                    continue
                
                # Calculate 50-day and 200-day DMA
                dma_data = []
                for i in range(len(prices)):
                    point = {
                        "time": prices[i]['date'],
                        "close": round(prices[i]['close'], 2)
                    }
                    
                    # 50-day DMA (if we have enough data)
                    if i >= dma_50_window - 1:
                        window_50 = prices[i - dma_50_window + 1:i + 1]
                        dma_50 = sum(p['close'] for p in window_50) / dma_50_window
                        point["dma_50"] = round(dma_50, 2)
                    
                    # 200-day DMA (if we have enough data)
                    if i >= dma_200_window - 1:
                        window_200 = prices[i - dma_200_window + 1:i + 1]
                        dma_200 = sum(p['close'] for p in window_200) / dma_200_window
                        point["dma_200"] = round(dma_200, 2)
                    
                    # Only include points that have at least the 50-day DMA
                    if "dma_50" in point:
                        dma_data.append(point)
                
                if dma_data:
                    result[ticker] = dma_data
            
            logger.info(f"Returning 50/200-day DMA data for {len(result)} tickers")
            return result
    
    except Exception as e:
        logger.error(f"Error calculating DMA by ticker: {e}")
        return {}


@router.get("/iv-data-by-ticker")
async def get_iv_data_by_ticker():
    """Fetch IV history for all tickers, grouped by ticker."""
    try:
        iv_by_ticker = fetch_iv_by_ticker()
        if iv_by_ticker:
            return {"tickers": iv_by_ticker}
        return {"tickers": {}, "error": "No IV data found"}
    except Exception as e:
        logger.error(f"Error fetching IV by ticker: {e}")
        return {"tickers": {}, "error": str(e)}


def fetch_iv_by_ticker() -> dict:
    """Fetch IV history for each ticker in the database."""
    try:
        with get_db() as db:
            is_turso = hasattr(db, 'execute')
            
            # Get all tickers with IV data
            if is_turso:
                ticker_rows = db.execute("""
                    SELECT DISTINCT ticker 
                    FROM iv_history 
                    WHERE atm_iv IS NOT NULL 
                    ORDER BY ticker
                """)
                tickers = [row['ticker'] for row in ticker_rows]
            else:
                cursor = db.cursor()
                cursor.execute("""
                    SELECT DISTINCT ticker 
                    FROM iv_history 
                    WHERE atm_iv IS NOT NULL 
                    ORDER BY ticker
                """)
                tickers = [row[0] for row in cursor.fetchall()]
            
            result = {}
            
            for ticker in tickers:
                if is_turso:
                    rows = db.execute("""
                        SELECT h.date, h.atm_iv, r.high_52wk, r.low_52wk
                        FROM iv_history h
                        LEFT JOIN iv_52wk_ranges r ON h.ticker = r.ticker
                        WHERE h.ticker = ? AND h.atm_iv IS NOT NULL
                        ORDER BY h.date ASC
                    """, [ticker])
                else:
                    cursor.execute("""
                        SELECT h.date, h.atm_iv, r.high_52wk, r.low_52wk
                        FROM iv_history h
                        LEFT JOIN iv_52wk_ranges r ON h.ticker = r.ticker
                        WHERE h.ticker = ? AND h.atm_iv IS NOT NULL
                        ORDER BY h.date ASC
                    """, (ticker,))
                    rows = [dict(row) for row in cursor.fetchall()]
                
                if rows:
                    result[ticker] = [
                        {
                            "date": row['date'],
                            "iv": round(row['atm_iv'], 3),
                            "iv_52wk_high": row.get('high_52wk'),
                            "iv_52wk_low": row.get('low_52wk')
                        }
                        for row in rows
                    ]
            
            logger.info(f"Returning IV data for {len(result)} tickers")
            return result
    
    except Exception as e:
        logger.error(f"Error fetching IV by ticker: {e}")
        return {}


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
        logger.error(f"WebSocket error: {e}")
    finally:
        active_connections.remove(websocket)


async def broadcast_update(update_data: dict):
    """Broadcast update to all active WebSocket connections."""
    for connection in active_connections.copy():
        try:
            await connection.send_text(json.dumps(update_data))
        except Exception as e:
            logger.error(f"Error sending WebSocket message: {e}")
            active_connections.remove(connection)