from uuid import uuid4

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

    def test_landlord_login_redirects_to_landlord_home(self):
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

        self.assertRedirects(response, reverse("landlord-home"))

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

        self.assertRedirects(response, reverse("landlord-home"))
        user = User.objects.latest("id")
        self.assertEqual(user.role, User.Role.LANDLORD)
        self.assertTrue(LandlordProfile.objects.filter(user=user).exists())
