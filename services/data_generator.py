"""Mock data generator for the derivatives trading dashboard."""

import random
from datetime import datetime, timedelta
from typing import List
import numpy as np

from models import PortfolioItem, Alert, DMADataPoint, IVDataPoint, OptionType, Priority

def generate_mock_positions(count: int = 10) -> List[PortfolioItem]:
    """Generate mock portfolio positions."""
    positions = []
    
    symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "NFLX", "AMD", "INTC"]
    option_types = [OptionType.CALL, OptionType.PUT]
    
    for i in range(count):
        symbol = random.choice(symbols)
        option_type = random.choice(option_types)
        strike = round(random.uniform(100, 500), 2)
        expiration = (datetime.now() + timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d")
        quantity = random.randint(1, 100)
        avg_price = round(random.uniform(5, 50), 2)
        
        # Generate realistic market data
        market_price = round(avg_price * random.uniform(0.8, 1.2), 2)
        pnl = round((market_price - avg_price) * quantity, 2)
        iv = round(random.uniform(0.1, 0.8), 2)
        
        # Greeks calculated realistically
        delta = round(random.uniform(-1, 1), 2)
        gamma = round(random.uniform(0, 0.1), 4)
        theta = round(random.uniform(-0.5, 0), 4)
        vega = round(random.uniform(0, 0.5), 4)
        
        position = PortfolioItem(
            id=f"pos_{i+1}",
            symbol=symbol,
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

def generate_mock_alerts(count: int = 5) -> List[Alert]:
    """Generate mock alerts."""
    alerts = []
    
    alert_titles = [
        "High IV Contraction",
        "Large Price Movement",
        "Expiring Soon",
        "Delta Neutrality Reached",
        "Volatility Spike Detected"
    ]
    
    alert_descriptions = [
        "Implied volatility has dropped significantly in your AAPL options",
        "Unusual price movement detected in your portfolio holdings",
        "Options expiring within 24 hours require attention",
        "Portfolio delta neutrality achieved - consider rebalancing",
        "Market volatility has increased beyond normal levels"
    ]
    
    priorities = [Priority.HIGH, Priority.MEDIUM, Priority.LOW]
    
    for i in range(count):
        title = random.choice(alert_titles)
        description = random.choice(alert_descriptions)
        timestamp = (datetime.now() - timedelta(minutes=random.randint(1, 120))).strftime("%Y-%m-%d %H:%M:%S")
        priority = random.choice(priorities)
        read = random.choice([True, False])
        
        alert = Alert(
            id=f"alert_{i+1}",
            title=title,
            description=description,
            timestamp=timestamp,
            priority=priority,
            read=read
        )
        alerts.append(alert)
    
    return alerts

def generate_dma_curve(points: int = 50) -> List[DMADataPoint]:
    """Generate mock DMA curve data."""
    dma_data = []
    
    # Generate a trend with some noise
    base_value = random.uniform(0, 100)
    
    for i in range(points):
        time = (datetime.now() - timedelta(hours=points-i)).strftime("%Y-%m-%d %H:%M")
        # Add some trend and noise
        trend = i * 0.2
        noise = random.uniform(-5, 5)
        value = round(base_value + trend + noise, 2)
        
        data_point = DMADataPoint(
            time=time,
            value=value
        )
        dma_data.append(data_point)
    
    return dma_data

def generate_iv_curve(strikes: int = 20) -> List[IVDataPoint]:
    """Generate mock implied volatility curve data."""
    iv_data = []
    
    # Generate a volatility skew curve
    base_strike = 100
    base_iv = 0.3
    
    for i in range(strikes):
        strike = base_strike + i * 5
        # Create a volatility smile/skew pattern
        distance_from_atm = abs(strike - (base_strike + strikes * 2.5))
        iv = round(base_iv + (distance_from_atm / 100), 3)
        
        data_point = IVDataPoint(
            strike=strike,
            iv=iv
        )
        iv_data.append(data_point)
    
    return iv_data