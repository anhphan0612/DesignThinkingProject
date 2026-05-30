from django.urls import path

from .views import LoginAPIView, MeAPIView, RegisterAPIView, StudentPreferenceAPIView


urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("me/", MeAPIView.as_view(), name="me"),
    path("student-preferences/", StudentPreferenceAPIView.as_view(), name="student-preferences"),
]
