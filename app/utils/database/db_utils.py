#!/usr/bin/env python3
"""
Database utility functions for appointment scheduling application.
Provides database initialization and connection functions.
"""

import os
import sqlite3
import logging
from app.config.settings import DB_PATH

logger = logging.getLogger(__name__)

def init_db():
    """
    Initialize the database by creating necessary tables if they don't exist.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Initializing database at: {DB_PATH}")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        # Connect to SQLite database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL
        )
        ''')
        
        # Create appointments table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            appointment_time DATETIME NOT NULL UNIQUE,
            status TEXT CHECK( status IN ('scheduled', 'canceled') ) DEFAULT 'scheduled',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        ''')
        
        # Commit changes and close database
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        return False

def get_db_connection():
    """
    Get a connection to the SQLite database.
    
    Returns:
        sqlite3.Connection: A connection to the database
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # This enables column access by name
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {str(e)}")
        raise 

if __name__ == "__main__":
    init_db()
    

