from django.urls import path
from . import views

# URL patterns for the account app
urlpatterns = [
    # General website pages
    path("",               views.home,        name="home"),
    path("bikes/",         views.bikes,       name="bikes"),
    path("bikes/<int:bike_id>/", views.bike_detail, name="bike_detail"),
    path("about/",         views.about,       name="about"),
    path("contact/",       views.contact,     name="contact"),
    
    # User authentication
    path("login/",         views.login,       name="login"),
    path("register/",      views.register,    name="register"),
    path("profile/",       views.profile,     name="profile"),
    path("logout/",        views.logout,      name="logout"),
    
    # Booking and documents
    path("book/<int:bike_id>/", views.book_bike, name="book_bike"),
    path("upload-document/", views.upload_document, name="upload_document"),
    path("my-bookings/",   views.my_bookings, name="my_bookings"),
    
    # Administration tools
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("add-bike/", views.add_bike, name="add_bike"),
    path("edit-bike/<int:bike_id>/", views.edit_bike, name="edit_bike"),
    path("delete-bike/<int:bike_id>/", views.delete_bike, name="delete_bike"),
    path("confirm-booking/<int:booking_id>/<str:action>/", views.confirm_booking, name="confirm_booking"),
    path("update-booking-date/<int:booking_id>/", views.update_booking_date, name="update_booking_date"),
    path("add-category/", views.add_category, name="add_category"),
    path("delete-category/<int:category_id>/", views.delete_category, name="delete_category"),
    path("delete-user/<int:user_id>/", views.delete_user, name="delete_user"),
    
    # Payments and invoices
    path("pay/<int:booking_id>/", views.initiate_payment, name="initiate_payment"),
    path("payment/verify/", views.verify_payment, name="verify_payment"),
    path("payment/success/<int:booking_id>/", views.payment_success, name="payment_success"),
    path("invoice/<int:booking_id>/", views.download_invoice, name="download_invoice"),
]