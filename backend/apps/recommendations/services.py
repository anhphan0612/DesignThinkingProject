from decimal import Decimal

from django.contrib.gis.db.models.functions import Distance
from django.db.models import Count, Q

from apps.interactions.models import ContentReport, Favorite, SearchLog
from apps.listings.models import Room, RoomImage
from apps.locations.models import Landmark
from apps.locations.services import nearby_landmarks

from .keywords import AMENITY_SYNONYMS, extract_keyword_intent
from .text import contains_any, normalize_text


WEIGHTS = {
    "budget": 0.25,
    "distance": 0.25,
    "district": 0.15,
    "amenities": 0.15,
    "landmarks": 0.10,
    "behavior": 0.05,
    "text": 0.05,
}

PROFILE_SIGNAL_FIELDS = (
    ("university", "Chọn trường để gợi ý theo khoảng cách"),
    ("budget", "Bổ sung ngân sách để xếp hạng giá tốt hơn"),
    ("preferred_districts", "Chọn khu vực ưu tiên"),
    ("lifestyle_tags", "Thêm thói quen sống để gợi ý ghép trọ tốt hơn"),
)


def decimal_or_none(value):
    return Decimal(value) if value is not None else None


def clamp(value, minimum=0, maximum=1):
    return max(minimum, min(maximum, float(value)))


def budget_score(room, profile):
    budget_min = decimal_or_none(profile.budget_min)
    budget_max = decimal_or_none(profile.budget_max)
    price = room.price
    if budget_min is None and budget_max is None:
        return 0.60
    if budget_max is not None and price > budget_max:
        over_ratio = float((price - budget_max) / max(budget_max, Decimal("1")))
        return clamp(0.45 - over_ratio)
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


def district_score(room, profile):
    preferred_ids = getattr(profile, "_preferred_district_ids", None)
    if preferred_ids is None:
        preferred_ids = set(profile.preferred_districts.values_list("id", flat=True))
        profile._preferred_district_ids = preferred_ids
    if not preferred_ids:
        return 0.55
    return 1 if room.ward.district_id in preferred_ids else 0.25


def amenity_score(room, intent=None):
    amenities = list(room.amenities.all())
    if not amenities:
        return 0.35
    baseline = clamp(len(amenities) / 6)
    if not intent or not intent.amenity_codes:
        return baseline
    names = " ".join(f"{amenity.name} {amenity.code}" for amenity in amenities)
    matched = 0
    for code in intent.amenity_codes:
        phrases = AMENITY_SYNONYMS.get(code, [code])
        if contains_any(names, phrases + [code]):
            matched += 1
    intent_score = matched / max(len(intent.amenity_codes), 1)
    return clamp((baseline * 0.4) + (intent_score * 0.6))


def _room_text(room):
    amenities = " ".join(amenity.name for amenity in room.amenities.all())
    return " ".join(
        [
            room.title,
            room.description,
            room.address,
            room.ward.name,
            room.ward.district.name,
            amenities,
        ]
    )


def text_score(room, intent):
    if not intent or not intent.has_signal:
        return 0.55
    normalized = normalize_text(_room_text(room))
    matched_terms = [term for term in intent.searchable_terms if term in normalized]
    matched_intents = 0
    for code in intent.amenity_codes:
        phrases = AMENITY_SYNONYMS.get(code, [code])
        if contains_any(normalized, phrases + [code]):
            matched_intents += 1
    signal_count = len(intent.searchable_terms) + len(intent.amenity_codes)
    if signal_count == 0:
        return 0.55
    return clamp((len(matched_terms) + matched_intents) / signal_count)


def _favorite_signals(user):
    favorite_rooms = (
        Favorite.objects.filter(user=user)
        .select_related("room__ward__district")
        .prefetch_related("room__amenities")
        .order_by("-created_at")[:20]
    )
    district_ids = set()
    amenity_ids = set()
    price_values = []
    for favorite in favorite_rooms:
        district_ids.add(favorite.room.ward.district_id)
        amenity_ids.update(favorite.room.amenities.values_list("id", flat=True))
        price_values.append(favorite.room.price)
    return district_ids, amenity_ids, price_values


def behavior_score(room, behavior):
    favorite_district_ids, favorite_amenity_ids, favorite_prices = behavior
    score = 0.45
    if favorite_district_ids and room.ward.district_id in favorite_district_ids:
        score += 0.25
    room_amenity_ids = set(room.amenities.values_list("id", flat=True))
    if favorite_amenity_ids and room_amenity_ids.intersection(favorite_amenity_ids):
        score += 0.20
    if favorite_prices:
        average = sum(favorite_prices) / len(favorite_prices)
        if average:
            score += clamp(1 - abs(float(room.price - average) / float(average))) * 0.10
    return clamp(score)


def profile_quality(profile):
    missing = []
    if not profile.university_id:
        missing.append(PROFILE_SIGNAL_FIELDS[0][1])
    if profile.budget_min is None and profile.budget_max is None:
        missing.append(PROFILE_SIGNAL_FIELDS[1][1])
    if not profile.preferred_districts.exists():
        missing.append(PROFILE_SIGNAL_FIELDS[2][1])
    if not profile.lifestyle_tags.exists():
        missing.append(PROFILE_SIGNAL_FIELDS[3][1])
    return {
        "is_cold_start": len(missing) >= 3,
        "missing": missing,
        "completion": round((len(PROFILE_SIGNAL_FIELDS) - len(missing)) / len(PROFILE_SIGNAL_FIELDS), 2),
    }


def room_quality_score(room):
    score = 1
    if room.location_status != Room.LocationStatus.GEOCODED:
        score -= 0.25
    if getattr(room, "approved_image_count", 0) <= 0:
        score -= 0.35
    if getattr(room, "open_report_count", 0) > 0:
        score -= 0.40
    return clamp(score)


def landmark_score(room, intent=None):
    landmarks = nearby_landmarks(room.location, limit=6, radius_km=2.5)
    room.nearby_landmarks_cache = landmarks
    if not landmarks:
        return 0.35
    baseline = clamp(len(landmarks) / 5)
    if not intent:
        return baseline
    desired_types = set()
    if "near_school" in intent.matched_intents:
        desired_types.add(Landmark.Type.UNIVERSITY)
    if "near_park" in intent.matched_intents:
        desired_types.add(Landmark.Type.PARK)
    if "near_bus" in intent.matched_intents:
        desired_types.add(Landmark.Type.BUS_STOP)
    if "near_hospital" in intent.matched_intents:
        desired_types.add(Landmark.Type.HOSPITAL)
    if "near_mall" in intent.matched_intents or "near_center" in intent.matched_intents:
        desired_types.add(Landmark.Type.SHOPPING_MALL)
    if not desired_types:
        return baseline
    matched = sum(1 for landmark in landmarks if landmark.type in desired_types)
    return clamp((baseline * 0.35) + ((matched / len(desired_types)) * 0.65))


def explain(room, scores, intent):
    reasons = []
    if scores["budget"] >= 0.80:
        reasons.append("Hợp ngân sách")
    if scores["distance"] >= 0.70:
        reasons.append("Gần trường")
    if scores["district"] >= 0.90:
        reasons.append("Đúng khu vực ưu tiên")
    if scores["amenities"] >= 0.70:
        reasons.append("Tiện ích khớp nhu cầu")
    if scores["behavior"] >= 0.70:
        reasons.append("Tương tự phòng đã lưu")
    if intent and intent.matched_intents:
        if "quiet" in intent.matched_intents:
            reasons.append("Phù hợp nhu cầu yên tĩnh")
        if "spacious" in intent.matched_intents and room.area >= 20:
            reasons.append("Diện tích thoải mái")
    if scores.get("quality", 1) >= 0.95:
        reasons.append("Tin đăng đủ ảnh và vị trí")
    if scores.get("landmarks", 0) >= 0.70:
        reasons.append("Gần địa điểm quan trọng")
    if not reasons:
        reasons.append("Phù hợp tương đối với hồ sơ")
    return reasons[:4]


def _recent_search_intent(user, explicit_query=""):
    if explicit_query:
        return extract_keyword_intent(explicit_query)
    latest = SearchLog.objects.filter(user=user).exclude(query_text="").order_by("-created_at").first()
    return extract_keyword_intent(latest.query_text if latest else "")


def recommended_rooms_for_student(user, limit=10, query=""):
    if not hasattr(user, "student_profile"):
        return []
    profile = user.student_profile
    intent = _recent_search_intent(user, explicit_query=query)
    behavior = _favorite_signals(user)
    profile_meta = profile_quality(profile)
    queryset = (
        Room.objects.filter(status=Room.Status.ACTIVE, deleted_at__isnull=True)
        .select_related("landlord__user", "ward__district")
        .prefetch_related("amenities", "images")
        .annotate(
            amenity_count=Count("amenities", distinct=True),
            approved_image_count=Count(
                "images",
                filter=Q(images__status=RoomImage.ModerationStatus.APPROVED),
                distinct=True,
            ),
            open_report_count=Count(
                "reports",
                filter=Q(reports__status=ContentReport.Status.OPEN),
                distinct=True,
            ),
        )
        .filter(
            location_status=Room.LocationStatus.GEOCODED,
            approved_image_count__gt=0,
            open_report_count=0,
        )
    )
    if profile.university:
        queryset = queryset.annotate(distance=Distance("location", profile.university.location))

    ranked = []
    for room in queryset[:200]:
        scores = {
            "budget": budget_score(room, profile),
            "distance": distance_score(room, profile),
            "district": district_score(room, profile),
            "amenities": amenity_score(room, intent),
            "landmarks": landmark_score(room, intent),
            "behavior": behavior_score(room, behavior),
            "text": text_score(room, intent),
            "quality": room_quality_score(room),
        }
        final_score = sum(WEIGHTS[key] * scores[key] for key in WEIGHTS) * scores["quality"]
        detail = {
            **scores,
            "weights": WEIGHTS,
            "reasons": explain(room, scores, intent),
            "matched_intents": intent.matched_intents,
            "matched_amenities": intent.amenity_codes,
            "fallback_used": intent.fallback_used,
            "profile": profile_meta,
        }
        ranked.append((room, round(final_score, 6), detail))

    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked[:limit]
