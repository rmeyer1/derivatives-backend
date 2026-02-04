#!/usr/bin/env python3
"""
Export SQLite database to SQL dump for Turso import.

Usage:
    python export_to_turso.py > turso_export.sql
    
Then import to Turso via:
    turso db shell market-data < turso_export.sql
    
Or use Turso web interface import feature.
"""

import os
import sqlite3
from datetime import datetime

SOURCE_DB_PATH = os.getenv('SOURCE_DB_PATH', '/Users/server/clawd/venv/xai-sdk/market_data.db')

def escape_sql(value):
    """Escape a value for SQL insertion."""
    if value is None:
        return 'NULL'
    if isinstance(value, (int, float)):
        return str(value)
    # String escape
    return "'" + str(value).replace("'", "''") + "'"

def export_table(conn, table_name, output_file):
    """Export a single table to SQL file."""
    cursor = conn.cursor()
    
    # Get schema
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    schema_row = cursor.fetchone()
    if not schema_row:
        print(f"-- Table {table_name} not found", file=output_file)
        return 0
    
    schema = schema_row[0]
    
    # Write DROP/CREATE
    print(f"-- Table: {table_name}", file=output_file)
    print(f"DROP TABLE IF EXISTS {table_name};", file=output_file)
    print(f"{schema};", file=output_file)
    print(file=output_file)
    
    # Get data
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    if not rows:
        print(f"-- No data in {table_name}", file=output_file)
        return 0
    
    # Get column names
    col_names = [desc[0] for desc in cursor.description]
    
    # Export as INSERT statements (batch for efficiency)
    batch_size = 100
    total = 0
    
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        
        for row in batch:
            values = [escape_sql(val) for val in row]
            insert = f"INSERT INTO {table_name} ({', '.join(col_names)}) VALUES ({', '.join(values)});"
            print(insert, file=output_file)
            total += 1
        
        print(f"-- Progress: {min(i+batch_size, len(rows))}/{len(rows)} rows", file=output_file)
    
    print(f"-- Exported {total} rows from {table_name}", file=output_file)
    print(file=output_file)
    
    return total

def main():
    print(f"-- Turso Export Generated: {datetime.now().isoformat()}")
    print(f"-- Source: {SOURCE_DB_PATH}")
    print("-- Database: market_data")
    print("")
    print("-- Enable foreign keys")
    print("PRAGMA foreign_keys = ON;")
    print("")
    
    if not os.path.exists(SOURCE_DB_PATH):
        print(f"-- ERROR: Source database not found: {SOURCE_DB_PATH}")
        return 1
    
    conn = sqlite3.connect(SOURCE_DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Get list of tables
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"-- Tables found: {', '.join(tables)}")
    print("")
    
    total_rows = 0
    for table in tables:
        count = export_table(conn, table, output_file=None)
        total_rows += count
    
    # Actually generate the file content
    # We'll write to a file instead of stdout for easier handling
    
    conn.close()
    
    # Now write the actual SQL file
    with open('turso_export.sql', 'w') as f:
        f.write(f"-- Turso Export Generated: {datetime.now().isoformat()}\n")
        f.write(f"-- Source: {SOURCE_DB_PATH}\n")
        f.write("-- Database: market_data\n\n")
        f.write("-- Enable foreign keys\n")
        f.write("PRAGMA foreign_keys = ON;\n\n")
        
        conn = sqlite3.connect(SOURCE_DB_PATH)
        conn.row_factory = sqlite3.Row
        
        for table in tables:
            export_table(conn, table, f)
        
        conn.close()
        
        f.write("-- Export complete\n")
    
    print(f"-- Export written to: turso_export.sql")
    print(f"-- Total rows exported: {total_rows}")
    return 0

if __name__ == "__main__":
    exit(main())
