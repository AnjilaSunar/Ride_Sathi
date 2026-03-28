from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import FileSystemStorage  # NEW: used to save uploaded files
import hashlib  # used to hash passwords (basic security)
from datetime import datetime  # used to calculate the number of days for booking
from django.db import connection  # Use Django's built-in DB connection from settings.py


# ─────────────────────────────────────────────
# Helper: hash a password simply using MD5
# In viva: "We hash the password before storing, so plain text is never saved"
# ─────────────────────────────────────────────
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

# ─────────────────────────────────────────────
# Helper: Return all rows from a cursor as a dict
# ─────────────────────────────────────────────
def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

# ─────────────────────────────────────────────
# Helper: Return one row from a cursor as a dict
# ─────────────────────────────────────────────
def dictfetchone(cursor):
    "Return one row from a cursor as a dict safely"
    row = cursor.fetchone()
    if row is None:
        return None
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))


# ─────────────────────────────────────────────
# HOME PAGE
# ─────────────────────────────────────────────
def home(request):
    with connection.cursor() as cursor:
        # 1. Fetch 4 available bikes for the "Featured Bikes" section
        cursor.execute("SELECT * FROM bikes WHERE status = 'available' LIMIT 4")
        featured_bikes = dictfetchall(cursor)

        # 2. Fetch distinct categories and one image for each from the database
        cursor.execute("SELECT category, MIN(image) as image FROM bikes GROUP BY category LIMIT 4")
        categories = dictfetchall(cursor)

    context = {
        "featured_bikes": featured_bikes,
        "categories": categories
    }
    
    return render(request, "accounts/index.html", context)


# ─────────────────────────────────────────────
# BIKES PAGE
# What it does:
#   1. Connects to MySQL
#   2. Runs: SELECT * FROM bikes WHERE status = 'available'
#   3. Passes the list of bikes to bikes.html template
# ─────────────────────────────────────────────
def bikes(request):
    # Get the current date to check real-time availability
    today = datetime.now().date()
    
    with connection.cursor() as cursor:
        # Raw SQL: Get all bikes that aren't out of service
        # Also join with bookings to see if they are currently occupied
        cursor.execute("""
            SELECT b.*, 
            (SELECT COUNT(*) FROM bookings bk 
             WHERE bk.bike_id = b.id 
             AND bk.status != 'cancelled' 
             AND %s BETWEEN bk.start_date AND bk.end_date) as is_booked_now
            FROM bikes b
            WHERE b.status != 'out_of_service'
            ORDER BY b.id ASC
        """, [today])
        
        all_bikes = dictfetchall(cursor)
        
        # Manually update the status field based on real-time data for the template
        for bike in all_bikes:
            if bike['is_booked_now'] > 0:
                bike['status'] = 'booked'
            else:
                # Keep original status (available or maintenance)
                pass

    return render(request, "accounts/bikes.html", {"bikes": all_bikes})


# ─────────────────────────────────────────────
# BIKE DETAIL PAGE
# What it does:
#   1. Gets the bike id from the URL (e.g. /bikes/3/)
#   2. Runs: SELECT * FROM bikes WHERE id = 3
#   3. Shows details of that specific bike
# ─────────────────────────────────────────────
def bike_detail(request, bike_id):
    today = datetime.now().date()
    with connection.cursor() as cursor:
        # Raw SQL: get ONE bike by its id
        # Join with bookings to see if currently booked
        cursor.execute("""
            SELECT b.*, 
            (SELECT COUNT(*) FROM bookings bk 
             WHERE bk.bike_id = b.id 
             AND bk.status != 'cancelled' 
             AND %s BETWEEN bk.start_date AND bk.end_date) as is_booked_now
            FROM bikes b
            WHERE b.id = %s
        """, [today, bike_id])
        bike = dictfetchone(cursor)

    if not bike:
        messages.error(request, "Bike not found.")
        return redirect("bikes")
        
    # Real-time status update
    if bike['is_booked_now'] > 0:
        bike['status'] = 'booked'

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

        # Step 2: Use Django's Database connection
        with connection.cursor() as cursor:
            # Step 3: Check if username already exists
            cursor.execute("SELECT id FROM users WHERE username = %s", [username])
            if cursor.fetchone():
                messages.error(request, "Username already exists.")
                return redirect("register")

            # Step 4: Check if email already exists
            cursor.execute("SELECT id FROM users WHERE email = %s", [email])
            if cursor.fetchone():
                messages.error(request, "Email already exists.")
                return redirect("register")

        # Step 5: Hash the password before saving
        hashed_pw = hash_password(password1)

        # Step 6: Insert new user into `users` table
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                [username, email, hashed_pw]
            )

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

        # Connect to MySQL using Django's connection
        with connection.cursor() as cursor:
            # Raw SQL: Find user with matching username AND password
            cursor.execute(
                "SELECT * FROM users WHERE username = %s AND password = %s",
                [username, hashed_pw]
            )
            user = dictfetchone(cursor)

        if user:
            # Save user info in session (so we know who is logged in)
            request.session["user_id"]   = user["id"]
            request.session["username"]  = user["username"]
            request.session["user_role"] = user["role"]
            messages.success(request, f"Welcome back, {user['username']}!")
            
            if user["role"] == "admin":
                return redirect("admin_dashboard")
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
# ADMIN DASHBOARD (Placeholder)
# ─────────────────────────────────────────────
def admin_dashboard(request):
    if request.session.get("user_role") != "admin":
        messages.error(request, "Access Denied. Admins only.")
        return redirect("home")
    
    return render(request, "accounts/admin_dashboard.html")


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

    # Connect to MySQL using Django natively
    with connection.cursor() as cursor:
        # 2. Get the bike details
        cursor.execute("SELECT * FROM bikes WHERE id = %s", [bike_id])
        bike = dictfetchone(cursor)
        
        if not bike:
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

        # 5.5 Prevent Double Booking (Overlap Check)
        with connection.cursor() as cursor:
            # An overlap happens if: existing_start <= new_end AND existing_end >= new_start
            cursor.execute(
                """
                SELECT id FROM bookings 
                WHERE bike_id = %s 
                  AND status != 'cancelled'
                  AND start_date <= %s 
                  AND end_date >= %s
                """,
                [bike_id, end_date, start_date]
            )
            conflict = cursor.fetchone()
            
            if conflict:
                messages.error(request, "Sorry, this bike is already booked for these selected dates. Please choose different dates.")
                return redirect("book_bike", bike_id=bike_id)

        # 5.6 Handle Document Upload & Contact Details
        phone    = request.POST.get("phone")
        address  = request.POST.get("address")
        doc_type = request.POST.get("doc_type")
        document = request.FILES.get("document")
        document_path = ""

        if document:
            # Save file to media/documents/
            fs = FileSystemStorage(location='media/documents/')
            filename = fs.save(document.name, document)
            document_path = f"documents/{filename}"

        # 6. Save the booking in MySQL using Raw SQL (INSERT)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO bookings (user_id, bike_id, start_date, end_date, total_days, total_cost, status, phone, address, doc_type, document_path) 
                VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s, %s, %s, %s)
                """,
                [user_id, bike_id, start_date, end_date, total_days, total_cost, phone, address, doc_type, document_path]
            )
            
            # Grabbing the ID from Django's cursor
            cursor.execute("SELECT LAST_INSERT_ID()")
            booking_id = cursor.fetchone()[0]

        messages.success(request, f"Booking successful! Proceed to payment to confirm your bike rental.")
        
        # Redirect to the payment page to complete the booking
        return redirect("payment", booking_id=booking_id)

    # GET request (just showing the page)
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

        # 3. Store the path using Django's connection
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO documents (user_id, doc_type, file_path) VALUES (%s, %s, %s)",
                [user_id, doc_type, file_path]
            )

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

    with connection.cursor() as cursor:
        # Validate the booking
        user_id = request.session["user_id"]
        cursor.execute("SELECT * FROM bookings WHERE id = %s AND user_id = %s", [booking_id, user_id])
        booking = dictfetchone(cursor)

        if not booking:
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
                [booking_id, user_id, booking["total_cost"]]
            )

            # 2. Update the booking status from pending to confirmed
            cursor.execute(
                "UPDATE bookings SET status = 'confirmed' WHERE id = %s",
                [booking_id]
            )

            messages.success(request, "Payment successful via eSewa! Your booking is confirmed.")
            
            # Fetch the updated booking for the success page
            cursor.execute("SELECT * FROM bookings WHERE id = %s", [booking_id])
            confirmed_booking = dictfetchone(cursor)
            
            return render(request, "accounts/booking_success.html", {"booking": confirmed_booking})

    return render(request, "accounts/payment.html", {"booking": booking})
