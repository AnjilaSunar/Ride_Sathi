from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import FileSystemStorage  # NEW: used to save uploaded files
import hashlib  # used to hash passwords (basic security)
from datetime import datetime  # used to calculate the number of days for booking
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
# What it does:
#   1. Connects to MySQL
#   2. Runs: SELECT * FROM bikes WHERE status = 'available'
#   3. Passes the list of bikes to bikes.html template
# ─────────────────────────────────────────────
def bikes(request):
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # dictionary=True = column names as keys

    # Raw SQL: get all available bikes
    cursor.execute("SELECT * FROM bikes WHERE status = 'available' ORDER BY id ASC")
    all_bikes = cursor.fetchall()  # returns a list of dictionaries

    cursor.close()
    conn.close()

    return render(request, "accounts/bikes.html", {"bikes": all_bikes})


# ─────────────────────────────────────────────
# BIKE DETAIL PAGE
# What it does:
#   1. Gets the bike id from the URL (e.g. /bikes/3/)
#   2. Runs: SELECT * FROM bikes WHERE id = 3
#   3. Shows details of that specific bike
# ─────────────────────────────────────────────
def bike_detail(request, bike_id):
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Raw SQL: get ONE bike by its id
    cursor.execute("SELECT * FROM bikes WHERE id = %s", (bike_id,))
    bike = cursor.fetchone()

    cursor.close()
    conn.close()

    if not bike:
        messages.error(request, "Bike not found.")
        return redirect("bikes")

    return render(request, "accounts/bike_detail.html", {"bike": bike})


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


# ─────────────────────────────────────────────
# BOOK BIKE PAGE
# What it does:
#   1. Makes sure the user is logged in
#   2. Gets the specific bike details
#   3. On POST: calculates days between start & end date
#   4. Checks if days are valid (> 0)
#   5. Calculates total_cost (days * price_per_day)
#   6. Runs: INSERT INTO bookings
# ─────────────────────────────────────────────
def book_bike(request, bike_id):
    # 1. Must be logged in to book a bike
    if "user_id" not in request.session:
        messages.error(request, "Please log in to book a bike.")
        return redirect("login")

    # Connect to MySQL
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 2. Get the bike details
    cursor.execute("SELECT * FROM bikes WHERE id = %s", (bike_id,))
    bike = cursor.fetchone()

    if not bike:
        cursor.close()
        conn.close()
        messages.error(request, "Bike not found.")
        return redirect("bikes")

    # Handle the form submission
    if request.method == "POST":
        start_date_str = request.POST.get("start_date")
        end_date_str   = request.POST.get("end_date")

        # Convert the string dates from the HTML form into real Python Dates
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date   = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        # 3. Calculate how many days
        # e.g., Jan 5 to Jan 7 = 2 days difference + 1 (so both days are counted) = 3 total days
        delta = end_date - start_date
        total_days = delta.days + 1

        # 4. Check if the dates make sense
        if total_days <= 0:
            messages.error(request, "End date must be after start date.")
            return redirect("book_bike", bike_id=bike_id)

        # 5. Calculate total cost
        total_cost = total_days * float(bike["price_per_day"])
        user_id = request.session["user_id"]

        # 6. Save the booking in MySQL using Raw SQL (INSERT)
        cursor.execute(
            """
            INSERT INTO bookings (user_id, bike_id, start_date, end_date, total_days, total_cost, status) 
            VALUES (%s, %s, %s, %s, %s, %s, 'pending')
            """,
            (user_id, bike_id, start_date, end_date, total_days, total_cost)
        )
        conn.commit()  # Make sure it literally saves!
        
        # We can grab the ID of the booking we just created (useful for payment later)
        booking_id = cursor.lastrowid
        cursor.close()
        conn.close()

        messages.success(request, f"Booking successful! Total cost is Rs. {total_cost}. Please proceed to payment.")
        
        # After booking, redirect to payment page with the new booking_id
        return redirect("payment", booking_id=booking_id)

    # GET request (just showing the page)
    cursor.close()
    conn.close()
    return render(request, "accounts/book_bike.html", {"bike": bike})


# ─────────────────────────────────────────────
# DOCUMENT UPLOAD PAGE
# What it does:
#   1. Must be logged in
#   2. Receives a file (like a photo of DL/ID)
#   3. Saves the file to the 'media' folder
#   4. Stores the file path inside the MySQL `documents` table
# ─────────────────────────────────────────────
def upload_document(request):
    if "user_id" not in request.session:
        messages.error(request, "Please log in to upload documents.")
        return redirect("login")

    if request.method == "POST" and request.FILES.get("document"):
        # 1. Get the file and document type from the HTML form
        user_id = request.session["user_id"]
        doc_type = request.POST.get("doc_type")
        uploaded_file = request.FILES["document"]

        # 2. Save the file directly to the /media/ folder
        fs = FileSystemStorage()
        # Ensure filename is unique by adding timestamp or keeping it simple
        filename = fs.save(uploaded_file.name, uploaded_file)
        file_path = fs.url(filename) # e.g., /media/my_license.jpg

        # 3. Store the path in MySQL using Raw SQL
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO documents (user_id, doc_type, file_path) VALUES (%s, %s, %s)",
            (user_id, doc_type, file_path)
        )
        conn.commit()
        cursor.close()
        conn.close()

        messages.success(request, "Document uploaded successfully!")
        return redirect("home") # Or redirect to dashboard later

    return render(request, "accounts/upload_document.html")


# ─────────────────────────────────────────────
# E-SEWA PAYMENT SIMULATION
# What it does:
#   1. Looks up the booking ID to get total_cost
#   2. When they click 'Pay with eSewa':
#      - INSERT into payments table (amount + booking_id)
#      - UPDATE bookings table status to 'confirmed'
#   3. Redirects to a success/invoice page (later)
# ─────────────────────────────────────────────
def payment(request, booking_id):
    if "user_id" not in request.session:
        return redirect("login")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Validate the booking
    user_id = request.session["user_id"]
    cursor.execute("SELECT * FROM bookings WHERE id = %s AND user_id = %s", (booking_id, user_id))
    booking = cursor.fetchone()

    if not booking:
        cursor.close()
        conn.close()
        messages.error(request, "Booking not found.")
        return redirect("bikes")

    # If the user clicks "Pay" on the form
    if request.method == "POST":
        # 1. Create a payment record in MySQL
        cursor.execute(
            """
            INSERT INTO payments (booking_id, user_id, amount, payment_method, payment_status)
            VALUES (%s, %s, %s, 'eSewa', 'paid')
            """,
            (booking_id, user_id, booking["total_cost"])
        )

        # 2. Update the booking status from pending to confirmed
        cursor.execute(
            "UPDATE bookings SET status = 'confirmed' WHERE id = %s",
            (booking_id,)
        )
        conn.commit()
        cursor.close()
        conn.close()

        messages.success(request, "Payment successful via eSewa! Your booking is confirmed.")
        
        # We'll go to Invoice or Home depending on what we build next
        return redirect("home") 

    cursor.close()
    conn.close()
    return render(request, "accounts/payment.html", {"booking": booking})
