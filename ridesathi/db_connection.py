import mysql.connector

# ─────────────────────────────────────────────
# Raw SQL connection to XAMPP MySQL
# Host: 127.0.0.1 (TCP, not socket — required for XAMPP on Mac)
# User: root
# Password: '' (XAMPP default — no password set)
# Port: 3306
# ─────────────────────────────────────────────
def get_db_connection():
    connection = mysql.connector.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="",            # XAMPP MySQL default: no password
        database="ridesathi_db"
    )
    return connection
