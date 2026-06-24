from types import SimpleNamespace

from django.contrib.gis.geos import Point
from django.test import TestCase, override_settings

from apps.dashboard.views import _apply_room_geocoding
from apps.listings.models import Room
from apps.locations.models import District, Landmark, Ward


class RoomGeocodingFallbackTests(TestCase):
    @override_settings(RENTIFY_GEOCODING_PROVIDER="disabled")
    def test_apply_room_geocoding_falls_back_to_local_street_match(self):
        district = District.objects.create(name="Hai Bà Trưng", code="HN-HBT")
        ward = Ward.objects.create(name="Bách Khoa", code="HN-HBT-BK", district=district)
        room = SimpleNamespace(
            address="01 Lê Thanh Nghị, phường Bách Khoa, quận Hai Bà Trưng, Hà Nội",
            ward=ward,
            ward_id=ward.id,
        )

        geocoded = _apply_room_geocoding(room)

        self.assertTrue(geocoded)
        self.assertEqual(room.location_status, Room.LocationStatus.GEOCODED)
        self.assertEqual(round(room.location.y, 4), 21.0049)
        self.assertIn("Lê Thanh Nghị", room.location_label)

    @override_settings(RENTIFY_GEOCODING_PROVIDER="disabled")
    def test_apply_room_geocoding_falls_back_to_ward_landmark(self):
        district = District.objects.create(name="Cầu Giấy", code="HN-CG")
        ward = Ward.objects.create(name="Dịch Vọng", code="HN-CG-DV", district=district)
        landmark = Landmark.objects.create(
            ward=ward,
            name="Đại học Quốc gia Hà Nội",
            type=Landmark.Type.UNIVERSITY,
            location=Point(105.7822, 21.0379, srid=4326),
        )
        room = SimpleNamespace(address="Ngõ 144 Xuân Thủy", ward=ward, ward_id=ward.id)

        geocoded = _apply_room_geocoding(room)

        self.assertTrue(geocoded)
        self.assertEqual(room.location_status, Room.LocationStatus.GEOCODED)
        self.assertEqual(room.location.x, landmark.location.x)
        self.assertIn("Ước lượng theo Dịch Vọng", room.location_label)
