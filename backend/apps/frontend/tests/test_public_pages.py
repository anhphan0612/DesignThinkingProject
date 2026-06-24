from uuid import uuid4

from django.contrib.gis.geos import Point
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import LandlordProfile, StudentProfile, User
from apps.listings.models import Room
from apps.locations.models import District, Ward


class PublicFrontendPageTests(TestCase):
    def test_guest_public_pages_render_with_expected_static_assets(self):
        expectations = {
            "home": ("frontend/styles.css",),
            "room-search": ("frontend/styles.css", "frontend/app.js"),
            "roommate-home": ("frontend/styles.css", "frontend/roommates.js"),
            "landlord-home": ("frontend/landlord.css",),
        }

        for route_name, assets in expectations.items():
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))

                self.assertEqual(response.status_code, 200)
                for asset in assets:
                    self.assertContains(response, asset)

    def test_authenticated_users_are_routed_to_their_workspaces(self):
        student = self.user(User.Role.STUDENT)
        StudentProfile.objects.create(user=student)
        landlord = self.user(User.Role.LANDLORD)
        LandlordProfile.objects.create(user=landlord)
        staff = self.user(User.Role.ADMIN, is_staff=True)

        cases = [
            (student, "home", "room-search"),
            (landlord, "home", "landlord-dashboard"),
            (landlord, "room-search", "landlord-dashboard"),
            (landlord, "roommate-home", "landlord-dashboard"),
            (staff, "home", "moderation-dashboard"),
            (staff, "room-search", "moderation-dashboard"),
            (staff, "roommate-home", "moderation-dashboard"),
        ]

        for user, source, target in cases:
            with self.subTest(role=user.role, source=source):
                self.client.force_login(user)
                response = self.client.get(reverse(source))
                self.assertRedirects(response, reverse(target))
                self.client.logout()

    def test_room_detail_page_renders_core_frontend_hooks(self):
        room = self.room()

        response = self.client.get(reverse("frontend-room-detail", args=[room.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "frontend/detail.css")
        self.assertContains(response, "frontend/detail-map.js")
        self.assertContains(response, 'id="detailLeafletMap"')
        self.assertContains(response, 'id="nearbyLandmarksData"')

    def user(self, role, **extra):
        return User.objects.create_user(
            email=f"{role}-{uuid4().hex[:8]}@example.com",
            password="password-123",
            full_name=f"{role.title()} User",
            role=role,
            **extra,
        )

    def room(self):
        district = District.objects.create(name="QA District", code=f"qa-{uuid4().hex[:6]}")
        ward = Ward.objects.create(district=district, name="QA Ward", code=f"qa-{uuid4().hex[:6]}")
        landlord_user = self.user(User.Role.LANDLORD)
        landlord = LandlordProfile.objects.create(user=landlord_user, business_name="QA Homes")
        return Room.objects.create(
            landlord=landlord,
            ward=ward,
            title="QA room",
            description="A room for frontend QA.",
            address="1 QA Street",
            location=Point(105.8342, 21.0278, srid=4326),
            location_status=Room.LocationStatus.GEOCODED,
            price=2500000,
            area=22,
            max_occupants=2,
            status=Room.Status.ACTIVE,
        )
