import sys
import os

# Add the project directory to sys.path
sys.path.append('/Users/anjilasunar/Desktop/Ride_Sathi/ridesathi')

try:
    from db_connection import get_db_connection
    conn = get_db_connection()
    print("SUCCESS: Connected to MySQL database.")
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    print("Tables in database:", tables)
    conn.close()
except Exception as e:
    print(f"ERROR: Could not connect to MySQL. {e}")
