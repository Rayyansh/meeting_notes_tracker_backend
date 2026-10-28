from django.urls import path

from tracker_apps.authentication.controllers.user import UserViewController

urlpatterns = [
    path("register/", UserViewController.register, name="register"),
    path("login/", UserViewController.login, name="login"),
    path("logout/", UserViewController.logout, name="logout"),
    path("token/refresh/", UserViewController.token_refresh, name="token_refresh"),
    path("me/", UserViewController.me, name="me"),
]
