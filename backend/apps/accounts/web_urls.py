from django.urls import path

from .views import web_login, web_logout, web_profile, web_register


urlpatterns = [
    path("login/", web_login, name="web-login"),
    path("register/", web_register, name="web-register"),
    path("logout/", web_logout, name="web-logout"),
    path("profile/", web_profile, name="web-profile"),
]
