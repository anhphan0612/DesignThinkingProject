from django.contrib.auth import views as auth_views
from django.urls import path
from django.urls import reverse_lazy

from .views import web_login, web_logout, web_preferences_onboarding, web_profile, web_register


urlpatterns = [
    path("login/", web_login, name="web-login"),
    path("register/", web_register, name="web-register"),
    path("preferences/", web_preferences_onboarding, name="web-preferences-onboarding"),
    path(
        "password/change/",
        auth_views.PasswordChangeView.as_view(
            template_name="accounts/password_change.html",
            success_url=reverse_lazy("password-change-done"),
        ),
        name="password-change",
    ),
    path(
        "password/change/done/",
        auth_views.PasswordChangeDoneView.as_view(template_name="accounts/password_change_done.html"),
        name="password-change-done",
    ),
    path(
        "password/reset/",
        auth_views.PasswordResetView.as_view(
            template_name="accounts/password_reset.html",
            email_template_name="accounts/password_reset_email.txt",
            subject_template_name="accounts/password_reset_subject.txt",
            success_url=reverse_lazy("password-reset-done"),
        ),
        name="password-reset",
    ),
    path(
        "password/reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="accounts/password_reset_done.html"),
        name="password-reset-done",
    ),
    path(
        "password/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url=reverse_lazy("password-reset-complete"),
        ),
        name="password-reset-confirm",
    ),
    path(
        "password/reset/complete/",
        auth_views.PasswordResetCompleteView.as_view(template_name="accounts/password_reset_complete.html"),
        name="password-reset-complete",
    ),
    path("logout/", web_logout, name="web-logout"),
    path("profile/", web_profile, name="web-profile"),
]
