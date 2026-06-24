from django.contrib.gis.geos import Point
from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models import LandlordProfile, User
from apps.listings.models import Room
from apps.locations.models import District, Landmark, Ward
from apps.locations.services import nearby_landmarks


class LandmarkTests(TestCase):
    def test_nearby_landmarks_returns_supported_types(self):
        district = District.objects.create(name="Cầu Giấy", code="test-cg")
        ward = Ward.objects.create(name="Dịch Vọng Hậu", code="test-dvh", district=district)
        landmark = Landmark.objects.create(
            name="Công viên test",
            type=Landmark.Type.PARK,
            ward=ward,
            location=Point(105.79, 21.03, srid=4326),
        )

        results = nearby_landmarks(Point(105.7902, 21.0302, srid=4326), limit=3)

        self.assertEqual(results, [landmark])
        self.assertEqual(results[0].type, Landmark.Type.PARK)

    def test_hanoi_seed_creates_landmarks_and_geocoded_rooms(self):
        call_command("seed_hanoi_demo_data", verbosity=0)

        self.assertGreaterEqual(Landmark.objects.count(), 20)
        self.assertGreaterEqual(
            Room.objects.filter(status=Room.Status.ACTIVE, location_status=Room.LocationStatus.GEOCODED).count(),
            10,
        )
        self.assertTrue(Landmark.objects.filter(type=Landmark.Type.SHOPPING_MALL).exists())

    def test_room_api_includes_nearby_landmarks(self):
        district = District.objects.create(name="Hai Bà Trưng", code="test-hbt")
        ward = Ward.objects.create(name="Bách Khoa", code="test-bk", district=district)
        landmark = Landmark.objects.create(
            name="Đại học test",
            type=Landmark.Type.UNIVERSITY,
            ward=ward,
            location=Point(105.8435, 21.0059, srid=4326),
        )
        landlord_user = User.objects.create_user(
            email="landmark-landlord@example.com",
            password="password-123",
            full_name="Landmark Landlord",
            role=User.Role.LANDLORD,
        )
        landlord = LandlordProfile.objects.create(user=landlord_user)
        room = Room.objects.create(
            landlord=landlord,
            ward=ward,
            title="Phòng gần landmark",
            description="",
            address="1 Đại Cồ Việt",
            location=Point(105.8436, 21.0060, srid=4326),
            location_status=Room.LocationStatus.GEOCODED,
            price=3000000,
            area=20,
            max_occupants=2,
            status=Room.Status.ACTIVE,
        )

        response = self.client.get("/api/rooms/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["results"][0]
        self.assertEqual(payload["id"], room.id)
        self.assertEqual(payload["nearby_landmarks"][0]["name"], landmark.name)
