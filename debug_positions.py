"""
Debug script to check positions in database
"""

from services.database import get_db

if __name__ == "__main__":
    print("Checking positions in database...")
    try:
        with get_db() as db:
            is_turso = hasattr(db, 'execute')
            
            if is_turso:
                position_rows = db.execute("SELECT * FROM positions")
            else:
                cursor = db.cursor()
                cursor.execute("SELECT * FROM positions")
                position_rows = [dict(row) for row in cursor.fetchall()]
            
            print(f"Found {len(position_rows)} positions:")
            for row in position_rows:
                print(row)
    except Exception as e:
        print(f"Error: {e}")