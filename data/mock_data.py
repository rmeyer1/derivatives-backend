"""Static mock data templates for the derivatives backend."""

# Symbols for mock data
SYMBOLS = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "AMZN", "META", "NFLX"]

# Alert templates
ALERT_TEMPLATES = [
    {
        "title": "High IV Crush Expected",
        "description": "Expected 30-40% IV crush after earnings announcement",
        "priority": "high"
    },
    {
        "title": "Large Position Delta Exposure",
        "description": "Portfolio delta exposure exceeds 150 deltas",
        "priority": "high"
    },
    {
        "title": "Earnings Announcement Soon",
        "description": "Earnings announcement in 24 hours",
        "priority": "medium"
    },
    {
        "title": "Portfolio PnL Threshold Approaching",
        "description": "Monthly PnL approaching profit target",
        "priority": "medium"
    },
    {
        "title": "Low Liquidity Warning",
        "description": "Consider closing positions in illiquid options",
        "priority": "low"
    },
    {
        "title": "Dividend Adjustment Needed",
        "description": "Upcoming dividend requires position adjustment",
        "priority": "low"
    }
]

# Base values for generating mock data
BASE_PRICES = {
    "AAPL": 185.0,
    "TSLA": 245.0,
    "NVDA": 880.0,
    "MSFT": 420.0,
    "GOOGL": 145.0,
    "AMZN": 155.0,
    "META": 500.0,
    "NFLX": 620.0
}