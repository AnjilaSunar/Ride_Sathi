import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ridesathi.settings')
django.setup()

def check_admins():
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, full_name, email, role FROM users WHERE role = 'admin'")
        admins = cursor.fetchall()
        for admin in admins:
            print(f"Admin Found: ID={admin[0]}, Name={admin[1]}, Email={admin[2]}, Role={admin[3]}")

if __name__ == "__main__":
    check_admins()
