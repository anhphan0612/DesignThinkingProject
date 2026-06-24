from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.locations.geocoding import (
    GeocodingError,
    build_room_location_queries,
    build_room_location_query,
    geocode_room_address,
)


class GeocodingTests(SimpleTestCase):
    def test_build_room_location_query_includes_ward_district_and_country(self):
        district = type("District", (), {"name": "Quận 1"})()
        ward = type("Ward", (), {"name": "Phường Bến Nghé", "district": district})()

        query = build_room_location_query(address="12 Lê Lợi", ward=ward)

        self.assertIn("12 Lê Lợi", query)
        self.assertIn("Phường Bến Nghé", query)
        self.assertIn("Quận 1", query)
        self.assertIn("Việt Nam", query)

    def test_build_room_location_query_deduplicates_full_hanoi_address(self):
        district = type("District", (), {"name": "Hai Bà Trưng"})()
        ward = type("Ward", (), {"name": "Bách Khoa", "district": district, "code": "HN-HBT-BK"})()

        query = build_room_location_query(
            address="01 Lê Thanh Nghị, phường Bách Khoa, quận Hai Bà Trưng, Hà Nội",
            ward=ward,
        )

        self.assertEqual(query.count("Bách Khoa"), 1)
        self.assertEqual(query.count("Hai Bà Trưng"), 1)
        self.assertEqual(query.count("Hà Nội"), 1)
        self.assertIn("Việt Nam", query)

    def test_build_room_location_queries_adds_short_street_variant(self):
        district = type("District", (), {"name": "Hai Bà Trưng"})()
        ward = type("Ward", (), {"name": "Bách Khoa", "district": district, "code": "HN-HBT-BK"})()

        queries = build_room_location_queries(
            address="01 Lê Thanh Nghị, phường Bách Khoa, quận Hai Bà Trưng, Hà Nội",
            ward=ward,
        )

        self.assertIn("01 Lê Thanh Nghị, Bách Khoa, Hai Bà Trưng, Hà Nội, Việt Nam", queries)

    @patch("apps.locations.geocoding.NominatimGeocoder.search", return_value=[])
    def test_le_thanh_nghi_uses_local_fallback_when_nominatim_is_empty(self, _search):
        district = type("District", (), {"name": "Hai Bà Trưng"})()
        ward = type("Ward", (), {"name": "Bách Khoa", "district": district, "code": "HN-HBT-BK"})()

        candidates = geocode_room_address(
            address="01 Lê Thanh Nghị, phường Bách Khoa, quận Hai Bà Trưng, Hà Nội",
            ward=ward,
        )

        self.assertEqual(candidates[0].provider, "local")
        self.assertEqual(str(candidates[0].latitude), "21.0049")

    @patch("apps.locations.geocoding.NominatimGeocoder.search", side_effect=GeocodingError("timeout"))
    def test_le_thanh_nghi_uses_local_fallback_when_nominatim_errors(self, _search):
        district = type("District", (), {"name": "Hai Bà Trưng"})()
        ward = type("Ward", (), {"name": "Bách Khoa", "district": district, "code": "HN-HBT-BK"})()

        candidates = geocode_room_address(
            address="01 Lê Thanh Nghị, phường Bách Khoa, quận Hai Bà Trưng, Hà Nội",
            ward=ward,
        )

        self.assertEqual(candidates[0].provider, "local")

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
