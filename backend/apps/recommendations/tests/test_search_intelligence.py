from django.contrib.gis.geos import Point
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import LandlordProfile, StudentProfile, User
from apps.interactions.models import ContentReport
from apps.listings.models import Amenity, Room, RoomImage
from apps.locations.models import District, University, Ward
from apps.recommendations.keywords import apply_room_keyword_search, extract_keyword_intent
from apps.recommendations.text import normalize_text


class SearchIntelligenceTests(TestCase):
    def setUp(self):
        self.district = District.objects.create(name="Quận Bình Thạnh", code="bt-s7")
        self.ward = Ward.objects.create(name="Phường 25", code="p25-s7", district=self.district)
        self.university = University.objects.create(
            name="Đại học Kiểm thử",
            short_name="UT",
            location=Point(106.714, 10.801, srid=4326),
        )
        landlord_user = User.objects.create_user(
            email="landlord-s7@example.com",
            password="password-123",
            full_name="Chủ trọ Sprint 7",
            role=User.Role.LANDLORD,
        )
        self.landlord = LandlordProfile.objects.create(user=landlord_user)
        self.wifi = Amenity.objects.create(name="Wifi", code="wifi-s7")
        self.parking = Amenity.objects.create(name="Chỗ để xe", code="parking-s7")
        self.room = Room.objects.create(
            landlord=self.landlord,
            ward=self.ward,
            title="Phòng yên tĩnh có wifi",
            description="Phù hợp sinh viên cần học tập.",
            address="12 Đường D1",
            location=Point(106.714, 10.801, srid=4326),
            location_status=Room.LocationStatus.GEOCODED,
            price=2800000,
            area=22,
            max_occupants=2,
            status=Room.Status.ACTIVE,
        )
        self.room.amenities.set([self.wifi, self.parking])
        RoomImage.objects.create(
            room=self.room,
            image="rooms/sprint-8.jpg",
            uploaded_by=landlord_user,
            source=RoomImage.Source.LANDLORD,
            status=RoomImage.ModerationStatus.APPROVED,
            is_cover=True,
        )
        self.user = User.objects.create_user(
            email="student-s7@example.com",
            password="password-123",
            full_name="Sinh viên Sprint 7",
            role=User.Role.STUDENT,
        )
        self.profile = StudentProfile.objects.create(
            user=self.user,
            university=self.university,
            budget_min=2000000,
            budget_max=3500000,
            max_distance_km=5,
        )
        self.profile.preferred_districts.add(self.district)

    def test_normalize_vietnamese_text(self):
        self.assertEqual(normalize_text("Phòng trọ yên tĩnh gần ĐH"), "phong tro yen tinh gan dh")

    def test_extract_keyword_intent_understands_synonyms(self):
        intent = extract_keyword_intent("cần phòng yên tĩnh có mạng và chỗ để xe")

        self.assertIn("quiet", intent.matched_intents)
        self.assertIn("wifi", intent.amenity_codes)
        self.assertIn("parking", intent.amenity_codes)

    def test_weird_keyword_falls_back_without_emptying_results(self):
        result = apply_room_keyword_search(Room.objects.filter(pk=self.room.pk), "zzzxqv la hoac")

        self.assertTrue(result.intent.fallback_used)
        self.assertEqual(list(result.queryset), [self.room])

    def test_recommendation_api_returns_reasons(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("recommendations"), {"q": "wifi yên tĩnh"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["room"]["id"], self.room.id)
        self.assertIn("reasons", response.json()[0]["score_detail"])
        self.assertIn("quiet", response.json()[0]["score_detail"]["matched_intents"])

    def test_recommendations_skip_rooms_without_approved_images(self):
        self.room.images.all().delete()
        self.client.force_login(self.user)

        response = self.client.get(reverse("recommendations"), {"q": "wifi"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_recommendations_skip_open_reported_rooms(self):
        ContentReport.objects.create(
            target_type=ContentReport.TargetType.ROOM,
            room=self.room,
            reason="Thông tin cần kiểm tra",
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse("recommendations"), {"q": "wifi"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])
