from django.test import TestCase
from django.urls import reverse
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient

from apps.accounts.models import LandlordProfile, StudentProfile, User
from apps.interactions.models import ChatMessage, ChatThread, ContactRequest, ContentReport
from apps.listings.models import Room
from apps.locations.models import District, Ward


class ContentReportApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="student-report@example.com",
            password="password-123",
            full_name="Student",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=self.user)
        landlord = User.objects.create_user(
            email="landlord-report@example.com",
            password="password-123",
            full_name="Landlord",
            role=User.Role.LANDLORD,
        )
        profile = LandlordProfile.objects.create(user=landlord)
        district = District.objects.create(name="Quận 1", code="q1-report")
        ward = Ward.objects.create(name="Phường Bến Nghé", code="bn-report", district=district)
        self.room = Room.objects.create(
            landlord=profile,
            ward=ward,
            title="Phòng cần báo cáo",
            description="",
            address="12 Lê Lợi",
            location=Point(106.7, 10.77, srid=4326),
            location_status=Room.LocationStatus.GEOCODED,
            price=2500000,
            area=20,
            max_occupants=2,
            status=Room.Status.ACTIVE,
        )
        self.client = APIClient()

    def test_guest_can_report_room(self):
        response = self.client.post(
            reverse("report-list"),
            {
                "target_type": ContentReport.TargetType.ROOM,
                "room": self.room.id,
                "reason": "Thông tin sai",
                "details": "Giá không khớp",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(ContentReport.objects.count(), 1)

    def test_room_contact_creates_request_and_does_not_return_phone(self):
        self.client.force_authenticate(self.user)

        response = self.client.post(
            reverse("room-contact", args=[self.room.id]),
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("phone", response.data)
        self.assertEqual(ContactRequest.objects.count(), 1)
        self.assertEqual(ChatThread.objects.count(), 1)
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_chat_thread_detail_and_reply_are_available_to_participant(self):
        self.client.force_authenticate(self.user)
        contact_response = self.client.post(
            reverse("room-contact", args=[self.room.id]),
            format="json",
        )
        thread_id = contact_response.data["thread_id"]

        detail_response = self.client.get(reverse("chat-thread-detail", args=[thread_id]))

        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(detail_response.data["current_user_id"], self.user.id)
        self.assertEqual(len(detail_response.data["messages"]), 0)

        reply_response = self.client.post(
            reverse("chat-thread-messages", args=[thread_id]),
            {"body": "Tin nhắn tiếp theo."},
            format="json",
        )

        self.assertEqual(reply_response.status_code, 201)
        self.assertEqual(ChatMessage.objects.count(), 1)
