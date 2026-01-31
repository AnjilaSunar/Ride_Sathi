from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("bikes/", views.bikes, name="bikes"),
    path("about/", views.about, name="about"),
    path("login/", views.login, name="login"),
    path("register/", views.register, name="register"),
]
