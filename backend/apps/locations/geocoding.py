import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.cache import cache


@dataclass(frozen=True)
class GeocodeCandidate:
    latitude: Decimal
    longitude: Decimal
    label: str
    provider: str
    query: str


class GeocodingError(Exception):
    pass


def build_room_location_query(*, address, ward):
    parts = [address]
    if ward:
        parts.extend([ward.name, ward.district.name])
    parts.extend(["TP. Hồ Chí Minh", "Việt Nam"])
    return ", ".join(part.strip() for part in parts if part and part.strip())


def geocode_room_address(*, address, ward, limit=1):
    query = build_room_location_query(address=address, ward=ward)
    provider = settings.RENTIFY_GEOCODING_PROVIDER.lower()
    if provider in {"", "disabled", "none"}:
        return []
    if provider != "nominatim":
        raise GeocodingError(f"Unsupported geocoding provider: {provider}")
    return NominatimGeocoder().search(query=query, limit=limit)


class NominatimGeocoder:
    endpoint = "https://nominatim.openstreetmap.org/search"
    provider = "nominatim"

    def search(self, *, query, limit=1):
        cache_key = f"rentify:geocode:{self.provider}:{query}:{limit}"
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
