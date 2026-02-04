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

## Database Configuration

The backend supports both **local SQLite** and **remote Turso SQLite** databases:

### Local SQLite (default)
Set `DATABASE_PATH` in `.env` or uses `./market_data.db` by default.

### Turso Remote (recommended for multi-device)
1. Get a Turso account at [turso.tech](https://turso.tech)
2. Set in `.env`:
   ```
   TURSO_DATABASE_URL=libsql://your-db.turso.io
   TURSO_AUTH_TOKEN=your_auth_token
   ```
3. The backend will auto-connect to Turso; falls back to local SQLite if unavailable

### Migration
To migrate existing data from the Mac mini to Turso:
```bash
# On Mac mini - migrate local DB to Turso
python migrate_to_turso.py
```

## Frontend Integration

CORS is already configured for `localhost:3000` to facilitate integration with the frontend.