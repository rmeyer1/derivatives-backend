"""
Database module for Turso remote SQLite with local fallback.

Supports:
- Turso (HTTP API) remote database as primary
- Local SQLite as fallback
- Auto-initialization of tables
"""

import os
import sqlite3
import logging
import requests
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default local database path
DEFAULT_LOCAL_DB = './market_data.db'


class TursoClient:
    """HTTP client for Turso database."""
    
    def __init__(self, url: str, auth_token: str):
        self.url = url.replace('libsql://', 'https://').rstrip('/')
        self.auth_token = auth_token
        self.headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        }
    
    def execute(self, sql: str, args: list = None) -> List[Dict]:
        """Execute SQL and return results via Turso HTTP API."""
        # Turso v2/pipeline expects requests array with type: execute
        payload = {
            'requests': [
                {
                    'type': 'execute',
                    'stmt': {
                        'sql': sql,
                        'args': args or []
                    }
                }
            ]
        }
        
        response = requests.post(
            f'{self.url}/v2/pipeline',
            headers=self.headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"Turso API error: {response.status_code} - {response.text[:200]}")
            response.raise_for_status()
        
        data = response.json()
        
        # Parse results from pipeline response
        results = []
        if 'results' in data:
            for result in data['results']:
                if 'response' in result and 'result' in result['response']:
                    result_data = result['response']['result']
                    rows = result_data.get('rows', [])
                    cols = result_data.get('cols', [])
                    
                    for row in rows:
                        row_dict = {}
                        for i, col in enumerate(cols):
                            col_name = col['name'] if isinstance(col, dict) else col
                            cell = row[i] if i < len(row) else None
                            # Handle Turso's value wrapper format
                            if isinstance(cell, dict) and 'value' in cell:
                                row_dict[col_name] = cell['value']
                            elif isinstance(cell, dict) and 'type' in cell:
                                # Turso may return {type: 'integer', value: '123'}
                                row_dict[col_name] = cell.get('value')
                            else:
                                row_dict[col_name] = cell
                        results.append(row_dict)
        
        return results
    
    def commit(self):
        """No-op for HTTP client (statements auto-commit)."""
        pass
    
    def close(self):
        """No-op for HTTP client."""
        pass


def get_db_connection():
    """
    Get database connection.
    
    Priority:
    1. Turso remote (if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN set)
    2. Local SQLite (fallback)
    
    Returns:
        Database connection object (TursoClient or sqlite3.Connection)
    """
    turso_url = os.getenv('TURSO_DATABASE_URL')
    turso_token = os.getenv('TURSO_AUTH_TOKEN')
    
    # Try Turso first if credentials available
    if turso_url and turso_token:
        try:
            client = TursoClient(turso_url, turso_token)
            # Test connection
            client.execute("SELECT 1")
            logger.info("Connected to Turso remote database (HTTP API)")
            return client
        except Exception as e:
            logger.warning(f"Failed to connect to Turso: {e}. Falling back to local SQLite.")
    
    # Fallback to local SQLite
    local_db_path = os.getenv('DATABASE_PATH', DEFAULT_LOCAL_DB)
    conn = sqlite3.connect(local_db_path)
    conn.row_factory = sqlite3.Row
    logger.info(f"Connected to local SQLite: {local_db_path}")
    return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        conn.close()


def initialize_database():
    """Initialize database tables if they don't exist."""
    conn = get_db_connection()
    
    # Check if we're using Turso or SQLite
    is_turso = isinstance(conn, TursoClient)
    
    if is_turso:
        # Turso uses HTTP API - tables created via SQL
        create_statements = [
            '''CREATE TABLE IF NOT EXISTS daily_prices (
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                PRIMARY KEY (ticker, date)
            )''',
            '''CREATE TABLE IF NOT EXISTS iv_history (
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                iv_30day REAL,
                iv_60day REAL,
                iv_90day REAL,
                iv_52wk_high REAL,
                iv_52wk_low REAL,
                PRIMARY KEY (ticker, date)
            )'''
        ]
        for sql in create_statements:
            conn.execute(sql)
    else:
        # SQLite path
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_prices (
                ticker TEXT NOT NULL,
                date DATE NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume INTEGER,
                PRIMARY KEY (ticker, date)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS iv_history (
                ticker TEXT NOT NULL,
                date DATE NOT NULL,
                iv_30day REAL,
                iv_60day REAL,
                iv_90day REAL,
                iv_52wk_high REAL,
                iv_52wk_low REAL,
                PRIMARY KEY (ticker, date)
            )
        ''')
        conn.commit()
    
    conn.close()
    logger.info("Database tables initialized")


def test_connection() -> bool:
    """Test database connection. Returns True if successful."""
    try:
        conn = get_db_connection()
        if isinstance(conn, TursoClient):
            conn.execute("SELECT 1")
        else:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


def is_turso_connected() -> bool:
    """Check if currently connected to Turso (vs local SQLite)."""
    turso_url = os.getenv('TURSO_DATABASE_URL')
    turso_token = os.getenv('TURSO_AUTH_TOKEN')
    return bool(turso_url and turso_token)
