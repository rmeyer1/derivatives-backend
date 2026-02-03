"""
Implied Volatility Calculator Module for Derivatives Dashboard

Provides Black-Scholes option pricing and IV calculation using Newton-Raphson
with bisection fallback method.
Adapted from daily briefing system.
"""

import os
import math
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Risk-free rate (default 4.5%)
DEFAULT_RISK_FREE_RATE = 0.045


def normal_cdf(x: float) -> float:
    """Cumulative distribution function for standard normal distribution."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def normal_pdf(x: float) -> float:
    """Probability density function for standard normal distribution."""
    return (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * x * x)


def calculate_d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Calculate d1 parameter for Black-Scholes formula."""
    if sigma <= 0 or T <= 0:
        return float('inf') if S > K else float('-inf')
    return (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))


def calculate_d2(d1: float, T: float, sigma: float) -> float:
    """Calculate d2 parameter for Black-Scholes formula."""
    return d1 - sigma * math.sqrt(T)


def black_scholes_price(S: float, K: float, T: float, r: float, sigma: float, 
                       option_type: str) -> float:
    """
    Calculate theoretical option price using Black-Scholes model.
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration in years (DTE/365)
        r: Risk-free interest rate (decimal)
        sigma: Volatility/IV (decimal, e.g., 0.30 for 30%)
        option_type: 'call' or 'put'
    """
    if T <= 0:
        if option_type.lower() == 'call':
            return max(0, S - K)
        else:
            return max(0, K - S)
    
    if sigma <= 0:
        sigma = 0.0001
    
    d1 = calculate_d1(S, K, T, r, sigma)
    d2 = calculate_d2(d1, T, sigma)
    disc_factor = math.exp(-r * T)
    
    if option_type.lower() == 'call':
        price = S * normal_cdf(d1) - K * disc_factor * normal_cdf(d2)
    else:
        price = K * disc_factor * normal_cdf(-d2) - S * normal_cdf(-d1)
    
    return max(0, price)


def calculate_vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
    """Calculate option vega (sensitivity to volatility changes)."""
    if T <= 0 or sigma <= 0:
        return 0
    d1 = calculate_d1(S, K, T, r, sigma)
    vega = S * normal_pdf(d1) * math.sqrt(T)
    return vega * 0.01  # Per 1% change


def calculate_implied_vol(market_price: float, S: float, K: float, T: float, 
                          r: float, option_type: str,
                          max_iterations: int = 50,
                          price_tolerance: float = 0.01) -> Optional[float]:
    """
    Calculate implied volatility from market price using Newton-Raphson + bisection fallback.
    
    Returns IV as decimal (e.g., 0.5231 for 52.31%) or None if calculation fails.
    """
    if market_price <= 0 or S <= 0 or K <= 0 or T <= 0:
        return None
    
    # Check intrinsic value
    intrinsic = max(0, S - K) if option_type.lower() == 'call' else max(0, K - S)
    if market_price < intrinsic:
        return None
    
    # Newton-Raphson method
    sigma = 0.5
    for i in range(max_iterations):
        theoretical_price = black_scholes_price(S, K, T, r, sigma, option_type)
        price_diff = theoretical_price - market_price
        
        if abs(price_diff) < price_tolerance:
            return sigma
        
        vega = calculate_vega(S, K, T, r, sigma)
        if abs(vega) < 1e-10:
            break
        
        sigma_new = sigma - price_diff / (vega * 100)
        if sigma_new <= 0 or sigma_new > 5.0:
            break
        sigma = sigma_new
    
    # Bisection fallback
    sigma_low, sigma_high = 0.001, 3.0
    for i in range(max_iterations):
        sigma = (sigma_low + sigma_high) / 2
        theoretical_price = black_scholes_price(S, K, T, r, sigma, option_type)
        price_diff = theoretical_price - market_price
        
        if abs(price_diff) < price_tolerance:
            return sigma
        
        if price_diff > 0:
            sigma_high = sigma
        else:
            sigma_low = sigma
        
        if sigma_high - sigma_low < 0.0001:
            return sigma
    
    return None


def find_atm_options(chain: List[Any], stock_price: float, strike_range: int = 2) -> List[Any]:
    """Filter options to find at-the-money options within range."""
    if not chain:
        return []
    
    strikes = sorted(set(opt.strike for opt in chain))
    if not strikes:
        return []
    
    atm_strike = min(strikes, key=lambda s: abs(s - stock_price))
    atm_idx = strikes.index(atm_strike)
    start_idx = max(0, atm_idx - strike_range)
    end_idx = min(len(strikes), atm_idx + strike_range + 1)
    target_strikes = set(strikes[start_idx:end_idx])
    
    return [opt for opt in chain if opt.strike in target_strikes]


def get_atm_iv_from_chain(option_chain: List[Any], stock_price: float,
                          target_dte: int = 35, dte_range: int = 15,
                          r: float = DEFAULT_RISK_FREE_RATE) -> Optional[float]:
    """
    Extract ATM implied volatility from option chain.
    
    Args:
        option_chain: List of OptionChainEntry objects
        stock_price: Current stock price
        target_dte: Target days to expiration
        dte_range: Acceptable range around target
        r: Risk-free rate
        
    Returns:
        Average ATM IV as decimal or None
    """
    if not option_chain or stock_price <= 0:
        return None
    
    from datetime import date
    today = date.today()
    
    # Group by expiration
    expirations: Dict[date, List[Any]] = {}
    for opt in option_chain:
        if opt.expiration not in expirations:
            expirations[opt.expiration] = []
        expirations[opt.expiration].append(opt)
    
    if not expirations:
        return None
    
    # Find best expiration
    best_exp = None
    best_dte_diff = float('inf')
    
    for exp in sorted(expirations.keys()):
        if exp <= today:
            continue
        dte = (exp - today).days
        if abs(dte - target_dte) <= dte_range:
            if abs(dte - target_dte) < best_dte_diff:
                best_dte_diff = abs(dte - target_dte)
                best_exp = exp
    
    if not best_exp:
        future_exps = [exp for exp in expirations.keys() if exp > today]
        if not future_exps:
            return None
        best_exp = min(future_exps, key=lambda e: abs((e - today).days - target_dte))
    
    exp_options = expirations[best_exp]
    dte = (best_exp - today).days
    T = dte / 365.0
    
    # Find ATM options
    atm_options = find_atm_options(exp_options, stock_price, strike_range=2)
    if not atm_options:
        return None
    
    # Calculate IV for each ATM option
    iv_values = []
    for opt in atm_options:
        if opt.bid > 0 and opt.ask > 0:
            market_price = (opt.bid + opt.ask) / 2
        elif opt.last_price > 0:
            market_price = opt.last_price
        else:
            continue
        
        if market_price < 0.10:
            continue
        
        iv = calculate_implied_vol(market_price, stock_price, opt.strike, T, r, opt.option_type)
        if iv and 0.05 <= iv <= 2.0:
            iv_values.append({'strike': opt.strike, 'iv': iv, 'distance': abs(opt.strike - stock_price)})
    
    if not iv_values:
        return None
    
    # Weight by inverse distance from ATM
    total_weight = sum(1 / (1 + v['distance'] / stock_price) for v in iv_values)
    weighted_iv = sum(v['iv'] * (1 / (1 + v['distance'] / stock_price)) for v in iv_values) / total_weight
    
    return weighted_iv
