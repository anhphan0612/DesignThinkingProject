from django.contrib.gis.geos import Point
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import LandlordProfile, User
from apps.listings.models import Room
from apps.locations.models import District, Ward


class LandlordChatInboxTests(TestCase):
    def test_landlord_dashboard_renders_chat_inbox_shell(self):
        landlord = User.objects.create_user(
            email="landlord-chat@example.com",
            password="password-123",
            full_name="Landlord Chat",
            role=User.Role.LANDLORD,
        )
        profile = LandlordProfile.objects.create(user=landlord)
        district = District.objects.create(name="Hai Ba Trung", code="hbt-chat")
        ward = Ward.objects.create(name="Bach Khoa", code="bk-chat", district=district)
        Room.objects.create(
            landlord=profile,
            ward=ward,
            title="Phong co inbox",
            address="1 Dai Co Viet",
            location=Point(105.84, 21.0, srid=4326),
            location_status=Room.LocationStatus.GEOCODED,
            price=2500000,
            area=20,
            max_occupants=2,
        )
        self.client.force_login(landlord)

        response = self.client.get(reverse("landlord-dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="landlordChatThreads"')
        self.assertContains(response, "Tin nhắn từ người thuê")
        self.assertContains(response, "landlord-chat.js")
