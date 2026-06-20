from uuid import uuid4

from django.core import mail
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import LandlordProfile, StudentProfile, User


class WebAuthRoleFlowTests(TestCase):
    def unique_email(self, prefix):
        return f"{prefix}-{uuid4().hex[:8]}@example.com"

    def test_student_login_redirects_to_room_search(self):
        user = User.objects.create_user(
            email=self.unique_email("student"),
            password="password-123",
            full_name="Student",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=user)

        response = self.client.post(
            reverse("web-login"),
            {"email": user.email, "password": "password-123"},
        )

        self.assertRedirects(response, reverse("room-search"))

    def test_landlord_login_redirects_to_landlord_dashboard(self):
        user = User.objects.create_user(
            email=self.unique_email("landlord"),
            password="password-123",
            full_name="Landlord",
            role=User.Role.LANDLORD,
        )
        LandlordProfile.objects.create(user=user)

        response = self.client.post(
            reverse("web-login"),
            {"email": user.email, "password": "password-123"},
        )

        self.assertRedirects(response, reverse("landlord-dashboard"))

    def test_landlord_register_tab_creates_landlord_account(self):
        response = self.client.post(
            f"{reverse('web-register')}?role=landlord",
            {
                "full_name": "New Landlord",
                "email": self.unique_email("new-landlord"),
                "phone": "0900000000",
                "role": User.Role.LANDLORD,
                "password1": "password-123",
                "password2": "password-123",
            },
        )

        self.assertRedirects(response, reverse("landlord-dashboard"))
        user = User.objects.latest("id")
        self.assertEqual(user.role, User.Role.LANDLORD)
        self.assertTrue(LandlordProfile.objects.filter(user=user).exists())

    def test_student_register_redirects_to_preferences_onboarding(self):
        response = self.client.post(
            f"{reverse('web-register')}?role=student",
            {
                "full_name": "New Student",
                "email": self.unique_email("new-student"),
                "phone": "0900000001",
                "role": User.Role.STUDENT,
                "password1": "password-123",
                "password2": "password-123",
            },
        )

        self.assertRedirects(response, reverse("web-preferences-onboarding"))
        user = User.objects.latest("id")
        self.assertEqual(user.role, User.Role.STUDENT)
        self.assertTrue(StudentProfile.objects.filter(user=user).exists())

    def test_student_preferences_onboarding_saves_and_redirects_to_search(self):
        user = User.objects.create_user(
            email=self.unique_email("student"),
            password="password-123",
            full_name="Student",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=user)
        self.client.force_login(user)

        response = self.client.post(
            reverse("web-preferences-onboarding"),
            {
                "student_code": "SV001",
                "budget_min": "1500000",
                "budget_max": "3000000",
                "max_distance_km": "5",
                "gender": "unknown",
                "move_in_date": "",
                "preferred_districts": [],
                "lifestyle_tags": [],
            },
        )

        self.assertRedirects(response, reverse("room-search"))
        user.student_profile.refresh_from_db()
        self.assertEqual(user.student_profile.student_code, "SV001")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_password_reset_sends_email_for_existing_account(self):
        user = User.objects.create_user(
            email=self.unique_email("reset"),
            password="password-123",
            full_name="Reset User",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=user)

        response = self.client.post(reverse("password-reset"), {"email": user.email})

        self.assertRedirects(response, reverse("password-reset-done"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(user.email, mail.outbox[0].to)

    def test_authenticated_user_can_change_password(self):
        user = User.objects.create_user(
            email=self.unique_email("change"),
            password="password-123",
            full_name="Change User",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=user)
        self.client.force_login(user)

        response = self.client.post(
            reverse("password-change"),
            {
                "old_password": "password-123",
                "new_password1": "new-password-456",
                "new_password2": "new-password-456",
            },
        )

        self.assertRedirects(response, reverse("password-change-done"))
        user.refresh_from_db()
        self.assertTrue(user.check_password("new-password-456"))
