from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.locations.geocoding import build_room_location_query, geocode_room_address


class GeocodingTests(SimpleTestCase):
    def test_build_room_location_query_includes_ward_district_and_country(self):
        district = type("District", (), {"name": "Quận 1"})()
        ward = type("Ward", (), {"name": "Phường Bến Nghé", "district": district})()

        query = build_room_location_query(address="12 Lê Lợi", ward=ward)

        self.assertIn("12 Lê Lợi", query)
        self.assertIn("Phường Bến Nghé", query)
        self.assertIn("Quận 1", query)
        self.assertIn("Việt Nam", query)

    @override_settings(RENTIFY_GEOCODING_PROVIDER="disabled")
    def test_disabled_provider_returns_no_candidates(self):
        candidates = geocode_room_address(address="12 Lê Lợi", ward=None)

        self.assertEqual(candidates, [])


class GeocodingEndpointTests(TestCase):
    def test_geocode_endpoint_requires_address(self):
        response = self.client.get(reverse("ward-geocode"))

        self.assertEqual(response.status_code, 400)

    @override_settings(RENTIFY_GEOCODING_PROVIDER="disabled")
    def test_geocode_endpoint_returns_candidates_shape(self):
        response = self.client.get(reverse("ward-geocode"), {"address": "12 Lê Lợi"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"results": []})
