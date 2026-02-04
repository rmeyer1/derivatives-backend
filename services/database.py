"""
Database module for Turso remote SQLite with local fallback.

Supports:
- Turso (libsql) remote database as primary
- Local SQLite as fallback
- Auto-initialization of tables
"""

import os
import sqlite3
import logging
from typing import Optional, Union
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import libsql-experimental for Turso support
try:
    from libsql_experimental import connect as libsql_connect
    LIBSQL_AVAILABLE = True
except ImportError:
    LIBSQL_AVAILABLE = False
    logger.warning("libsql-experimental not installed. Using local SQLite only.")


# Default local database path
DEFAULT_LOCAL_DB = './market_data.db'


def get_db_connection():
    """
    Get database connection.
    
    Priority:
    1. Turso remote (if TURSO_DATABASE_URL and TURSO_AUTH_TOKEN set)
    2. Local SQLite (fallback)
    
    Returns:
        Database connection object
    """
    turso_url = os.getenv('TURSO_DATABASE_URL')
    turso_token = os.getenv('TURSO_AUTH_TOKEN')
    
    # Try Turso first if credentials available
    if turso_url and turso_token and LIBSQL_AVAILABLE:
        try:
            conn = libsql_connect(turso_url, auth_token=turso_token)
            logger.info("Connected to Turso remote database")
            return conn
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
    cursor = conn.cursor()
    
    # Daily prices table
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
    
    # IV history table
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
    
    # Options positions table (for tracking actual positions)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            option_type TEXT NOT NULL,
            strike REAL NOT NULL,
            expiration DATE NOT NULL,
            quantity INTEGER NOT NULL,
            avg_price REAL NOT NULL,
            entry_date DATE,
            notes TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database tables initialized")


def test_connection() -> bool:
    """Test database connection. Returns True if successful."""
    try:
        conn = get_db_connection()
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
    return bool(turso_url and turso_token and LIBSQL_AVAILABLE)
