"""
Market Data Module for Derivatives Dashboard

Fetches live market data from:
- yfinance: stock prices, earnings dates
- Alpaca API (HTTP): options chains, option prices

Falls back to cached/generated data if APIs fail.
Adapted from daily briefing system.
"""

import os
import re
import logging
import requests
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import yfinance
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance not installed. Stock prices will use fallback.")

# Alpaca API Configuration
ALPACA_DATA_URL = "https://data.alpaca.markets/v1beta1"


def get_alpaca_headers() -> Optional[Dict[str, str]]:
    """
    Get Alpaca API authentication headers.
    Uses environment variables ALPACA_API_KEY and ALPACA_API_SECRET.
    """
    api_key = os.getenv('ALPACA_API_KEY')
    api_secret = os.getenv('ALPACA_API_SECRET')
    
    if not api_key or not api_secret:
        logger.warning("Alpaca API credentials not found in environment.")
        return None
    
    return {
        'APCA-API-KEY-ID': api_key,
        'APCA-API-SECRET-KEY': api_secret
    }


@dataclass
class OptionChainEntry:
    """Represents a single option contract in the chain."""
    strike: float
    expiration: date
    option_type: str  # 'call' or 'put'
    bid: float
    ask: float
    last_price: float
    implied_volatility: Optional[float] = None
    open_interest: Optional[int] = None
    volume: Optional[int] = None
    underlying: Optional[str] = None
    symbol: Optional[str] = None
    
    @property
    def mid_price(self) -> float:
        """Calculate mid price between bid and ask."""
        if self.bid > 0 and self.ask > 0:
            return (self.bid + self.ask) / 2
        return self.last_price if self.last_price > 0 else 0


def get_stock_price(ticker: str) -> Optional[float]:
    """
    Get current stock price using yfinance.
    
    Args:
        ticker: Stock symbol (e.g., 'AAPL', 'AMD')
        
    Returns:
        Current stock price or None if unavailable
    """
    if not YFINANCE_AVAILABLE:
        logger.warning(f"yfinance not available for {ticker}")
        return None
    
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
        
        info = stock.fast_info
        if info and hasattr(info, 'last_price'):
            return float(info.last_price)
        
        return None
    except Exception as e:
        logger.error(f"Error fetching stock price for {ticker}: {e}")
        return None


def get_option_chain(ticker: str, expiration: Optional[date] = None) -> List[OptionChainEntry]:
    """
    Get option chain for a ticker using Alpaca HTTP API.
    
    Args:
        ticker: Stock symbol
        expiration: Optional specific expiration date
        
    Returns:
        List of OptionChainEntry objects
    """
    headers = get_alpaca_headers()
    if not headers:
        logger.warning(f"Alpaca credentials not available for {ticker}")
        return []
    
    try:
        url = f"{ALPACA_DATA_URL}/options/snapshots/{ticker}"
        params = {
            'feed': 'indicative',
            'limit': 1000
        }
        
        if expiration:
            params['expiration_date'] = expiration.strftime('%Y-%m-%d')
        
        logger.info(f"Fetching options for {ticker} from Alpaca...")
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code != 200:
            logger.error(f"Alpaca API error: {response.status_code}")
            return []
        
        data = response.json()
        snapshots = data.get('snapshots', {})
        
        if not snapshots:
            return []
        
        options = []
        for option_symbol, snapshot in snapshots.items():
            try:
                # Parse option symbol
                match = re.match(r'^([A-Z]+)(\d{6})([CP])(\d{8})$', option_symbol.upper())
                if not match:
                    continue
                
                underlying = match.group(1)
                date_code = match.group(2)
                opt_type_code = match.group(3)
                strike_code = match.group(4)
                
                exp_year = 2000 + int(date_code[0:2])
                exp_month = int(date_code[2:4])
                exp_day = int(date_code[4:6])
                parsed_date = date(exp_year, exp_month, exp_day)
                
                option_type = 'call' if opt_type_code == 'C' else 'put'
                strike = int(strike_code) / 1000.0
                
                quote = snapshot.get('latestQuote', {})
                trade = snapshot.get('latestTrade', {})
                
                bid = float(quote.get('bp', 0) or 0)
                ask = float(quote.get('ap', 0) or 0)
                last_price = float(trade.get('p', 0) or 0)
                
                if last_price == 0 and bid > 0 and ask > 0:
                    last_price = (bid + ask) / 2
                
                implied_vol = snapshot.get('implied_volatility')
                open_interest = snapshot.get('open_interest')
                volume = snapshot.get('volume')
                
                if expiration and parsed_date != expiration:
                    continue
                
                options.append(OptionChainEntry(
                    strike=strike,
                    expiration=parsed_date,
                    option_type=option_type,
                    bid=bid,
                    ask=ask,
                    last_price=last_price,
                    implied_volatility=implied_vol,
                    open_interest=open_interest,
                    volume=volume,
                    underlying=underlying,
                    symbol=option_symbol
                ))
                
            except Exception as e:
                logger.warning(f"Error parsing option {option_symbol}: {e}")
                continue
        
        options.sort(key=lambda x: (x.expiration, x.strike, x.option_type))
        logger.info(f"Retrieved {len(options)} options for {ticker}")
        return options
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout fetching option chain for {ticker}")
        return []
    except Exception as e:
        logger.error(f"Error fetching option chain for {ticker}: {e}")
        return []


def get_nearest_strike(chain: List[OptionChainEntry], target_strike: float, 
                        option_type: str) -> Optional[OptionChainEntry]:
    """Find the option in the chain with the strike nearest to target."""
    filtered = [opt for opt in chain if opt.option_type.lower() == option_type.lower()]
    if not filtered:
        return None
    return min(filtered, key=lambda opt: abs(opt.strike - target_strike))


def get_option_by_details(ticker: str, strike: float, option_type: str, 
                          expiration: date) -> Optional[OptionChainEntry]:
    """Get a specific option contract matching exact details."""
    chain = get_option_chain(ticker, expiration)
    if not chain:
        return None
    
    option_type = option_type.lower().rstrip('s')
    
    for opt in chain:
        if (abs(opt.strike - strike) < 0.01 and 
            opt.option_type == option_type and 
            opt.expiration == expiration):
            return opt
    
    # Find nearest if no exact match
    filtered = [opt for opt in chain if opt.option_type == option_type]
    if filtered:
        closest = min(filtered, key=lambda opt: abs(opt.strike - strike))
        if abs(closest.strike - strike) < 5.0:
            return closest
    
    return None


def get_current_option_price(ticker: str, strike: float, option_type: str, 
                              expiration: Optional[date] = None,
                              fallback_price: Optional[float] = None) -> Tuple[Optional[float], str]:
    """
    Get current market price for a specific option contract.
    
    Returns:
        Tuple of (price, source) where source is 'live', 'fallback', or 'error'
    """
    option_type = option_type.lower().rstrip('s')
    if option_type not in ['call', 'put']:
        return fallback_price, 'error' if fallback_price else (None, 'error')
    
    try:
        if expiration:
            opt = get_option_by_details(ticker, strike, option_type, expiration)
            if opt:
                return opt.mid_price, 'live'
        
        chain = get_option_chain(ticker, expiration)
        if chain:
            nearest = get_nearest_strike(chain, strike, option_type)
            if nearest:
                return nearest.mid_price, 'live'
    except Exception as e:
        logger.error(f"Error fetching option price: {e}")
    
    if fallback_price is not None:
        return fallback_price, 'fallback'
    
    return None, 'error'


def get_earnings_dates(ticker: str) -> List[date]:
    """Get upcoming earnings dates for a ticker using yfinance."""
    earnings_dates = []
    
    if not YFINANCE_AVAILABLE:
        return []
    
    try:
        stock = yf.Ticker(ticker)
        calendar = stock.calendar
        
        if calendar is not None and not calendar.empty:
            if 'Earnings Date' in calendar.index:
                date_val = calendar.loc['Earnings Date'].iloc[0]
                if isinstance(date_val, (datetime, date)):
                    if isinstance(date_val, datetime):
                        date_val = date_val.date()
                    if date_val >= date.today():
                        earnings_dates.append(date_val)
    except Exception as e:
        logger.error(f"Error fetching earnings for {ticker}: {e}")
    
    return sorted(set(earnings_dates))


def get_market_timestamp() -> str:
    """Get current market data timestamp for display."""
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S EST')
