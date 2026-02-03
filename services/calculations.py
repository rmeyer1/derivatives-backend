"""Greeks and IV calculations for the derivatives trading dashboard."""

import numpy as np
from scipy.stats import norm
import math

def calculate_greeks(
    spot_price: float,
    strike_price: float,
    time_to_expiry: float,
    risk_free_rate: float,
    volatility: float,
    option_type: str
) -> dict:
    """
    Calculate option greeks using Black-Scholes model.
    
    Parameters:
    - spot_price: Current price of the underlying asset
    - strike_price: Strike price of the option
    - time_to_expiry: Time to expiration in years
    - risk_free_rate: Risk-free interest rate
    - volatility: Implied volatility
    - option_type: 'call' or 'put'
    
    Returns:
    - Dictionary containing delta, gamma, theta, vega
    """
    
    # Prevent division by zero
    if volatility <= 0 or time_to_expiry <= 0:
        return {
            'delta': 0.0,
            'gamma': 0.0,
            'theta': 0.0,
            'vega': 0.0
        }
    
    # Calculate d1 and d2
    d1 = (math.log(spot_price / strike_price) + 
          (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry) / (
          volatility * math.sqrt(time_to_expiry))
    
    d2 = d1 - volatility * math.sqrt(time_to_expiry)
    
    # Calculate Greeks
    if option_type.lower() == 'call':
        delta = norm.cdf(d1)
        theta = (-spot_price * norm.pdf(d1) * volatility / (2 * math.sqrt(time_to_expiry)) -
                 risk_free_rate * strike_price * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2))
    else:  # put
        delta = norm.cdf(d1) - 1
        theta = (-spot_price * norm.pdf(d1) * volatility / (2 * math.sqrt(time_to_expiry)) +
                 risk_free_rate * strike_price * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2))
    
    # Gamma and Vega are the same for calls and puts
    gamma = norm.pdf(d1) / (spot_price * volatility * math.sqrt(time_to_expiry))
    vega = spot_price * norm.pdf(d1) * math.sqrt(time_to_expiry)
    
    return {
        'delta': round(delta, 4),
        'gamma': round(gamma, 6),
        'theta': round(theta / 365, 6),  # Per day
        'vega': round(vega / 100, 6)     # Per 1% change in volatility
    }

def calculate_iv(
    market_price: float,
    spot_price: float,
    strike_price: float,
    time_to_expiry: float,
    risk_free_rate: float,
    option_type: str,
    max_iterations: int = 100,
    precision: float = 1e-5
) -> float:
    """
    Calculate implied volatility using Newton-Raphson method.
    
    Parameters:
    - market_price: Observed market price of the option
    - spot_price: Current price of the underlying asset
    - strike_price: Strike price of the option
    - time_to_expiry: Time to expiration in years
    - risk_free_rate: Risk-free interest rate
    - option_type: 'call' or 'put'
    - max_iterations: Maximum number of iterations
    - precision: Desired precision
    
    Returns:
    - Implied volatility as a decimal
    """
    
    # Initial guess for volatility
    sigma = 0.3
    
    for i in range(max_iterations):
        # Calculate option price and vega using current sigma
        price = black_scholes_price(spot_price, strike_price, time_to_expiry, risk_free_rate, sigma, option_type)
        vega = black_scholes_vega(spot_price, strike_price, time_to_expiry, risk_free_rate, sigma)
        
        # Avoid division by zero
        if vega == 0:
            break
            
        # Newton-Raphson iteration
        diff = price - market_price
        sigma = sigma - diff / vega
        
        # Ensure sigma stays positive
        sigma = max(sigma, 1e-10)
        
        # Check for convergence
        if abs(diff) < precision:
            break
    
    return round(sigma, 4)

def black_scholes_price(
    spot_price: float,
    strike_price: float,
    time_to_expiry: float,
    risk_free_rate: float,
    volatility: float,
    option_type: str
) -> float:
    """Calculate Black-Scholes option price."""
    
    if volatility <= 0 or time_to_expiry <= 0:
        if option_type.lower() == 'call':
            return max(0, spot_price - strike_price)
        else:
            return max(0, strike_price - spot_price)
    
    d1 = (math.log(spot_price / strike_price) + 
          (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry) / (
          volatility * math.sqrt(time_to_expiry))
    
    d2 = d1 - volatility * math.sqrt(time_to_expiry)
    
    if option_type.lower() == 'call':
        price = (spot_price * norm.cdf(d1) - 
                strike_price * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2))
    else:
        price = (strike_price * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2) - 
                spot_price * norm.cdf(-d1))
    
    return max(0, price)

def black_scholes_vega(
    spot_price: float,
    strike_price: float,
    time_to_expiry: float,
    risk_free_rate: float,
    volatility: float
) -> float:
    """Calculate Black-Scholes vega."""
    
    if volatility <= 0 or time_to_expiry <= 0:
        return 0
    
    d1 = (math.log(spot_price / strike_price) + 
          (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry) / (
          volatility * math.sqrt(time_to_expiry))
    
    vega = spot_price * norm.pdf(d1) * math.sqrt(time_to_expiry)
    return vega