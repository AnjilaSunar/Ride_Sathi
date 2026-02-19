from django.shortcuts import render, redirect
from django.contrib import messages
import hashlib  # used to hash passwords (basic security)
from db_connection import get_db_connection  # our MySQL helper


# ─────────────────────────────────────────────
# Helper: hash a password simply using MD5
# In viva: "We hash the password before storing, so plain text is never saved"
# ─────────────────────────────────────────────
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()


# ─────────────────────────────────────────────
# HOME PAGE
# ─────────────────────────────────────────────
def home(request):
    return render(request, "accounts/index.html")


# ─────────────────────────────────────────────
# BIKES PAGE
# ─────────────────────────────────────────────
def bikes(request):
    return render(request, "accounts/bikes.html")


# ─────────────────────────────────────────────
# ABOUT PAGE
# ─────────────────────────────────────────────
def about(request):
    return render(request, "accounts/about.html")


# ─────────────────────────────────────────────
# REGISTER PAGE
# What it does:
#   1. Gets username, email, password from the HTML form
#   2. Checks if username or email already exists (raw SQL SELECT)
#   3. If not, inserts new user into MySQL `users` table (raw SQL INSERT)
# ─────────────────────────────────────────────
def register(request):
    if request.method == "POST":
        username  = request.POST.get("username")
        email     = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        # Step 1: Check passwords match
        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        # Step 2: Connect to MySQL
        conn   = get_db_connection()
        cursor = conn.cursor()

        # Step 3: Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            messages.error(request, "Username already exists.")
            cursor.close()
            conn.close()
            return redirect("register")

        # Step 4: Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            messages.error(request, "Email already exists.")
            cursor.close()
            conn.close()
            return redirect("register")

        # Step 5: Hash the password before saving
        hashed_pw = hash_password(password1)

        # Step 6: Insert new user into `users` table
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (username, email, hashed_pw)
        )
        conn.commit()  # save the change to database
        cursor.close()
        conn.close()

        messages.success(request, "Account created successfully! Please login.")
        return redirect("login")

    return render(request, "accounts/register.html")


# ─────────────────────────────────────────────
# LOGIN PAGE
# What it does:
#   1. Gets username and password from the HTML form
#   2. Hashes the password (same way we saved it)
#   3. Checks if user exists in MySQL with that username + hashed password
#   4. If found → saves user info in session (like a cookie)
#   5. If not found → shows error
# ─────────────────────────────────────────────
def login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        # Hash the entered password to match what is in the database
        hashed_pw = hash_password(password)

        # Connect to MySQL
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)  # dictionary=True gives us column names

        # Raw SQL: Find user with matching username AND password
        cursor.execute(
            "SELECT * FROM users WHERE username = %s AND password = %s",
            (username, hashed_pw)
        )
        user = cursor.fetchone()  # gets the first matching row
        cursor.close()
        conn.close()

        if user:
            # Save user info in session (so we know who is logged in)
            request.session["user_id"]   = user["id"]
            request.session["username"]  = user["username"]
            request.session["user_role"] = user["role"]
            messages.success(request, f"Welcome back, {user['username']}!")
            return redirect("home")
        else:
            messages.error(request, "Invalid username or password.")
            return render(request, "accounts/login.html")

    return render(request, "accounts/login.html")


# ─────────────────────────────────────────────
# LOGOUT
# What it does: clears the session (removes login info)
# ─────────────────────────────────────────────
def logout(request):
    request.session.flush()  # clears everything saved in session
    messages.success(request, "You have been logged out.")
    return redirect("login")
