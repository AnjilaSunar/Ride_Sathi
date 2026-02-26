from django.urls import path
from . import views

urlpatterns = [
    path("",               views.home,        name="home"),
    path("bikes/",         views.bikes,       name="bikes"),
    path("bikes/<int:bike_id>/", views.bike_detail, name="bike_detail"),  # NEW: bike detail
    path("about/",         views.about,       name="about"),
    path("login/",         views.login,       name="login"),
    path("register/",      views.register,    name="register"),
    path("logout/",        views.logout,      name="logout"),
]
