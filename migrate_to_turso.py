#!/usr/bin/env python3
"""
Migration script to copy local SQLite data to Turso remote database.

Usage:
    python migrate_to_turso.py

Requires:
    - TURSO_DATABASE_URL and TURSO_AUTH_TOKEN in .env or environment
    - Source database at /Users/server/clawd/venv/xai-sdk/market_data.db
      (or set SOURCE_DB_PATH env var)
"""

import os
import sys
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to import libsql
try:
    from libsql_experimental import connect as libsql_connect
except ImportError:
    print("Error: libsql-experimental not installed.")
    print("Run: pip install libsql-experimental")
    sys.exit(1)

# Configuration
SOURCE_DB_PATH = os.getenv('SOURCE_DB_PATH', '/Users/server/clawd/venv/xai-sdk/market_data.db')
TURSO_URL = os.getenv('TURSO_DATABASE_URL')
TURSO_TOKEN = os.getenv('TURSO_AUTH_TOKEN')


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
    
    return libsql_connect(TURSO_URL, auth_token=TURSO_TOKEN)


def migrate_table(source_cur, target_conn, table_name, columns):
    """Migrate a single table."""
    print(f"\nMigrating {table_name}...")
    
    # Fetch all data from source
    source_cur.execute(f"SELECT * FROM {table_name}")
    rows = source_cur.fetchall()
    
    if not rows:
        print(f"  No data in {table_name}")
        return 0
    
    # Get column names from first row
    col_names = list(rows[0].keys())
    placeholders = ','.join(['?' for _ in col_names])
    
    # Insert into target
    target_cur = target_conn.cursor()
    inserted = 0
    
    for row in rows:
        try:
            values = [row[col] for col in col_names]
            target_cur.execute(
                f"INSERT OR REPLACE INTO {table_name} ({','.join(col_names)}) VALUES ({placeholders})",
                values
            )
            inserted += 1
        except Exception as e:
            print(f"  Error inserting row: {e}")
            continue
    
    target_conn.commit()
    print(f"  Migrated {inserted} rows to {table_name}")
    return inserted


def main():
    print("=" * 60)
    print("Turso Database Migration Tool")
    print("=" * 60)
    print(f"Source: {SOURCE_DB_PATH}")
    print(f"Target: {TURSO_URL}")
    print("=" * 60)
    
    # Connect to databases
    try:
        source_conn = connect_source()
        source_cur = source_conn.cursor()
        print("\n✓ Connected to source database")
    except Exception as e:
        print(f"\n✗ Failed to connect to source: {e}")
        sys.exit(1)
    
    try:
        target_conn = connect_turso()
        print("✓ Connected to Turso remote database")
    except Exception as e:
        print(f"✗ Failed to connect to Turso: {e}")
        source_conn.close()
        sys.exit(1)
    
    # Ensure target tables exist
    print("\nInitializing target tables...")
    target_cur = target_conn.cursor()
    
    target_cur.execute('''
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
    
    target_cur.execute('''
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
    
    # Check what tables exist in source
    source_cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    source_tables = {row['name'] for row in source_cur.fetchall()}
    print(f"  Source tables: {', '.join(source_tables)}")
    
    # Migrate tables
    total_migrated = 0
    
    if 'daily_prices' in source_tables:
        total_migrated += migrate_table(source_cur, target_conn, 'daily_prices', None)
    else:
        print("\n  daily_prices table not found in source")
    
    if 'iv_history' in source_tables:
        total_migrated += migrate_table(source_cur, target_conn, 'iv_history', None)
    else:
        print("  iv_history table not found in source")
    
    # Cleanup
    source_conn.close()
    target_conn.close()
    
    print("\n" + "=" * 60)
    print(f"Migration complete! Total rows migrated: {total_migrated}")
    print("=" * 60)


if __name__ == "__main__":
    main()
