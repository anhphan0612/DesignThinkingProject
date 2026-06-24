import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache

LOCAL_GEOCODE_FALLBACKS = (
    {
        "tokens": ("le thanh nghi",),
        "context_tokens": ("bach khoa", "hai ba trung"),
        "latitude": Decimal("21.0049"),
        "longitude": Decimal("105.8455"),
        "label": "Ước lượng khu vực Lê Thanh Nghị, Bách Khoa, Hai Bà Trưng, Hà Nội",
    },
)


@dataclass(frozen=True)
class GeocodeCandidate:
    latitude: Decimal
    longitude: Decimal
    label: str
    provider: str
    query: str


class GeocodingError(Exception):
    pass


def _search_key(value):
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    ascii_text = ascii_text.lower()
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


def _append_location_part(parts, part):
    key = _search_key(part)
    if not key:
        return
    existing = _search_key(", ".join(parts))
    if key not in existing:
        parts.append(part)


def build_room_location_query(*, address, ward):
    parts = [address]
    if ward:
        _append_location_part(parts, ward.name)
        _append_location_part(parts, ward.district.name)
    _append_location_part(parts, room_location_city(ward=ward))
    _append_location_part(parts, "Việt Nam")
    return ", ".join(part.strip() for part in parts if part and part.strip())


def room_location_city(*, ward):
    ward_code = getattr(ward, "code", "") if ward else ""
    district_code = getattr(getattr(ward, "district", None), "code", "") if ward else ""
    if ward_code.startswith("HN-") or district_code.startswith("HN-"):
        return "Hà Nội"
    return "Hà Nội"


def build_room_location_queries(*, address, ward):
    queries = [build_room_location_query(address=address, ward=ward)]
    street_address = (address or "").split(",")[0].strip()
    if street_address and ward:
        short_parts = [street_address, ward.name, ward.district.name, room_location_city(ward=ward), "Việt Nam"]
        short_query = ", ".join(part.strip() for part in short_parts if part and part.strip())
        if short_query not in queries:
            queries.append(short_query)
    return queries


def local_geocode_room_address(*, address, ward):
    query = build_room_location_query(address=address, ward=ward)
    lookup = _search_key(query)
    for fallback in LOCAL_GEOCODE_FALLBACKS:
        has_street = all(token in lookup for token in fallback["tokens"])
        has_context = any(token in lookup for token in fallback["context_tokens"])
        if has_street and has_context:
            return [
                GeocodeCandidate(
                    latitude=fallback["latitude"],
                    longitude=fallback["longitude"],
                    label=fallback["label"],
                    provider="local",
                    query=query,
                )
            ]
    return []


def geocode_room_address(*, address, ward, limit=1):
    provider = settings.RENTIFY_GEOCODING_PROVIDER.lower()
    if provider in {"", "disabled", "none"}:
        return []
    if provider != "nominatim":
        raise GeocodingError(f"Unsupported geocoding provider: {provider}")
    geocoder = NominatimGeocoder()
    errors = []
    for query in build_room_location_queries(address=address, ward=ward):
        try:
            candidates = geocoder.search(query=query, limit=limit)
        except GeocodingError as exc:
            errors.append(exc)
            continue
        if candidates:
            return candidates
    local_candidates = local_geocode_room_address(address=address, ward=ward)
    if local_candidates:
        return local_candidates[:limit]
    if errors:
        raise errors[0]
    return []


class NominatimGeocoder:
    endpoint = "https://nominatim.openstreetmap.org/search"
    provider = "nominatim"

    def search(self, *, query, limit=1):
        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
        cache_key = f"rentify:geocode:{self.provider}:{query_hash}:{limit}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        params = urlencode(
            {
                "format": "jsonv2",
                "q": query,
                "limit": limit,
                "addressdetails": 1,
                "countrycodes": settings.RENTIFY_GEOCODING_COUNTRY_CODES,
            }
        )
        request = Request(
            f"{self.endpoint}?{params}",
            headers={
                "User-Agent": settings.RENTIFY_GEOCODING_USER_AGENT,
                "Accept": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=settings.RENTIFY_GEOCODING_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise GeocodingError("Không thể gọi dịch vụ bản đồ lúc này.") from exc

        candidates = []
        for item in payload:
            try:
                latitude = Decimal(str(item["lat"]))
                longitude = Decimal(str(item["lon"]))
            except (KeyError, InvalidOperation):
                continue
            candidates.append(
                GeocodeCandidate(
                    latitude=latitude,
                    longitude=longitude,
                    label=item.get("display_name", query),
                    provider=self.provider,
                    query=query,
                )
            )

        cache.set(cache_key, candidates, settings.RENTIFY_GEOCODING_CACHE_SECONDS)
        return candidates
