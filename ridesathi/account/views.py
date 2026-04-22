from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import FileSystemStorage
import hashlib
import hmac
import base64
import uuid
from datetime import datetime
from django.db import connection
import json
from django.http import HttpResponse, FileResponse
from fpdf import FPDF
import io
import requests
from django.core.mail import EmailMessage, send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.core.paginator import Paginator
from django.conf import settings
import os
import re


# Function to convert passwords into a secure hash
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

def dictfetchall(cursor):
    # This turns database results into a list of easy-to-use dictionaries
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def dictfetchone(cursor):
    # This gets just one row from the database as a dictionary
    row = cursor.fetchone()
    if row is None: return None
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))


# --- INTERNAL HELPER FUNCTIONS (KEEPING CODE CLEAN) ---

def _is_admin(request):
    """Helper to check if the current user is an admin."""
    return request.session.get("user_role") == "admin"

def _get_bike_availability_sql():
    """Returns the standardized SQL for checking bike availability on a given date."""
    return """
        SELECT b.*, 
        (SELECT COUNT(*) FROM bookings bk 
         WHERE bk.bike_id = b.id 
         AND bk.status != 'cancelled' 
         AND %s BETWEEN bk.start_date AND bk.end_date) as is_booked_now 
        FROM bikes b
    """

def _check_booking_conflict(cursor, bike_id, start_date, end_date, exclude_booking_id=None):
    """Checks for overlapping confirmed bookings for a specific bike."""
    sql = """
        SELECT id FROM bookings 
        WHERE bike_id = %s 
        AND status != 'cancelled'
        AND (start_date <= %s AND end_date >= %s)
    """
    params = [bike_id, end_date, start_date]
    
    if exclude_booking_id:
        sql += " AND id != %s"
        params.append(exclude_booking_id)
        
    cursor.execute(sql, params)
    return cursor.fetchone()


# These are the main page views for the website
def contact(request):
    # This view handles the contact form and sends an email
    if request.method == "POST":
        n, e, ph, m = request.POST.get("rs_full_name"), request.POST.get("rs_email_address"), request.POST.get("rs_phone_number"), request.POST.get("rs_message_content")
        
        errors = False
        if not n:
            messages.error(request, "Please enter your full name.")
            errors = True
        if not e:
            messages.error(request, "Please enter your email address.")
            errors = True
        if not ph:
            messages.error(request, "Please enter your phone number.")
            errors = True
        if not m:
            messages.error(request, "Please enter your message.")
            errors = True

        # Email and Phone Regex Validation
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if e and not re.match(email_regex, e):
            messages.error(request, "Please enter a valid email address.")
            errors = True

        if ph and not re.match(r"^[0-9]{10}$", ph):
            messages.error(request, "Please enter a valid 10-digit phone number.")
            errors = True
            
        if errors:
            return redirect("contact")

        try:
            full_msg = f"Inquiry from: {n} <{e}>\nPhone: {ph}\n\nMessage:\n{m}"
            send_mail(f"Contact Inquiry from {n}", full_msg, settings.EMAIL_HOST_USER, [settings.EMAIL_HOST_USER])
            messages.success(request, "Message sent successfully!")
        except Exception: 
            messages.error(request, "Wait, something went wrong with the email.")
        return redirect("contact")
    return render(request, "accounts/contact.html")

def home(request):
    # This is the home page that shows featured bikes
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM bikes WHERE status = 'available' ORDER BY id DESC LIMIT 6")
        featured_bikes = dictfetchall(cursor)
        cursor.execute("SELECT category, MIN(image) as image FROM bikes GROUP BY category LIMIT 4")
        categories = dictfetchall(cursor)
    return render(request, "accounts/index.html", {"featured_bikes": featured_bikes, "categories": categories})

def bikes(request):
    # This page shows the list of all available bikes with filtering
    query, cat, sort, st_filter = request.GET.get('q', ''), request.GET.get('category', ''), request.GET.get('sort', 'id_desc'), request.GET.get('status', 'all')
    today = datetime.now().date()
    
    # Use centralized availability query
    sql = _get_bike_availability_sql() + " WHERE b.status != 'out_of_service'"
    params = [today]
    
    if query:
        sql += " AND (b.model LIKE %s OR b.description LIKE %s)"
        params.extend([f"%{query}%", f"%{query}%"])
    if cat and cat != 'all':
        sql += " AND b.category = %s"
        params.append(cat)
        
    if sort == 'price_asc': sql += " ORDER BY b.price_per_day ASC"
    elif sort == 'price_desc': sql += " ORDER BY b.price_per_day DESC"
    else: sql += " ORDER BY b.id DESC"
    
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        all_bikes = dictfetchall(cursor)
        cursor.execute("SELECT DISTINCT category FROM bikes")
        categories = [row[0] for row in cursor.fetchall()]
        
        # Determine current status and apply status filter
        filtered_bikes = []
        for b in all_bikes:
            if b['is_booked_now'] > 0: b['status'] = 'booked'
            
            # Simple filtering logic based on status
            if st_filter == 'available' and b['status'] != 'available': continue
            if st_filter == 'reserved' and b['status'] != 'booked': continue
            filtered_bikes.append(b)

        # Implementation of Pagination (9 bikes per page)
        paginator = Paginator(filtered_bikes, 9)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

    return render(request, "accounts/bikes.html", {
        "bikes": page_obj, "categories": categories, 
        "current_search": query, "current_category": cat, 
        "current_sort": sort, "current_status": st_filter
    })

def bike_detail(request, bike_id):
    # Shows the specific details of a single bike
    today = datetime.now().date()
    with connection.cursor() as cursor:
        # Use centralized availability query
        sql = _get_bike_availability_sql() + " WHERE b.id = %s"
        cursor.execute(sql, [today, bike_id])
        bike = dictfetchone(cursor)
    if not bike: return redirect("bikes")
    if bike['is_booked_now'] > 0: bike['status'] = 'booked'
    return render(request, "accounts/bike_detail.html", {"bike": bike})

def about(request):
    # A simple page explaining what our service is about
    return render(request, "accounts/about.html")


# Views to handle user authentication (Sign up, Login, Logout)
def register(request):
    # Handles new user registration
    if request.method == "POST":
        fname, e, ph, p1, p2 = request.POST.get("full_name"), request.POST.get("email"), request.POST.get("phone"), request.POST.get("password1"), request.POST.get("password2")
        
        errors = False
        if not fname:
            messages.error(request, "Full Name is required."); errors = True
        if not e:
            messages.error(request, "Email Address is required."); errors = True
        if not ph:
            messages.error(request, "Phone Number is required."); errors = True
        if not p1:
            messages.error(request, "Password is required."); errors = True

        # Validations
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if e and not re.match(email_regex, e):
            messages.error(request, "Please enter a valid email address."); errors = True

        if ph and not re.match(r"^[0-9]{10}$", ph):
            messages.error(request, "Please enter a valid 10-digit phone number."); errors = True
            
        if p1 and p2 and p1 != p2:
            messages.error(request, "Passwords do not match."); errors = True
            
        if errors: 
            return render(request, "accounts/register.html", {"values": request.POST})

        with connection.cursor() as cursor:
            # Check uniqueness for Email
            cursor.execute("SELECT id FROM users WHERE email = %s", [e])
            if cursor.fetchone():
                messages.error(request, "This email is already registered.")
                return render(request, "accounts/register.html", {"values": request.POST})
            
            # Save user info (username field removed from capture, setting it to email or null)
            cursor.execute("INSERT INTO users (email, password, full_name, phone) VALUES (%s, %s, %s, %s)", [e, hash_password(p1), fname, ph])
            
        messages.success(request, "Account created successfully. Please sign in.")
        return redirect("login")
    return render(request, "accounts/register.html")

def login(request):
    # Checks user credentials and starts a login session
    if request.method == "POST":
        e, p = request.POST.get("email"), request.POST.get("password")
        if not e or not p:
            messages.error(request, "Please provide both email and password.")
            return redirect("login")
            
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", [e, hash_password(p)])
            user = dictfetchone(cursor)
        if user:
            request.session["user_id"], request.session["user_name"], request.session["user_role"] = user["id"], user["full_name"], user["role"]
            return redirect("admin_dashboard" if user["role"] == "admin" else "profile")
        messages.error(request, "Invalid email or password.")
    return render(request, "accounts/login.html")

def profile(request):
    # This allows users to view and update their profile
    if "user_id" not in request.session: return redirect("login")
    uid = request.session["user_id"]
    
    if request.method == "POST":
        fname, e, ph = request.POST.get("full_name"), request.POST.get("email"), request.POST.get("phone")
        
        # Validations
        if not fname or not e or not ph:
            messages.error(request, "Name, Email, and Phone are required.")
            return redirect("profile")
            
        if ph and not re.match(r"^[0-9]{10}$", ph):
            messages.error(request, "Please enter a valid 10-digit phone number.")
            return redirect("profile")

        with connection.cursor() as cursor:
            # Check if email is taken by ANOTHER user
            cursor.execute("SELECT id FROM users WHERE email = %s AND id != %s", [e, uid])
            if cursor.fetchone():
                messages.error(request, "This email is already registered to another account.")
                return redirect("profile")
            # Update all details in single users table
            cursor.execute("UPDATE users SET email = %s, full_name = %s, phone = %s WHERE id = %s", [e, fname, ph, uid])
                
        messages.success(request, "Profile updated successfully.")
        return redirect("profile")

    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM users WHERE id = %s", [uid])
        user_info = dictfetchone(cursor)
    return render(request, "accounts/profile.html", {"user": user_info})

def logout(request):
    # Ends the user session and sends them back to the login page
    request.session.flush()
    return redirect("login")


# Views for booking bikes and managing documents
def book_bike(request, bike_id):
    if "user_id" not in request.session: return redirect("login")
    uid = request.session["user_id"]
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM bikes WHERE id = %s", [bike_id])
        bike_data = dictfetchone(cursor)
        cursor.execute("SELECT * FROM users WHERE id = %s", [uid])
        user_data = dictfetchone(cursor)
        
        # Check documents from separate table
        cursor.execute("SELECT doc_type FROM documents WHERE user_id = %s", [uid])
        docs = [row[0] for row in cursor.fetchall()]
    has_docs = 'license' in docs and 'id_card' in docs
    if request.method == "POST":
        sd, ed = request.POST.get("start_date"), request.POST.get("end_date")
        s, e = datetime.strptime(sd, "%Y-%m-%d").date(), datetime.strptime(ed, "%Y-%m-%d").date()
        days = (e - s).days + 1
        if days <= 0: return redirect("book_bike", bike_id=bike_id)
        if not has_docs:
            ph, ad = request.POST.get("phone"), request.POST.get("address")
            
            if ph and not re.match(r"^[0-9]{10}$", ph):
                messages.error(request, "Please enter a valid 10-digit phone number.")
                return redirect("book_bike", bike_id=bike_id)

            id_d, lic_d = request.FILES.get("id_document"), request.FILES.get("license_document")
            fs = FileSystemStorage(location='media/documents/')
            id_p, lic_p = f"documents/{fs.save(id_d.name, id_d)}", f"documents/{fs.save(lic_d.name, lic_d)}"
            with connection.cursor() as cursor:
                cursor.execute("UPDATE users SET phone=%s, address=%s WHERE id=%s", [ph, ad, uid])
                # Save docs to documents table
                cursor.execute("DELETE FROM documents WHERE user_id = %s", [uid]) # Clean start for fresh upload
                cursor.execute("INSERT INTO documents (user_id, doc_type, file_path) VALUES (%s, 'id_card', %s)", [uid, id_p])
                cursor.execute("INSERT INTO documents (user_id, doc_type, file_path) VALUES (%s, 'license', %s)", [uid, lic_p])
        with connection.cursor() as cursor:
            # Use centralized conflict helper
            if _check_booking_conflict(cursor, bike_id, s, e):
                messages.error(request, "Sorry, this bike is already booked for the selected dates. Please choose different dates or another bike.")
                return redirect("book_bike", bike_id=bike_id)

            cursor.execute("INSERT INTO bookings (user_id, bike_id, start_date, end_date, total_days, total_cost, status) VALUES (%s, %s, %s, %s, %s, %s, 'pending')", [uid, bike_id, s, e, days, days * float(bike_data["price_per_day"])])
            bid = cursor.lastrowid
            
            # ── Admin Email Alert
            try:
                ctx = {
                    'booking_id': bid, 'name': request.session["user_name"], 'email': "New Booking", 
                    'bike': bike_data['model'], 'amount': days * float(bike_data["price_per_day"]), 
                    'admin_url': request.build_absolute_uri('/admin-dashboard/')
                }
                html_msg = render_to_string('emails/admin_alert.html', ctx)
                email = EmailMultiAlternatives(f"New Booking Request: RS-{bid}", "New request on RideSathi.", settings.EMAIL_HOST_USER, [settings.EMAIL_HOST_USER])
                email.attach_alternative(html_msg, "text/html")
                email.send()
            except Exception: pass

        return redirect("my_bookings")
    return render(request, "accounts/book_bike.html", {"bike": bike_data, "user": user_data, "has_documents": has_docs})

def upload_document(request):
    # Allows users to upload their ID cards and licenses
    if "user_id" not in request.session: return redirect("login")
    uid = request.session["user_id"]
    
    if request.method == "POST":
        fs = FileSystemStorage(location='media/documents/')
        license_file = request.FILES.get("license_file")
        id_file = request.FILES.get("id_file")
        
        if not license_file and not id_file:
            messages.error(request, "Please select at least one document to upload.")
        else:
            with connection.cursor() as cursor:
                if license_file:
                    l_path = f"documents/{fs.save(license_file.name, license_file)}"
                    # Handle separate documents table
                    cursor.execute("SELECT id FROM documents WHERE user_id = %s AND doc_type = 'license'", [uid])
                    if cursor.fetchone():
                        cursor.execute("UPDATE documents SET file_path = %s WHERE user_id = %s AND doc_type = 'license'", [l_path, uid])
                    else:
                        cursor.execute("INSERT INTO documents (user_id, doc_type, file_path) VALUES (%s, 'license', %s)", [uid, l_path])
                
                if id_file:
                    i_path = f"documents/{fs.save(id_file.name, id_file)}"
                    cursor.execute("SELECT id FROM documents WHERE user_id = %s AND doc_type = 'id_card'", [uid])
                    if cursor.fetchone():
                        cursor.execute("UPDATE documents SET file_path = %s WHERE user_id = %s AND doc_type = 'id_card'", [i_path, uid])
                    else:
                        cursor.execute("INSERT INTO documents (user_id, doc_type, file_path) VALUES (%s, 'id_card', %s)", [uid, i_path])
            
            messages.success(request, "Documents uploaded successfully.")
        return redirect("upload_document")
    
    with connection.cursor() as cursor:
        cursor.execute("SELECT full_name FROM users WHERE id = %s", [uid])
        user_info = dictfetchone(cursor)
        
        # Pull document status from separate table
        cursor.execute("SELECT doc_type, file_path FROM documents WHERE user_id = %s", [uid])
        docs = {row[0]: row[1] for row in cursor.fetchall()}
        user_info['license_document'] = docs.get('license')
        user_info['id_document'] = docs.get('id_card')
    
    return render(request, "accounts/upload_document.html", {"user": user_info})

def my_bookings(request):
    # Shows a list of all bikes a user has booked
    if "user_id" not in request.session: return redirect("login")
    uid = request.session["user_id"]
    with connection.cursor() as cursor:
        # Join with bikes for details, and payments for Khalti status
        cursor.execute("""
            SELECT DISTINCT b.*, v.model, v.category, v.image, 
                   IFNULL(p.payment_status, 'unpaid') as payment_status
            FROM bookings b 
            JOIN bikes v ON b.bike_id = v.id 
            LEFT JOIN payments p ON b.id = p.booking_id
            WHERE b.user_id = %s 
            GROUP BY b.id
            ORDER BY b.created_at DESC
        """, [uid])
        bookings = dictfetchall(cursor)
        cursor.execute("SELECT full_name FROM users WHERE id = %s", [uid])
        user_info = dictfetchone(cursor)
    return render(request, "accounts/my_bookings.html", {"bookings": bookings, "user": user_info})


# Admin area to manage the entire system
def admin_dashboard(request):
    if not _is_admin(request): return redirect("home")
    with connection.cursor() as cursor:
        # Complex query to join bookings, users, bikes, AND separate documents/payments
        cursor.execute("""
            SELECT bk.*, u.full_name, b.model, b.category, u.phone,
                   (SELECT file_path FROM documents WHERE user_id = u.id AND doc_type = 'id_card' LIMIT 1) as id_document,
                   (SELECT file_path FROM documents WHERE user_id = u.id AND doc_type = 'license' LIMIT 1) as license_document
            FROM bookings bk 
            JOIN users u ON bk.user_id = u.id 
            JOIN bikes b ON bk.bike_id = b.id 
            ORDER BY bk.created_at DESC
        """)
        bk_list = dictfetchall(cursor)
        cursor.execute("SELECT COUNT(*), SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) FROM bookings")
        total, pend = cursor.fetchone()
        
        cursor.execute("SELECT SUM(total_cost) FROM bookings WHERE payment_status='paid'")
        rev = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM bikes")
        total_bikes = cursor.fetchone()[0]

        # Calculate "In Use" purely based on active confirmed bookings today
        today_date = datetime.now().strftime('%Y-%m-%d')
        cursor.execute("""
            SELECT COUNT(DISTINCT bike_id) FROM bookings 
            WHERE payment_status='paid' AND %s BETWEEN start_date AND end_date
        """, [today_date])
        rented = cursor.fetchone()[0]
        
        # Available = Total - In Use
        avail = total_bikes - rented

        cursor.execute("SELECT COUNT(*) FROM users WHERE role != 'admin'")
        u_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM bookings WHERE payment_status='paid'")
        p_count = cursor.fetchone()[0]

        cursor.execute("SELECT * FROM bikes ORDER BY id DESC")
        bikes_list_raw = dictfetchall(cursor)
        
        # Paginate bikes (8 per page)
        bike_paginator = Paginator(bikes_list_raw, 8)
        bike_page_num = request.GET.get('bike_page', 1)
        bikes_obj = bike_paginator.get_page(bike_page_num)
        
        cursor.execute("SELECT * FROM users WHERE role != 'admin' ORDER BY id DESC")
        users_list = dictfetchall(cursor)
        cursor.execute("SELECT b.category, COUNT(bk.id) as count FROM bookings bk JOIN bikes b ON bk.bike_id = b.id GROUP BY b.category")
        cat_stats = dictfetchall(cursor)
        
        cursor.execute("SELECT status, COUNT(*) as count FROM bookings GROUP BY status")
        st_stats = dictfetchall(cursor)
        # Fetch all formal invoices from the invoices table (As per ERD)
        cursor.execute("""
            SELECT i.*, u.full_name, b.model, p.amount, p.transaction_id
            FROM invoices i
            JOIN bookings bk ON i.booking_id = bk.id
            JOIN payments p ON i.payment_id = p.id
            JOIN users u ON bk.user_id = u.id
            JOIN bikes b ON bk.bike_id = b.id
            ORDER BY i.invoice_date DESC
        """)
        inv_list = dictfetchall(cursor)

        # Revenue Trend logic (Last 7 days)
        cursor.execute("""
            SELECT DATE(created_at) as date, SUM(total_cost) as total 
            FROM bookings 
            WHERE payment_status='paid' 
            GROUP BY DATE(created_at) 
            ORDER BY date ASC 
            LIMIT 7
        """)
        rev_trend = dictfetchall(cursor)
        # Convert date and Decimal objects for JSON serialization
        from decimal import Decimal
        for r in rev_trend:
            if r.get('date'):
                r['date'] = r['date'].strftime('%Y-%m-%d')
            if isinstance(r.get('total'), Decimal):
                r['total'] = float(r['total'])

        cursor.execute("SELECT * FROM categories ORDER BY name ASC")
        cat_list = dictfetchall(cursor)

        # Get documents for all users (not just booking-linked)
        cursor.execute("""
            SELECT u.id, u.full_name, u.email,
                   (SELECT file_path FROM documents WHERE user_id = u.id AND doc_type = 'id_card' LIMIT 1) as id_document,
                   (SELECT file_path FROM documents WHERE user_id = u.id AND doc_type = 'license' LIMIT 1) as license_document
            FROM users u
            WHERE (SELECT COUNT(*) FROM documents WHERE user_id = u.id) > 0
            ORDER BY u.full_name ASC
        """)
        all_user_docs = dictfetchall(cursor)

    return render(request, "accounts/admin_dashboard.html", {
        "bookings": bk_list, 
        "total_bookings_count": total, 
        "pending_count": pend, 
        "total_revenue": rev, 
        "total_bikes_count": total_bikes,
        "available_bikes_count": avail,
        "rented_bikes_count": rented,
        "total_users_count": u_count,
        "completed_payments_count": p_count,
        "bikes": bikes_obj, 
        "users": users_list, 
        "invoices": inv_list, 
        "categories": cat_list,
        "rev_trend": rev_trend,
        "cat_stats": cat_stats,
        "st_stats": st_stats,
        "category_stats": cat_stats,
        "status_stats": st_stats,
        "user_documents": all_user_docs,
        "category_stats_json": json.dumps(cat_stats), 
        "status_stats_json": json.dumps(st_stats),
        "revenue_trend_json": json.dumps(rev_trend)
    })

def add_bike(request):
    # Admin tool to add a new bike to the system
    if request.method == "POST" and _is_admin(request):
        m, c, p = request.POST.get("model"), request.POST.get("category"), request.POST.get("price_per_day")
        im = request.FILES.get("image")
        path = f"bikes/{FileSystemStorage(location='media/bikes/').save(im.name, im)}" if im else ""
        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO bikes (model, category, price_per_day, image, status) VALUES (%s, %s, %s, %s, 'available')", [m, c, p, path])
    return redirect("admin_dashboard")

def update_booking_date(request, booking_id):
    # Admin tool to manually change a booking date (for defense/testing)
    if request.method == "POST" and _is_admin(request):
        new_date = request.POST.get("created_at")
        if new_date:
            with connection.cursor() as cursor:
                # Get bike_id first
                cursor.execute("SELECT bike_id FROM bookings WHERE id = %s", [booking_id])
                row = cursor.fetchone()
                if row:
                    bike_id = row[0]
                    # Use centralized conflict helper
                    if _check_booking_conflict(cursor, bike_id, new_date, new_date, exclude_booking_id=booking_id):
                        messages.error(request, f"Conflict: Bike is already booked on {new_date}.")
                        return redirect("admin_dashboard")

                # Update created_at (for revenue charts) and start_date
                cursor.execute("""
                    UPDATE bookings 
                    SET created_at = %s, start_date = DATE(%s)
                    WHERE id = %s
                """, [new_date, new_date, booking_id])
                
                # Also update associated payment/invoice dates to keep data consistent
                cursor.execute("UPDATE payments SET created_at = %s WHERE booking_id = %s", [new_date, booking_id])
                cursor.execute("UPDATE invoices SET invoice_date = DATE(%s) WHERE booking_id = %s", [new_date, booking_id])
                
            messages.success(request, f"Booking #{booking_id} date updated successfully.")
    return redirect("admin_dashboard")

def edit_bike(request, bike_id):
    # Admin tool to update the details of an existing bike
    if request.method == "POST" and _is_admin(request):
        m, c, p, s = request.POST.get("model"), request.POST.get("category"), request.POST.get("price_per_day"), request.POST.get("status")
        im = request.FILES.get("image")
        with connection.cursor() as cursor:
            if im:
                path = f"bikes/{FileSystemStorage(location='media/bikes/').save(im.name, im)}"
                cursor.execute("UPDATE bikes SET model=%s, category=%s, price_per_day=%s, status=%s, image=%s WHERE id=%s", [m, c, p, s, path, bike_id])
            else:
                cursor.execute("UPDATE bikes SET model=%s, category=%s, price_per_day=%s, status=%s WHERE id=%s", [m, c, p, s, bike_id])
    return redirect("admin_dashboard")

def delete_bike(request, bike_id):
    # Admin tool to remove a bike from the system
    if _is_admin(request):
        with connection.cursor() as cursor: cursor.execute("DELETE FROM bikes WHERE id = %s", [bike_id])
    return redirect("admin_dashboard")

def confirm_booking(request, booking_id, action):
    # The admin uses this to either confirm or cancel a booking request
    if not _is_admin(request): return redirect("home")
    st = 'confirmed' if action == 'confirm' else 'cancelled'
    
    with connection.cursor() as cursor:
        if st == 'confirmed':
            # ── Final safety check before confirming: prevent double-booking
            cursor.execute("SELECT bike_id, start_date, end_date FROM bookings WHERE id = %s", [booking_id])
            target = cursor.fetchone()
            if target:
                bid, s, e = target
                # Use centralized conflict helper 
                # (Note: we check for 'confirmed' specifically for admin overrides if needed, 
                # but helper uses '!= cancelled' by default which is safer)
                if _check_booking_conflict(cursor, bid, s, e, exclude_booking_id=booking_id):
                    messages.error(request, f"Error: This bike is already confirmed for another user during these dates. You cannot confirm booking #{booking_id}.")
                    return redirect("admin_dashboard")

        # Fetch booking/user info for the email notification
        cursor.execute("""
            SELECT u.full_name, u.email, b.model, bk.start_date, bk.end_date, bk.total_cost 
            FROM bookings bk 
            JOIN users u ON bk.user_id = u.id 
            JOIN bikes b ON bk.bike_id = b.id 
            WHERE bk.id = %s
        """, [booking_id])
        bk = dictfetchone(cursor)
        
        # Actually update the status
        cursor.execute("UPDATE bookings SET status = %s WHERE id = %s", [st, booking_id])

    # ── Notification Email logic continues...
    if bk:
            try:
                ctx = {
                    'name': bk['full_name'], 'bike': bk['model'], 'booking_id': booking_id, 
                    'status': st, 'start_date': bk['start_date'], 'end_date': bk['end_date'],
                    'amount': bk['total_cost'],
                    'dashboard_url': request.build_absolute_uri('/my-bookings/'),
                    'contact_url': request.build_absolute_uri('/contact/')
                }
                html_msg = render_to_string('emails/booking_update.html', ctx)
                subj = f"Update on your booking #{booking_id}"
                
                text_msg = f"Hi {bk['full_name']},\n\nYour booking for {bk['model']} has been {st}.\n\nRideSathi Team"
                email = EmailMultiAlternatives(subj, text_msg, settings.EMAIL_HOST_USER, [bk['email']])
                email.attach_alternative(html_msg, "text/html")
                
                # Attach PDF if confirmed
                if st == 'confirmed':
                    buffer, bk_info = get_invoice_pdf_buffer(booking_id)
                    if buffer:
                        email.attach(f"Invoice_{booking_id}.pdf", buffer.getvalue(), "application/pdf")
                
                email.send()
            except Exception: pass

    return redirect("admin_dashboard")

# Views for processing Khalti payments
def initiate_payment(request, booking_id):
    # Starts the payment process with Khalti for a confirmed booking
    if "user_id" not in request.session: return redirect("login")
    with connection.cursor() as cursor:
        cursor.execute("SELECT bk.*, b.model FROM bookings bk JOIN bikes b ON bk.bike_id = b.id WHERE bk.id = %s AND bk.user_id = %s", [booking_id, request.session["user_id"]])
        bk = dictfetchone(cursor)
    
    if not bk or bk["status"] != "confirmed": 
        return redirect("my_bookings")
        
    payload = {
        "return_url": request.build_absolute_uri(f"/payment/verify/?booking_id={booking_id}"),
        "website_url": request.build_absolute_uri("/"), "amount": int(float(bk["total_cost"]) * 100),
        "purchase_order_id": f"RS-{booking_id}", "purchase_order_name": f"Rental-{bk['model']}", "customer_info": {"name": request.session["user_name"]}
    }
    headers = {"Authorization": f"Key {settings.KHALTI_SECRET_KEY}", "Content-Type": "application/json"}
    
    try:
        res = requests.post(settings.KHALTI_INITIATE_URL, json=payload, headers=headers)
        if res.status_code == 200: 
            return redirect(res.json()["payment_url"])
        else:
            messages.error(request, f"Khalti Error: {res.text}")
    except Exception as e:
        messages.error(request, f"Payment connection failed: {str(e)}")
    return redirect("my_bookings")

def verify_payment(request):
    # Verifies the Khalti payment and creates an invoice if successful
    pidx, bid = request.GET.get("pidx"), request.GET.get("booking_id")
    if pidx and bid:
        headers = {"Authorization": f"Key {settings.KHALTI_SECRET_KEY}", "Content-Type": "application/json"}
        res = requests.post(settings.KHALTI_LOOKUP_URL, json={"pidx": pidx}, headers=headers)
        if res.status_code == 200 and res.json().get("status") == "Completed":
            with connection.cursor() as cursor: 
                # Update Booking
                cursor.execute("UPDATE bookings SET payment_status = 'paid', transaction_id = %s WHERE id = %s", [pidx, bid])
                # Record in separate PAYMENTS table
                cursor.execute("SELECT user_id, total_cost FROM bookings WHERE id = %s", [bid])
                bk_tmp = cursor.fetchone()
                cursor.execute("INSERT INTO payments (booking_id, user_id, amount, payment_method, payment_status, transaction_id) VALUES (%s, %s, %s, 'Khalti', 'paid', %s)", [bid, bk_tmp[0], bk_tmp[1], pidx])
                pay_id = cursor.lastrowid
                # Record in separate INVOICES table (NEW as per ERD)
                cursor.execute("INSERT INTO invoices (booking_id, payment_id) VALUES (%s, %s)", [bid, pay_id])
            return redirect("payment_success", booking_id=bid)
    return redirect("my_bookings")

def get_invoice_pdf_buffer(booking_id):
    # Generates a PDF invoice for a specific booking
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT b.*, v.model, v.category, v.price_per_day, u.full_name, u.email, u.phone, u.address,
                   IFNULL(p.payment_status, 'unpaid') as payment_status,
                   p.transaction_id, p.payment_date as paid_at
            FROM bookings b
            JOIN bikes v ON b.bike_id = v.id
            JOIN users u ON b.user_id = u.id
            LEFT JOIN payments p ON b.id = p.booking_id
            WHERE b.id = %s
        """, [booking_id])
        bk = dictfetchone(cursor)
    if not bk: return None, None

    # Initialize PDF
    pdf = FPDF()
    pdf.add_page()
    
    # ─── HEADER ───
    logo_path = os.path.join(settings.BASE_DIR, 'static/assets/image/Logo.webp')
    if os.path.exists(logo_path):
        # Logo on the left
        pdf.image(logo_path, 10, 8, 25)
        
        # Dual-tone Brand Name next to logo
        pdf.set_font("helvetica", "B", 20)
        pdf.set_xy(37, 16)
        
        # "Ride" in Red
        pdf.set_text_color(196, 22, 28)
        pdf.cell(pdf.get_string_width("Ride") + 1, 10, "Ride")
        
        # "Sathi" in Black
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, "Sathi")
    else:
        # Fallback if logo missing
        pdf.set_font("helvetica", "B", 24)
        pdf.set_xy(10, 15)
        pdf.set_text_color(196, 22, 28)
        pdf.cell(pdf.get_string_width("Ride") + 1, 10, "Ride")
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, "Sathi")
    
    pdf.set_font("helvetica", "B", 22)
    pdf.set_text_color(0, 0, 0)
    pdf.set_xy(140, 10)
    pdf.cell(60, 12, "INVOICE", ln=1, align="R")
    
    pdf.ln(15)
    pdf.set_draw_color(220, 220, 220)
    pdf.line(10, 35, 200, 35)
    
    # ─── INFORMATION ───
    pdf.ln(10)
    pdf.set_font("helvetica", "B", 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(95, 7, "BILL TO:")
    pdf.cell(0, 7, "INVOICE DETAILS:", ln=1)
    
    addr, ph = bk.get('address') or 'N/A', bk.get('phone') or 'N/A'
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    
    cur_y = pdf.get_y()
    pdf.set_font("helvetica", "B", 10); pdf.set_text_color(0, 0, 0)
    pdf.multi_cell(95, 6, bk['full_name'].upper())
    pdf.set_font("helvetica", "", 10); pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(95, 5, f"{bk['email']}\n{ph}\n{addr}")
    
    pdf.set_xy(110, cur_y)
    pdf.set_font("helvetica", "B", 10); pdf.set_text_color(0, 0, 0)
    pdf.cell(90, 6, f"Invoice #: {bk['id']}", ln=1, align="R")
    pdf.set_font("helvetica", "", 10); pdf.set_text_color(80, 80, 80)
    pdf.set_x(110)
    pdf.cell(90, 5, f"Date: {datetime.now().strftime('%d %b, %Y')}", ln=1, align="R")
    pdf.set_x(110)
    pdf.cell(90, 5, f"Period: {bk['start_date']} to {bk['end_date']}", ln=1, align="R")
    
    # ─── TABLE ───
    pdf.ln(20)
    
    # Table Header
    pdf.set_fill_color(196, 22, 28)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(100, 10, " Description", fill=True)
    pdf.cell(30, 10, " Days", fill=True, align="C")
    pdf.cell(30, 10, " Rate", fill=True, align="C")
    pdf.cell(30, 10, " Amount", fill=True, align="R", ln=1)
    
    # Table Row
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("helvetica", "", 10)
    pdf.cell(100, 12, f" {bk['model']} Rental ({bk['category']})", border="B")
    pdf.cell(30, 12, f" {bk['total_days']}", border="B", align="C")
    pdf.cell(30, 12, f" Rs. {float(bk['price_per_day']):.2f}", border="B", align="C")
    pdf.cell(30, 12, f" Rs. {float(bk['total_cost']):.2f}", border="B", align="R", ln=1)
    
    # ─── SUMMARY ───
    pdf.ln(10)
    pdf.set_x(130)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(40, 10, "Total Amount:")
    pdf.set_text_color(196, 22, 28)
    pdf.cell(0, 10, f"Rs. {float(bk['total_cost']):.2f} ", ln=1, align="R")
    
    # ─── FOOTER ───
    pdf.set_y(-35)
    pdf.set_font("helvetica", "I", 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 10, "Thank you for riding with RideSathi!", align="C", ln=1)
    pdf.set_font("helvetica", "", 8)
    pdf.cell(0, 5, "RideSathi Rentals | Lakeside, Pokhara", align="C")

    buffer = io.BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer, bk

def download_invoice(request, booking_id):
    # Allows users to download their PDF invoice
    if "user_id" not in request.session: return redirect("login")
    buffer, bk = get_invoice_pdf_buffer(booking_id)
    if not buffer: return redirect("my_bookings")
    return FileResponse(buffer, as_attachment=True, filename=f"Invoice_{booking_id}.pdf", content_type='application/pdf')

def payment_success(request, booking_id):
    # This is shown when a payment is successful and sends the invoice
    with connection.cursor() as cursor:
        cursor.execute("SELECT bk.*, b.model, b.category, b.image FROM bookings bk JOIN bikes b ON bk.bike_id = b.id WHERE bk.id = %s", [booking_id])
        bk = dictfetchone(cursor)

    # ── HTML Email with PDF Attachment
    buffer, bk_info = get_invoice_pdf_buffer(booking_id)
    if buffer:
        try:
            ctx = {
                'name': bk_info['full_name'], 'bike': bk_info['model'], 'booking_id': booking_id, 
                'amount': bk_info['total_cost'], 'date': datetime.now().strftime('%d %b, %Y'),
                'dashboard_url': request.build_absolute_uri('/my-bookings/')
            }
            html_msg = render_to_string('emails/payment_received.html', ctx)
            subj = f"Payment Successful - RideSathi Invoice #{booking_id}"
            
            text_msg = f"Hi {bk_info['full_name']},\n\nThank you! Your payment for {bk_info['model']} is received. Please find your invoice attached.\n\nRideSathi Team"
            
            # Send to BOTH the customer and the admin
            email = EmailMultiAlternatives(subj, text_msg, settings.EMAIL_HOST_USER, [bk_info['email'], settings.EMAIL_HOST_USER])
            email.attach_alternative(html_msg, "text/html")
            email.attach(f"Invoice_{booking_id}.pdf", buffer.getvalue(), "application/pdf")
            email.send()
        except Exception: pass

    return render(request, "accounts/payment_success.html", {"booking": bk})
def add_category(request):
    if request.method == "POST" and _is_admin(request):
        name = request.POST.get("name")
        desc = request.POST.get("description", "")
        if name:
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO categories (name, description) VALUES (%s, %s)", [name, desc])
            messages.success(request, f"Category '{name}' added successfully!")
    return redirect("/admin-dashboard/?tab=categories")

def delete_category(request, category_id):
    if _is_admin(request):
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM categories WHERE id = %s", [category_id])
        messages.success(request, "Category removed successfully!")
    return redirect("/admin-dashboard/?tab=categories")

def delete_user(request, user_id):
    # Admin tool to completely remove a user and all their linked data
    if _is_admin(request):
        with connection.cursor() as cursor:
            # Delete in order of constraints: Invoices -> Payments -> Bookings -> Documents -> User
            cursor.execute("DELETE FROM invoices WHERE booking_id IN (SELECT id FROM bookings WHERE user_id = %s)", [user_id])
            cursor.execute("DELETE FROM payments WHERE user_id = %s", [user_id])
            cursor.execute("DELETE FROM bookings WHERE user_id = %s", [user_id])
            cursor.execute("DELETE FROM documents WHERE user_id = %s", [user_id])
            cursor.execute("DELETE FROM users WHERE id = %s AND role != 'admin'", [user_id])
            
        messages.success(request, "User and all associated records have been permanently deleted.")
    return redirect("admin_dashboard")
