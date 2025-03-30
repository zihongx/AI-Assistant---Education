#!/usr/bin/env python3
"""
Database check utility for the appointment system.

This script checks the database for common issues and can fix them:
- Verifies database file exists
- Checks tables structure
- Validates user and appointment entries
- Can create missing tables if needed
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path to import from app
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))
sys.path.insert(0, project_root)

try:
    from app.config.settings import DB_PATH
except ImportError:
    logger.error("Could not import settings. Make sure you're running from the project root.")
    DB_PATH = os.path.join(project_root, 'data', 'appointments.db')
    logger.info(f"Using fallback DB path: {DB_PATH}")

def check_database():
    """
    Check database for common issues
    
    Returns:
        bool: True if database is healthy, False otherwise
    """
    logger.info(f"Checking database at: {DB_PATH}")
    
    # Check if database file exists
    if not os.path.exists(DB_PATH):
        logger.error(f"Database file does not exist: {DB_PATH}")
        return False
    
    # Check file permissions
    try:
        with open(DB_PATH, 'rb') as f:
            pass
        logger.info("Database file is readable")
    except PermissionError:
        logger.error("Permission denied: Cannot read database file")
        return False
    
    # Make sure the data directory exists
    data_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(data_dir):
        logger.warning(f"Data directory does not exist: {data_dir}")
        return False
    
    try:
        # Check if can connect to database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check for required tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        logger.info(f"Found tables in database: {', '.join(tables)}")
        
        required_tables = ['users', 'appointments']
        missing_tables = [table for table in required_tables if table not in tables]
        
        if missing_tables:
            logger.error(f"Missing required tables: {', '.join(missing_tables)}")
            return False
        
        # Check user table count
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        logger.info(f"Found {user_count} users in the database")
        
        # Check appointments table count
        cursor.execute("SELECT COUNT(*) FROM appointments")
        appointment_count = cursor.fetchone()[0]
        logger.info(f"Found {appointment_count} appointments in the database")
        
        # Check for orphaned appointments (no user)
        cursor.execute("""
            SELECT COUNT(*) FROM appointments a
            LEFT JOIN users u ON a.user_id = u.id
            WHERE u.id IS NULL
        """)
        orphaned_count = cursor.fetchone()[0]
        if orphaned_count > 0:
            logger.warning(f"Found {orphaned_count} orphaned appointments with no user")
        
        conn.close()
        logger.info("Database check completed successfully")
        return True
    
    except sqlite3.Error as e:
        logger.error(f"SQLite error during database check: {str(e)}")
        return False

def fix_database_issues():
    """
    Fix common database issues
    
    Returns:
        bool: True if fixes were applied successfully, False otherwise
    """
    logger.info("Attempting to fix database issues...")
    
    # Create data directory if it doesn't exist
    data_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(data_dir):
        try:
            os.makedirs(data_dir, exist_ok=True)
            logger.info(f"Created data directory: {data_dir}")
        except PermissionError:
            logger.error(f"Permission denied: Cannot create data directory: {data_dir}")
            return False
    
    try:
        # Connect to database (creates it if it doesn't exist)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check for missing tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Create users table if missing
        if 'users' not in tables:
            logger.info("Creating users table...")
            cursor.execute("""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    phone TEXT
                )
            """)
            logger.info("Created users table")
        
        # Create appointments table if missing
        if 'appointments' not in tables:
            logger.info("Creating appointments table...")
            cursor.execute("""
                CREATE TABLE appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    appointment_time TEXT NOT NULL,
                    status TEXT DEFAULT 'scheduled',
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """)
            logger.info("Created appointments table")
        
        conn.commit()
        conn.close()
        logger.info("Database fixes applied successfully")
        return True
    
    except sqlite3.Error as e:
        logger.error(f"SQLite error during database fix: {str(e)}")
        return False

if __name__ == "__main__":
    print("--------------------------------------------------")
    print("Database Check Utility for Appointment System")
    print("--------------------------------------------------")
    print(f"Database path: {DB_PATH}")
    print()
    
    is_healthy = check_database()
    
    if not is_healthy:
        print("\nDatabase issues detected. Would you like to fix them? (y/n)")
        choice = input("> ").strip().lower()
        
        if choice == 'y':
            success = fix_database_issues()
            if success:
                print("\nDatabase fixes applied successfully.")
                print("Running check again to verify...")
                check_database()
            else:
                print("\nFailed to fix database issues.")
        else:
            print("\nNo fixes applied.")
    else:
        print("\nDatabase is healthy. No issues detected.") 