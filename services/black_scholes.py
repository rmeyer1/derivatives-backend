"""
Black-Scholes Option Pricing Model Service

Implements the Black-Scholes model for European option pricing and Greeks calculation.
"""

import math
from scipy.stats import norm
from dataclasses import dataclass
from typing import NamedTuple

@dataclass
class Greeks:
    """Container for option Greeks."""
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float

class BlackScholesResult(NamedTuple):
    """Result container for Black-Scholes calculations."""
    price: float
    greeks: Greeks

def black_scholes_option_price(spot: float, strike: float, time_to_expiry: float, 
                               risk_free_rate: float, volatility: float, option_type: str) -> float:
    """
    Calculate the Black-Scholes option price for European options.
    
    Args:
        spot: Current stock price
        strike: Strike price
        time_to_expiry: Time to expiration in years
        risk_free_rate: Risk-free interest rate (annualized)
        volatility: Implied volatility (annualized)
        option_type: 'call' or 'put'
        
    Returns:
        Theoretical option price
    """
    if time_to_expiry <= 0:
        # Expired option
        if option_type.lower() == 'call':
            return max(spot - strike, 0)
        else:
            return max(strike - spot, 0)
    
    if volatility <= 0:
        # No volatility, price at intrinsic value
        if option_type.lower() == 'call':
            return max(spot - strike, 0)
        else:
            return max(strike - spot, 0)
    
    # Calculate d1 and d2
    sqrt_time = math.sqrt(time_to_expiry)
    d1 = (math.log(spot / strike) + (risk_free_rate + 0.5 * volatility**2) * time_to_expiry) / (volatility * sqrt_time)
    d2 = d1 - volatility * sqrt_time
    
    # Calculate option price
    if option_type.lower() == 'call':
        price = spot * norm.cdf(d1) - strike * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2)
    else:  # put
        price = strike * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2) - spot * norm.cdf(-d1)
    
    return max(price, 0)  # Ensure non-negative price

def greeks(spot: float, strike: float, time_to_expiry: float, 
           risk_free_rate: float, volatility: float, option_type: str) -> Greeks:
    """
    Calculate the Greeks for an option using Black-Scholes model.
    
    Args:
        spot: Current stock price
        strike: Strike price
        time_to_expiry: Time to expiration in years
        risk_free_rate: Risk-free interest rate (annualized)
        volatility: Implied volatility (annualized)
        option_type: 'call' or 'put'
        
    Returns:
        Greeks object containing delta, gamma, theta, vega, and rho
    """
    if time_to_expiry <= 0:
        # At expiration, Greeks are undefined or zero (except delta for ITM options)
        if option_type.lower() == 'call':
            delta = 1.0 if spot > strike else 0.0
        else:
            delta = -1.0 if spot < strike else 0.0
        return Greeks(delta=delta, gamma=0.0, theta=0.0, vega=0.0, rho=0.0)
    
    if volatility <= 0:
        # No volatility, Greeks are simplified
        return Greeks(delta=0.0, gamma=0.0, theta=0.0, vega=0.0, rho=0.0)
    
    sqrt_time = math.sqrt(time_to_expiry)
    d1 = (math.log(spot / strike) + (risk_free_rate + 0.5 * volatility**2) * time_to_expiry) / (volatility * sqrt_time)
    d2 = d1 - volatility * sqrt_time
    
    # Standard normal PDF
    pdf_d1 = norm.pdf(d1)
    
    # Calculate Greeks
    if option_type.lower() == 'call':
        delta = norm.cdf(d1)
        theta = (-spot * pdf_d1 * volatility / (2 * sqrt_time) - 
                 risk_free_rate * strike * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2)) / 365
        rho = strike * time_to_expiry * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2) / 100
    else:  # put
        delta = norm.cdf(d1) - 1
        theta = (-spot * pdf_d1 * volatility / (2 * sqrt_time) + 
                 risk_free_rate * strike * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2)) / 365
        rho = -strike * time_to_expiry * math.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2) / 100
    
    gamma = pdf_d1 / (spot * volatility * sqrt_time)
    vega = spot * sqrt_time * pdf_d1 / 100  # Per 1% change in volatility
    
    return Greeks(
        delta=delta,
        gamma=gamma,
        theta=theta,  # Per day
        vega=vega,    # Per 1% change in volatility
        rho=rho       # Per 1% change in interest rate
    )

def black_scholes_full(spot: float, strike: float, time_to_expiry: float, 
                       risk_free_rate: float, volatility: float, option_type: str) -> BlackScholesResult:
    """
    Calculate both price and Greeks for an option.
    
    Args:
        spot: Current stock price
        strike: Strike price
        time_to_expiry: Time to expiration in years
        risk_free_rate: Risk-free interest rate (annualized)
        volatility: Implied volatility (annualized)
        option_type: 'call' or 'put'
        
    Returns:
        BlackScholesResult containing both price and Greeks
    """
    price = black_scholes_option_price(spot, strike, time_to_expiry, risk_free_rate, volatility, option_type)
    option_greeks = greeks(spot, strike, time_to_expiry, risk_free_rate, volatility, option_type)
    
    return BlackScholesResult(price=price, greeks=option_greeks)