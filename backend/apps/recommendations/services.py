from decimal import Decimal

from django.contrib.gis.db.models.functions import Distance
from django.db.models import Count

from apps.listings.models import Room


def decimal_or_none(value):
    return Decimal(value) if value is not None else None


def clamp(value, minimum=0, maximum=1):
    return max(minimum, min(maximum, float(value)))


def budget_score(room, profile):
    budget_min = decimal_or_none(profile.budget_min)
    budget_max = decimal_or_none(profile.budget_max)
    price = room.price
    if budget_min is None and budget_max is None:
        return 0.65
    if budget_max is not None and price > budget_max:
        over_ratio = float((price - budget_max) / max(budget_max, Decimal("1")))
        return clamp(0.4 - over_ratio)
    if budget_min is not None and price < budget_min:
        under_ratio = float((budget_min - price) / max(budget_min, Decimal("1")))
        return clamp(0.85 - under_ratio / 2)
    if budget_min is not None and budget_max is not None:
        midpoint = (budget_min + budget_max) / 2
        half_range = max((budget_max - budget_min) / 2, Decimal("1"))
        return clamp(1 - float(abs(price - midpoint) / half_range * Decimal("0.35")))
    return 1


def distance_score(room, profile):
    distance = getattr(room, "distance", None)
    if not distance:
        return 0.55
    max_distance = float(profile.max_distance_km or 5)
    return clamp(1 - (distance.km / max_distance))


def area_score(room):
    return clamp(float(room.area) / 30)


def amenity_score(room):
    amenity_count = getattr(room, "amenity_count", None)
    if amenity_count is None:
        amenity_count = room.amenities.count()
    return clamp(amenity_count / 6)


def explain(room, scores):
    reasons = []
    if scores["budget"] >= 0.8:
        reasons.append("Gia phong phu hop voi ngan sach")
    if scores["distance"] >= 0.7:
        reasons.append("Gan truong ban dang quan tam")
    if scores["amenities"] >= 0.6:
        reasons.append("Co nhieu tien ich co ban")
    if scores["area"] >= 0.7:
        reasons.append("Dien tich kha rong")
    if not reasons:
        reasons.append("Phu hop tuong doi voi bo loc hien tai")
    return reasons


def recommended_rooms_for_student(user, limit=10):
    if not hasattr(user, "student_profile"):
        return []
    profile = user.student_profile
    queryset = (
        Room.objects.filter(status=Room.Status.ACTIVE, deleted_at__isnull=True)
        .select_related("landlord__user", "ward__district")
        .prefetch_related("amenities", "images")
        .annotate(amenity_count=Count("amenities", distinct=True))
    )
    if profile.university:
        queryset = queryset.annotate(distance=Distance("location", profile.university.location))

    ranked = []
    for room in queryset:
        scores = {
            "budget": budget_score(room, profile),
            "distance": distance_score(room, profile),
            "area": area_score(room),
            "amenities": amenity_score(room),
        }
        final_score = (
            0.40 * scores["budget"]
            + 0.30 * scores["distance"]
            + 0.15 * scores["amenities"]
            + 0.15 * scores["area"]
        )
        detail = {
            **scores,
            "reasons": explain(room, scores),
        }
        ranked.append((room, round(final_score, 6), detail))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked[:limit]
