import sqlite3
import os

# Set database storage path
db_path = os.path.join(os.getcwd(), "data", "appointments.db")

# Ensure directory exists
os.makedirs(os.path.dirname(db_path), exist_ok=True)

# Connect to SQLite database 
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create users table
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL UNIQUE
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

print("Database initialized!")





