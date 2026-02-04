#!/usr/bin/env python3
"""
Migration script to copy local SQLite data to Turso remote database.
Uses HTTP API instead of libsql (avoids native dependency issues).

Usage:
    export TURSO_DATABASE_URL=libsql://your-db.turso.io
    export TURSO_AUTH_TOKEN=your_token
    python migrate_to_turso.py

Optional:
    export SOURCE_DB_PATH=/path/to/local/market_data.db
"""

import os
import sys
import sqlite3
import requests
from datetime import datetime

# Configuration
SOURCE_DB_PATH = os.getenv('SOURCE_DB_PATH', '/Users/server/clawd/venv/xai-sdk/market_data.db')
TURSO_URL = os.getenv('TURSO_DATABASE_URL')
TURSO_TOKEN = os.getenv('TURSO_AUTH_TOKEN')


class TursoHTTPClient:
    """Simple HTTP client for Turso."""
    
    def __init__(self, url: str, token: str):
        self.url = url.replace('libsql://', 'https://').rstrip('/')
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def execute(self, sql: str, args: list = None):
        """Execute SQL via HTTP API."""
        payload = {'statements': [{'sql': sql, 'args': args or []}]}
        response = requests.post(
            f'{self.url}/v2/pipeline',
            headers=self.headers,
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json()


def connect_source():
    """Connect to source local database."""
    if not os.path.exists(SOURCE_DB_PATH):
        print(f"Error: Source database not found at {SOURCE_DB_PATH}")
        print("Set SOURCE_DB_PATH env var if located elsewhere.")
        sys.exit(1)
    
    conn = sqlite3.connect(SOURCE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def connect_turso():
    """Connect to Turso remote database."""
    if not TURSO_URL or not TURSO_TOKEN:
        print("Error: TURSO_DATABASE_URL and TURSO_AUTH_TOKEN must be set")
        sys.exit(1)
    
    return TursoHTTPClient(TURSO_URL, TURSO_TOKEN)


def migrate_table(source_conn, turso_client, table_name):
    """Migrate a single table."""
    print(f"\nMigrating {table_name}...")
    
    # Fetch all data from source
    source_cur = source_conn.cursor()
    source_cur.execute(f"SELECT * FROM {table_name}")
    rows = source_cur.fetchall()
    
    if not rows:
        print(f"  No data in {table_name}")
        return 0
    
    print(f"  Found {len(rows)} rows in source")
    
    # Get column names from first row
    col_names = list(rows[0].keys())
    placeholders = ','.join(['?' for _ in col_names])
    col_list = ','.join(col_names)
    
    # Build INSERT SQL
    insert_sql = f"INSERT OR REPLACE INTO {table_name} ({col_list}) VALUES ({placeholders})"
    
    # Insert into Turso in batches
    inserted = 0
    batch_size = 50
    
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        statements = []
        
        for row in batch:
            values = [row[col] for col in col_names]
            # Convert dates to strings if needed
            values = [str(v) if hasattr(v, 'strftime') else v for v in values]
            statements.append({'sql': insert_sql, 'args': values})
        
        try:
            payload = {'statements': statements}
            response = requests.post(
                f'{turso_client.url}/v2/pipeline',
                headers=turso_client.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            inserted += len(batch)
            print(f"  Migrated {inserted}/{len(rows)} rows...")
        except Exception as e:
            print(f"  Error in batch: {e}")
            continue
    
    print(f"  ✓ Migrated {inserted} rows to {table_name}")
    return inserted


def create_turso_tables(turso_client):
    """Create tables in Turso if they don't exist."""
    print("\nInitializing Turso tables...")
    
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
        try:
            turso_client.execute(sql)
            print(f"  ✓ Table created/verified")
        except Exception as e:
            print(f"  Warning: {e}")


def main():
    print("=" * 60)
    print("Turso Database Migration Tool (HTTP API)")
    print("=" * 60)
    print(f"Source: {SOURCE_DB_PATH}")
    print(f"Target: {TURSO_URL}")
    print("=" * 60)
    
    # Check if source exists
    if not os.path.exists(SOURCE_DB_PATH):
        print(f"\nError: Source database not found!")
        print(f"Expected at: {SOURCE_DB_PATH}")
        print(f"\nCheck if the path exists:")
        os.system(f"ls -la {os.path.dirname(SOURCE_DB_PATH)} 2>/dev/null || echo 'Directory does not exist'")
        sys.exit(1)
    
    # Connect to source
    try:
        source_conn = connect_source()
        print("\n✓ Connected to source database")
    except Exception as e:
        print(f"\n✗ Failed to connect to source: {e}")
        sys.exit(1)
    
    # Connect to Turso
    try:
        turso_client = connect_turso()
        # Test connection
        turso_client.execute("SELECT 1")
        print("✓ Connected to Turso remote database")
    except Exception as e:
        print(f"\n✗ Failed to connect to Turso: {e}")
        source_conn.close()
        sys.exit(1)
    
    # Create tables in Turso
    create_turso_tables(turso_client)
    
    # Check what tables exist in source
    source_cur = source_conn.cursor()
    source_cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    source_tables = {row['name'] for row in source_cur.fetchall()}
    print(f"\nSource tables: {', '.join(source_tables)}")
    
    # Migrate tables
    total_migrated = 0
    
    if 'daily_prices' in source_tables:
        total_migrated += migrate_table(source_conn, turso_client, 'daily_prices')
    else:
        print("\n  daily_prices table not found in source")
    
    if 'iv_history' in source_tables:
        total_migrated += migrate_table(source_conn, turso_client, 'iv_history')
    else:
        print("  iv_history table not found in source")
    
    # Cleanup
    source_conn.close()
    
    print("\n" + "=" * 60)
    print(f"Migration complete! Total rows migrated: {total_migrated}")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Add TURSO_DATABASE_URL and TURSO_AUTH_TOKEN to your .env")
    print("2. Pull the backend on your laptop")
    print("3. Run: python -c \"from services.database import test_connection; print(test_connection())\"")


if __name__ == "__main__":
    main()
