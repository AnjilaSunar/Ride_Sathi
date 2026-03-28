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
    path("book/<int:bike_id>/", views.book_bike, name="book_bike"),
    path("upload-document/", views.upload_document, name="upload_document"),
    path("payment/<int:booking_id>/", views.payment, name="payment"), # NEW
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
]
