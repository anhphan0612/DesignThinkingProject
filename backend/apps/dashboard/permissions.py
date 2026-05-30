from django.contrib.auth.decorators import user_passes_test

from apps.accounts.models import User


def landlord_required(view_func):
    return user_passes_test(
        lambda user: user.is_authenticated and user.role == User.Role.LANDLORD and hasattr(user, "landlord_profile"),
        login_url="web-login",
    )(view_func)


def staff_required(view_func):
    return user_passes_test(
        lambda user: user.is_authenticated and user.is_staff,
        login_url="web-login",
    )(view_func)

