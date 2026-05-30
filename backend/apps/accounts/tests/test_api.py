from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import StudentProfile, User


class RegistrationAPITests(APITestCase):
    def test_student_registration_creates_profile(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "student@example.com",
                "password": "a-valid-password",
                "full_name": "Student Test",
                "role": User.Role.STUDENT,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="student@example.com")
        self.assertTrue(StudentProfile.objects.filter(user=user).exists())
        self.assertNotEqual(user.password, "a-valid-password")

    def test_public_registration_rejects_admin_role(self):
        response = self.client.post(
            "/api/auth/register/",
            {
                "email": "admin@example.com",
                "password": "a-valid-password",
                "full_name": "Admin Test",
                "role": User.Role.ADMIN,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

