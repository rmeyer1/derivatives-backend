"""
Initialize the database with all required tables
"""

from services.database import initialize_database

if __name__ == "__main__":
    print("Initializing database...")
    initialize_database()
    print("Database initialized successfully!")