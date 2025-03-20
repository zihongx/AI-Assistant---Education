import sqlite3
import os

def check_database():
    # Set database storage path
    db_path = os.path.join(os.getcwd(), "data", "appointments.db")
    
    print(f"Checking database at: {db_path}")
    
    # Check if database exists
    if not os.path.exists(db_path):
        print("Database file does not exist!")
        return
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables
        print("\nChecking tables:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"Found tables: {[table[0] for table in tables]}")
        
        # Check users table
        print("\nChecking users table:")
        cursor.execute("SELECT * FROM users")
        users = cursor.fetchall()
        print(f"Number of users: {len(users)}")
        if users:
            print("Sample user data:")
            for user in users[:3]:
                print(f"ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Phone: {user[3]}")
        
        # Check appointments table
        print("\nChecking appointments table:")
        cursor.execute("SELECT * FROM appointments")
        appointments = cursor.fetchall()
        print(f"Number of appointments: {len(appointments)}")
        if appointments:
            print("Sample appointment data:")
            for appt in appointments[:3]:
                print(f"ID: {appt[0]}, User ID: {appt[1]}, Time: {appt[2]}, Status: {appt[3]}")
        
        conn.close()
        print("\nDatabase check completed successfully!")
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_database() 