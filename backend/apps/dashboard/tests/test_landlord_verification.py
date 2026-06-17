from uuid import uuid4

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import LandlordProfile, User


class LandlordVerificationDashboardTests(TestCase):
    def unique_email(self, prefix):
        return f"{prefix}-{uuid4().hex[:8]}@example.com"

    def create_landlord(self):
        user = User.objects.create_user(
            email=self.unique_email("landlord"),
            password="password-123",
            full_name="Landlord",
            role=User.Role.LANDLORD,
        )
        profile = LandlordProfile.objects.create(user=user)
        return user, profile

    def test_landlord_can_submit_verification_profile(self):
        user, profile = self.create_landlord()
        self.client.force_login(user)

        response = self.client.post(
            reverse("landlord-verification"),
            {
                "business_name": "Rentify Rooms",
                "identity_number": "0123456789",
            },
        )

        self.assertRedirects(response, reverse("landlord-dashboard"))
        profile.refresh_from_db()
        self.assertEqual(profile.verification_status, LandlordProfile.VerificationStatus.PENDING)
        self.assertEqual(profile.business_name, "Rentify Rooms")
        self.assertEqual(profile.identity_number, "0123456789")

    def test_staff_can_approve_pending_landlord(self):
        _, profile = self.create_landlord()
        profile.verification_status = LandlordProfile.VerificationStatus.PENDING
        profile.save(update_fields=("verification_status",))
        admin = User.objects.create_superuser(
            email=self.unique_email("admin"),
            password="password-123",
            full_name="Admin",
            role=User.Role.ADMIN,
        )
        self.client.force_login(admin)

        response = self.client.post(reverse("moderation-landlord-approve", args=[profile.id]))

        self.assertRedirects(response, reverse("moderation-dashboard"))
        profile.refresh_from_db()
        self.assertEqual(profile.verification_status, LandlordProfile.VerificationStatus.APPROVED)
        self.assertIsNotNone(profile.verified_at)

    def test_staff_can_reject_pending_landlord_with_note(self):
        _, profile = self.create_landlord()
        profile.verification_status = LandlordProfile.VerificationStatus.PENDING
        profile.save(update_fields=("verification_status",))
        admin = User.objects.create_superuser(
            email=self.unique_email("admin"),
            password="password-123",
            full_name="Admin",
            role=User.Role.ADMIN,
        )
        self.client.force_login(admin)

        response = self.client.post(
            reverse("moderation-landlord-reject", args=[profile.id]),
            {"verification_note": "Thiếu giấy tờ xác minh."},
        )

        self.assertRedirects(response, reverse("moderation-dashboard"))
        profile.refresh_from_db()
        self.assertEqual(profile.verification_status, LandlordProfile.VerificationStatus.REJECTED)
        self.assertEqual(profile.verification_note, "Thiếu giấy tờ xác minh.")
