"""
Volatility Estimation Service

Provides methods for estimating implied volatility for options.
"""

import yfinance as yf
import numpy as np
from datetime import datetime, date
from typing import Optional

def estimate_iv(ticker: str, strike: float, time_to_expiry: float, is_call: bool) -> float:
    """
    Estimate implied volatility for an option using historical volatility as a proxy.
    
    Args:
        ticker: Stock symbol
        strike: Strike price
        time_to_expiry: Time to expiration in years
        is_call: True for call options, False for puts
        
    Returns:
        Estimated implied volatility (annualized)
    """
    try:
        # Fetch stock data
        stock = yf.Ticker(ticker)
        hist = stock.history(period="6mo")  # Get 6 months of data
        
        if len(hist) < 10:  # Need at least 10 data points
            return 0.3  # Default IV if insufficient data
        
        # Calculate historical volatility
        hist['returns'] = hist['Close'].pct_change()
        hist.dropna(inplace=True)
        
        # Annualized volatility (assuming 252 trading days)
        volatility = hist['returns'].std() * np.sqrt(252)
        
        # Adjust for moneyness (simplified approach)
        current_price = hist['Close'].iloc[-1]
        moneyness = abs(current_price - strike) / current_price
        
        # Increase IV for OTM options, decrease for ITM
        if (is_call and strike > current_price) or (not is_call and strike < current_price):
            # OTM option - increase IV
            adjusted_iv = volatility * (1 + min(moneyness, 0.5))
        else:
            # ITM option - decrease IV slightly
            adjusted_iv = volatility * (1 - min(moneyness * 0.5, 0.2))
        
        # Ensure reasonable bounds (5% to 200%)
        return max(0.05, min(adjusted_iv, 2.0))
        
    except Exception as e:
        # If any error occurs, return default IV based on time to expiry
        # Longer-dated options typically have higher IV
        base_iv = 0.25 + (min(time_to_expiry, 1.0) * 0.1)  # Between 0.25 and 0.35
        return base_iv


def get_historical_volatility(ticker: str, period: str = "1y") -> Optional[float]:
    """
    Calculate historical volatility for a given ticker.
    
    Args:
        ticker: Stock symbol
        period: Time period for historical data ('1y', '6mo', '3mo', etc.)
        
    Returns:
        Annualized historical volatility or None if error
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        
        if len(hist) < 10:
            return None
            
        hist['returns'] = hist['Close'].pct_change()
        hist.dropna(inplace=True)
        
        # Annualized volatility (assuming 252 trading days)
        volatility = hist['returns'].std() * np.sqrt(252)
        return volatility
        
    except Exception as e:
        print(f"Error calculating historical volatility for {ticker}: {e}")
        return None
