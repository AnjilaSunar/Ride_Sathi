from django.shortcuts import render, redirect
from django.contrib.auth.models import User 
from django.contrib.auth import authenticate, login as auth_login
from django.contrib import messages


# Home page
def home(request):
    return render(request, "accounts/index.html")


# Bikes page
def bikes(request):
    return render(request, "accounts/bikes.html")


# About page
def about(request):
    return render(request, "accounts/about.html")


# Login page
def login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect("home")
        else:
            messages.error(request, "Invalid username or password.")
            return render(request, "accounts/login.html")

    return render(request, "accounts/login.html")


# Register page
def register(request):
    
    if request.method == "POST": 
        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect("register")
        

        User.objects.create_user(
            username=username,
            email=email,
            password=password1
        )

        messages.success(request, "Account created successfully! Please login.")
        return redirect("login")

    return render(request, "accounts/register.html")
