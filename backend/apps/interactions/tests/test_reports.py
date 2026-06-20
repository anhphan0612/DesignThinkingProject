from django.test import TestCase
from django.urls import reverse
from django.contrib.gis.geos import Point

from apps.accounts.models import LandlordProfile, StudentProfile, User
from apps.interactions.models import ContentReport
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
        )

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
