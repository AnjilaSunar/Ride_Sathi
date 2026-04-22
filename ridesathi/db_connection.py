import mysql.connector

# This function connects to your MySQL database (XAMPP)
def get_db_connection():
    connection = mysql.connector.connect(
        host="localhost",       # XAMPP runs on localhost
        user="root",            # default XAMPP username
        password="",            # default XAMPP password (empty)
        database="ridesathi_db" # the database we created
    )
    return connection
