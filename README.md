# Derivatives Trading Backend

This is the backend service for a derivatives trading platform, providing real-time data and alerts.

## Installation

```bash
pip install -r requirements.txt
```

## How to Run

```bash
uvicorn main:app --reload
```

The application runs on port 8000.

## API Endpoints

- `/positions` - Get current positions
- `/alerts` - Get alert information
- `/dma-data` - Get DMA data
- `/iv-data` - Get implied volatility data
- `/ws` - WebSocket endpoint for real-time updates

## Frontend Integration

CORS is already configured for `localhost:3000` to facilitate integration with the frontend.