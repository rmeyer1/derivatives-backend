"""Financial calculations for the derivatives backend."""

import math
from typing import Dict
from data.mock_data import BASE_PRICES


def calculate_greeks(symbol: str, strike: float, option_type: str) -> Dict[str, float]:
    """
    Calculate option greeks using simplified approximations.
    
    Args:
        symbol: Underlying asset symbol
        strike: Strike price
        option_type: "Call" or "Put"
        
    Returns:
        Dictionary containing delta, gamma, theta, vega
    """
    # Get base price for the symbol
    base_price = BASE_PRICES.get(symbol, 100.0)
    
    # Simple delta approximation based on moneyness
    moneyness = (base_price - strike) / base_price
    
    if option_type.lower() == "call":
        delta = min(1.0, max(0.0, 0.5 + moneyness * 0.4))
    else:  # put
        delta = min(0.0, max(-1.0, -0.5 + moneyness * 0.4))
    
    # Gamma approximation (highest at-the-money)
    gamma = 0.02 * math.exp(-((strike - base_price) / (base_price * 0.1)) ** 2)
    
    # Theta approximation (time decay)
    theta = -0.05 * gamma * 0.5
    
    # Vega approximation
    vega = 0.1 * gamma * base_price * 0.2
    
    return {
        "delta": round(delta, 3),
        "gamma": round(gamma, 5),
        "theta": round(theta, 4),
        "vega": round(vega, 3)
    }


def calculate_iv(symbol: str, strike: float, option_type: str) -> float:
    """
    Calculate implied volatility using a simplified model.
    
    Args:
        symbol: Underlying asset symbol
        strike: Strike price
        option_type: "Call" or "Put"
        
    Returns:
        Implied volatility as a percentage
    """
    base_price = BASE_PRICES.get(symbol, 100.0)
    
    # Simple model based on strike distance from spot
    distance = abs(strike - base_price) / base_price
    
    # IV is higher for near money options
    base_iv = 0.25  # 25% base IV
    adjustment = 0.1 * math.exp(-distance * 5)  # Higher IV closer to money
    
    # Additional adjustment based on option type and moneyness
    if option_type.lower() == "call" and strike < base_price:
        adjustment += 0.05  # ITM calls have higher IV
    elif option_type.lower() == "put" and strike > base_price:
        adjustment += 0.05  # ITM puts have higher IV
        
    return round(base_iv + adjustment, 3)