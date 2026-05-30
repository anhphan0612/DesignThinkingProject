from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import StudentProfile, User


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        user.role = User.Role.STUDENT
        user.full_name = data.get("name") or data.get("email") or "Student"
        return user

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        user.role = User.Role.STUDENT
        if not user.full_name:
            user.full_name = user.email
            user.save(update_fields=("role", "full_name"))
        else:
            user.save(update_fields=("role",))
        StudentProfile.objects.get_or_create(user=user)
        return user

