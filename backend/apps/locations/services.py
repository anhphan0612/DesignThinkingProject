from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D

from .models import Landmark


LANDMARK_TYPE_PRIORITY = {
    Landmark.Type.UNIVERSITY: 0,
    Landmark.Type.BUS_STOP: 1,
    Landmark.Type.HOSPITAL: 2,
    Landmark.Type.PARK: 3,
    Landmark.Type.SHOPPING_MALL: 4,
}


def nearby_landmarks(point, *, limit=5, radius_km=2.5):
    if point is None:
        return []
    landmarks = (
        Landmark.objects.filter(is_active=True, location__distance_lte=(point, D(km=radius_km)))
        .select_related("ward__district")
        .annotate(distance=Distance("location", point))
    )
    ranked = sorted(
        landmarks,
        key=lambda item: (
            LANDMARK_TYPE_PRIORITY.get(item.type, 99),
            item.distance.km if item.distance else 999,
            item.name,
        ),
    )
    return ranked[:limit]
