#!/usr/bin/env python3
"""
Chunked import of SQL dump to Turso via HTTP API.
Splits large SQL files into batches to avoid timeout issues.

Usage:
    export TURSO_DATABASE_URL=libsql://market-data-rmeyer1.aws-us-east-1.turso.io
    export TURSO_AUTH_TOKEN=your_token_here
    python import_to_turso.py turso_export.sql
"""

import os
import sys
import requests
import re
import time

TURSO_URL = os.getenv('TURSO_DATABASE_URL', '').replace('libsql://', 'https://').rstrip('/')
TURSO_TOKEN = os.getenv('TURSO_AUTH_TOKEN')

if not TURSO_URL or not TURSO_TOKEN:
    print("Error: Set TURSO_DATABASE_URL and TURSO_AUTH_TOKEN")
    sys.exit(1)

HEADERS = {
    'Authorization': f'Bearer {TURSO_TOKEN}',
    'Content-Type': 'application/json'
}

def execute_statements(statements):
    """Execute a batch of SQL statements via Turso HTTP API."""
    payload = {
        'requests': [
            {'type': 'execute', 'stmt': {'sql': stmt}} 
            for stmt in statements if stmt.strip()
        ]
    }
    
    # Use the correct v2 endpoint format
    response = requests.post(
        f'{TURSO_URL}/v2/pipeline',
        headers=HEADERS,
        json=payload,
        timeout=60
    )
    
    if response.status_code != 200:
        print(f"  Error: {response.status_code} - {response.text[:200]}")
        return False
    return True

def main():
    sql_file = sys.argv[1] if len(sys.argv) > 1 else 'turso_export.sql'
    
    if not os.path.exists(sql_file):
        print(f"Error: File not found: {sql_file}")
        sys.exit(1)
    
    print(f"Importing {sql_file} to Turso...")
    print(f"Target: {TURSO_URL}")
    
    # Read and parse SQL file
    with open(sql_file, 'r') as f:
        content = f.read()
    
    # Split into individual statements
    statements = [s.strip() for s in re.split(r';\n', content) if s.strip() and not s.strip().startswith('--')]
    
    print(f"Total statements: {len(statements)}")
    
    # First, run CREATE TABLE and PRAGMA statements
    setup_statements = [s for s in statements if s.upper().startswith(('CREATE', 'DROP', 'PRAGMA'))]
    data_statements = [s for s in statements if s.upper().startswith('INSERT')]
    
    print(f"Setup statements: {len(setup_statements)}")
    print(f"Data statements: {len(data_statements)}")
    
    # Execute setup first
    print("\nCreating tables...")
    for stmt in setup_statements:
        if execute_statements([stmt]):
            print(f"  ✓ {stmt[:50]}...")
        else:
            print(f"  ✗ Failed: {stmt[:50]}...")
    
    # Execute INSERTs in batches
    print("\nInserting data...")
    batch_size = 25
    total_batches = (len(data_statements) + batch_size - 1) // batch_size
    
    for i in range(0, len(data_statements), batch_size):
        batch = data_statements[i:i+batch_size]
        batch_num = i // batch_size + 1
        
        if execute_statements(batch):
            print(f"  Batch {batch_num}/{total_batches}: {len(batch)} rows ✓")
        else:
            print(f"  Batch {batch_num}/{total_batches}: FAILED")
            # Try one by one
            for stmt in batch:
                if not execute_statements([stmt]):
                    print(f"    Skipped: {stmt[:60]}...")
        
        time.sleep(0.1)  # Brief pause between batches
    
    print("\n✓ Import complete!")
    print(f"Check your data at: https://turso.tech/app")

if __name__ == "__main__":
    main()
